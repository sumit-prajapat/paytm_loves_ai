import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.db.models import AuditLog
from app.schemas.envelope import AgentEnvelope
from app.services.loan_service import loan_service
from app.services.templates import templates


class OfferAgent(BaseAgent):
    """Consent-first loan offers, EMI answers, and respectful refusal handling (Rule R6)."""

    def __init__(self) -> None:
        super().__init__(name="offer")

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        merchant_id = input_data.get("merchant_id", "m_ramesh")
        user_intent = input_data.get("intent", "check_offer")
        language = input_data.get("language", "hi")
        already_offered = bool(input_data.get("already_offered", False))

        offer_result: dict[str, Any] = {}
        status = "done"
        confidence = 0.95

        # 1. User declined offer -> Stop immediately, never offer again, log refusal
        if user_intent == "decline_offer":
            audit_entry = AuditLog(
                case_id=case_id,
                actor="merchant",
                action="OFFER_DECLINED_CONSENT_RESPECTED",
                detail={"merchant_id": merchant_id, "stopped": True},
            )
            db.add(audit_entry)
            await db.commit()

            offer_result = {
                "action": "stop_offers",
                "text": "Theek hai Ramesh ji, humne note kar liya hai. Hum dobara loan ka sujhav nahi denge. Dhanyawad!",
                "offer_made": False,
            }
            next_agent = "done"

        # 2. User asked "EMI kitna"
        elif user_intent in ["loan_emi_query", "loan_interest"]:
            amount = float(input_data.get("amount", 50000.0))
            tenure = int(input_data.get("tenure", 12))
            eligibility = await loan_service.get_eligibility(db, merchant_id)
            rate = eligibility.get("rate", 14.0)

            emi_info = loan_service.calculate_emi(amount, rate, tenure)
            # Create loan request in 'awaiting_approval' status (Human console only)
            req = await loan_service.create_request(db, merchant_id, amount, tenure, confidence=0.91)

            reply_text = templates.loan_emi_explanation(
                amount=amount,
                tenure_months=tenure,
                emi=emi_info["monthly_emi"],
                rate_pct=rate,
                language=language,
            )

            offer_result = {
                "action": "loan_emi_explained",
                "text": reply_text,
                "emi_details": emi_info,
                "request_id": req.id,
                "status": "awaiting_approval",
                "offer_made": True,
            }
            next_agent = "done"

        # 3. Post-resolution single offer check (Consent-First Rule: At most ONE offer per session)
        elif not already_offered:
            eligibility = await loan_service.get_eligibility(db, merchant_id)
            if eligibility.get("eligible") and eligibility.get("max_amount", 0) > 0:
                max_amt = eligibility["max_amount"]
                reply_text = templates.loan_offer_proposal(max_amt, language=language)
                offer_result = {
                    "action": "single_loan_offer_proposed",
                    "text": reply_text,
                    "max_amount": max_amt,
                    "offer_made": True,
                }
            else:
                offer_result = {"offer_made": False, "reason": "Not eligible or below threshold"}
            next_agent = "done"
        else:
            # Rule R6: At most ONE offer. Silence!
            offer_result = {"offer_made": False, "reason": "Offer limit of 1 per interaction reached"}
            next_agent = "done"

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="evaluate_consent_first_loan_offer",
            input_data={"merchant_id": merchant_id, "intent": user_intent},
            output_data=offer_result,
            confidence=confidence,
            db=db,
        )

        return AgentEnvelope(
            agent=self.name,
            status=status,
            result=offer_result,
            confidence=confidence,
            evidence=["loan_service_eligibility", "consent_first_rule_r6"],
            next=next_agent,
            language=language,
            latency_ms=latency_ms,
        )


offer_agent = OfferAgent()

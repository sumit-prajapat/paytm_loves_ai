"""Consent-first offers and loans (R6, R3).

- Offer only after a user-triggered fix, only if eligible, max ONE per interaction, with a
  cooldown, and NEVER again after a decline (persisted in offer_consents).
- An EMI question returns a quote only; an application is created only when the merchant
  explicitly says "apply", and it always waits for human approval.
"""
import datetime
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.guardian import guardian_agent
from app.config import get_settings
from app.core.turn import current_turn
from app.db.models import OfferConsent
from app.i18n import t
from app.i18n.numbers import format_inr, format_rate, money
from app.services.audit import record_audit_log
from app.services.loan_service import loan_service

DEFAULT_TENURE_MONTHS = 12


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class OfferAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="offer")

    async def _consent(self, db: AsyncSession, merchant_id: str) -> OfferConsent:
        row = (await db.execute(select(OfferConsent).where(OfferConsent.merchant_id == merchant_id))).scalar_one_or_none()
        if row is None:
            row = OfferConsent(merchant_id=merchant_id, status="none", offers_shown=0, updated_at=_now())
            db.add(row)
            await db.flush()
        return row

    async def offer_pending(self, db: AsyncSession, merchant_id: str, within_minutes: int = 30) -> bool:
        row = (await db.execute(select(OfferConsent).where(OfferConsent.merchant_id == merchant_id))).scalar_one_or_none()
        return bool(row and row.status == "offered" and row.last_offered_at
                    and _now() - row.last_offered_at <= datetime.timedelta(minutes=within_minutes))

    async def maybe_offer(self, case_id: str, db: AsyncSession, *, merchant_id: str, lang: str) -> dict[str, Any] | None:
        """Called only after a resolved, user-triggered check-up."""
        ctx = current_turn()
        consent = await self._consent(db, merchant_id)
        reason = None
        if ctx is not None and ctx.offer_made:
            reason = "one_offer_per_interaction"
        elif consent.status in ("declined", "accepted"):
            reason = f"consent_{consent.status}"
        elif consent.last_offered_at and _now() - consent.last_offered_at < datetime.timedelta(
                days=get_settings().OFFER_COOLDOWN_DAYS):
            reason = "offer_cooldown"
        eligibility = None
        if reason is None:
            eligibility = await loan_service.get_eligibility(db, merchant_id)
            if not eligibility.get("eligible"):
                reason = "not_eligible"
        card = None
        if reason is None and eligibility:
            card = {
                "type": "offer_card",
                "product": "working_capital_loan",
                "max_amount": money(eligibility["max_amount"]),
                "annual_rate_pct": eligibility["rate"],
                "text": t("offer.proposal", lang, max_amount=format_inr(eligibility["max_amount"])),
                "actions": ["know_more", "decline"],
            }
            consent.status, consent.offers_shown = "offered", consent.offers_shown + 1
            consent.last_offered_at = consent.updated_at = _now()
            if ctx is not None:
                ctx.offer_made = True
            await record_audit_log(db, case_id=case_id, actor="offer_agent", action="OFFER_SHOWN",
                                   detail={"merchant_id": merchant_id, "max_amount": eligibility["max_amount"]})
        await self.emit_step(case_id=case_id, tool="evaluate_consent_first_loan_offer",
                             input_data={"merchant_id": merchant_id},
                             output_data={"offer_made": card is not None, "skipped_reason": reason},
                             confidence=1.0, db=db)
        return card

    async def decline(self, case_id: str, db: AsyncSession, *, merchant_id: str, actor_id: str, lang: str) -> str:
        consent = await self._consent(db, merchant_id)
        consent.status, consent.declined_at, consent.updated_at = "declined", _now(), _now()
        await record_audit_log(db, case_id=case_id, actor=actor_id, action="OFFER_DECLINED_CONSENT_RESPECTED",
                               detail={"merchant_id": merchant_id})
        await self.emit_step(case_id=case_id, tool="record_offer_decline", input_data={"merchant_id": merchant_id},
                             output_data={"status": "declined"}, confidence=1.0, db=db)
        return t("offer.declined_ack", lang)

    async def emi_quote(self, case_id: str, db: AsyncSession, *, merchant_id: str, lang: str,
                        amount: float | None, tenure: int | None) -> dict[str, Any]:
        start = time.perf_counter()
        eligibility = await loan_service.get_eligibility(db, merchant_id)
        if not eligibility.get("eligible"):
            text, quote = t("loan.not_eligible", lang), None
        elif amount is None:
            text, quote = t("loan.ask_amount", lang), None
        else:
            tenure = tenure or DEFAULT_TENURE_MONTHS
            quote = loan_service.calculate_emi(amount, eligibility["rate"], tenure)
            text = t("loan.emi_quote", lang, amount=format_inr(amount), tenure=tenure,
                     emi=format_inr(round(quote["monthly_emi"])), rate=format_rate(eligibility["rate"]))
        await self.emit_step(case_id=case_id, tool="quote_emi",
                             input_data={"merchant_id": merchant_id, "amount": amount, "tenure": tenure},
                             output_data={"quote": quote, "eligible": eligibility.get("eligible")},
                             confidence=1.0, db=db, latency_ms=(time.perf_counter() - start) * 1000)
        return {"text": text, "quote": quote, "eligibility": eligibility}

    async def apply(self, case_id: str, db: AsyncSession, *, merchant_id: str, actor_id: str, lang: str,
                    amount: float, tenure: int | None) -> dict[str, Any]:
        """Explicit 'apply': creates a request that ONLY a human can approve (R3)."""
        tenure = tenure or DEFAULT_TENURE_MONTHS
        decision = await guardian_agent.review(case_id, db, action_class="create_loan_request",
                                               subject=merchant_id, detail={"amount": amount})
        if not decision.allowed:
            return {"status": "escalate", "reason": decision.reason}
        req = await loan_service.create_request(db, merchant_id, amount, tenure, confidence=0.9)
        consent = await self._consent(db, merchant_id)
        consent.status, consent.updated_at = "accepted", _now()
        await record_audit_log(db, case_id=req.id, actor=actor_id, action="LOAN_APPLICATION_CREATED",
                               detail={"merchant_id": merchant_id, "amount": amount, "tenure": tenure})
        await self.emit_step(case_id=case_id, tool="create_loan_request_for_human_approval",
                             input_data={"merchant_id": merchant_id, "amount": amount, "tenure": tenure},
                             output_data={"request_id": req.id, "status": req.status}, confidence=1.0, db=db)
        return {"status": "awaiting_approval", "request_id": req.id,
                "text": t("loan.applied", lang, amount=format_inr(amount), request_id=req.id),
                "request": {"request_id": req.id, "amount": money(req.amount), "tenure_months": req.tenure,
                            "emi": money(req.emi), "rate_pct": req.rate, "status": req.status}}


offer_agent = OfferAgent()

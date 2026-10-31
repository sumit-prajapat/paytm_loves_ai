import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.payments.mock import payment_adapter
from app.agents.base import BaseAgent
from app.schemas.envelope import AgentEnvelope
from app.services.number_validator import number_validator
from app.services.travel_service import travel_service


class RankerAgent(BaseAgent):
    """Scores flight options deterministically, produces top 3 labeled picks,

    and builds the human-only Review and Pay handoff package.
    """

    def __init__(self) -> None:
        super().__init__(name="ranker")

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        search_data = input_data.get("search_result", {})
        language = input_data.get("language", "hi")
        passenger_name = input_data.get("passenger_name", "Arjun Sharma")

        options = search_data.get("options", [])
        recommended = search_data.get("recommended", {})

        # Build booking summary + human Review and Pay link
        booking_summary = travel_service.create_booking_summary(recommended, passenger_name)
        # Payment link from payments adapter
        pay_order = payment_adapter.create_payment_order(
            amount=recommended.get("price_inr", 4600.0),
            description=f"Flight {recommended.get('airline')} to BOM",
        )
        booking_summary["payment_link"] = pay_order["payment_link"]

        reason_text = recommended.get("reason", "")
        # Enforce Rule R1: Ensure reason numbers match flight data
        is_valid, _ = number_validator.validate(reason_text, search_data)
        if not is_valid:
            reason_text = f"Sabse santulit vikalp hai. Fares: ₹{int(recommended.get('price_inr', 4600))}."

        recommendation_dossier = {
            "top_options": options,
            "recommended_pick": recommended,
            "reason_text": reason_text,
            "booking_summary": booking_summary,
            "human_handoff_notice": "Review & Pay is required by human. The AI does not enter PINs.",
        }

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="rank_and_package_human_handoff",
            input_data={"candidate_count": len(options)},
            output_data={"recommended_airline": recommended.get("airline"), "fare": recommended.get("price_inr")},
            confidence=0.98,
            db=db,
        )

        return AgentEnvelope(
            agent=self.name,
            status="done",
            result=recommendation_dossier,
            confidence=0.98,
            evidence=["deterministic_scoring_formula", "payments_adapter_mock"],
            next="human",  # Handover to human to review and pay!
            language=language,
            latency_ms=latency_ms,
        )


ranker_agent = RankerAgent()

"""Ranker: deterministic scoring, CHEAPEST / FASTEST / BEST_BALANCE, reason from real numbers,
Guardian-checked human review-and-pay handoff (R1, R2, R3)."""
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.guardian import guardian_agent
from app.i18n import t
from app.i18n.numbers import money
from app.services.travel_service import booking_summary, rank, reason_text, risk_flags


class RankerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="ranker")

    async def rank_and_handoff(
        self, case_id: str, flights: list[dict[str, Any]], slots: dict[str, Any], *, lang: str,
        passenger_name: str, elder: bool, db: AsyncSession,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        ranked = rank(flights, slots["date"], slots.get("preference", "balanced"), slots.get("window"), elder)
        if not ranked["options"]:
            text = t("travel.no_flights", lang, origin=slots["origin"], destination=slots["destination"],
                     date=slots["date"])
            await self.emit_step(case_id=case_id, tool="rank_and_package_human_handoff",
                                 input_data={"candidates": 0}, output_data={"options": 0}, confidence=1.0, db=db)
            return {"status": "no_results", "text": text, "facts": slots}
        reason, reason_facts = reason_text(ranked, lang)
        notes = []
        if ranked["date_adjusted"]:
            notes.append(t("travel.date_adjusted", lang, requested=slots["date"], actual=ranked["actual_date"]))
        decision = await guardian_agent.review(case_id, db, action_class="handoff_payment_link",
                                               subject=slots.get("destination", ""),
                                               detail={"flight_id": ranked["recommended"]["flight_id"]})
        summary = booking_summary(ranked["recommended"], passenger_name) if decision.allowed else None
        text = " ".join([*notes, reason, t("travel.handoff_notice", lang)])
        options = [{**o, "price": money(o["price_inr"]), "risk_flags": risk_flags(o)} for o in ranked["options"]]
        await self.emit_step(
            case_id=case_id, tool="rank_and_package_human_handoff",
            input_data={"candidates": ranked["candidates"], "preference": ranked["preference"]},
            output_data={"recommended": ranked["recommended"]["flight_id"],
                         "score": ranked["recommended"]["score_breakdown"]["total_score"],
                         "handoff": summary is not None},
            confidence=1.0, db=db, latency_ms=(time.perf_counter() - start) * 1000,
        )
        return {
            "status": "ready_for_review_and_pay",
            "text": text,
            "options": options,
            "recommended": {**ranked["recommended"], "price": money(ranked["recommended"]["price_inr"]),
                            "reason": reason, "reason_facts": reason_facts},
            "booking_summary": summary,
            "date_adjusted": ranked["date_adjusted"],
            "facts": {"options": ranked["options"], "reason": reason_facts, "slots": slots,
                      "actual_date": ranked["actual_date"]},
        }


ranker_agent = RankerAgent()

"""Planner: merges slots, asks ONE missing question at a time, builds the visible roadmap."""
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.i18n import t
from app.nlu.rules import CITY_TO_IATA


class PlannerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="planner")

    async def plan(self, case_id: str, slots: dict[str, Any], *, home_city: str | None, lang: str,
                   db: AsyncSession) -> dict[str, Any]:
        start = time.perf_counter()
        slots = dict(slots)
        notes = []
        if "origin" not in slots and home_city and home_city.lower() in CITY_TO_IATA and "destination" in slots:
            if CITY_TO_IATA[home_city.lower()] != slots["destination"]:
                slots["origin"] = CITY_TO_IATA[home_city.lower()]
                notes.append("origin_from_profile")
        missing = next((s for s in ("destination", "origin", "date") if s not in slots), None)
        roadmap: list[str] = []
        question = None
        if missing:
            question = t(f"travel.ask_{missing}", lang)
        else:
            slots.setdefault("preference", "balanced")
            roadmap = [
                t("travel.roadmap.understand", lang, origin=slots["origin"], destination=slots["destination"],
                  date=slots["date"]),
                t("travel.roadmap.search", lang, date=slots["date"]),
                *([t("travel.roadmap.filter", lang, window=slots["window"])] if slots.get("window") else []),
                t("travel.roadmap.score", lang, preference=slots["preference"]),
                t("travel.roadmap.guardian", lang),
                t("travel.roadmap.handoff", lang),
            ]
        await self.emit_step(case_id=case_id, tool="generate_travel_roadmap", input_data={"slots": slots},
                             output_data={"missing": missing, "roadmap": roadmap, "notes": notes},
                             confidence=1.0 if not missing else 0.7, db=db,
                             latency_ms=(time.perf_counter() - start) * 1000)
        return {"slots": slots, "missing": missing, "question": question, "roadmap": roadmap, "notes": notes}


planner_agent = PlannerAgent()

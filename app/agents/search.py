"""Search: flight inventory for the requested route, date +-1 day (cached by route+date)."""
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.services.travel_service import search_flights


class SearchAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="search")

    async def search(self, case_id: str, slots: dict[str, Any], db: AsyncSession) -> list[dict[str, Any]]:
        start = time.perf_counter()
        flights = await search_flights(db, slots["origin"], slots["destination"], slots["date"])
        await self.emit_step(case_id=case_id, tool="search_flight_inventories",
                             input_data={"from": slots["origin"], "to": slots["destination"], "date": slots["date"]},
                             output_data={"candidates": len(flights)}, confidence=1.0, db=db,
                             latency_ms=(time.perf_counter() - start) * 1000)
        return flights


search_agent = SearchAgent()

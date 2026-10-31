import datetime
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.flights.seeded import flights_provider
from app.agents.base import BaseAgent
from app.schemas.envelope import AgentEnvelope


class SearchAgent(BaseAgent):
    """Executes parallel searches across flights, returning raw travel options."""

    def __init__(self) -> None:
        super().__init__(name="search")

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        roadmap_data = input_data.get("roadmap", {})
        origin = roadmap_data.get("origin", "DEL")
        destination = roadmap_data.get("destination", "BOM")
        window = roadmap_data.get("window", "evening")
        preference = roadmap_data.get("preference", "balanced")
        language = input_data.get("language", "hi")

        date_str = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

        search_result = await flights_provider.search_flights(
            db=db,
            from_iata=origin,
            to_iata=destination,
            date=date_str,
            window=window,
            preference=preference,
            language=language,
        )

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="search_flight_inventories",
            input_data={"from": origin, "to": destination, "date": date_str},
            output_data={"options_count": len(search_result.get("options", []))},
            confidence=0.98,
            db=db,
        )

        return AgentEnvelope(
            agent=self.name,
            status="done",
            result=search_result,
            confidence=0.98,
            evidence=["flights_inventory_search"],
            next="ranker",
            language=language,
            latency_ms=latency_ms,
        )


search_agent = SearchAgent()

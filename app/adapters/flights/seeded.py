from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.travel_service import travel_service


class SeededFlightsProvider:
    """Reads flights from seeded database with deterministic ranking."""

    async def search_flights(
        self,
        db: AsyncSession,
        from_iata: str,
        to_iata: str,
        date: str | None = None,
        window: str | None = None,
        preference: str = "balanced",
        language: str = "hi",
    ) -> dict[str, Any]:
        return await travel_service.search_and_rank(
            db=db,
            from_iata=from_iata,
            to_iata=to_iata,
            date_str=date,
            window=window,
            preference=preference,
            language=language,
        )


flights_provider = SeededFlightsProvider()

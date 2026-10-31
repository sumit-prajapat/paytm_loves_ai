from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Airport
from app.db.session import get_db
from app.services.travel_service import travel_service

router = APIRouter(prefix="/travel", tags=["Travel"])


class BookingSummaryRequest(BaseModel):
    flight_id: str = Field(..., description="Selected flight ID")
    airline: str = Field(..., description="Airline name")
    dep_time: str = Field(..., description="Departure time")
    arr_time: str = Field(..., description="Arrival time")
    price_inr: float = Field(..., description="Total fare in INR")
    refundable: bool = Field(False, description="Whether fare is refundable")
    passenger_name: str = Field("Arjun Sharma", description="Passenger full name")


@router.get("/flights/search")
async def search_flights(
    from_iata: str = Query("DEL", alias="from", description="Departure airport code (e.g. DEL)"),
    to_iata: str = Query("BOM", alias="to", description="Destination airport code (e.g. BOM)"),
    date: str | None = Query(None, description="Date of travel (YYYY-MM-DD)"),
    window: str | None = Query("evening", description="Time window: morning | afternoon | evening | night"),
    preference: str = Query("balanced", description="Preference: sasta | jaldi | elder | balanced"),
    lang: str = Query("hi", description="Response language"),
    db: AsyncSession = Depends(get_db),
):
    """Executes parallel flight search, applies deterministic scoring, and returns roadmap + top 3 options."""
    return await travel_service.search_and_rank(
        db=db,
        from_iata=from_iata,
        to_iata=to_iata,
        date_str=date,
        window=window,
        preference=preference,
        language=lang,
    )


@router.get("/airports")
async def search_airports(
    q: str = Query(..., min_length=1, description="Search query by city, IATA code, or airport name"),
    db: AsyncSession = Depends(get_db),
):
    """Lookup Indian airports by city name or IATA code."""
    query = f"%{q.strip().lower()}%"
    stmt = (
        select(Airport)
        .where(
            or_(
                Airport.city.ilike(query),
                Airport.iata.ilike(query),
                Airport.name.ilike(query),
            )
        )
        .limit(10)
    )
    res = await db.execute(stmt)
    airports = list(res.scalars().all())

    return [
        {"iata": a.iata, "name": a.name, "city": a.city, "lat": a.lat, "lon": a.lon}
        for a in airports
    ]


@router.post("/booking-summary")
async def create_booking_summary(payload: BookingSummaryRequest):
    """Generates the pre-filled human review & pay handoff object.

    The AI never confirms payments autonomously (Rule R3).
    """
    flight_dict = payload.model_dump()
    return travel_service.create_booking_summary(flight_dict, payload.passenger_name)


@router.get("/status/{flight_no}")
async def get_flight_status(
    flight_no: str,
    date: str | None = Query(None, description="Travel date"),
):
    """Returns simulated flight status, departure gate, and delay notifications."""
    return {
        "flight_no": flight_no,
        "date": date,
        "status": "on_time",
        "gate": "T3 - Gate 14B",
        "delay_minutes": 0,
        "weather_at_dest": "Clear, 28°C",
        "notice": "All systems normal. Web check-in available.",
    }

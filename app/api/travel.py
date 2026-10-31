"""Travel: airport lookup, direct search, booking status ON REQUEST, simulated checkout page.

Booking summaries are only produced by the Ranker (never from client-supplied prices).
"""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, resolve_subject
from app.db.models import Airport, User
from app.db.session import get_db
from app.i18n import resolve_language
from app.i18n.numbers import money
from app.services.pulse_service import booking_status
from app.services.travel_service import rank, search_flights

router = APIRouter(prefix="/travel", tags=["Travel"])
payments_router = APIRouter(prefix="/payments", tags=["Payments (simulated)"])


@router.get("/flights/search")
async def search(
    from_iata: str = Query(..., alias="from", min_length=3, max_length=3),
    to_iata: str = Query(..., alias="to", min_length=3, max_length=3),
    date: datetime.date = Query(...),
    window: str | None = Query(None, pattern="^(morning|afternoon|evening|night)$"),
    preference: str = Query("balanced", pattern="^(cheap|fast|comfort|balanced)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deterministic search + ranking with score breakdown (no LLM). Read-only."""
    flights = await search_flights(db, from_iata.upper(), to_iata.upper(), date.isoformat())
    ranked = rank(flights, date.isoformat(), preference, window)
    for o in ranked.get("options", []):
        o["price"] = money(o["price_inr"])
    return {"from": from_iata.upper(), "to": to_iata.upper(), "date": date.isoformat(), **ranked}


@router.get("/airports")
async def search_airports(q: str = Query(..., min_length=1, max_length=64),
                          current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = f"%{q.strip().lower()}%"
    rows = (await db.execute(select(Airport).where(or_(Airport.city.ilike(query), Airport.iata.ilike(query),
                                                       Airport.name.ilike(query))).limit(10))).scalars().all()
    return [{"iata": a.iata, "name": a.name, "city": a.city, "lat": a.lat, "lon": a.lon} for a in rows]


@router.get("/status/{booking_ref}")
async def travel_status(booking_ref: str, language: str | None = Query(None, max_length=16),
                        customer_id: str | None = Query(None, description="ops/admin only"),
                        current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Status of the traveller's own booking, only when they ask (no watchers)."""
    _, subject_id, _ = resolve_subject(current_user, "traveller" if customer_id else None, customer_id)
    st = await booking_status(db, subject_id, booking_ref, resolve_language(language or "en"))
    if st["booking"] is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return {"text": st["text"], "booking": st["booking"]}


@payments_router.get("/mock-checkout/{order_id}")
async def mock_checkout(order_id: str):
    """Simulated payment page target. Real payment happens only on Paytm with the user's own UPI PIN."""
    return {"order_id": order_id, "status": "simulated_checkout",
            "notice": "SIMULATED. In production the traveller reviews and pays on Paytm with their UPI PIN. "
                      "Saarthi never pays or confirms bookings."}

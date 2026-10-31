"""Morning pulse, festival / battery advice and travel booking status.

All ON REQUEST only (R11), deterministic templates (Tier 0), one subject per call.
"""
from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.action import date_label, display_date
from app.config import get_settings
from app.db.models import Device, Dispute, Festival, Merchant, Refund, Transaction, TravelBooking
from app.i18n import t
from app.i18n.numbers import format_inr
from app.services.settlement_service import settlement_service


async def _battery(db: AsyncSession, merchant: Merchant) -> int | None:
    if not merchant.device_id:
        return None
    d = (await db.execute(select(Device).where(Device.id == merchant.device_id))).scalar_one_or_none()
    return d.battery if d else None


async def build_pulse(db: AsyncSession, merchant: Merchant, lang: str) -> dict[str, Any]:
    name = t("common.name", lang, name=merchant.name.split()[0])
    s = await settlement_service.get_settlement(db, merchant.id)
    pending_refunds = (await db.execute(
        select(func.count(Refund.id)).join(Transaction, Refund.txn_id == Transaction.txn_id)
        .where(Transaction.merchant_id == merchant.id, Refund.status.in_(("pending", "overdue")))
    )).scalar_one()
    open_disputes = (await db.execute(
        select(func.count(Dispute.id)).join(Transaction, Dispute.txn_id == Transaction.txn_id)
        .where(Transaction.merchant_id == merchant.id, Dispute.status.in_(("open", "under_review")))
    )).scalar_one()
    battery = await _battery(db, merchant)
    battery_val = battery if battery is not None else "-"
    facts: dict[str, Any] = {"pending_refunds": pending_refunds, "open_disputes": open_disputes,
                             "battery": battery, "settlement": s}
    if s is None:
        text = t("pulse.no_settlement", lang, name=name, battery=battery_val)
    else:
        gap_part = t("pulse.gap_part", lang, gap=format_inr(s["gap"])) if s["gap"] > 0 else ""
        text = t("pulse.text", lang, name=name, date_label=date_label(s["date"], lang),
                 actual=format_inr(s["actual"]), gap_part=gap_part, pending_refunds=pending_refunds,
                 open_disputes=open_disputes, battery=battery_val)
    return {"text": text, "facts": facts}


async def build_advice(db: AsyncSession, merchant: Merchant, lang: str, topic: str = "all") -> dict[str, Any]:
    window = get_settings().FESTIVAL_ADVICE_WINDOW_DAYS
    today = datetime.date.today()
    battery = await _battery(db, merchant)
    facts: dict[str, Any] = {"battery": battery, "window_days": window}
    lines = []
    if topic in ("festival", "all"):
        fest = (await db.execute(
            select(Festival).where(Festival.date >= today.isoformat(),
                                   Festival.date <= (today + datetime.timedelta(days=window)).isoformat())
            .order_by(Festival.date.asc()).limit(1)
        )).scalar_one_or_none()
        if fest:
            days = (datetime.date.fromisoformat(fest.date) - today).days
            facts.update(festival=fest.name, festival_date=fest.date, days_until=days)
            lines.append(t("advice.festival", lang, festival=fest.name, days=days,
                           battery=battery if battery is not None else "-"))
        else:
            lines.append(t("advice.no_festival", lang, days=window))
    if topic in ("battery", "all") and battery is not None:
        key = "advice.battery_low" if battery <= get_settings().DEVICE_LOW_BATTERY_PCT else "advice.battery_ok"
        lines.append(t(key, lang, battery=battery))
    return {"text": " ".join(lines), "facts": facts}


async def booking_status(db: AsyncSession, customer_id: str, booking_ref: str | None, lang: str) -> dict[str, Any]:
    stmt = select(TravelBooking).where(TravelBooking.customer_id == customer_id)
    if booking_ref:
        stmt = stmt.where(TravelBooking.booking_ref == booking_ref.upper())
    else:
        stmt = stmt.order_by(TravelBooking.date.asc())
    booking = (await db.execute(stmt.limit(1))).scalars().first()
    if booking is None:
        key = "travel.status.not_found" if booking_ref else "travel.status.ask_ref"
        return {"text": t(key, lang), "facts": {}, "booking": None}
    facts = {"booking_ref": booking.booking_ref, "flight_no": booking.flight_no, "airline": booking.airline,
             "from": booking.from_iata, "to": booking.to_iata, "date": booking.date, "dep_time": booking.dep_time,
             "status": booking.status, "delay_minutes": booking.delay_minutes, "terminal": booking.terminal,
             "gate": booking.gate}
    text = t(f"travel.status.{booking.status}", lang, booking_ref=booking.booking_ref, airline=booking.airline,
             flight_no=booking.flight_no, date=display_date(booking.date), dep_time=booking.dep_time,
             delay=booking.delay_minutes, gate=booking.gate or "-")
    return {"text": text, "facts": facts, "booking": facts}

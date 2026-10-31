import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.captain import captain_agent
from app.db.models import Device, Dispute, Settlement, SettlementItem, Transaction
from app.db.session import get_db

router = APIRouter(prefix="/events", tags=["Events"])

EVENT_HISTORY: list[dict[str, Any]] = []


class EventInjectRequest(BaseModel):
    type: str = Field(
        ...,
        description="Event type: settlement_short | soundbox_offline | low_battery_festival | payment_failed | refund_overdue | chargeback_dispute | new_unknown_case | flight_delay",
    )
    merchant_id: str = Field("m_ramesh", description="Target merchant ID")
    extra: dict[str, Any] | None = Field(None, description="Optional payload customization")


@router.post("/inject")
async def inject_event(payload: EventInjectRequest, db: AsyncSession = Depends(get_db)):
    """Live scenario injection endpoint (Chaos/Demo Panel) triggering proactive autonomous pipeline."""
    event_id = f"evt_{uuid.uuid4().hex[:8]}"
    now = datetime.datetime.now(datetime.timezone.utc)
    today = datetime.date.today()

    event_record = {
        "event_id": event_id,
        "type": payload.type,
        "merchant_id": payload.merchant_id,
        "injected_at": now.isoformat(),
    }

    # 1. Modify DB state realistically based on injected event
    if payload.type == "settlement_short":
        set_id = f"set_inj_{event_id}"
        await db.merge(Settlement(
            id=set_id,
            merchant_id=payload.merchant_id,
            date=today.isoformat(),
            expected=24500.0,
            actual=22700.0,
            gap=1800.0,
        ))
        await db.merge(SettlementItem(settlement_id=set_id, type="refund_adjustment", amount=1200.0))
        await db.merge(SettlementItem(settlement_id=set_id, type="fee", amount=600.0))
        await db.commit()

    elif payload.type in ["soundbox_offline", "low_battery_festival"]:
        # Set battery low
        device_id = f"soundbox_{payload.merchant_id}_01"
        await db.merge(Device(
            id=device_id,
            merchant_id=payload.merchant_id,
            battery=12,
            network="4G",
            last_seen=now,
        ))
        await db.commit()

    elif payload.type == "chargeback_dispute":
        txn_id = f"txn_inj_disp_{event_id}"
        await db.merge(Transaction(
            txn_id=txn_id,
            merchant_id=payload.merchant_id,
            amount=6500.0,
            status="success",
            mode="card",
            ts=now,
        ))
        await db.merge(Dispute(
            id=f"disp_inj_{event_id}",
            txn_id=txn_id,
            amount=6500.0,
            reason="Cardholder disputes charge as fraudulent",
            status="open",
            deadline=now + datetime.timedelta(days=7),
            evidence_json={"invoice_required": True},
        ))
        await db.commit()

    # 2. Run through Captain's proactive pipeline
    turn_res = await captain_agent.run_turn(
        user_id=payload.merchant_id,
        event={"type": payload.type, "event_id": event_id},
        role="merchant",
        language="hi",
        db=db,
    )

    event_record["result"] = turn_res
    EVENT_HISTORY.append(event_record)

    return {
        "event_id": event_id,
        "type": payload.type,
        "merchant_id": payload.merchant_id,
        "pipeline_result": turn_res,
    }


@router.get("")
async def get_events():
    """Retrieve history of injected and scheduled events."""
    return EVENT_HISTORY

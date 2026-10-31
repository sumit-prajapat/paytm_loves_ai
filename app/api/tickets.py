import datetime
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_merchant_ownership
from app.core.idempotency import check_idempotency, enforce_action_cap, save_idempotency_record
from app.db.models import Ticket, User
from app.db.session import get_db
from app.services.audit import record_audit_log

router = APIRouter(prefix="/tickets", tags=["Tickets"])


class TicketCreateRequest(BaseModel):
    merchant_id: str = Field(..., description="Target merchant ID")
    category: str = Field(..., description="Ticket category (e.g. soundbox_replacement, settlement_inquiry)")
    priority: str = Field("medium", description="Priority: low | medium | high | urgent")
    source: str = Field("saarthi", description="Source: saarthi | human")


@router.post("")
async def create_ticket(
    payload: TicketCreateRequest,
    current_user: User = Depends(get_current_user),
    x_idempotency_key: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
):
    """Creates a support or device replacement ticket with SLA, IDOR checks, idempotency, and runaway action caps."""
    verify_merchant_ownership(payload.merchant_id, current_user)

    # 1. Idempotency Check: if identical key previously processed, return cached payload
    cached = await check_idempotency(db, x_idempotency_key, current_user.id, "/tickets")
    if cached:
        return cached

    # 2. Action Cap Check: protect against runaway loops
    enforce_action_cap(payload.merchant_id, action_type="ticket", max_per_hour=15)

    ticket_id = f"tkt_{uuid.uuid4().hex[:8]}"
    now = datetime.datetime.now(datetime.timezone.utc)
    eta = now + datetime.timedelta(hours=24)

    ticket = Ticket(
        id=ticket_id,
        merchant_id=payload.merchant_id,
        category=payload.category,
        status="open",
        source=payload.source,
        priority=payload.priority,
        eta=eta,
        created_at=now,
    )
    db.add(ticket)

    await record_audit_log(
        db=db,
        case_id=ticket_id,
        actor=current_user.username,
        action="TICKET_CREATED",
        detail={"category": payload.category, "priority": payload.priority, "merchant_id": payload.merchant_id},
    )
    await db.commit()

    response_data = {
        "ticket_id": ticket_id,
        "merchant_id": payload.merchant_id,
        "category": payload.category,
        "status": "open",
        "priority": payload.priority,
        "source": payload.source,
        "eta": eta.isoformat(),
        "created_at": now.isoformat(),
    }

    # Save response with idempotency key
    await save_idempotency_record(db, x_idempotency_key, current_user.id, "/tickets", response_data)

    return response_data

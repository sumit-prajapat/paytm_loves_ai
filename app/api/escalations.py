from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.models import Ticket, User
from app.db.session import get_db
from app.services.audit import record_audit_log
from app.services.playbook_service import playbook_service

router = APIRouter(prefix="/escalations", tags=["Escalations"])


class ResolveEscalationRequest(BaseModel):
    resolution: str = Field(..., description="Human resolution notes")
    operator_id: str | None = Field(None, description="Operator identifier")
    save_as_playbook: bool = Field(True, description="Convert resolution to learned playbook rule")
    issue_type: str = Field("chargeback_dispute", description="Issue type category")
    root_cause: str = Field("proof_verified", description="Identified root cause")


@router.get("")
async def list_escalations(
    current_user: User = Depends(require_roles(["ops_agent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve human escalation queue with packaged dossiers for operator review (Ops Agent or Admin)."""
    stmt = (
        select(Ticket)
        .where(Ticket.category == "human_escalation", Ticket.status == "open")
        .order_by(Ticket.created_at.desc())
    )
    res = await db.execute(stmt)
    tickets = list(res.scalars().all())

    return [
        {
            "ticket_id": t.id,
            "merchant_id": t.merchant_id,
            "priority": t.priority,
            "status": t.status,
            "eta": t.eta.isoformat() if t.eta else None,
            "created_at": t.created_at.isoformat(),
        }
        for t in tickets
    ]


@router.post("/{ticket_id}/resolve")
async def resolve_escalation(
    ticket_id: str,
    payload: ResolveEscalationRequest,
    current_user: User = Depends(require_roles(["ops_agent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Operator resolves escalation in console (Ops Agent or Admin).

    Optionally saves the resolution as a reusable playbook so repeat issues auto-resolve!
    """
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    res = await db.execute(stmt)
    ticket = res.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Escalation ticket not found")

    ticket.status = "resolved"
    operator_actor = current_user.username or payload.operator_id or "ops_agent"

    # Save to tamper-evident audit trail
    await record_audit_log(
        db=db,
        case_id=ticket.id,
        actor=operator_actor,
        action="ESCALATION_RESOLVED_BY_HUMAN",
        detail={
            "resolution": payload.resolution,
            "save_as_playbook": payload.save_as_playbook,
        },
    )

    learned_playbook_id = None
    if payload.save_as_playbook:
        pb = await playbook_service.create_playbook(
            db=db,
            issue_type=payload.issue_type,
            root_cause=payload.root_cause,
            action=payload.resolution,
            created_from_case=ticket_id,
        )
        learned_playbook_id = pb.id

    await db.commit()

    return {
        "ticket_id": ticket.id,
        "status": "resolved",
        "resolved_by": operator_actor,
        "saved_as_playbook": payload.save_as_playbook,
        "learned_playbook_id": learned_playbook_id,
    }

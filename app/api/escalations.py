"""Human escalation queue (ops/admin). Resolving can teach a playbook so the next similar case
auto-resolves (with a SAFE action only)."""
import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notify.in_app import notification_bus
from app.core.deps import require_roles
from app.db.models import Checkup, Ticket, User
from app.db.session import get_db
from app.services.audit import record_audit_log
from app.services.playbook_service import DEFAULT_ACTION_FOR_ISSUE, playbook_service

router = APIRouter(prefix="/escalations", tags=["Escalations"])


class ResolveEscalationRequest(BaseModel):
    resolution: str = Field(..., min_length=2, max_length=2000, description="Human notes (internal only)")
    save_as_playbook: bool = True
    playbook_action: str | None = Field(None, description="Safe action; defaults by issue type")
    root_cause: str = Field("resolved_by_specialist", max_length=128)


def _ticket(t: Ticket) -> dict:
    return {"ticket_id": t.id, "merchant_id": t.merchant_id, "priority": t.priority, "status": t.status,
            "eta": t.eta.isoformat() if t.eta else None, "created_at": t.created_at.isoformat(),
            "case_id": t.case_id, "checkup_id": t.checkup_id, "dossier": t.details_json,
            "resolved_by": t.resolved_by}


@router.get("")
async def list_escalations(status_filter: str = "open",
                           current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                           db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Ticket).where(Ticket.category == "human_escalation",
                                                  Ticket.status == status_filter)
                             .order_by(Ticket.created_at.desc()).limit(200))).scalars().all()
    return [_ticket(t) for t in rows]


@router.post("/{ticket_id}/resolve")
async def resolve_escalation(ticket_id: str, payload: ResolveEscalationRequest,
                             current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                             db: AsyncSession = Depends(get_db)):
    ticket = (await db.execute(select(Ticket).where(Ticket.id == ticket_id))).scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Escalation ticket not found")
    if ticket.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ticket is already {ticket.status}")
    ticket.status = "resolved"
    ticket.resolved_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    ticket.resolved_by = current_user.username

    dossier = ticket.details_json if isinstance(ticket.details_json, dict) else {}
    learned = None
    if payload.save_as_playbook:
        issue_types = [i for i in dossier.get("issue_types", []) if i in DEFAULT_ACTION_FOR_ISSUE]
        if not issue_types:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                "This escalation has no issue type that can become a safe playbook")
        issue_type = issue_types[0]
        action = payload.playbook_action or DEFAULT_ACTION_FOR_ISSUE[issue_type]
        try:
            pb = await playbook_service.create_playbook(db, issue_type, payload.root_cause, action,
                                                        dossier.get("conditions") or {}, ticket.case_id)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
        learned = {"playbook_id": pb.id, "issue_type": pb.issue_type, "action": pb.action,
                   "conditions": pb.conditions_json}

    # New knowledge: cached check-ups for this merchant must not hide the learned playbook.
    await db.execute(update(Checkup).where(Checkup.merchant_id == ticket.merchant_id).values(cache_valid=False))
    await record_audit_log(db, case_id=ticket.id, actor=current_user.username, action="ESCALATION_RESOLVED_BY_HUMAN",
                           detail={"resolution": payload.resolution, "learned_playbook": learned})
    await db.commit()
    await notification_bus.push_console("escalation_updated", {"ticket_id": ticket.id, "status": "resolved",
                                                               "learned_playbook": learned})
    return {"ticket_id": ticket.id, "status": "resolved", "resolved_by": current_user.username,
            "saved_as_playbook": learned is not None, "learned_playbook": learned}

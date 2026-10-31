"""Playbooks (ops/admin only). Learned actions are restricted to a safe set (no money movement)."""
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.models import Playbook, User
from app.db.session import get_db
from app.services.audit import record_audit_log
from app.services.playbook_service import SAFE_PLAYBOOK_ACTIONS, playbook_service

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])

IssueType = Literal["settlement_short", "soundbox_offline", "chargeback_dispute", "refund_status", "payment_failed"]


class PlaybookCreateRequest(BaseModel):
    issue_type: IssueType
    root_cause: str = Field(..., min_length=2, max_length=128)
    action: str = Field(..., description=f"One of {sorted(SAFE_PLAYBOOK_ACTIONS)}")
    conditions_json: dict[str, Any] | None = None
    created_from_case: str | None = Field(None, max_length=64)


def _pb(pb: Playbook) -> dict[str, Any]:
    return {"playbook_id": pb.id, "issue_type": pb.issue_type, "root_cause": pb.root_cause, "action": pb.action,
            "conditions_json": pb.conditions_json, "times_used": pb.times_used,
            "created_from_case": pb.created_from_case}


@router.post("")
async def create_playbook(payload: PlaybookCreateRequest,
                          current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                          db: AsyncSession = Depends(get_db)):
    try:
        pb = await playbook_service.create_playbook(db, payload.issue_type, payload.root_cause, payload.action,
                                                    payload.conditions_json, payload.created_from_case)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None
    await record_audit_log(db, case_id=pb.id, actor=current_user.username, action="PLAYBOOK_CREATED",
                           detail=_pb(pb))
    await db.commit()
    return _pb(pb)


@router.get("")
async def list_playbooks(current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                         db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Playbook).order_by(Playbook.times_used.desc()))).scalars().all()
    return [_pb(p) for p in rows]


@router.get("/match")
async def match_playbook(issue_type: IssueType = Query(...),
                         current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                         db: AsyncSession = Depends(get_db)):
    pb, score = await playbook_service.match_playbook(db, issue_type, {})
    return {"matched": pb is not None, "match_score": score, "playbook": _pb(pb) if pb else None}

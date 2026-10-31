from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.playbook_service import playbook_service

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])


class PlaybookCreateRequest(BaseModel):
    issue_type: str = Field(..., description="Issue category (e.g. settlement_short, soundbox_offline)")
    root_cause: str = Field(..., description="Identified root cause")
    action: str = Field(..., description="Resolution action")
    conditions_json: dict[str, Any] | None = Field(None, description="Matching conditions")
    created_from_case: str | None = Field(None, description="Case ID this playbook was learned from")


@router.post("")
async def create_playbook(payload: PlaybookCreateRequest, db: AsyncSession = Depends(get_db)):
    """Saves a resolved escalation as a learned playbook so repeat issues auto-resolve with zero tickets."""
    pb = await playbook_service.create_playbook(
        db=db,
        issue_type=payload.issue_type,
        root_cause=payload.root_cause,
        action=payload.action,
        conditions=payload.conditions_json,
        created_from_case=payload.created_from_case,
    )
    return {
        "playbook_id": pb.id,
        "issue_type": pb.issue_type,
        "root_cause": pb.root_cause,
        "action": pb.action,
        "conditions_json": pb.conditions_json,
        "times_used": pb.times_used,
    }


@router.get("/match")
async def match_playbook(
    issue_type: str = Query(..., description="Target issue type"),
    db: AsyncSession = Depends(get_db),
):
    """Finds a matching playbook rule for an issue type and calculates match confidence score."""
    pb, score = await playbook_service.match_playbook(db, issue_type)
    if not pb:
        return {"matched": False, "match_score": 0.0, "playbook": None}

    return {
        "matched": score >= 0.80,
        "match_score": score,
        "playbook": {
            "id": pb.id,
            "issue_type": pb.issue_type,
            "root_cause": pb.root_cause,
            "action": pb.action,
            "times_used": pb.times_used,
        },
    }

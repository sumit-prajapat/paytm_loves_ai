"""On-demand check-ups (R11): the merchant (or an ops agent acting for them, audited) presses
"Check my settlement" / "Raise an issue". Diagnostics run for that ONE merchant only."""
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.captain import Trigger, captain_agent
from app.core.deps import get_current_user, resolve_subject, verify_merchant_ownership
from app.db.models import Checkup, User
from app.db.session import get_db
from app.services.audit import record_audit_log
from app.services.voice_service import reply_audio

router = APIRouter(tags=["Check-ups (on demand)"])

Scope = Literal["settlement", "device", "payments", "refunds", "all"]
Channel = Literal["app", "chat", "voice", "soundbox"]


class CheckupRequest(BaseModel):
    scope: Scope = "all"
    channel: Channel = "app"
    language: str | None = Field(None, max_length=16, description="hi | hinglish | en | ... (default: profile)")
    merchant_id: str | None = Field(None, description="Only for ops_agent/admin acting for a merchant")
    force_refresh: bool = Field(False, description="Re-check instead of returning a recent cached result")
    include_audio: bool = False
    session_id: str | None = Field(None, max_length=64)


class IssueRequest(BaseModel):
    scope: Scope = "all"
    description: str | None = Field(None, max_length=2000)
    insist: bool = Field(False, description="Create a ticket even if the check-up resolved it")
    language: str | None = Field(None, max_length=16)
    merchant_id: str | None = None
    channel: Channel = "app"


async def _audit_on_behalf(db: AsyncSession, user: User, merchant_id: str, what: str) -> None:
    await record_audit_log(db, case_id=merchant_id, actor=user.username, action="OPS_ACTING_ON_BEHALF",
                           detail={"merchant_id": merchant_id, "what": what})


async def execute_checkup(user: User, req: CheckupRequest, db: AsyncSession) -> dict[str, Any]:
    subject_type, subject_id, on_behalf = resolve_subject(
        user, "merchant" if req.merchant_id or user.role in ("ops_agent", "admin") else None, req.merchant_id)
    if subject_type != "merchant":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Check-ups are for merchant accounts")
    if on_behalf:
        await _audit_on_behalf(db, user, subject_id, f"checkup:{req.scope}")
    trigger = Trigger(channel=req.channel, request_type="checkup", actor_id=user.id, actor_role=user.role,
                      subject_type="merchant", subject_id=subject_id, scope=req.scope, language=req.language,
                      session_id=req.session_id, force_refresh=req.force_refresh)
    result = await captain_agent.handle(trigger, db)
    if req.include_audio or req.channel in ("voice", "soundbox"):
        result["audio"] = await reply_audio(result.get("spoken_text") or result["reply_text"], result["language"])
    return result


@router.post("/checkups")
async def create_checkup(req: CheckupRequest, current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Run a check-up for the authenticated merchant (Tier 0 diagnostics + templates)."""
    result = await execute_checkup(current_user, req, db)
    if result["status"] == "quota_exceeded":
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, result["reply_text"])
    return result


@router.get("/checkups/{checkup_id}")
async def get_checkup(checkup_id: str, current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Checkup).where(Checkup.id == checkup_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Check-up not found")
    verify_merchant_ownership(row.merchant_id, current_user)
    return {"id": row.id, "merchant_id": row.merchant_id, "scope": row.scope, "channel": row.channel,
            "status": row.status, "reply_text": row.reply_text, "findings": row.findings_json,
            "ticket_id": row.ticket_id, "tier": row.tier, "llm_calls": row.llm_calls, "cost_inr": row.cost_inr,
            "created_at": row.created_at.isoformat() + "Z"}


@router.post("/issues")
async def raise_issue(req: IssueRequest, current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """'Raise an issue': Saarthi runs a check-up first; a ticket is created only if it cannot
    resolve it, or if the merchant insists."""
    subject_type, subject_id, on_behalf = resolve_subject(
        current_user, "merchant" if req.merchant_id or current_user.role in ("ops_agent", "admin") else None,
        req.merchant_id)
    if subject_type != "merchant":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Issues are for merchant accounts")
    if on_behalf:
        await _audit_on_behalf(db, current_user, subject_id, "raise_issue")
    trigger = Trigger(channel=req.channel, request_type="issue", actor_id=current_user.id,
                      actor_role=current_user.role, subject_type="merchant", subject_id=subject_id,
                      scope=req.scope, language=req.language, insist_ticket=req.insist,
                      description=req.description, force_refresh=True)
    result = await captain_agent.handle(trigger, db)
    if result["status"] == "quota_exceeded":
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, result["reply_text"])
    return result

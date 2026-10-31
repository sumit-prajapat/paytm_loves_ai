"""Chat: the user's message is the trigger. Subject always comes from the token (IDOR-safe);
ops/admin must name the subject and are audited as acting on behalf."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.captain import SubjectNotFound, Trigger, captain_agent
from app.core.deps import get_current_user, resolve_subject
from app.core.security import sanitize_agent_output
from app.db.models import User
from app.db.session import get_db
from app.services.audit import record_audit_log

router = APIRouter(prefix="/chat", tags=["Conversation"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Hindi, Hinglish or English")
    language: str | None = Field(None, max_length=16, description="Force reply language (hi|hinglish|en)")
    session_id: str | None = Field(None, max_length=64)
    subject_type: Literal["merchant", "traveller"] | None = Field(None, description="ops/admin only")
    subject_id: str | None = Field(None, max_length=64, description="ops/admin only")
    elder_mode: bool = False


async def execute_chat(user: User, payload: ChatRequest, db: AsyncSession, channel: str = "chat") -> dict:
    subject_type, subject_id, on_behalf = resolve_subject(user, payload.subject_type, payload.subject_id)
    if on_behalf:
        await record_audit_log(db, case_id=subject_id, actor=user.username, action="OPS_ACTING_ON_BEHALF",
                               detail={"subject_type": subject_type, "what": channel})
    trigger = Trigger(channel=channel, request_type="voice" if channel == "voice" else "chat", actor_id=user.id,
                      actor_role=user.role, subject_type=subject_type, subject_id=subject_id,
                      message=payload.message, language=payload.language, session_id=payload.session_id,
                      elder_mode=payload.elder_mode)
    try:
        result = await captain_agent.handle(trigger, db)
    except SubjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found") from None
    result["reply_text"] = sanitize_agent_output(result.get("reply_text", ""))
    return result


@router.post("")
async def send_chat_message(payload: ChatRequest, current_user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    return await execute_chat(current_user, payload, db)

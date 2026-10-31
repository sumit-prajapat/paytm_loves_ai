"""Soundbox button press or voice command ("Saarthi, mera settlement check karo").

Simulates the device: runs the same on-demand flow for the device owner, returns the spoken
answer as a signed audio_url, and pushes it to that merchant's WebSocket only."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notify.in_app import notification_bus
from app.agents.captain import Trigger, captain_agent
from app.core.deps import get_current_user, verify_merchant_ownership
from app.db.models import Device, User
from app.db.session import get_db
from app.services.audit import record_audit_log
from app.services.voice_service import reply_audio

router = APIRouter(prefix="/soundbox", tags=["Soundbox (on demand)"])


class SoundboxAsk(BaseModel):
    button: Literal["settlement", "device", "payments", "refunds", "all"] | None = Field(
        None, description="Physical button press: which check to run")
    command_text: str | None = Field(None, max_length=500, description="Transcribed voice command")
    language: str | None = Field(None, max_length=16)
    force_refresh: bool = False


async def execute_soundbox_ask(user: User, device_id: str, req: SoundboxAsk, db: AsyncSession) -> dict:
    device = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if device is None or device.merchant_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    verify_merchant_ownership(device.merchant_id, user)
    if user.role in ("ops_agent", "admin"):
        await record_audit_log(db, case_id=device.merchant_id, actor=user.username, action="OPS_ACTING_ON_BEHALF",
                               detail={"merchant_id": device.merchant_id, "what": f"soundbox:{device_id}"})
    if not req.button and not req.command_text:
        req.button = "settlement"
    trigger = Trigger(channel="soundbox", request_type="soundbox", actor_id=user.id, actor_role=user.role,
                      subject_type="merchant", subject_id=device.merchant_id,
                      scope=req.button if not req.command_text else None, message=req.command_text,
                      language=req.language, force_refresh=req.force_refresh)
    result = await captain_agent.handle(trigger, db)
    spoken = result.get("spoken_text") or result["reply_text"]
    result["audio"] = await reply_audio(spoken, result["language"])
    result["device_id"] = device_id
    await notification_bus.push_merchant(device.merchant_id, "soundbox_answer", {
        "device_id": device_id, "case_id": result["case_id"], "text": spoken,
        "audio_url": result["audio"]["audio_url"], "language": result["language"]})
    return result


@router.post("/{device_id}/ask")
async def soundbox_ask(device_id: str, req: SoundboxAsk, current_user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    result = await execute_soundbox_ask(current_user, device_id, req, db)
    if result["status"] == "quota_exceeded":
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, result["reply_text"])
    return result

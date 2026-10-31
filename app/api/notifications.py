from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.adapters.notify.in_app import notification_bus

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationRequest(BaseModel):
    recipient_id: str = Field(..., description="Target merchant or customer ID")
    channel: str = Field("soundbox", description="Delivery channel: soundbox | whatsapp_ui | push")
    text: str = Field(..., description="Message text")
    language: str = Field("hi", description="Language: hi | hinglish | en | mr | ta | bn | gu")
    audio_url: str | None = Field(None, description="Optional pre-generated audio URL")
    extra: dict[str, Any] | None = Field(None, description="Optional extra metadata")


@router.post("")
async def send_notification(payload: NotificationRequest):
    """Dispatches a notification across Soundbox speaker, WhatsApp UI, or Push notification."""
    result = await notification_bus.send_notification(
        recipient_id=payload.recipient_id,
        channel=payload.channel,
        text=payload.text,
        language=payload.language,
        audio_url=payload.audio_url,
        extra=payload.extra,
    )
    return result

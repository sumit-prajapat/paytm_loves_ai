"""Morning pulse and festival / battery advice: ON REQUEST only, Tier 0 templates."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_merchant_ownership
from app.db.models import Merchant, User
from app.db.session import get_db
from app.i18n import resolve_language
from app.services.pulse_service import build_advice, build_pulse
from app.services.usage_service import record_usage
from app.services.voice_service import reply_audio

router = APIRouter(tags=["Pulse & advice (on demand)"])


async def _merchant(db: AsyncSession, merchant_id: str, user: User) -> Merchant:
    verify_merchant_ownership(merchant_id, user)
    m = (await db.execute(select(Merchant).where(Merchant.id == merchant_id))).scalar_one_or_none()
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Merchant not found")
    return m


@router.get("/pulse/{merchant_id}")
async def get_morning_pulse(
    merchant_id: str,
    audio: bool = Query(False, description="Also return a spoken version as a signed audio_url"),
    language: str | None = Query(None, max_length=16),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    m = await _merchant(db, merchant_id, current_user)
    lang = resolve_language(language or m.language)
    p = await build_pulse(db, m, lang)
    body = {"merchant_id": m.id, "language": lang, "text": p["text"], "facts": p["facts"], "tier": 0}
    if audio:
        body["audio"] = await reply_audio(p["text"], lang)
    await record_usage(db, user_id=m.id, actor_id=current_user.id, kind="request", request_type="pulse",
                       channel="app", tier=0, outcome="resolved")
    await db.commit()
    return body


@router.get("/advice/{merchant_id}")
async def get_advice(
    merchant_id: str,
    topic: Literal["festival", "battery", "all"] = "all",
    language: str | None = Query(None, max_length=16),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    m = await _merchant(db, merchant_id, current_user)
    lang = resolve_language(language or m.language)
    a = await build_advice(db, m, lang, topic)
    await record_usage(db, user_id=m.id, actor_id=current_user.id, kind="request", request_type="advice",
                       channel="app", tier=0, outcome="resolved")
    await db.commit()
    return {"merchant_id": m.id, "language": lang, "topic": topic, "text": a["text"], "facts": a["facts"], "tier": 0}

"""Voice: STT -> same Captain turn as chat -> TTS reply as a signed audio_url. Auth required."""
import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat import ChatRequest, execute_chat
from app.config import get_settings
from app.core.deps import get_current_user, resolve_subject
from app.core.security import mask_pii, sanitize_agent_output
from app.db.models import User
from app.db.session import get_db
from app.i18n import resolve_language, t
from app.services.voice_service import get_stt, reply_audio, synthesize

router = APIRouter(prefix="/voice", tags=["Voice"])

ALLOWED_AUDIO_MIMES = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/webm",
                       "application/octet-stream"}


def validate_audio(file: UploadFile, audio_bytes: bytes) -> None:
    """Size limit, MIME allow-list and magic bytes (never trust the extension)."""
    s = get_settings()
    if len(audio_bytes) > s.MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"Audio file exceeds {s.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)}MB")
    if file.content_type and file.content_type.lower() not in ALLOWED_AUDIO_MIMES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Unsupported audio type '{file.content_type}'")
    is_wav = audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]
    is_mp3 = audio_bytes.startswith(b"ID3") or (len(audio_bytes) > 2 and audio_bytes[0] == 0xFF
                                                 and (audio_bytes[1] & 0xE0) == 0xE0)
    if not (is_wav or is_mp3 or audio_bytes.startswith(b"OggS") or audio_bytes.startswith(b"\x1a\x45\xdf\xa3")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid audio stream: magic bytes verification failed.")


async def _transcribe(file: UploadFile) -> dict:
    audio_bytes = await file.read()
    validate_audio(file, audio_bytes)
    # Isolated temp copy (some providers need a file); always deleted.
    tmp = os.path.join(tempfile.gettempdir(), f"saarthi_{uuid.uuid4().hex}.audio")
    try:
        with open(tmp, "wb") as f:
            f.write(audio_bytes)
        return await get_stt().transcribe(audio_bytes=audio_bytes, filename=file.filename)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    language: str = Field("hi", max_length=16)
    slow: bool = Field(False, description="Elder mode: slower speech")


@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    result = await _transcribe(file)
    result["text"] = mask_pii(result.get("text", ""))
    return result


@router.post("/tts")
async def text_to_speech(payload: TTSRequest, current_user: User = Depends(get_current_user)):
    audio, ctype, provider, fallback = await synthesize(sanitize_agent_output(payload.text), payload.language,
                                                        payload.slow)
    return Response(content=audio, media_type=ctype,
                    headers={"X-TTS-Provider": provider, "X-TTS-Fallback": str(fallback).lower()})


@router.post("/turn")
async def voice_turn(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    slow: bool = Form(False, description="Elder mode: slower speech and simpler choices"),
    session_id: str | None = Form(None),
    subject_type: str | None = Form(None, description="ops/admin only"),
    subject_id: str | None = Form(None, description="ops/admin only"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Voice note -> transcript -> Captain -> spoken reply (audio_url)."""
    resolve_subject(current_user, subject_type, subject_id)  # fail fast on IDOR before any processing
    stt = await _transcribe(file)
    transcript = stt.get("text", "")
    if not transcript:
        lang = resolve_language(language or stt.get("language"))
        text = t("voice.not_understood", lang)
        return {"status": "needs_input", "transcript": "", "transcript_unavailable": True, "language": lang,
                "reply_text": text, "audio": await reply_audio(text, lang, slow), "stt_provider": stt.get("provider")}
    payload = ChatRequest(message=transcript[:2000], language=language, session_id=session_id,
                          subject_type=subject_type, subject_id=subject_id, elder_mode=slow)
    result = await execute_chat(current_user, payload, db, channel="voice")
    result["transcript"] = mask_pii(transcript)
    result["stt_provider"] = stt.get("provider")
    result["stt_fallback_used"] = bool(stt.get("fallback_used"))
    result["audio"] = await reply_audio(result.get("spoken_text") or result["reply_text"], result["language"], slow)
    return result

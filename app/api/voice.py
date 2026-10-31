import os
import tempfile
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.stt.factory import get_stt_adapter
from app.adapters.tts.factory import get_tts_adapter
from app.agents.captain import captain_agent
from app.config import get_settings
from app.core.deps import get_current_user_optional, verify_merchant_ownership, verify_traveller_ownership
from app.core.security import mask_pii, sanitize_agent_output
from app.db.session import get_db

settings = get_settings()
router = APIRouter(prefix="/voice", tags=["Voice"])

stt_adapter = get_stt_adapter()
tts_adapter = get_tts_adapter()

ALLOWED_AUDIO_MIMES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/webm",
    "application/octet-stream",
}


def validate_and_save_audio_temp(file: UploadFile, audio_bytes: bytes) -> str:
    """Enforces audio security: size limit, MIME whitelist, magic bytes, and temporary auto-deleted file."""
    # 1. Size check
    if len(audio_bytes) > settings.MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file size exceeds maximum limit of {settings.MAX_AUDIO_SIZE_BYTES // (1024*1024)}MB",
        )

    # 2. MIME check
    if file.content_type and file.content_type.lower() not in ALLOWED_AUDIO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio type '{file.content_type}'. Supported: wav, mp3, ogg, webm",
        )

    # 3. Magic bytes check
    is_wav = audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]
    is_mp3 = audio_bytes.startswith(b"ID3") or (len(audio_bytes) > 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0)
    is_ogg = audio_bytes.startswith(b"OggS")
    is_webm = audio_bytes.startswith(b"\x1a\x45\xdf\xa3")

    if not (is_wav or is_mp3 or is_ogg or is_webm):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid audio stream: magic bytes verification failed.",
        )

    # 4. Save to isolated temp file
    temp_dir = os.path.join(tempfile.gettempdir(), "saarthi_audio")
    os.makedirs(temp_dir, exist_ok=True)
    temp_filepath = os.path.join(temp_dir, f"{uuid.uuid4().hex}.audio")
    with open(temp_filepath, "wb") as f:
        f.write(audio_bytes)

    return temp_filepath


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    language: str = Field("hi", description="Language: hi | mr | en | ta")
    slow: bool = Field(False, description="Enable slower cadence for elder mode")


@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """Transcribes uploaded audio with size/MIME/magic-byte checks and isolated temp file cleanup."""
    audio_bytes = await file.read()
    temp_path = validate_and_save_audio_temp(file, audio_bytes)
    try:
        result = await stt_adapter.transcribe(audio_bytes=audio_bytes, filename=file.filename)
        # Mask any accidental PII in returned transcript
        if "text" in result:
            result["text"] = mask_pii(result["text"])
        return result
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@router.post("/tts")
async def text_to_speech(payload: TTSRequest):
    """Synthesizes text into spoken Indic audio (supports elder mode slow flag)."""
    sanitized_text = sanitize_agent_output(payload.text)
    audio_bytes = await tts_adapter.synthesize(
        text=sanitized_text,
        language=payload.language,
        slow=payload.slow,
    )
    return Response(content=audio_bytes, media_type="audio/wav")


@router.post("/turn")
async def voice_turn(
    file: UploadFile = File(...),
    user_id: str = Form("m_ramesh"),
    role: str = Form("merchant"),
    slow: bool = Form(False),
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Complete voice turn: Speech-to-Text -> Multi-Agent Reasoning -> Text-to-Speech audio response."""
    if current_user:
        if role == "merchant":
            verify_merchant_ownership(user_id, current_user)
        elif role == "traveller":
            verify_traveller_ownership(user_id, current_user)

    audio_bytes = await file.read()
    temp_path = validate_and_save_audio_temp(file, audio_bytes)
    try:
        stt_res = await stt_adapter.transcribe(audio_bytes=audio_bytes, filename=file.filename)
        transcript = stt_res.get("text", "")
        language = stt_res.get("language", "hi")

        # Run Captain turn
        turn_res = await captain_agent.run_turn(
            user_id=user_id,
            message=transcript,
            role=role,
            language=language,
            db=db,
        )
        reply_text = turn_res.get("reply_text", "")
        reply_text = sanitize_agent_output(reply_text)

        # Synthesize reply audio
        reply_audio_bytes = await tts_adapter.synthesize(
            text=reply_text,
            language=language,
            slow=slow,
        )

        return {
            "transcript": mask_pii(transcript),
            "language": language,
            "reply_text": reply_text,
            "case_id": turn_res.get("case_id"),
            "status": turn_res.get("status"),
            "has_audio": len(reply_audio_bytes) > 0,
            "audio_bytes_length": len(reply_audio_bytes),
        }
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

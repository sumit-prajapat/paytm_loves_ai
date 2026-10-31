"""Speech helpers shared by /voice, /soundbox and check-ups: STT, TTS with timeout and a
visible fallback (R9), and conversion of a reply into a signed audio URL."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.adapters.stt.base import BaseSTTAdapter
from app.adapters.stt.mock import MockSTT
from app.adapters.stt.sarvam import SarvamSTT
from app.adapters.tts.base import BaseTTSAdapter
from app.adapters.tts.edge_tts_adapter import EdgeTTSAdapter
from app.adapters.tts.mock import MockTTS
from app.config import get_settings
from app.services.audio_store import save_audio

logger = logging.getLogger(__name__)
_mock_tts = MockTTS()


def get_stt() -> BaseSTTAdapter:
    s = get_settings()
    if s.STT_PROVIDER == "sarvam" and s.SARVAM_API_KEY:
        return SarvamSTT(s.SARVAM_API_KEY)
    return MockSTT()


def get_tts() -> BaseTTSAdapter:
    return EdgeTTSAdapter() if get_settings().TTS_PROVIDER == "edge-tts" else _mock_tts


async def synthesize(text: str, language: str, slow: bool = False) -> tuple[bytes, str, str, bool]:
    """Returns (audio, content_type, provider, fallback_used)."""
    tts = get_tts()
    try:
        audio = await asyncio.wait_for(tts.synthesize(text, language, slow), get_settings().TTS_TIMEOUT_SECONDS)
        if audio:
            return audio, tts.content_type, tts.provider, False
    except Exception as exc:  # network / timeout / provider error: degrade, never fail the turn
        logger.warning("TTS provider %s failed (%s); using offline audio", tts.provider, type(exc).__name__)
    audio = await _mock_tts.synthesize(text, language, slow)
    return audio, _mock_tts.content_type, _mock_tts.provider, tts.provider != _mock_tts.provider


async def reply_audio(text: str, language: str, slow: bool = False) -> dict[str, Any]:
    audio, ctype, provider, fallback = await synthesize(text, language, slow)
    meta = save_audio(audio, ctype)
    return {**meta, "tts_provider": provider, "tts_fallback": fallback, "slow": slow}

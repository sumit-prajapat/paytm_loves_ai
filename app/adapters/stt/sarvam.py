"""Sarvam AI speech-to-text. Model comes from SARVAM_STT_MODEL. On failure falls back to the
offline adapter, which only recognises demo clips and otherwise reports transcript_unavailable."""
import logging
from typing import Any

import httpx

from app.adapters.stt.base import BaseSTTAdapter
from app.adapters.stt.mock import MockSTT
from app.config import get_settings

logger = logging.getLogger(__name__)
ENDPOINT = "https://api.sarvam.ai/speech-to-text"


class SarvamSTT(BaseSTTAdapter):
    provider = "sarvam"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._fallback = MockSTT()

    async def transcribe(
        self, audio_bytes: bytes, filename: str | None = None, language_code: str | None = None,
    ) -> dict[str, Any]:
        s = get_settings()
        try:
            async with httpx.AsyncClient(timeout=s.STT_TIMEOUT_SECONDS) as client:
                res = await client.post(
                    ENDPOINT,
                    headers={"api-subscription-key": self._api_key},
                    files={"file": (filename or "audio.wav", audio_bytes, "audio/wav")},
                    data={"language_code": language_code or "unknown", "model": s.SARVAM_STT_MODEL},
                )
            if res.status_code == 200:
                payload = res.json()
                text = payload.get("transcript", "")
                return {"text": text, "language": payload.get("language_code", "hi"),
                        "confidence": payload.get("confidence", 0.9), "provider": "sarvam",
                        "transcript_unavailable": not text}
            logger.warning("Sarvam STT HTTP %s; using offline fallback", res.status_code)
        except httpx.HTTPError as exc:
            logger.warning("Sarvam STT error %s; using offline fallback", type(exc).__name__)
        out = await self._fallback.transcribe(audio_bytes, filename, language_code)
        out["fallback_used"] = True
        return out

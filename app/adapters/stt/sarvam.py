import logging
from typing import Any

import httpx

from app.adapters.stt.base import BaseSTTAdapter
from app.adapters.stt.mock import MockSTT

logger = logging.getLogger(__name__)


class SarvamSTT(BaseSTTAdapter):
    """Sarvam AI Indic Speech-to-Text adapter."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.mock_fallback = MockSTT()
        self.endpoint = "https://api.sarvam.ai/speech-to-text"

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str | None = None,
        language_code: str | None = "hi-IN",
    ) -> dict[str, Any]:
        try:
            headers = {"api-subscription-key": self.api_key}
            files = {"file": (filename or "audio.wav", audio_bytes, "audio/wav")}
            data = {"language_code": language_code or "hi-IN", "model": "saarika:v1"}

            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(self.endpoint, headers=headers, files=files, data=data)
                if res.status_code == 200:
                    payload = res.json()
                    return {
                        "text": payload.get("transcript", ""),
                        "language": payload.get("language_code", "hi"),
                        "confidence": payload.get("confidence", 0.95),
                    }
                else:
                    logger.warning(f"Sarvam STT failed ({res.status_code}). FALLBACK USED")
                    return await self.mock_fallback.transcribe(audio_bytes, filename, language_code)
        except Exception as e:
            logger.warning(f"Sarvam STT exception: {e}. FALLBACK USED")
            return await self.mock_fallback.transcribe(audio_bytes, filename, language_code)

import io
import logging

import edge_tts

from app.adapters.tts.base import BaseTTSAdapter

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "hi": "hi-IN-MadhurNeural",
    "hinglish": "hi-IN-MadhurNeural",
    "en": "en-IN-PrabhatNeural",
    "mr": "mr-IN-AarohiNeural",
    "ta": "ta-IN-ValluvarNeural",
}


class EdgeTTSAdapter(BaseTTSAdapter):
    """High quality neural Indic Text-to-Speech using edge-tts without API keys."""

    async def synthesize(
        self,
        text: str,
        language: str = "hi",
        slow: bool = False,
    ) -> bytes:
        voice = VOICE_MAP.get(language.lower(), "hi-IN-MadhurNeural")
        rate = "-25%" if slow else "+0%"

        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])

        return buffer.getvalue()

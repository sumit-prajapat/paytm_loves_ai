import io

import edge_tts

from app.adapters.tts.base import BaseTTSAdapter

VOICE_MAP = {
    "hi": "hi-IN-MadhurNeural",
    "hinglish": "hi-IN-MadhurNeural",
    "en": "en-IN-PrabhatNeural",
    "mr": "mr-IN-AarohiNeural",
    "ta": "ta-IN-ValluvarNeural",
    "bn": "bn-IN-BashkarNeural",
}


class EdgeTTSAdapter(BaseTTSAdapter):
    """Neural Indic TTS via edge-tts (needs internet, no key). Timeout applied by the caller."""

    provider = "edge-tts"
    content_type = "audio/mpeg"

    async def synthesize(self, text: str, language: str = "hi", slow: bool = False) -> bytes:
        voice = VOICE_MAP.get(language.lower(), VOICE_MAP["hi"])
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="-25%" if slow else "+0%")
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue()

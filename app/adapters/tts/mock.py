import logging

from app.adapters.tts.base import BaseTTSAdapter

logger = logging.getLogger(__name__)


class MockTTS(BaseTTSAdapter):
    """Deterministic Mock TTS generating lightweight valid audio bytes offline."""

    # 1 second silent WAV header
    SILENT_WAV = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    async def synthesize(
        self,
        text: str,
        language: str = "hi",
        slow: bool = False,
    ) -> bytes:
        logger.info(f"MockTTS synthesizing: '{text[:40]}...' (lang={language}, slow={slow})")
        return self.SILENT_WAV

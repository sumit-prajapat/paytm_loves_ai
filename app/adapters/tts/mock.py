from app.adapters.tts.base import BaseTTSAdapter


class MockTTS(BaseTTSAdapter):
    """Offline TTS: a short valid silent WAV (deterministic; demo-safe)."""

    provider = "mock"
    content_type = "audio/wav"
    SILENT_WAV = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00"
        b"\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

    async def synthesize(self, text: str, language: str = "hi", slow: bool = False) -> bytes:
        return self.SILENT_WAV

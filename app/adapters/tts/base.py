import abc


class BaseTTSAdapter(abc.ABC):
    @abc.abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str = "hi",
        slow: bool = False,
    ) -> bytes:
        """Synthesizes text into audio bytes (e.g., MP3/WAV)."""
        pass

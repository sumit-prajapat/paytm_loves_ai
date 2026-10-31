import abc


class BaseTTSAdapter(abc.ABC):
    provider: str = "base"
    content_type: str = "audio/wav"

    @abc.abstractmethod
    async def synthesize(self, text: str, language: str = "hi", slow: bool = False) -> bytes:
        """Return audio bytes in `content_type`."""

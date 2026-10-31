import abc
from typing import Any


class BaseSTTAdapter(abc.ABC):
    @abc.abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str | None = None,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        """Transcribes audio returning {text: str, language: str, confidence: float}."""
        pass

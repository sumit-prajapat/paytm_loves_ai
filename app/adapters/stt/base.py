import abc
from typing import Any


class BaseSTTAdapter(abc.ABC):
    provider: str = "base"

    @abc.abstractmethod
    async def transcribe(
        self, audio_bytes: bytes, filename: str | None = None, language_code: str | None = None,
    ) -> dict[str, Any]:
        """Return {text, language, confidence, provider, transcript_unavailable?}."""

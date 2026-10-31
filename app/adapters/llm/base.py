import abc
from typing import Any


class LLMUnavailable(Exception):
    """Raised when the provider fails (network, quota, bad model, malformed output).

    Adapters never silently substitute another provider; the LLM gateway decides how to
    degrade (templates, then human queue) and records it.
    """


class BaseLLMAdapter(abc.ABC):
    provider: str = "base"

    @abc.abstractmethod
    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        tier: int,
        json_mode: bool,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return {"text": str, "input_tokens": int, "output_tokens": int}."""

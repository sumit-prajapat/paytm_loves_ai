import abc
from typing import Any


class BaseLLMAdapter(abc.ABC):
    @abc.abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_instruction: str | None = None,
        context: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generates reasoning or explanation with optional structured tool calls."""
        pass

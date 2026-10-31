import abc
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.envelope import AgentEnvelope
from app.trace.bus import trace_bus


class BaseAgent(abc.ABC):
    """Abstract Base Class for all Saarthi specialist agents."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        """Processes typed input and returns a strictly typed AgentEnvelope."""
        pass

    async def emit_step(
        self,
        case_id: str,
        tool: str | None,
        input_data: Any,
        output_data: Any,
        confidence: float,
        db: AsyncSession | None = None,
    ) -> str:
        """Emits an observable execution step to both WebSocket trace and database."""
        return await trace_bus.publish_step(
            case_id=case_id,
            agent=self.name,
            tool=tool,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            db=db,
        )

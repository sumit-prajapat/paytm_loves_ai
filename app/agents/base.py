import abc
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.envelope import AgentEnvelope
from app.trace.bus import trace_bus


class BaseAgent(abc.ABC):
    """Base class for Saarthi specialist agents. Every step goes through the trace bus,
    which enforces the R3 tool allow-list and the per-turn tool budget."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def process(self, case_id: str, input_data: dict[str, Any], db: AsyncSession) -> AgentEnvelope:
        raise NotImplementedError

    async def emit_step(
        self,
        case_id: str,
        tool: str | None,
        input_data: Any,
        output_data: Any,
        confidence: float,
        db: AsyncSession | None = None,
        latency_ms: float = 0.0,
    ) -> str:
        return await trace_bus.publish_step(
            case_id=case_id,
            agent=self.name,
            tool=tool,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            db=db,
            latency_ms=latency_ms,
        )

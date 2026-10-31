from typing import Any, Literal

from pydantic import BaseModel, Field

AgentStatus = Literal["done", "needs_input", "blocked", "escalate"]


class AgentEnvelope(BaseModel):
    """Standardized inter-agent message envelope ensuring explainability and deterministic routing."""

    agent: str = Field(..., description="Name of the reporting agent")
    status: AgentStatus = Field(
        ..., description="Execution status: done | needs_input | blocked | escalate"
    )
    result: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured deterministic payload (no unverified LLM generated numbers)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0 used by confidence router",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="List of tool_call IDs or verified artifact IDs justifying the decision",
    )
    next: str = Field(
        ...,
        description="Recommended next agent name or 'human' for escalation handoff",
    )
    language: str = Field(
        default="en",
        description="Detected or target language (e.g., 'hi', 'hinglish', 'en', 'mr')",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Execution latency in milliseconds",
    )

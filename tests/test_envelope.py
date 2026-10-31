import pytest
from pydantic import ValidationError

from app.schemas.envelope import AgentEnvelope


def test_agent_envelope_valid():
    envelope = AgentEnvelope(
        agent="listener",
        status="done",
        result={"intent": "settlement_short", "merchant_id": "m_ramesh"},
        confidence=0.95,
        evidence=["tool_get_settlement_123"],
        next="diagnostician",
        language="hi",
        latency_ms=145.2,
    )
    assert envelope.agent == "listener"
    assert envelope.status == "done"
    assert envelope.confidence == 0.95
    assert envelope.language == "hi"
    assert envelope.evidence == ["tool_get_settlement_123"]
    assert envelope.latency_ms == 145.2


def test_agent_envelope_invalid_status():
    with pytest.raises(ValidationError):
        AgentEnvelope(
            agent="listener",
            status="invalid_status",  # type: ignore
            result={},
            confidence=0.9,
            next="human",
        )


def test_agent_envelope_confidence_bounds():
    # Confidence > 1.0 must fail
    with pytest.raises(ValidationError):
        AgentEnvelope(
            agent="diagnostician",
            status="done",
            result={},
            confidence=1.2,
            next="action",
        )

    # Confidence < 0.0 must fail
    with pytest.raises(ValidationError):
        AgentEnvelope(
            agent="diagnostician",
            status="done",
            result={},
            confidence=-0.1,
            next="action",
        )

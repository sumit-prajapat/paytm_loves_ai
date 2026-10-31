"""Rule-based Confidence Router for Saarthi Multi-Agent Architecture."""
from typing import Literal

RoutingDecision = Literal["auto_resolve", "needs_clarification", "escalate"]


def route_decision(
    confidence: float,
    financial_impact: float,
    threshold_inr: float = 5000.0,
    is_dispute: bool = False,
    is_kill_switch_active: bool = False,
) -> tuple[RoutingDecision, str]:
    """Confidence router policy logic:

    - Kill switch on => escalate
    - Chargeback / Dispute => escalate
    - Financial impact >= threshold => escalate
    - Confidence >= 0.85 & impact < threshold => auto_resolve
    - 0.60 <= Confidence < 0.85 => needs_clarification
    - Confidence < 0.60 => escalate
    """
    if is_kill_switch_active:
        return "escalate", "Global Kill Switch active: Autonomous actions paused."

    if is_dispute:
        return "escalate", "Disputed transaction or chargeback requires human specialist."

    if financial_impact >= threshold_inr:
        return "escalate", f"Financial impact ₹{financial_impact:,.2f} exceeds threshold ₹{threshold_inr:,.2f}."

    if confidence >= 0.85:
        return "auto_resolve", "High confidence and low risk: Safe for autonomous zero-ticket resolution."

    if confidence >= 0.60:
        return "needs_clarification", "Medium confidence: Requires ONE clarifying question."

    return "escalate", f"Confidence {confidence:.2f} is below minimum autonomy threshold."

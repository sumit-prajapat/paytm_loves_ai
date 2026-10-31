import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.config import get_settings
from app.schemas.envelope import AgentEnvelope
from app.services.kill_switch import kill_switch_service


class GuardianAgent(BaseAgent):
    """Policy & safety enforcement engine reviewing every proposed action before execution."""

    def __init__(self) -> None:
        super().__init__(name="guardian")
        self.settings = get_settings()

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        proposed_action = input_data.get("action", "unknown")
        confidence = float(input_data.get("confidence", 1.0))
        financial_impact = float(input_data.get("financial_impact", 0.0))
        is_unsafe = bool(input_data.get("is_unsafe", False))
        intent = input_data.get("intent", "")
        language = input_data.get("language", "hi")

        decision = "allow"
        reason = "All policy safety checks passed"
        next_agent = "action"
        status = "done"

        # Rule R7: Unsafe PIN / OTP requests
        if is_unsafe or any(k in intent.lower() for k in ["pin", "otp", "password", "unsafe"]):
            decision = "block"
            status = "blocked"
            next_agent = "human"
            reason = "Strict Security Policy: User entered or asked for PIN/OTP credentials."

        # Rule R5: Global Kill Switch
        elif kill_switch_service.is_active():
            decision = "escalate"
            status = "escalate"
            next_agent = "handoff"
            reason = "Global Kill Switch is ENGAGED. Autonomous mutations paused; escalated to human."

        # Rule R3: Payments, loan approvals, refund issuance are strictly human-only
        elif any(act in proposed_action.lower() for act in ["pay", "confirm_booking", "approve_loan", "issue_refund"]):
            decision = "escalate"
            status = "escalate"
            next_agent = "handoff"
            reason = "Human-in-the-Loop Rule R3: Irreversible financial movement requires human confirmation."

        # High financial impact threshold check (> 5,000 INR default)
        elif financial_impact >= self.settings.FINANCIAL_IMPACT_THRESHOLD_INR:
            decision = "escalate"
            status = "escalate"
            next_agent = "handoff"
            reason = f"Financial impact ₹{financial_impact:,.2f} exceeds safety threshold of ₹{self.settings.FINANCIAL_IMPACT_THRESHOLD_INR:,.2f}."

        # Low confidence (< 0.60)
        elif confidence < self.settings.CLARIFY_CONFIDENCE_THRESHOLD:
            decision = "escalate"
            status = "escalate"
            next_agent = "handoff"
            reason = f"Confidence score {confidence:.2f} is below minimum autonomy threshold ({self.settings.CLARIFY_CONFIDENCE_THRESHOLD})."

        # Medium confidence (0.60 to 0.85) -> Clarification needed
        elif confidence < self.settings.AUTO_RESOLVE_CONFIDENCE_THRESHOLD:
            decision = "needs_clarification"
            status = "needs_input"
            next_agent = "listener"
            reason = f"Confidence {confidence:.2f} requires ONE clarifying question before proceeding."

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="evaluate_action_policy",
            input_data={"proposed_action": proposed_action, "financial_impact": financial_impact, "confidence": confidence},
            output_data={"decision": decision, "reason": reason, "status": status},
            confidence=1.0,
            db=db,
        )

        return AgentEnvelope(
            agent=self.name,
            status=status,
            result={
                "decision": decision,
                "reason": reason,
                "proposed_action": proposed_action,
                "financial_impact": financial_impact,
            },
            confidence=confidence,
            evidence=["policy_rules_engine"],
            next=next_agent,
            language=language,
            latency_ms=latency_ms,
        )


guardian_agent = GuardianAgent()

"""Guardian (R2): reviews EVERY proposed action before execution by action CLASS.

- R3: payment, loan approval, refund issuance, booking confirmation -> always BLOCK.
- R5: kill switch -> autonomous mutations ESCALATE; reads/explanations/guidance continue.
- Confidence thresholds come from config (AUTO_RESOLVE / CLARIFY).
"""
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.config import get_settings
from app.services.kill_switch import kill_switch_service

FORBIDDEN_ACTIONS = {"payment", "loan_approval", "refund_issue", "booking_confirm"}
AUTONOMOUS_MUTATIONS = {"playbook_resolution", "create_loan_request"}
CONFIDENCE_GATED = {"explain", "guide", "playbook_resolution"}
ALWAYS_ALLOWED = {"read", "notify", "create_ticket", "handoff_payment_link", "refuse"}


@dataclass
class GuardianDecision:
    decision: str  # allow | block | escalate | needs_input
    reason: str
    action_class: str

    @property
    def allowed(self) -> bool:
        return self.decision == "allow"


class GuardianAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="guardian")

    def evaluate(
        self, action_class: str, confidence: float = 1.0, financial_impact: float = 0.0,
        money_effect: bool = False,
    ) -> GuardianDecision:
        s = get_settings()
        if action_class in FORBIDDEN_ACTIONS:
            return GuardianDecision("block", "R3: payments, loan approvals, refund issuance and booking "
                                             "confirmation are human-only", action_class)
        if action_class in AUTONOMOUS_MUTATIONS and kill_switch_service.is_active():
            return GuardianDecision("escalate", "R5: kill switch engaged; autonomous actions go to a human",
                                    action_class)
        if money_effect and financial_impact >= s.FINANCIAL_IMPACT_THRESHOLD_INR:
            return GuardianDecision("escalate", f"Financial impact {financial_impact} at or above threshold "
                                                f"{s.FINANCIAL_IMPACT_THRESHOLD_INR}", action_class)
        if action_class in CONFIDENCE_GATED:
            if confidence < s.CLARIFY_CONFIDENCE_THRESHOLD:
                return GuardianDecision("escalate", f"Confidence {confidence:.2f} below "
                                                    f"{s.CLARIFY_CONFIDENCE_THRESHOLD}", action_class)
            if confidence < s.AUTO_RESOLVE_CONFIDENCE_THRESHOLD:
                return GuardianDecision("needs_input", f"Confidence {confidence:.2f} below "
                                                       f"{s.AUTO_RESOLVE_CONFIDENCE_THRESHOLD}", action_class)
            return GuardianDecision("allow", "Policy checks passed", action_class)
        if action_class in ALWAYS_ALLOWED or action_class in AUTONOMOUS_MUTATIONS:
            return GuardianDecision("allow", "Policy checks passed", action_class)
        return GuardianDecision("block", f"Unknown action class '{action_class}' (deny by default)", action_class)

    async def review(
        self, case_id: str, db: AsyncSession, *, action_class: str, subject: str,
        confidence: float = 1.0, financial_impact: float = 0.0, money_effect: bool = False,
        detail: dict[str, Any] | None = None,
    ) -> GuardianDecision:
        start = time.perf_counter()
        decision = self.evaluate(action_class, confidence, financial_impact, money_effect)
        await self.emit_step(
            case_id=case_id, tool="evaluate_action_policy",
            input_data={"action_class": action_class, "subject": subject, "confidence": confidence,
                        "financial_impact": financial_impact, **(detail or {})},
            output_data={"decision": decision.decision, "reason": decision.reason},
            confidence=1.0, db=db, latency_ms=(time.perf_counter() - start) * 1000,
        )
        return decision


guardian_agent = GuardianAgent()

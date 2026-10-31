import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.rag.retriever import policy_retriever
from app.schemas.envelope import AgentEnvelope
from app.services.playbook_service import playbook_service


class DiagnosticianAgent(BaseAgent):
    """Diagnoses root cause of merchant/user issues using playbooks first, then RAG and deterministic tools."""

    def __init__(self) -> None:
        super().__init__(name="diagnostician")

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        intent = input_data.get("intent", "settlement_short")
        context_bundle = input_data.get("context", {})
        language = input_data.get("language", "hi")

        root_cause = "unknown"
        action = "explain_and_resolve"
        confidence = 0.85
        evidence = []
        financial_impact = 0.0

        # 1. Playbook lookup (Continuous Learning: Check learned rules first)
        matched_pb, pb_score = await playbook_service.match_playbook(db, intent)
        if matched_pb and pb_score >= 0.80:
            root_cause = matched_pb.root_cause
            action = matched_pb.action
            confidence = pb_score
            evidence.append(f"playbook_{matched_pb.id}")
            # Increment playbook usage counter
            await playbook_service.increment_usage(db, matched_pb.id)

        # 2. Domain-specific root-cause diagnosis using deterministic context
        if intent == "settlement_short":
            settlement = context_bundle.get("settlement", {})
            gap = settlement.get("gap", 0.0)
            financial_impact = gap
            refund_adj = settlement.get("refund_adjustment", 0.0)
            fees = settlement.get("fees", 0.0)
            chargeback_hold = settlement.get("chargeback_hold", 0.0)

            if abs(gap - (refund_adj + fees + chargeback_hold)) < 0.01 and gap > 0:
                root_cause = "reconciled_refund_adjustment_and_fees"
                action = "explain_breakdown_zero_ticket"
                confidence = 0.98
                evidence.append("settlement_items_reconciliation")
            else:
                root_cause = "unreconciled_settlement_gap"
                action = "escalate_to_settlements_desk"
                confidence = 0.70

        elif intent == "soundbox_offline":
            device = context_bundle.get("device", {})
            battery = device.get("battery", 100)
            if battery <= 20:
                root_cause = "low_battery_depleted"
                action = "voice_instruction_connect_charger"
                confidence = 0.96
                evidence.append(f"device_battery_{battery}pct")
            else:
                root_cause = "cellular_network_unreachable"
                action = "prompt_device_restart_or_ticket"
                confidence = 0.85
                evidence.append("device_heartbeat_timeout")

        elif intent == "refund_status":
            root_cause = "banking_clearing_delay"
            action = "explain_expected_sla"
            confidence = 0.92
            evidence.append("rbi_refund_sla_matrix")

        elif intent == "chargeback_dispute":
            root_cause = "cardholder_unauthorized_claim"
            action = "escalate_to_risk_specialist"
            confidence = 0.55  # Always below autonomy threshold!
            financial_impact = 6500.0  # Above 5,000 threshold
            evidence.append("dispute_notice_bank")

        elif intent in ["loan_emi_query", "loan_interest"]:
            root_cause = "merchant_credit_inquiry"
            action = "calculate_loan_emi"
            confidence = 0.95
            evidence.append("loan_amortization_calculator")

        elif intent == "decline_offer":
            root_cause = "merchant_declined_consent"
            action = "log_refusal_and_decline_loan"
            confidence = 1.0
            evidence.append("consent_first_rule_r6")

        # 3. Retrieve relevant policies via local RAG
        rag_results = policy_retriever.search(query=intent, top_k=2, language=language)
        for r in rag_results:
            evidence.append(f"policy_{r['id']}")

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="diagnose_root_cause_and_consult_rag",
            input_data={"intent": intent, "financial_impact": financial_impact},
            output_data={"root_cause": root_cause, "action": action, "confidence": confidence},
            confidence=confidence,
            db=db,
        )

        return AgentEnvelope(
            agent=self.name,
            status="done",
            result={
                "root_cause": root_cause,
                "action": action,
                "financial_impact": financial_impact,
                "evidence": evidence,
                "rag_snippets": [r["title"] for r in rag_results],
            },
            confidence=confidence,
            evidence=evidence,
            next="guardian",
            language=language,
            latency_ms=latency_ms,
        )


diagnostician_agent = DiagnosticianAgent()

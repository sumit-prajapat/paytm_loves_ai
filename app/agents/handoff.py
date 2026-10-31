import datetime
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notify.in_app import notification_bus
from app.agents.base import BaseAgent
from app.db.models import AuditLog, Ticket
from app.schemas.envelope import AgentEnvelope
from app.services.metrics_service import metrics_service


class HandoffAgent(BaseAgent):
    """Packages cases for human escalation with complete context so merchants never repeat the story."""

    def __init__(self) -> None:
        super().__init__(name="handoff")

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        merchant_id = input_data.get("merchant_id", "m_disputed")
        reason = input_data.get("reason", "Autonomous threshold exceeded or chargeback dispute")
        evidence = input_data.get("evidence", [])
        language = input_data.get("language", "hi")
        root_cause_guess = input_data.get("root_cause", "chargeback_investigation_required")

        now = datetime.datetime.now(datetime.timezone.utc)
        eta = now + datetime.timedelta(hours=4)

        # 1. Create escalation ticket
        ticket_id = f"tkt_esc_{case_id[-6:]}"
        ticket = Ticket(
            id=ticket_id,
            merchant_id=merchant_id,
            category="human_escalation",
            status="open",
            source="saarthi",
            priority="high",
            eta=eta,
            created_at=now,
        )
        db.add(ticket)

        # 2. Package complete handoff dossier
        escalation_package = {
            "ticket_id": ticket_id,
            "case_id": case_id,
            "merchant_id": merchant_id,
            "merchant_language": language,
            "reason": reason,
            "root_cause_guess": root_cause_guess,
            "evidence": evidence,
            "suggested_fix": "Request invoice & store delivery proof from merchant within 7 days.",
            "timeline": [
                {"ts": now.isoformat(), "event": "Flagged by Guardian agent for human review"},
            ],
            "merchant_facing_message": "Aapka mudda humare varishth sahayak (Senior Specialist) ko bhej diya gaya hai. Aapko dobara baat dohrane ki zaroorat nahi hai.",
        }

        # 3. Log to audit trail and record metrics
        audit_entry = AuditLog(
            case_id=case_id,
            actor="handoff_agent",
            action="ESCALATED_TO_HUMAN_CONSOLE",
            detail=escalation_package,
            ts=now,
        )
        db.add(audit_entry)
        await db.commit()

        metrics_service.record_escalation()

        # 4. Stream to Ops Console over WebSocket
        await notification_bus.send_notification(
            recipient_id="console",
            channel="ops_console",
            text=f"Escalation Package for Case {case_id}: {reason}",
            extra=escalation_package,
        )

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="package_escalation_dossier",
            input_data={"case_id": case_id, "reason": reason},
            output_data={"ticket_id": ticket_id, "status": "escalated_to_human_queue"},
            confidence=1.0,
            db=db,
        )

        return AgentEnvelope(
            agent=self.name,
            status="escalate",
            result=escalation_package,
            confidence=1.0,
            evidence=evidence,
            next="human",
            language=language,
            latency_ms=latency_ms,
        )


handoff_agent = HandoffAgent()

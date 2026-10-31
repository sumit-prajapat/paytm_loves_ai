"""Handoff: packages a human escalation with the full dossier (merchant never repeats the story).

- Reuses an already-open escalation for the same evidence (repeated triggers are idempotent).
- Optional Tier 2 summary for the specialist, validated against facts; template fallback.
"""
import datetime
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notify.in_app import notification_bus
from app.agents.base import BaseAgent
from app.config import get_settings
from app.db.models import Ticket
from app.llm.gateway import llm_gateway
from app.services.audit import record_audit_log

NEXT_STEP = {
    "chargeback_dispute": "Collect invoice and delivery proof from the merchant and respond before the deadline.",
    "refund_status": "Chase the bank with the refund reference; confirm credit date to the merchant.",
    "settlement_short": "Reconcile the unexplained part of the settlement gap with the settlements ledger.",
    "soundbox_offline": "Arrange a device check or replacement.",
    "unknown": "Read the merchant's message and reply.",
}


def _evidence_key(findings: list[dict[str, Any]], reason_code: str) -> list[str]:
    keys = sorted({e for f in findings for e in f.get("evidence", []) if ":" in e and not e.startswith("playbook")})
    return keys or [reason_code]


class HandoffAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="handoff")

    async def escalate(
        self, case_id: str, db: AsyncSession, *, merchant_id: str, findings: list[dict[str, Any]],
        reason: str, reason_code: str, language: str, actor_id: str, checkup_id: str | None = None,
        user_message: str | None = None,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        evidence_key = _evidence_key(findings, reason_code)

        open_tickets = (await db.execute(
            select(Ticket).where(Ticket.merchant_id == merchant_id, Ticket.category == "human_escalation",
                                 Ticket.status == "open")
        )).scalars().all()
        for existing in open_tickets:
            details = existing.details_json if isinstance(existing.details_json, dict) else {}
            if details.get("evidence_key") == evidence_key:
                await self.emit_step(case_id=case_id, tool="package_escalation_dossier",
                                     input_data={"reason_code": reason_code},
                                     output_data={"ticket_id": existing.id, "reused": True},
                                     confidence=1.0, db=db)
                return {"ticket_id": existing.id, "reused": True, "dossier": details}

        now = datetime.datetime.now(datetime.timezone.utc)
        issue_types = sorted({f.get("issue_type") or "unknown" for f in findings}) or ["unknown"]
        facts = {
            "merchant_id": merchant_id,
            "issue_type": ", ".join(issue_types),
            "reason": reason,
            "findings": [{"code": f["code"], "facts": f["facts"]} for f in findings],
            "evidence": [e for f in findings for e in f.get("evidence", [])],
            "suggested_next_step": " ".join(NEXT_STEP.get(i, NEXT_STEP["unknown"]) for i in issue_types),
        }
        summary = (f"{', '.join(issue_types)} for {merchant_id}: {reason}. "
                   f"Next step: {facts['suggested_next_step']}")
        summary_source = "template"
        llm = await llm_gateway.summarize(db, facts)
        if llm.ok and llm.text.strip():
            summary, summary_source = llm.text.strip(), "llm_tier2"

        ticket_id = f"tkt_{uuid.uuid4().hex[:10]}"
        dossier = {
            "ticket_id": ticket_id,
            "case_id": case_id,
            "checkup_id": checkup_id,
            "merchant_id": merchant_id,
            "merchant_language": language,
            "issue_types": issue_types,
            "reason": reason,
            "reason_code": reason_code,
            "summary": summary,
            "summary_source": summary_source,
            "findings": facts["findings"],
            "conditions": {k: v for f in findings for k, v in f.get("conditions", {}).items()},
            "evidence": facts["evidence"],
            "evidence_key": evidence_key,
            "suggested_next_step": facts["suggested_next_step"],
            "user_message": user_message,
            "timeline": [{"ts": now.isoformat(), "event": f"Escalated by Guardian: {reason_code}"}],
        }
        db.add(Ticket(
            id=ticket_id, merchant_id=merchant_id, category="human_escalation", status="open",
            source="saarthi", priority="high",
            eta=now + datetime.timedelta(hours=get_settings().ESCALATION_ETA_HOURS),
            created_at=now, case_id=case_id, checkup_id=checkup_id, details_json=dossier,
        ))
        await record_audit_log(db, case_id=case_id, actor="handoff_agent", action="ESCALATED_TO_HUMAN",
                               detail={"ticket_id": ticket_id, "reason_code": reason_code,
                                       "merchant_id": merchant_id, "triggered_by": actor_id})
        await self.emit_step(
            case_id=case_id, tool="package_escalation_dossier",
            input_data={"reason_code": reason_code, "findings": [f["code"] for f in findings]},
            output_data={"ticket_id": ticket_id, "summary_source": summary_source, "reused": False},
            confidence=1.0, db=db, latency_ms=(time.perf_counter() - start) * 1000,
        )
        await notification_bus.push_console("escalation_created", {"ticket": dossier})
        return {"ticket_id": ticket_id, "reused": False, "dossier": dossier}


handoff_agent = HandoffAgent()

"""Action: turns findings into per-language text from templates (Tier 0) and validates every
number against the tool facts (R1). Never moves money."""
from __future__ import annotations

import datetime
import logging
import time
from collections import Counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.i18n import t
from app.i18n.numbers import format_inr, spoken_number
from app.services.number_validator import number_validator

logger = logging.getLogger(__name__)
validator_stats: Counter[str] = Counter()


def display_date(iso: str) -> str:
    try:
        d = datetime.date.fromisoformat(iso[:10])
    except ValueError:
        return iso
    return d.strftime("%d/%m/%Y")


def date_label(iso: str, lang: str) -> str:
    if iso[:10] == datetime.date.today().isoformat():
        return t("common.today", lang)
    return display_date(iso)


def _breakdown(items: list[dict[str, Any]], lang: str, spoken: bool) -> str:
    parts = []
    for item in items:
        key = f"settlement.item.{item['type']}"
        try:
            t(key, "en", amount="")
        except KeyError:
            key = "settlement.item.other"
        amount = (f"{spoken_number(item['amount'], lang)} {t('common.rupees', lang)}" if spoken
                  else format_inr(item["amount"]))
        parts.append(t(key, lang, amount=amount))
    return t("common.and", lang).join(parts)


def render_finding(f: dict[str, Any], lang: str, name: str, *, spoken: bool = False,
                   ticket_id: str | None = None) -> str:
    facts = f["facts"]
    nm = t("common.name", lang, name=name)
    code = f["code"]
    if f.get("resolution") == "playbook" and f["playbook"]["action"] == "request_evidence_upload":
        return t("dispute.playbook_evidence", lang, amount=format_inr(facts["amount"]),
                 deadline=display_date(facts["deadline"]))
    if code == "settlement_gap_reconciled":
        if spoken:
            return t("settlement.gap_explained_spoken", lang, name=nm,
                     date_label=date_label(facts["date"], lang),
                     gap_spoken=spoken_number(facts["gap"], lang),
                     breakdown_spoken=_breakdown(facts["items"], lang, spoken=True))
        return t("settlement.gap_explained", lang, name=nm, date_label=date_label(facts["date"], lang),
                 gap=format_inr(facts["gap"]), breakdown=_breakdown(facts["items"], lang, spoken=False))
    if code == "settlement_gap_unreconciled":
        return t("settlement.unreconciled", lang, name=nm, date_label=date_label(facts["date"], lang),
                 gap=format_inr(facts["gap"]), explained=format_inr(facts["explained_total"]),
                 ticket_id=ticket_id or "-")
    if code == "settlement_ok":
        return t("settlement.ok", lang, name=nm, date_label=date_label(facts["date"], lang),
                 actual=format_inr(facts["actual"]))
    if code == "settlement_none":
        return t("settlement.none", lang)
    if code == "device_low_battery":
        if spoken:
            return t("device.low_battery_spoken", lang, battery_spoken=spoken_number(facts["battery"], lang))
        return t("device.low_battery", lang, battery=facts["battery"])
    if code == "device_offline":
        if spoken:
            return t("device.offline_spoken", lang,
                     minutes_spoken=spoken_number(facts["minutes_since_seen"], lang))
        return t("device.offline", lang, minutes=facts["minutes_since_seen"])
    if code == "device_ok":
        if spoken:
            return t("device.ok_spoken", lang, battery_spoken=spoken_number(facts["battery"], lang))
        return t("device.ok", lang, battery=facts["battery"])
    if code == "device_none":
        return t("device.none", lang)
    if code == "refund_pending":
        return t("refunds.pending", lang, amount=format_inr(facts["amount"]), bank_ref=facts["bank_ref"],
                 expected_by=display_date(facts["expected_by"]))
    if code == "refund_overdue":
        return t("refunds.overdue", lang, amount=format_inr(facts["amount"]), bank_ref=facts["bank_ref"],
                 expected_by=display_date(facts["expected_by"]), ticket_id=ticket_id or "-")
    if code == "refunds_none":
        return t("refunds.none", lang)
    if code == "payments_failed":
        try:
            reason = t(f"failure_reason.{facts['reason_code']}", lang)
        except KeyError:
            reason = t("failure_reason.other", lang)
        return t("payments.failed_summary", lang, days=facts["days"], count=facts["count"],
                 amount=format_inr(facts["amount"]), reason=reason)
    if code == "payments_none":
        return t("payments.none", lang, days=facts["days"])
    if code == "dispute_open":
        return t("dispute.escalated", lang, amount=format_inr(facts["amount"]),
                 deadline=display_date(facts["deadline"]), ticket_id=ticket_id or "-")
    raise KeyError(f"No renderer for finding '{code}'")


class ActionAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="action")

    async def explain(
        self, case_id: str, findings: list[dict[str, Any]], *, lang: str, name: str, scope: str,
        ticket_id: str | None, db: AsyncSession,
    ) -> dict[str, Any]:
        """Render the check-up reply. Returns {'text', 'spoken_text', 'violations'}."""
        start = time.perf_counter()
        issues = [f for f in findings if f["is_issue"]]
        shown = issues if issues else ([] if scope == "all" else findings)
        lines, spoken_lines, violations = [], [], []
        for f in shown:
            text = render_finding(f, lang, name, ticket_id=ticket_id)
            facts = {**f["facts"], "ticket_id": ticket_id}
            ok, bad = number_validator.validate(text, facts)
            if not ok:  # R1: never send an ungrounded number
                validator_stats["violations"] += 1
                violations.append({"code": f["code"], "numbers": sorted(bad)})
                logger.error("R1 violation in template %s: %s", f["code"], bad)
                text = t("escalation.generic", lang, ticket_id=ticket_id or "-") if ticket_id else \
                    t("clarify.care", lang)
            lines.append(text)
            spoken_lines.append(render_finding(f, lang, name, spoken=True, ticket_id=ticket_id) if ok else text)
        if not shown:
            lines = [t("checkup.all_clear", lang)]
            spoken_lines = list(lines)
        result = {"text": "\n".join(lines), "spoken_text": " ".join(spoken_lines), "violations": violations}
        await self.emit_step(
            case_id=case_id, tool="render_explanation",
            input_data={"codes": [f["code"] for f in shown], "language": lang},
            output_data={"chars": len(result["text"]), "violations": violations},
            confidence=1.0, db=db, latency_ms=(time.perf_counter() - start) * 1000,
        )
        return result


action_agent = ActionAgent()

"""Deterministic diagnostics for ONE merchant, run only when that merchant (or an authorised
ops agent acting for them) triggers a check-up (R11). Pure SQL + rules: no LLM (Tier 0).

Each diagnostic returns "findings": structured facts plus a resolution class. The Action agent
turns findings into per-language text; the Guardian approves the resolution.
"""
from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Device, Dispute, Merchant, Refund, Transaction
from app.services.settlement_service import settlement_service

SCOPES = ("settlement", "device", "payments", "refunds")
ALL_SCOPES = SCOPES


def _utcnow_naive() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _naive(dt: datetime.datetime) -> datetime.datetime:
    return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def expand_scope(scope: str) -> tuple[str, ...]:
    """'all' -> every scope; 'payments,refunds' -> both; unknown names are rejected."""
    if scope == "all":
        return ALL_SCOPES
    parts = tuple(p.strip() for p in scope.split(",") if p.strip())
    unknown = [p for p in parts if p not in SCOPES]
    if unknown or not parts:
        raise ValueError(f"Unknown check-up scope: {scope}")
    return parts


def _finding(scope: str, code: str, *, resolution: str, is_issue: bool, confidence: float,
             facts: dict[str, Any], evidence: list[str], issue_type: str | None = None,
             impact: float = 0.0, conditions: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "scope": scope,
        "code": code,
        "issue_type": issue_type,
        "resolution": resolution,  # explain | guide | escalate | info
        "is_issue": is_issue,
        "confidence": confidence,
        "financial_impact_inr": impact,
        "facts": facts,
        "evidence": evidence,
        "conditions": conditions or {},
    }


async def diagnose_settlement(db: AsyncSession, merchant: Merchant) -> list[dict[str, Any]]:
    s = await settlement_service.get_settlement(db, merchant.id)
    if s is None:
        return [_finding("settlement", "settlement_none", resolution="info", is_issue=False,
                         confidence=1.0, facts={}, evidence=["settlements:none"])]
    ev = [f"settlement:{s['id']}"]
    if s["gap"] <= 0:
        return [_finding("settlement", "settlement_ok", resolution="info", is_issue=False,
                         confidence=1.0, facts=s, evidence=ev)]
    if s["is_reconciled"]:
        return [_finding("settlement", "settlement_gap_reconciled", resolution="explain",
                         is_issue=True, confidence=0.98, facts=s, evidence=ev + ["reconciled_items"],
                         issue_type="settlement_short", impact=s["gap"],
                         conditions={"settlement_gap_matches_items": True})]
    return [_finding("settlement", "settlement_gap_unreconciled", resolution="escalate",
                     is_issue=True, confidence=0.6, facts=s, evidence=ev + ["unexplained_gap"],
                     issue_type="settlement_short", impact=s["gap"],
                     conditions={"settlement_gap_matches_items": False})]


async def diagnose_device(db: AsyncSession, merchant: Merchant) -> list[dict[str, Any]]:
    cfg = get_settings()
    device = None
    if merchant.device_id:
        device = (await db.execute(select(Device).where(Device.id == merchant.device_id))).scalar_one_or_none()
    if device is None:
        return [_finding("device", "device_none", resolution="info", is_issue=False,
                         confidence=1.0, facts={}, evidence=["devices:none"])]
    minutes = int((_utcnow_naive() - _naive(device.last_seen)).total_seconds() // 60)
    facts = {"device_id": device.id, "battery": device.battery, "network": device.network,
             "minutes_since_seen": minutes, "last_seen": _naive(device.last_seen).isoformat(timespec="minutes")}
    ev = [f"device:{device.id}"]
    if minutes > cfg.DEVICE_OFFLINE_MINUTES:
        return [_finding("device", "device_offline", resolution="guide", is_issue=True,
                         confidence=0.9, facts=facts, evidence=ev + ["heartbeat_missing"],
                         issue_type="soundbox_offline", conditions={"offline": True})]
    if device.battery <= cfg.DEVICE_LOW_BATTERY_PCT:
        return [_finding("device", "device_low_battery", resolution="guide", is_issue=True,
                         confidence=0.96, facts=facts, evidence=ev + ["battery_low"],
                         issue_type="soundbox_offline", conditions={"battery_below_pct": cfg.DEVICE_LOW_BATTERY_PCT})]
    return [_finding("device", "device_ok", resolution="info", is_issue=False, confidence=1.0,
                     facts=facts, evidence=ev)]


async def diagnose_refunds(db: AsyncSession, merchant: Merchant) -> list[dict[str, Any]]:
    now = _utcnow_naive()
    stmt = (
        select(Refund, Transaction)
        .join(Transaction, Refund.txn_id == Transaction.txn_id)
        .where(Transaction.merchant_id == merchant.id, Refund.status.in_(("pending", "overdue")))
        .order_by(Refund.expected_by.asc())
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return [_finding("refunds", "refunds_none", resolution="info", is_issue=False,
                         confidence=1.0, facts={}, evidence=["refunds:none"])]
    findings = []
    for refund, txn in rows:
        expected_by = _naive(refund.expected_by)
        overdue = refund.status == "overdue" or expected_by < now
        facts = {"refund_id": refund.id, "txn_id": txn.txn_id, "amount": txn.amount,
                 "bank_ref": refund.bank_ref or "-", "expected_by": expected_by.date().isoformat(),
                 "status": "overdue" if overdue else "pending"}
        ev = [f"refund:{refund.id}", f"txn:{txn.txn_id}"]
        if overdue:
            findings.append(_finding("refunds", "refund_overdue", resolution="escalate", is_issue=True,
                                     confidence=0.95, facts=facts, evidence=ev + ["sla_breached"],
                                     issue_type="refund_status", impact=txn.amount,
                                     conditions={"refund_overdue": True}))
        else:
            findings.append(_finding("refunds", "refund_pending", resolution="explain", is_issue=True,
                                     confidence=0.95, facts=facts, evidence=ev + ["within_sla"],
                                     issue_type="refund_status", impact=txn.amount,
                                     conditions={"refund_overdue": False}))
    return findings


async def diagnose_payments(db: AsyncSession, merchant: Merchant) -> list[dict[str, Any]]:
    cfg = get_settings()
    since = _utcnow_naive() - datetime.timedelta(days=cfg.PAYMENTS_LOOKBACK_DAYS)
    findings: list[dict[str, Any]] = []
    failed = (await db.execute(
        select(Transaction)
        .where(Transaction.merchant_id == merchant.id, Transaction.status == "failed", Transaction.ts >= since)
        .order_by(Transaction.ts.desc())
    )).scalars().all()
    if failed:
        latest = failed[0]
        findings.append(_finding(
            "payments", "payments_failed", resolution="explain", is_issue=True, confidence=0.95,
            facts={"count": len(failed), "days": cfg.PAYMENTS_LOOKBACK_DAYS, "latest_txn_id": latest.txn_id,
                   "amount": latest.amount, "reason_code": latest.failure_reason or "other"},
            evidence=[f"txn:{t.txn_id}" for t in failed[:5]], issue_type="payment_failed",
        ))
    else:
        findings.append(_finding("payments", "payments_none", resolution="info", is_issue=False,
                                 confidence=1.0, facts={"days": cfg.PAYMENTS_LOOKBACK_DAYS},
                                 evidence=["txns:no_failures"]))
    disputes = (await db.execute(
        select(Dispute, Transaction)
        .join(Transaction, Dispute.txn_id == Transaction.txn_id)
        .where(Transaction.merchant_id == merchant.id, Dispute.status.in_(("open", "under_review")))
    )).all()
    for dispute, txn in disputes:
        reason = (dispute.reason or "").lower()
        category = "fraud_claim" if any(w in reason for w in ("stolen", "unauthori", "fraud")) else "other"
        evidence_json = dispute.evidence_json if isinstance(dispute.evidence_json, dict) else {}
        findings.append(_finding(
            "payments", "dispute_open", resolution="escalate", is_issue=True, confidence=0.55,
            facts={"dispute_id": dispute.id, "txn_id": txn.txn_id, "amount": dispute.amount,
                   "deadline": _naive(dispute.deadline).date().isoformat(), "reason": dispute.reason},
            evidence=[f"dispute:{dispute.id}", f"txn:{txn.txn_id}"], issue_type="chargeback_dispute",
            impact=dispute.amount,
            conditions={"dispute_reason_category": category,
                        "invoice_required": bool(evidence_json.get("invoice_required"))},
        ))
    return findings


DIAGNOSTICS = {
    "settlement": diagnose_settlement,
    "device": diagnose_device,
    "refunds": diagnose_refunds,
    "payments": diagnose_payments,
}


async def run_diagnostics(db: AsyncSession, merchant: Merchant, scope: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for sc in expand_scope(scope):
        findings.extend(await DIAGNOSTICS[sc](db, merchant))
    return findings

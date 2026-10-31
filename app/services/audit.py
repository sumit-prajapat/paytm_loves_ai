import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import compute_audit_hash
from app.db.models import AuditLog


async def record_audit_log(
    db: AsyncSession,
    case_id: str,
    actor: str,
    action: str,
    detail: Any = None,
    ip_address: str | None = None,
    correlation_id: str | None = None,
) -> AuditLog:
    """Inserts a tamper-evident audit log row cryptographically chained to the previous row."""
    # Find the most recent row in the chain
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
    res = await db.execute(stmt)
    last_row = res.scalar_one_or_none()

    previous_hash = (
        last_row.hash
        if (last_row and last_row.hash and last_row.hash not in ("UNVERIFIED", "GENESIS_HASH"))
        else "GENESIS_HASH"
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    current_hash = compute_audit_hash(
        previous_hash=previous_hash,
        case_id=case_id,
        actor=actor,
        action=action,
        detail=detail,
        ts=now,
    )

    audit_entry = AuditLog(
        case_id=case_id,
        actor=actor,
        action=action,
        detail=detail,
        previous_hash=previous_hash,
        hash=current_hash,
        ip_address=ip_address,
        correlation_id=correlation_id,
        ts=now,
    )
    db.add(audit_entry)
    return audit_entry


async def verify_audit_chain(db: AsyncSession) -> dict[str, Any]:
    """Verifies the cryptographic integrity of the entire audit chain.

    Detects if any previous row was modified, inserted, or deleted.
    """
    stmt = select(AuditLog).order_by(AuditLog.id.asc())
    res = await db.execute(stmt)
    records = list(res.scalars().all())

    if not records:
        return {
            "chain_intact": True,
            "total_records": 0,
            "message": "Audit log is empty; genesis state valid.",
        }

    expected_prev_hash = "GENESIS_HASH"
    for r in records:
        if r.previous_hash != expected_prev_hash:
            return {
                "chain_intact": False,
                "tampered_row_id": r.id,
                "reason": f"Broken chain: expected previous_hash '{expected_prev_hash}', found '{r.previous_hash}'",
            }

        recalculated = compute_audit_hash(
            previous_hash=r.previous_hash,
            case_id=r.case_id,
            actor=r.actor,
            action=r.action,
            detail=r.detail,
            ts=r.ts,
        )

        if r.hash != recalculated:
            return {
                "chain_intact": False,
                "tampered_row_id": r.id,
                "reason": f"Tampered record: stored hash '{r.hash}' != recalculated hash '{recalculated}'",
            }

        expected_prev_hash = r.hash

    return {
        "chain_intact": True,
        "total_records": len(records),
        "latest_hash": expected_prev_hash,
        "message": "Cryptographic chain verified intact.",
    }

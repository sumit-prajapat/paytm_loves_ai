from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.models import AuditLog, User
from app.db.session import get_db
from app.services.audit import verify_audit_chain

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
async def get_audit_trail(
    case_id: str | None = Query(None, description="Filter by case ID"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve immutable audit log records verifying agent decisions, actions, and operator overrides (Admin only)."""
    stmt = select(AuditLog)
    if case_id:
        stmt = stmt.where(AuditLog.case_id == case_id)
    stmt = stmt.order_by(AuditLog.ts.desc()).limit(limit)

    res = await db.execute(stmt)
    records = list(res.scalars().all())

    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "actor": r.actor,
            "action": r.action,
            "detail": r.detail,
            "previous_hash": r.previous_hash,
            "hash": r.hash,
            "ip_address": r.ip_address,
            "correlation_id": r.correlation_id,
            "timestamp": r.ts.isoformat(),
        }
        for r in records
    ]


@router.get("/verify")
async def verify_audit_integrity(
    current_user: User = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Verifies the SHA-256 tamper-evident cryptographic chain of the entire audit log (Admin only)."""
    return await verify_audit_chain(db)


@router.get("/export")
async def export_audit_trail(
    current_user: User = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Exports full audit trail with cryptographic proof hashes for external auditor inspection (Admin only)."""
    stmt = select(AuditLog).order_by(AuditLog.id.asc())
    res = await db.execute(stmt)
    records = list(res.scalars().all())

    verification = await verify_audit_chain(db)

    return {
        "status": "success",
        "verified": verification.get("chain_intact", False),
        "total_records": len(records),
        "exported_by": current_user.username,
        "records": [
            {
                "id": r.id,
                "case_id": r.case_id,
                "actor": r.actor,
                "action": r.action,
                "detail": r.detail,
                "previous_hash": r.previous_hash,
                "hash": r.hash,
                "ip_address": r.ip_address,
                "correlation_id": r.correlation_id,
                "timestamp": r.ts.isoformat(),
            }
            for r in records
        ],
    }

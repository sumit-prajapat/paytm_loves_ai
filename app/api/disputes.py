from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dispute
from app.db.session import get_db

router = APIRouter(prefix="/disputes", tags=["Disputes"])


@router.get("/{dispute_id}")
async def get_dispute(dispute_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve details of a disputed transaction or chargeback claim."""
    stmt = select(Dispute).where(Dispute.id == dispute_id)
    res = await db.execute(stmt)
    dispute = res.scalar_one_or_none()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute record not found")

    return {
        "dispute_id": dispute.id,
        "txn_id": dispute.txn_id,
        "amount": dispute.amount,
        "reason": dispute.reason,
        "status": dispute.status,
        "deadline": dispute.deadline.isoformat(),
        "evidence_json": dispute.evidence_json,
    }

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Refund
from app.db.session import get_db

router = APIRouter(prefix="/refunds", tags=["Refunds"])


@router.get("/{txn_id}")
async def get_refund_by_transaction(txn_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve refund status, initiation timestamp, expected SLA, and bank reference code."""
    stmt = select(Refund).where(Refund.txn_id == txn_id)
    res = await db.execute(stmt)
    refund = res.scalar_one_or_none()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found for transaction")

    return {
        "refund_id": refund.id,
        "txn_id": refund.txn_id,
        "status": refund.status,
        "initiated_at": refund.initiated_at.isoformat(),
        "expected_by": refund.expected_by.isoformat(),
        "bank_ref": refund.bank_ref,
    }

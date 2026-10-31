from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_merchant_ownership
from app.db.models import Transaction, User
from app.db.session import get_db

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("")
async def get_transactions(
    merchant_id: str = Query(..., description="Merchant ID"),
    status: str | None = Query(None, description="Filter by transaction status"),
    from_date: str | None = Query(None, description="Start ISO date"),
    to_date: str | None = Query(None, description="End ISO date"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve transaction history with failure reasons and timestamps.

    Protected against IDOR: merchants can only query their own transactions.
    """
    verify_merchant_ownership(merchant_id, current_user)

    stmt = select(Transaction).where(Transaction.merchant_id == merchant_id)
    if status:
        stmt = stmt.where(Transaction.status == status)
    if from_date:
        try:
            dt_from = datetime.fromisoformat(from_date)
            stmt = stmt.where(Transaction.ts >= dt_from)
        except ValueError:
            pass
    if to_date:
        try:
            dt_to = datetime.fromisoformat(to_date)
            stmt = stmt.where(Transaction.ts <= dt_to)
        except ValueError:
            pass

    stmt = stmt.order_by(Transaction.ts.desc()).limit(limit)
    res = await db.execute(stmt)
    txns = list(res.scalars().all())

    return [
        {
            "txn_id": t.txn_id,
            "merchant_id": t.merchant_id,
            "amount": t.amount,
            "status": t.status,
            "mode": t.mode,
            "failure_reason": t.failure_reason,
            "timestamp": t.ts.isoformat(),
        }
        for t in txns
    ]

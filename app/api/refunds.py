from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_merchant_ownership
from app.db.models import Refund, Transaction, User
from app.db.session import get_db
from app.i18n.numbers import money

router = APIRouter(prefix="/refunds", tags=["Refunds"])


@router.get("/{txn_id}")
async def get_refund_by_transaction(txn_id: str, current_user: User = Depends(get_current_user),
                                    db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Refund, Transaction).join(Transaction, Refund.txn_id == Transaction.txn_id)
                            .where(Refund.txn_id == txn_id))).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Refund not found for transaction")
    refund, txn = row
    verify_merchant_ownership(txn.merchant_id, current_user)
    return {"refund_id": refund.id, "txn_id": refund.txn_id, "amount": money(txn.amount), "status": refund.status,
            "initiated_at": refund.initiated_at.isoformat(), "expected_by": refund.expected_by.isoformat(),
            "bank_ref": refund.bank_ref}

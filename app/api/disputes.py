from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_merchant_ownership
from app.db.models import Dispute, Transaction, User
from app.db.session import get_db
from app.i18n.numbers import money

router = APIRouter(prefix="/disputes", tags=["Disputes"])


@router.get("/{dispute_id}")
async def get_dispute(dispute_id: str, current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Dispute, Transaction).join(Transaction, Dispute.txn_id == Transaction.txn_id)
                            .where(Dispute.id == dispute_id))).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Dispute record not found")
    dispute, txn = row
    verify_merchant_ownership(txn.merchant_id, current_user)
    return {"dispute_id": dispute.id, "txn_id": dispute.txn_id, "amount": money(dispute.amount),
            "reason": dispute.reason, "status": dispute.status, "deadline": dispute.deadline.isoformat(),
            "evidence_json": dispute.evidence_json}

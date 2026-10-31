from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_merchant_ownership
from app.db.models import User
from app.db.session import get_db
from app.services.settlement_service import settlement_service

router = APIRouter(prefix="/settlements", tags=["Settlements"])


@router.get("/{merchant_id}")
async def get_settlement_by_merchant(
    merchant_id: str,
    date: str | None = Query(None, description="Settlement date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve settlement reconciliation details: expected, actual, gap, and line item deductions.

    Protected against IDOR: merchants can only access their own settlements.
    """
    verify_merchant_ownership(merchant_id, current_user)

    data = await settlement_service.get_settlement(db, merchant_id, date)
    if not data:
        raise HTTPException(status_code=404, detail="No settlement record found for merchant")
    return data

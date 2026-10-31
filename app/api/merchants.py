from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_merchant_ownership
from app.db.models import Merchant, User
from app.db.session import get_db

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.get("/{merchant_id}")
async def get_merchant(
    merchant_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch merchant profile, language preference, business type, device ID, and KYC status.

    Protected against IDOR: merchants can only inspect their own profile.
    """
    verify_merchant_ownership(merchant_id, current_user)

    stmt = select(Merchant).where(Merchant.id == merchant_id)
    res = await db.execute(stmt)
    merchant = res.scalar_one_or_none()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    return {
        "id": merchant.id,
        "name": merchant.name,
        "city": merchant.city,
        "state": merchant.state,
        "language": merchant.language,
        "business_type": merchant.business_type,
        "device_id": merchant.device_id,
        "joined_on": merchant.joined_on.isoformat(),
        "risk_tier": merchant.risk_tier,
        "kyc_status": merchant.kyc_status,
    }

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, verify_merchant_ownership
from app.db.models import User
from app.db.session import get_db
from app.services.device_service import device_service

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("/{device_id}/status")
async def get_device_status(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve Soundbox device health: battery percentage, network connection, and last seen heartbeat.

    Protected against IDOR: merchants can only inspect their own devices.
    """
    status = await device_service.get_device_status(db, device_id)
    if not status:
        raise HTTPException(status_code=404, detail="Device not found")

    device_merchant = status.get("merchant_id")
    if device_merchant:
        verify_merchant_ownership(device_merchant, current_user)

    return status

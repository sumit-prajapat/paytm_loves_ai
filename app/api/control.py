from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.models import User
from app.db.session import get_db
from app.schemas.control import ControlStateResponse, KillSwitchRequest
from app.services.kill_switch import kill_switch_service

router = APIRouter(prefix="/control", tags=["Control"])


@router.get("/state", response_model=ControlStateResponse)
async def get_control_state(
    current_user: User = Depends(require_roles(["ops_agent", "admin"])),
):
    """Retrieve current autonomy status and safety thresholds (Ops Agent or Admin)."""
    return kill_switch_service.get_state()


@router.post("/kill-switch", response_model=ControlStateResponse)
async def toggle_kill_switch(
    payload: KillSwitchRequest,
    current_user: User = Depends(require_roles(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Pause or resume all autonomous agent mutations (Admin only).

    When active, all safe actions downgrade to human escalations.
    """
    updated_state = await kill_switch_service.set_active(
        active=payload.active,
        actor=current_user.username or payload.actor,
        reason=payload.reason,
        db=db,
    )
    return updated_state

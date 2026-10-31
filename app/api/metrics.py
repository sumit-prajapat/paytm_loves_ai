from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.models import User
from app.db.session import get_db
from app.services.metrics_service import get_business_metrics

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
async def get_metrics(current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                      db: AsyncSession = Depends(get_db)):
    """Business metrics computed from the DB (SIMULATED DATA): deflection, escalation, tier mix, cost."""
    return await get_business_metrics(db)

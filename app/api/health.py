import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """System health check endpoint verifying database connectivity and configuration."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "demo_mode": settings.DEMO_MODE,
        "database": db_status,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

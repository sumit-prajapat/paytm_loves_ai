from fastapi import APIRouter

from app.services.metrics_service import metrics_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
async def get_metrics():
    """Live counters for tickets prevented, auto-resolutions, escalations, savings, and loan leads."""
    return metrics_service.get_metrics()

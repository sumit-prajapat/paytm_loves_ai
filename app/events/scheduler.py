import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import AsyncSessionLocal
from app.services.anomaly_service import anomaly_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_periodic_anomalies() -> None:
    """Periodic anomaly scan detecting settlement shortfalls, offline Soundboxes, and low battery."""
    try:
        async with AsyncSessionLocal() as session:
            anomalies = await anomaly_service.scan_anomalies(session)
            if anomalies:
                logger.info(f"Anomaly scanner detected {len(anomalies)} active anomalies across fleet")
    except Exception as e:
        logger.warning(f"Error in anomaly scanner: {e}")


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(check_periodic_anomalies, "interval", seconds=30, id="fleet_anomaly_check")
        scheduler.start()
        logger.info("Background anomaly scheduler started (30s interval)")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background anomaly scheduler stopped")

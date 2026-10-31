import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device


class DeviceService:
    """Inspects Soundbox status, battery thresholds, and heartbeat logs."""

    @staticmethod
    async def get_device_status(db: AsyncSession, device_id: str) -> dict[str, Any] | None:
        result = await db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        if not device:
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        # Ensure last_seen is timezone-aware
        last_seen = device.last_seen
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=datetime.timezone.utc)

        minutes_since_seen = (now - last_seen).total_seconds() / 60.0
        is_offline = minutes_since_seen > 120 or device.battery <= 10

        diagnosis = "healthy"
        action_recommendation = "none"

        if device.battery <= 20:
            diagnosis = "critical_low_battery"
            action_recommendation = "connect_charger"
        elif is_offline:
            diagnosis = "heartbeat_missing_offline"
            action_recommendation = "restart_device_check_network"

        return {
            "device_id": device.id,
            "merchant_id": device.merchant_id,
            "model": device.model,
            "battery": device.battery,
            "network": device.network,
            "last_seen": device.last_seen.isoformat(),
            "firmware": device.firmware,
            "is_offline": is_offline,
            "minutes_since_seen": round(minutes_since_seen, 1),
            "diagnosis": diagnosis,
            "action_recommendation": action_recommendation,
        }


device_service = DeviceService()

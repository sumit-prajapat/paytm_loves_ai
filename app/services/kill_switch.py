import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notify.in_app import notification_bus
from app.config import get_settings
from app.services.audit import record_audit_log

logger = logging.getLogger(__name__)


class KillSwitchService:
    """Global kill switch (R5): reads and explanations continue; autonomous actions escalate.

    State is process memory initialised from config (multi-worker persistence: Step F).
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._is_active: bool = settings.KILL_SWITCH_ACTIVE
        self._last_updated = datetime.datetime.now(datetime.timezone.utc)
        self._updated_by: str | None = "system_init"
        self._reason: str | None = "Initialized from config"

    def is_active(self) -> bool:
        return self._is_active

    def get_state(self) -> dict:
        s = get_settings()
        return {
            "kill_switch_active": self._is_active,
            "financial_impact_threshold_inr": s.FINANCIAL_IMPACT_THRESHOLD_INR,
            "auto_resolve_confidence_threshold": s.AUTO_RESOLVE_CONFIDENCE_THRESHOLD,
            "clarify_confidence_threshold": s.CLARIFY_CONFIDENCE_THRESHOLD,
            "last_updated": self._last_updated.isoformat(),
            "reason": self._reason,
            "updated_by": self._updated_by,
        }

    async def set_active(self, active: bool, actor: str, reason: str | None, db: AsyncSession) -> dict:
        old_state = self._is_active
        self._is_active = active
        self._last_updated = datetime.datetime.now(datetime.timezone.utc)
        self._updated_by = actor
        self._reason = reason
        action_name = "KILL_SWITCH_ENGAGED" if active else "KILL_SWITCH_DISENGAGED"
        logger.warning("Control state changed: %s by %s", action_name, actor)
        await record_audit_log(
            db, case_id="system_control", actor=actor, action=action_name,
            detail={"previous_state": old_state, "new_state": active, "reason": reason},
        )
        await db.commit()
        await notification_bus.push_console("killswitch_changed", self.get_state())
        return self.get_state()


kill_switch_service = KillSwitchService()

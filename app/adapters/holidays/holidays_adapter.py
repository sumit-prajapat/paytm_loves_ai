import datetime
from typing import Any

from app.db.seed import UPCOMING_FESTIVALS


class HolidaysAdapter:
    """Provides Indian holiday and festival awareness for proactive preparation."""

    @staticmethod
    def get_upcoming_festivals(days_ahead: int = 30) -> list[dict[str, Any]]:
        today = datetime.date.today()
        upcoming = []
        for fest in UPCOMING_FESTIVALS:
            try:
                f_date = datetime.date.fromisoformat(fest["date"])
                diff = (f_date - today).days
                if 0 <= diff <= days_ahead:
                    upcoming.append({
                        "name": fest["name"],
                        "date": fest["date"],
                        "region": fest["region"],
                        "days_until": diff,
                    })
            except Exception:
                pass
        return upcoming


holidays_adapter = HolidaysAdapter()

"""Anomaly detection rules for proactive merchant support."""
from typing import Any


def evaluate_settlement_anomaly(expected: float, actual: float, gap: float) -> dict[str, Any] | None:
    if gap > 0:
        return {
            "type": "settlement_short",
            "gap": gap,
            "expected": expected,
            "actual": actual,
        }
    return None


def evaluate_device_anomaly(battery: int, minutes_since_seen: float) -> dict[str, Any] | None:
    if battery <= 20:
        return {"type": "low_battery", "battery": battery}
    if minutes_since_seen > 120:
        return {"type": "soundbox_offline", "minutes_since_seen": minutes_since_seen}
    return None

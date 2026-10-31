import time
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IdempotencyRecord

# In-memory action cap tracking: (user_id, action_type) -> list of timestamps
_ACTION_TIMESTAMPS: dict[tuple[str, str], list[float]] = {}
MAX_TICKETS_PER_HOUR = 15


async def check_idempotency(
    db: AsyncSession,
    idempotency_key: str | None,
    user_id: str,
    endpoint: str,
) -> dict[str, Any] | None:
    """Checks whether this idempotency key was previously processed for this user.

    Returns the cached response dictionary if duplicate, or None if novel.
    """
    if not idempotency_key:
        return None

    stmt = select(IdempotencyRecord).where(
        IdempotencyRecord.key == idempotency_key,
        IdempotencyRecord.user_id == user_id,
    )
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()

    if record and record.response_json is not None:
        return dict(record.response_json) if isinstance(record.response_json, dict) else record.response_json

    return None


async def save_idempotency_record(
    db: AsyncSession,
    idempotency_key: str | None,
    user_id: str,
    endpoint: str,
    response_data: Any,
) -> None:
    """Saves the final response payload keyed by the idempotency token."""
    if not idempotency_key:
        return

    record = IdempotencyRecord(
        key=idempotency_key,
        user_id=user_id,
        endpoint=endpoint,
        response_json=response_data,
    )
    db.add(record)
    await db.commit()


def enforce_action_cap(user_id: str, action_type: str = "ticket", max_per_hour: int = MAX_TICKETS_PER_HOUR) -> None:
    """Enforces per-merchant action limits (e.g.

    max 15 tickets per hour) to stop runaway loops.
    """
    now = time.time()
    one_hour_ago = now - 3600.0

    key = (user_id, action_type)
    timestamps = _ACTION_TIMESTAMPS.get(key, [])
    # Filter to timestamps within the last hour
    recent = [t for t in timestamps if t > one_hour_ago]

    if len(recent) >= max_per_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Action limit exceeded: Merchant '{user_id}' has reached the maximum of {max_per_hour} {action_type}s per hour.",
        )

    recent.append(now)
    _ACTION_TIMESTAMPS[key] = recent

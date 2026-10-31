"""Short-lived per-subject dialogue state in the DB (stateless workers). Expires after 30 min."""
import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationState

TTL = datetime.timedelta(minutes=30)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


async def load_state(db: AsyncSession, subject_id: str) -> dict[str, Any]:
    row = (await db.execute(select(ConversationState).where(ConversationState.subject_id == subject_id))).scalar_one_or_none()
    if row is None or row.updated_at is None or _now() - row.updated_at.replace(tzinfo=None) > TTL:
        return {}
    return dict(row.data_json or {})


async def save_state(db: AsyncSession, subject_id: str, data: dict[str, Any]) -> None:
    row = (await db.execute(select(ConversationState).where(ConversationState.subject_id == subject_id))).scalar_one_or_none()
    if row is None:
        db.add(ConversationState(subject_id=subject_id, data_json=data, updated_at=_now()))
    else:
        row.data_json = data
        row.updated_at = _now()
    await db.flush()

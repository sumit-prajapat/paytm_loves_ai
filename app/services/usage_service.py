"""Usage ledger, per-user quotas and the global LLM budget guard (R12).

Everything is computed from the `usage_events` / `checkups` tables so limits hold across
stateless workers. No background job reads these tables.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Checkup, UsageEvent


def _start_of_day_utc() -> datetime.datetime:
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


@dataclass
class BudgetDecision:
    allowed: bool
    reason: str | None = None


class QuotaExceeded(Exception):
    def __init__(self, kind: str, limit: int) -> None:
        super().__init__(f"{kind} quota exceeded ({limit})")
        self.kind = kind
        self.limit = limit


async def record_usage(
    db: AsyncSession,
    *,
    user_id: str,
    kind: str,
    actor_id: str | None = None,
    session_id: str | None = None,
    case_id: str | None = None,
    request_type: str | None = None,
    channel: str | None = None,
    tier: int = 0,
    tokens: int = 0,
    cost_inr: float = 0.0,
    duration_ms: float = 0.0,
    outcome: str | None = None,
) -> None:
    db.add(
        UsageEvent(
            user_id=user_id,
            actor_id=actor_id,
            session_id=session_id,
            case_id=case_id,
            kind=kind,
            request_type=request_type,
            channel=channel,
            tier=tier,
            tokens=tokens,
            cost_inr=cost_inr,
            duration_ms=duration_ms,
            outcome=outcome,
        )
    )
    await db.flush()


async def checkups_today(db: AsyncSession, merchant_id: str) -> int:
    stmt = select(func.count(Checkup.id)).where(
        Checkup.merchant_id == merchant_id, Checkup.created_at >= _start_of_day_utc()
    )
    return int((await db.execute(stmt)).scalar_one())


async def enforce_checkup_quota(db: AsyncSession, merchant_id: str) -> None:
    limit = get_settings().CHECKUPS_PER_USER_PER_DAY
    if await checkups_today(db, merchant_id) >= limit:
        raise QuotaExceeded("checkups_per_day", limit)


async def llm_budget_check(
    db: AsyncSession, *, user_id: str, session_id: str | None
) -> BudgetDecision:
    """Per-user calls/tokens per day, per-session calls, and global INR per day."""
    s = get_settings()
    day = _start_of_day_utc()
    user_stmt = select(func.count(UsageEvent.id), func.coalesce(func.sum(UsageEvent.tokens), 0)).where(
        UsageEvent.user_id == user_id, UsageEvent.kind == "llm_call", UsageEvent.ts >= day
    )
    calls, tokens = (await db.execute(user_stmt)).one()
    if calls >= s.LLM_CALLS_PER_USER_PER_DAY:
        return BudgetDecision(False, "user_llm_calls_per_day")
    if tokens >= s.LLM_TOKENS_PER_USER_PER_DAY:
        return BudgetDecision(False, "user_llm_tokens_per_day")
    if session_id:
        sess_stmt = select(func.count(UsageEvent.id)).where(
            UsageEvent.session_id == session_id, UsageEvent.kind == "llm_call"
        )
        if (await db.execute(sess_stmt)).scalar_one() >= s.LLM_CALLS_PER_SESSION:
            return BudgetDecision(False, "session_llm_calls")
    global_stmt = select(func.coalesce(func.sum(UsageEvent.cost_inr), 0.0)).where(
        UsageEvent.kind == "llm_call", UsageEvent.ts >= day
    )
    spent = float((await db.execute(global_stmt)).scalar_one())
    if spent >= s.GLOBAL_LLM_BUDGET_INR_PER_DAY:
        return BudgetDecision(False, "global_llm_budget_inr_per_day")
    return BudgetDecision(True)

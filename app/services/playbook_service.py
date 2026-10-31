"""Playbook learning: a human-resolved escalation becomes a rule so the next similar case
auto-resolves. Playbook actions are limited to a SAFE set that never moves money (R3)."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Playbook

# action -> (issue types it may be used for, template key used to explain it)
SAFE_PLAYBOOK_ACTIONS: dict[str, tuple[set[str], str | None]] = {
    "explain_breakdown": ({"settlement_short"}, None),  # None = the finding's own explanation
    "guide_charger": ({"soundbox_offline"}, None),
    "guide_restart": ({"soundbox_offline"}, None),
    "request_evidence_upload": ({"chargeback_dispute"}, "dispute.playbook_evidence"),
}
DEFAULT_ACTION_FOR_ISSUE = {
    "chargeback_dispute": "request_evidence_upload",
    "settlement_short": "explain_breakdown",
    "soundbox_offline": "guide_charger",
}


def match_score(playbook: Playbook, conditions: dict[str, Any]) -> float:
    pb_conditions = playbook.conditions_json if isinstance(playbook.conditions_json, dict) else {}
    if not pb_conditions:
        return 0.8  # issue type only: below the default auto-resolve threshold
    matched = sum(1 for k, v in pb_conditions.items() if conditions.get(k) == v)
    return round(0.75 + 0.25 * matched / len(pb_conditions), 3)


class PlaybookService:
    @staticmethod
    async def match_playbook(
        db: AsyncSession, issue_type: str, conditions: dict[str, Any] | None = None
    ) -> tuple[Playbook | None, float]:
        candidates = (await db.execute(select(Playbook).where(Playbook.issue_type == issue_type))).scalars().all()
        best, best_score = None, 0.0
        for pb in candidates:
            score = match_score(pb, conditions or {})
            if score > best_score or (score == best_score and best and pb.times_used > best.times_used):
                best, best_score = pb, score
        return best, best_score

    @staticmethod
    def is_safe(playbook: Playbook) -> bool:
        spec = SAFE_PLAYBOOK_ACTIONS.get(playbook.action)
        return bool(spec and playbook.issue_type in spec[0])

    @staticmethod
    async def create_playbook(
        db: AsyncSession,
        issue_type: str,
        root_cause: str,
        action: str,
        conditions: dict[str, Any] | None = None,
        created_from_case: str | None = None,
    ) -> Playbook:
        if action not in SAFE_PLAYBOOK_ACTIONS or issue_type not in SAFE_PLAYBOOK_ACTIONS[action][0]:
            raise ValueError(f"Action '{action}' is not a safe playbook action for '{issue_type}'")
        pb = Playbook(
            id=f"pb_{uuid.uuid4().hex[:8]}",
            issue_type=issue_type,
            root_cause=root_cause,
            action=action,
            conditions_json=conditions or {},
            created_from_case=created_from_case,
            times_used=0,
        )
        db.add(pb)
        await db.flush()
        return pb

    @staticmethod
    async def increment_usage(db: AsyncSession, playbook: Playbook) -> None:
        playbook.times_used += 1
        await db.flush()


playbook_service = PlaybookService()

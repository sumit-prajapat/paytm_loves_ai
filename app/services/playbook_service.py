import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Playbook


class PlaybookService:
    """Manages the continuous learning loop: converts resolved escalations into playbooks

    so repeat issues auto-resolve with 0 tickets.
    """

    @staticmethod
    async def match_playbook(
        db: AsyncSession,
        issue_type: str,
        conditions: dict[str, Any] | None = None,
    ) -> tuple[Playbook | None, float]:
        """Looks up stored playbook by issue_type.

        Returns (playbook, match_score). A match score >= 0.8 allows auto-resolution.
        """
        stmt = select(Playbook).where(Playbook.issue_type == issue_type)
        res = await db.execute(stmt)
        candidates = list(res.scalars().all())

        if not candidates:
            return None, 0.0

        # Exact issue type matched
        best_match = candidates[0]
        score = 0.90  # High confidence match

        # If conditions provided, verify match
        if conditions and best_match.conditions_json:
            matches = 0
            total = len(best_match.conditions_json)
            for k, v in best_match.conditions_json.items():
                if conditions.get(k) == v:
                    matches += 1
            if total > 0:
                score = 0.70 + (0.28 * (matches / total))

        return best_match, round(score, 2)

    @staticmethod
    async def create_playbook(
        db: AsyncSession,
        issue_type: str,
        root_cause: str,
        action: str,
        conditions: dict[str, Any] | None = None,
        created_from_case: str | None = None,
    ) -> Playbook:
        """Stores a newly learned playbook rule from a human-resolved escalation."""
        playbook_id = f"pb_{uuid.uuid4().hex[:8]}"
        pb = Playbook(
            id=playbook_id,
            issue_type=issue_type,
            root_cause=root_cause,
            action=action,
            conditions_json=conditions or {},
            created_from_case=created_from_case,
            times_used=0,
        )
        db.add(pb)
        await db.commit()
        await db.refresh(pb)
        return pb

    @staticmethod
    async def increment_usage(db: AsyncSession, playbook_id: str) -> None:
        stmt = select(Playbook).where(Playbook.id == playbook_id)
        res = await db.execute(stmt)
        pb = res.scalar_one_or_none()
        if pb:
            pb.times_used += 1
            await db.commit()


playbook_service = PlaybookService()

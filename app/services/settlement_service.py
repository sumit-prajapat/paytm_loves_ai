import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Settlement


class SettlementService:
    """Deterministic settlement query, reconciliation, and breakdown service."""

    @staticmethod
    async def get_settlement(db: AsyncSession, merchant_id: str, date_str: str | None = None) -> dict[str, Any] | None:
        if not date_str:
            date_str = datetime.date.today().isoformat()

        stmt = (
            select(Settlement)
            .options(selectinload(Settlement.items))
            .where(Settlement.merchant_id == merchant_id, Settlement.date == date_str)
        )
        result = await db.execute(stmt)
        settlement = result.scalar_one_or_none()

        if not settlement:
            # Fallback to latest settlement if specific date not found
            fallback_stmt = (
                select(Settlement)
                .options(selectinload(Settlement.items))
                .where(Settlement.merchant_id == merchant_id)
                .order_by(Settlement.date.desc())
            )
            fallback_result = await db.execute(fallback_stmt)
            settlement = fallback_result.scalar_one_or_none()

        if not settlement:
            return None

        items_breakdown = []
        total_items_sum = 0.0
        refund_adj = 0.0
        fee_sum = 0.0
        chargeback_hold = 0.0

        for item in settlement.items:
            items_breakdown.append({"type": item.type, "amount": item.amount})
            total_items_sum += item.amount
            if item.type == "refund_adjustment":
                refund_adj += item.amount
            elif item.type == "fee":
                fee_sum += item.amount
            elif item.type == "chargeback_hold":
                chargeback_hold += item.amount

        is_reconciled = abs(settlement.gap - total_items_sum) < 0.01

        return {
            "id": settlement.id,
            "merchant_id": settlement.merchant_id,
            "date": settlement.date,
            "expected": settlement.expected,
            "actual": settlement.actual,
            "gap": settlement.gap,
            "items": items_breakdown,
            "refund_adjustment": refund_adj,
            "fees": fee_sum,
            "chargeback_hold": chargeback_hold,
            "is_reconciled": is_reconciled,
            "explanation_needed": settlement.gap > 0,
        }


settlement_service = SettlementService()

import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Settlement


class SettlementService:
    """Deterministic settlement query, reconciliation and breakdown for ONE merchant."""

    @staticmethod
    async def get_settlement(
        db: AsyncSession, merchant_id: str, date_str: str | None = None
    ) -> dict[str, Any] | None:
        base = select(Settlement).options(selectinload(Settlement.items)).where(
            Settlement.merchant_id == merchant_id
        )
        if date_str:
            base = base.where(Settlement.date == date_str)
        # Latest first; LIMIT 1 so duplicate rows can never raise MultipleResultsFound.
        stmt = base.order_by(Settlement.date.desc(), Settlement.id.desc()).limit(1)
        settlement = (await db.execute(stmt)).scalars().first()
        if settlement is None:
            return None

        refund_adj = fee_sum = chargeback_hold = other = 0.0
        items = []
        for item in settlement.items:
            items.append({"type": item.type, "amount": item.amount})
            if item.type == "refund_adjustment":
                refund_adj += item.amount
            elif item.type == "fee":
                fee_sum += item.amount
            elif item.type == "chargeback_hold":
                chargeback_hold += item.amount
            else:
                other += item.amount
        explained = round(refund_adj + fee_sum + chargeback_hold + other, 2)
        return {
            "id": settlement.id,
            "merchant_id": settlement.merchant_id,
            "date": settlement.date,
            "is_today": settlement.date == datetime.date.today().isoformat(),
            "expected": settlement.expected,
            "actual": settlement.actual,
            "gap": settlement.gap,
            "items": items,
            "refund_adjustment": refund_adj,
            "fees": fee_sum,
            "chargeback_hold": chargeback_hold,
            "other_deductions": other,
            "explained_total": explained,
            "is_reconciled": abs(settlement.gap - explained) < 0.01,
            "explanation_needed": settlement.gap > 0,
        }


settlement_service = SettlementService()

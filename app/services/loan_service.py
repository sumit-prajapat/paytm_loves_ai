import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LoanProfile, LoanRequest


class LoanService:
    """Deterministic loan calculations and consent-first workflow management."""

    @staticmethod
    def calculate_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> dict[str, float]:
        """Calculates standard reducing-balance monthly EMI and total interest deterministically."""
        if tenure_months <= 0 or principal <= 0:
            return {"principal": principal, "tenure_months": tenure_months, "rate_pct": annual_rate_pct, "monthly_emi": 0.0, "total_payable": principal}

        monthly_rate = (annual_rate_pct / 100.0) / 12.0
        if monthly_rate == 0:
            emi = principal / tenure_months
        else:
            factor = math.pow(1.0 + monthly_rate, tenure_months)
            emi = (principal * monthly_rate * factor) / (factor - 1.0)

        monthly_emi = round(emi, 2)
        total_payable = round(monthly_emi * tenure_months, 2)
        total_interest = round(total_payable - principal, 2)

        return {
            "principal": round(principal, 2),
            "tenure_months": tenure_months,
            "rate_pct": annual_rate_pct,
            "monthly_emi": monthly_emi,
            "total_payable": total_payable,
            "total_interest": total_interest,
            "daily_deduction": round(monthly_emi / 30.0, 2),
        }

    @staticmethod
    async def get_eligibility(db: AsyncSession, merchant_id: str) -> dict[str, Any]:
        """Checks merchant loan eligibility based on transaction history and credit score."""
        result = await db.execute(
            select(LoanProfile).where(LoanProfile.merchant_id == merchant_id)
        )
        profile = result.scalar_one_or_none()

        if not profile or profile.eligible_limit <= 0:
            return {
                "merchant_id": merchant_id,
                "eligible": False,
                "max_amount": 0.0,
                "rate": 15.0,
                "tenure_options": [6, 12],
                "reason": "Insufficient transaction vintage or below threshold score",
            }

        return {
            "merchant_id": merchant_id,
            "eligible": True,
            "max_amount": profile.eligible_limit,
            "rate": 14.0 if profile.score >= 750 else 16.5,
            "tenure_options": [6, 9, 12, 18],
            "monthly_volume": profile.monthly_volume,
            "vintage_months": profile.vintage_months,
            "score": profile.score,
        }

    @staticmethod
    async def create_request(
        db: AsyncSession,
        merchant_id: str,
        amount: float,
        tenure_months: int = 12,
        confidence: float = 0.91,
    ) -> LoanRequest:
        """Creates a loan request in 'awaiting_approval' status.

        Human approval in console is mandatory (Rule R3).
        """
        eligibility = await LoanService.get_eligibility(db, merchant_id)
        rate = eligibility.get("rate", 15.0)
        emi_calc = LoanService.calculate_emi(amount, rate, tenure_months)

        request_id = f"loan_req_{uuid.uuid4().hex[:10]}"
        loan_req = LoanRequest(
            id=request_id,
            merchant_id=merchant_id,
            amount=amount,
            tenure=tenure_months,
            rate=rate,
            emi=emi_calc["monthly_emi"],
            status="awaiting_approval",  # Strictly human-approved!
            confidence=confidence,
            approved_by=None,
        )
        db.add(loan_req)
        await db.commit()
        await db.refresh(loan_req)
        return loan_req

    @staticmethod
    async def update_status(db: AsyncSession, request_id: str, new_status: str, operator_id: str) -> LoanRequest | None:
        """Approves or rejects a loan request from human console."""
        result = await db.execute(
            select(LoanRequest).where(LoanRequest.id == request_id)
        )
        loan_req = result.scalar_one_or_none()
        if not loan_req:
            return None

        loan_req.status = new_status
        loan_req.approved_by = operator_id
        await db.commit()
        await db.refresh(loan_req)
        return loan_req


loan_service = LoanService()

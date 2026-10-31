from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles, verify_merchant_ownership
from app.db.models import User
from app.db.session import get_db
from app.services.audit import record_audit_log
from app.services.loan_service import loan_service
from app.services.metrics_service import metrics_service

router = APIRouter(prefix="/loans", tags=["Loans"])


class EMIRequest(BaseModel):
    principal: float = Field(..., ge=1000, description="Loan principal amount in INR")
    rate: float = Field(14.0, ge=1.0, description="Annual interest rate percentage")
    tenure_months: int = Field(12, ge=1, le=36, description="Tenure in months")


class LoanApplicationRequest(BaseModel):
    merchant_id: str = Field(..., description="Target merchant ID")
    amount: float = Field(..., ge=1000, description="Requested loan amount in INR")
    tenure_months: int = Field(12, ge=1, le=36, description="Tenure in months")
    confidence: float = Field(0.91, description="Agent confidence score")


class LoanReviewRequest(BaseModel):
    operator_id: str = Field("human_supervisor_01", description="Human console supervisor ID")
    notes: str | None = Field(None, description="Optional notes on credit decision")
    confirm: bool = Field(False, description="Explicit two-step confirmation required for financial effect")
    confirm_token: str | None = Field(None, description="Cryptographic confirmation token from console preview")


@router.get("/eligibility/{merchant_id}")
async def get_loan_eligibility(
    merchant_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check working-capital loan pre-approval eligibility for a merchant with IDOR verification."""
    verify_merchant_ownership(merchant_id, current_user)
    return await loan_service.get_eligibility(db, merchant_id)


@router.post("/emi")
async def calculate_emi(payload: EMIRequest):
    """Calculates reducing-balance monthly EMI, total interest, and daily deduction from settlements."""
    return loan_service.calculate_emi(
        principal=payload.principal,
        annual_rate_pct=payload.rate,
        tenure_months=payload.tenure_months,
    )


@router.post("/requests")
async def create_loan_request(
    payload: LoanApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a loan application strictly with 'awaiting_approval' status.

    Human approval is non-negotiable (Rule R3).
    """
    verify_merchant_ownership(payload.merchant_id, current_user)

    req = await loan_service.create_request(
        db=db,
        merchant_id=payload.merchant_id,
        amount=payload.amount,
        tenure_months=payload.tenure_months,
        confidence=payload.confidence,
    )
    metrics_service.record_loan_lead()

    await record_audit_log(
        db=db,
        case_id=req.id,
        actor=current_user.username,
        action="LOAN_APPLICATION_CREATED",
        detail={"amount": req.amount, "tenure": req.tenure, "merchant_id": req.merchant_id},
    )
    await db.commit()

    return {
        "request_id": req.id,
        "merchant_id": req.merchant_id,
        "amount": req.amount,
        "tenure": req.tenure,
        "rate": req.rate,
        "emi": req.emi,
        "status": req.status,
        "confidence": req.confidence,
        "human_approval_required": True,
        "message": "Loan request logged in console as 'Awaiting approval'. A human supervisor must approve.",
    }


@router.post("/requests/{request_id}/approve")
async def approve_loan(
    request_id: str,
    payload: LoanReviewRequest,
    current_user: User = Depends(require_roles(["ops_agent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Human supervisor approves a loan request from the Ops Console with two-step confirmation."""
    # Enforce two-step confirmation requirement for actions with financial impact
    if not payload.confirm and not payload.confirm_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-step confirmation required for financial commitment: provide confirm=true or confirm_token",
        )

    operator_actor = current_user.username or payload.operator_id
    req = await loan_service.update_status(db, request_id, "approved", operator_actor)
    if not req:
        raise HTTPException(status_code=404, detail="Loan request not found")

    await record_audit_log(
        db=db,
        case_id=req.id,
        actor=operator_actor,
        action="LOAN_APPROVED_BY_HUMAN",
        detail={"request_id": req.id, "amount": req.amount, "notes": payload.notes},
    )
    await db.commit()

    return {"request_id": req.id, "status": "approved", "approved_by": operator_actor}


@router.post("/requests/{request_id}/reject")
async def reject_loan(
    request_id: str,
    payload: LoanReviewRequest,
    current_user: User = Depends(require_roles(["ops_agent", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Human supervisor rejects a loan request from the Ops Console."""
    operator_actor = current_user.username or payload.operator_id
    req = await loan_service.update_status(db, request_id, "rejected", operator_actor)
    if not req:
        raise HTTPException(status_code=404, detail="Loan request not found")

    await record_audit_log(
        db=db,
        case_id=req.id,
        actor=operator_actor,
        action="LOAN_REJECTED_BY_HUMAN",
        detail={"request_id": req.id, "notes": payload.notes},
    )
    await db.commit()

    return {"request_id": req.id, "status": "rejected", "approved_by": operator_actor}

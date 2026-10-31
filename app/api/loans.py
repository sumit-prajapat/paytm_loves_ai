"""Loans: eligibility, EMI calculator, explicit application (awaiting human approval),
human approve/reject with a strict state machine (R3)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notify.in_app import notification_bus
from app.agents.guardian import guardian_agent
from app.core.deps import get_current_user, require_roles, verify_merchant_ownership
from app.db.models import LoanRequest, OfferConsent, User
from app.db.session import get_db
from app.i18n.numbers import money
from app.services.audit import record_audit_log
from app.services.loan_service import InvalidLoanTransition, loan_service

router = APIRouter(prefix="/loans", tags=["Loans"])


class EMIRequest(BaseModel):
    principal: float = Field(..., ge=1000, le=10_000_000)
    rate: float = Field(14.0, ge=1.0, le=60.0)
    tenure_months: int = Field(12, ge=1, le=60)


class LoanApplicationRequest(BaseModel):
    merchant_id: str = Field(..., max_length=64)
    amount: float = Field(..., ge=1000, le=10_000_000)
    tenure_months: int = Field(12, ge=1, le=60)


class LoanReviewRequest(BaseModel):
    notes: str | None = Field(None, max_length=1000)
    confirm: bool = Field(False, description="Explicit second step required for a financial decision")


def _req(r: LoanRequest) -> dict:
    return {"request_id": r.id, "merchant_id": r.merchant_id, "amount": money(r.amount), "tenure_months": r.tenure,
            "rate_pct": r.rate, "emi": money(r.emi), "status": r.status, "approved_by": r.approved_by}


@router.get("/eligibility/{merchant_id}")
async def get_loan_eligibility(merchant_id: str, current_user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    verify_merchant_ownership(merchant_id, current_user)
    e = await loan_service.get_eligibility(db, merchant_id)
    return {**e, "max_amount_money": money(e.get("max_amount", 0))}


@router.post("/emi")
async def calculate_emi(payload: EMIRequest, current_user: User = Depends(get_current_user)):
    out = loan_service.calculate_emi(payload.principal, payload.rate, payload.tenure_months)
    return {**out, "monthly_emi_money": money(out["monthly_emi"]), "total_payable_money": money(out["total_payable"])}


@router.post("/requests")
async def create_loan_request(payload: LoanApplicationRequest, current_user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    """Explicit 'Apply' button. Always lands in awaiting_approval for a human."""
    verify_merchant_ownership(payload.merchant_id, current_user)
    decision = guardian_agent.evaluate("create_loan_request")
    if not decision.allowed:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Guardian: {decision.reason}")
    eligibility = await loan_service.get_eligibility(db, payload.merchant_id)
    if not eligibility.get("eligible"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Merchant is not eligible for a loan")
    req = await loan_service.create_request(db, payload.merchant_id, payload.amount, payload.tenure_months)
    consent = (await db.execute(select(OfferConsent).where(OfferConsent.merchant_id == payload.merchant_id))).scalar_one_or_none()
    if consent is not None:
        consent.status = "accepted"
    await record_audit_log(db, case_id=req.id, actor=current_user.username, action="LOAN_APPLICATION_CREATED",
                           detail={"amount": req.amount, "tenure": req.tenure, "merchant_id": req.merchant_id})
    await db.commit()
    await notification_bus.push_console("loan_request_updated", _req(req))
    return {**_req(req), "human_approval_required": True}


@router.get("/requests")
async def list_loan_requests(status_filter: str = "awaiting_approval",
                             current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                             db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(LoanRequest).where(LoanRequest.status == status_filter))).scalars().all()
    return [_req(r) for r in rows]


async def _decide(request_id: str, new_status: str, payload: LoanReviewRequest, user: User, db: AsyncSession):
    if new_status == "approved" and not payload.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Two-step confirmation required: set confirm=true")
    try:
        req = await loan_service.update_status(db, request_id, new_status, user.username)
    except InvalidLoanTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Loan request not found")
    await record_audit_log(db, case_id=req.id, actor=user.username,
                           action=f"LOAN_{new_status.upper()}_BY_HUMAN",
                           detail={"request_id": req.id, "amount": req.amount, "notes": payload.notes})
    await db.commit()
    await notification_bus.push_console("loan_request_updated", _req(req))
    return _req(req)


@router.post("/requests/{request_id}/approve")
async def approve_loan(request_id: str, payload: LoanReviewRequest,
                       current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                       db: AsyncSession = Depends(get_db)):
    return await _decide(request_id, "approved", payload, current_user, db)


@router.post("/requests/{request_id}/reject")
async def reject_loan(request_id: str, payload: LoanReviewRequest,
                      current_user: User = Depends(require_roles(["ops_agent", "admin"])),
                      db: AsyncSession = Depends(get_db)):
    return await _decide(request_id, "rejected", payload, current_user, db)

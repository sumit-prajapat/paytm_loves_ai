from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.captain import captain_agent
from app.core.deps import get_current_user, verify_merchant_ownership, verify_traveller_ownership
from app.core.security import detect_prompt_injection, mask_pii, sanitize_agent_output
from app.db.models import User
from app.db.session import get_db
from app.services.audit import record_audit_log

router = APIRouter(prefix="/chat", tags=["Conversation"])


class ChatRequest(BaseModel):
    user_id: str = Field("m_ramesh", description="Merchant or Traveller ID")
    role: str = Field("merchant", description="Role: merchant | traveller")
    message: str = Field(..., description="User query or utterance (Hindi, Hinglish, English)")
    language: str | None = Field(None, description="Optional explicit language code")


@router.post("")
async def send_chat_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Primary chat endpoint for merchants and travellers.

    Protected with JWT auth, IDOR verification, prompt-injection defense, and sensitive-data guards.
    """
    # 1. IDOR Ownership Check
    if payload.role == "merchant":
        verify_merchant_ownership(payload.user_id, current_user)
    elif payload.role == "traveller":
        verify_traveller_ownership(payload.user_id, current_user)

    user_query = payload.message.strip()

    # 2. Sensitive Data Guard (PIN, OTP, CVV, Card Numbers)
    masked_query = mask_pii(user_query)
    if "[REDACTED_CREDENTIAL]" in masked_query or "****-****-" in masked_query:
        await record_audit_log(
            db=db,
            case_id=payload.user_id,
            actor=current_user.username,
            action="SENSITIVE_CREDENTIAL_BLOCKED",
            detail={"masked_input": masked_query, "warning": "User submitted PIN/OTP/Card info"},
        )
        await db.commit()
        return {
            "case_id": f"sec_pin_{current_user.id}",
            "status": "refused",
            "reply_text": (
                "Savdhani: Paytm ya Saarthi kabhi bhi aapse apna UPI PIN, OTP ya password nahi maangta. "
                "Kripya ise kisi ke saath saajha na karein. Suraksha ke liye humne ise process nahi kiya."
            ),
            "language": payload.language or "hi",
            "sensitive_data_blocked": True,
            "zero_ticket": True,
        }

    # 3. Prompt Injection Defense
    is_injection, reason = detect_prompt_injection(user_query)
    if is_injection:
        await record_audit_log(
            db=db,
            case_id=payload.user_id,
            actor=current_user.username,
            action="PROMPT_INJECTION_BLOCKED",
            detail={"reason": reason, "raw_snippet": user_query[:100]},
        )
        await db.commit()
        return {
            "case_id": f"sec_inj_{current_user.id}",
            "status": "refused",
            "reply_text": (
                "Kshama karein, Saarthi keval pradhikrit sahayata niyamawali ke antargat hi sahayata kar sakta hai. "
                "System instructions ya anधिकrit nirdesh sweekar nahi kiye ja sakte."
            ),
            "language": payload.language or "hi",
            "prompt_injection_blocked": True,
            "zero_ticket": True,
        }

    # 4. Multi-Agent Turn Execution
    turn_result = await captain_agent.run_turn(
        user_id=payload.user_id,
        message=user_query,
        role=payload.role,
        language=payload.language or "hi",
        db=db,
    )

    # 5. Output Sanitization (block leaking keys, tracebacks, or system internals)
    if "reply_text" in turn_result:
        turn_result["reply_text"] = sanitize_agent_output(turn_result["reply_text"])

    return turn_result

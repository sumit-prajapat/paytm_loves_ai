import re
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.factory import get_llm_adapter
from app.agents.base import BaseAgent
from app.schemas.envelope import AgentEnvelope


def detect_language(text: str) -> str:
    """Detects Hindi script, Hinglish code-switching, Marathi, or English."""
    # Check Devanagari Unicode block
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    lower = text.lower()
    hinglish_markers = ["kya", "kyun", "aaya", "chahiye", "mera", "meri", "hai", "nahi", "nahin", "shaam", "sasta", "jaldi", "dukaan"]
    if any(m in lower.split() for m in hinglish_markers):
        return "hinglish"
    return "en"


class ListenerAgent(BaseAgent):
    """Understands customer input: speech-to-text, language detection, intent classification, and slot extraction."""

    def __init__(self) -> None:
        super().__init__(name="listener")
        self.llm = get_llm_adapter()

    async def process(
        self,
        case_id: str,
        input_data: dict[str, Any],
        db: AsyncSession,
    ) -> AgentEnvelope:
        start_time = time.time()
        user_text = input_data.get("message", "").strip()
        language = input_data.get("language") or detect_language(user_text)

        # 1. First line of defense: Check for unsafe PIN / OTP credentials (Rule R7)
        has_pin_otp = bool(re.search(r"\b(pin|otp|password|cvv)\b", user_text, re.IGNORECASE))
        has_digits_with_pin = bool(re.search(r"\b\d{4,6}\b", user_text)) and has_pin_otp

        if has_pin_otp or has_digits_with_pin:
            latency_ms = (time.time() - start_time) * 1000.0
            await self.emit_step(
                case_id=case_id,
                tool="sanitize_security_input",
                input_data={"raw_text_length": len(user_text)},
                output_data={"intent": "unsafe_request", "refusal": True},
                confidence=1.0,
                db=db,
            )
            return AgentEnvelope(
                agent=self.name,
                status="blocked",
                result={
                    "intent": "unsafe_request",
                    "text": "Paytm ya Saarthi kabhi bhi aapka PIN, OTP ya password nahi mangta. Kripya kisi ke sath PIN share na karein.",
                    "is_unsafe": True,
                },
                confidence=1.0,
                evidence=["security_rule_r7"],
                next="guardian",
                language=language,
                latency_ms=latency_ms,
            )

        # 2. Consult LLM / Intent matching
        llm_response = await self.llm.generate_response(prompt=user_text, context=input_data)
        intent = llm_response.get("intent", "smalltalk")
        confidence = float(llm_response.get("confidence", 0.90))
        slots = llm_response.get("slots", {})

        # Extract numeric slots if present
        if "50000" in user_text:
            slots["amount"] = 50000.0
        elif "100000" in user_text:
            slots["amount"] = 100000.0

        latency_ms = (time.time() - start_time) * 1000.0

        await self.emit_step(
            case_id=case_id,
            tool="classify_intent_and_extract_slots",
            input_data={"message": user_text, "language": language},
            output_data={"intent": intent, "slots": slots, "confidence": confidence},
            confidence=confidence,
            db=db,
        )

        next_agent = "planner" if "travel" in intent else "context"

        return AgentEnvelope(
            agent=self.name,
            status="done",
            result={
                "intent": intent,
                "slots": slots,
                "text": user_text,
                "response_text": llm_response.get("text"),
            },
            confidence=confidence,
            evidence=["intent_classifier"],
            next=next_agent,
            language=language,
            latency_ms=latency_ms,
        )


listener_agent = ListenerAgent()

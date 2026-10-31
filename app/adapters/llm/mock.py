import logging
from typing import Any

from app.adapters.llm.base import BaseLLMAdapter

logger = logging.getLogger(__name__)


class MockLLM(BaseLLMAdapter):
    """Deterministic, scripted Mock LLM that runs completely offline for golden demo reliability."""

    def __init__(self) -> None:
        logger.info("MockLLM initialized (OFFLINE DETERMINISTIC MODE)")

    async def generate_response(
        self,
        prompt: str,
        system_instruction: str | None = None,
        context: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        p_lower = prompt.lower()
        context = context or {}

        # 1. Unsafe PIN / OTP requests
        if any(w in p_lower for w in ["otp", "pin", "password", "cvv", "mera pin"]):
            return {
                "intent": "unsafe_request",
                "text": "Paytm ya Saarthi kabhi bhi aapka PIN ya OTP nahi mangta. Kripya apna PIN/OTP kisi ke sath share na karein. Yeh fraud ho sakta hai.",
                "action": "refuse_and_warn",
                "confidence": 1.0,
            }

        # 2. Settlement short (Hero Scenario A)
        if any(w in p_lower for w in ["settlement", "kam aaya", "paisa kam", "cut gaya", "short", "deduction"]):
            return {
                "intent": "settlement_short",
                "text": "Ramesh ji, aaj ka settlement ₹1,800 kam aaya hai. ₹1,200 refund adjust hua aur ₹600 fees. Aapko kuch karne ki zaroorat nahi.",
                "action": "explain_settlement",
                "confidence": 0.96,
                "tool_calls": [{"tool": "get_settlement_breakdown", "args": {"merchant_id": context.get("merchant_id", "m_ramesh")}}],
            }

        # 3. Soundbox offline / battery (Hero Scenario B)
        if any(w in p_lower for w in ["soundbox", "battery", "awaaz", "chalu nahi", "offline"]):
            battery = context.get("battery", 12)
            return {
                "intent": "soundbox_offline",
                "text": f"Soundbox ki battery {battery}% hai. Kripya charger lagaiye aur network check kijiye.",
                "action": "voice_instruction_connect_charger",
                "confidence": 0.94,
                "tool_calls": [{"tool": "get_device_status", "args": {"device_id": context.get("device_id", "soundbox_ramesh_01")}}],
            }

        # 4. Refund / failed payment (Hero Scenario C)
        if any(w in p_lower for w in ["fail", "refund", "paisa kab aayega", "wapas", "pending"]):
            return {
                "intent": "refund_status",
                "text": "Aapka ₹1,450 ka refund samay seema se zyada vilambit hai. Humne ise prathmikta par banking team ko bhej diya hai (Bank Ref REF9876543210IN).",
                "action": "check_and_escalate_refund",
                "confidence": 0.92,
                "tool_calls": [{"tool": "get_refund_status", "args": {"txn_id": "txn_sunita_refund_01"}}],
            }

        # 4b. Chargeback Dispute (Hero Scenario D - Risky Case)
        if any(w in p_lower for w in ["chargeback", "dispute", "fraud", "stolen", "unauthorized", "claim"]):
            return {
                "intent": "chargeback_dispute",
                "text": "₹6,500 ka chargeback dispute paya gaya hai. Humare risk specialist ko case bhej diya gaya hai.",
                "action": "escalate_to_risk_specialist",
                "confidence": 0.55,  # Low confidence triggers escalation!
            }

        # 4c. Ambiguous query needing clarification
        if any(w in p_lower for w in ["kahan gaya", "samajh nahi aa raha", "book travel tomorrow"]):
            return {
                "intent": "ambiguous_query",
                "text": "Kripya vistaar se batayein, aapko settlement, soundbox ya kisi transaction me sahayata chahiye?",
                "action": "ask_clarifying_question",
                "confidence": 0.70,  # 0.60 to 0.85 requires clarification!
            }

        # 5. Decline offer (Consent-First rule: check decline first)
        if any(w in p_lower for w in ["nahi chahiye", "no", "nahin", "decline", "mat do", "mat bhejo", "baad mein"]):
            return {
                "intent": "decline_offer",
                "text": "Theek hai Ramesh ji, humne note kar liya hai. Hum dobara loan ka sujhav nahi denge. Aapka din shubh ho!",
                "action": "log_refusal_and_stop",
                "confidence": 1.0,
            }

        # 6. Loan EMI inquiry / Loan interest (Hero Scenario F)
        if any(w in p_lower for w in ["loan", "emi", "50000", "chahiye", "karz"]):
            return {
                "intent": "loan_emi_query",
                "text": "₹50,000 ke liye 12 mahine ki EMI ₹4,520 hogi (14.0% annual rate par). Daily subah settlement se adjust hoti hai.",
                "action": "calculate_emi",
                "confidence": 0.95,
                "tool_calls": [{"tool": "calculate_emi", "args": {"amount": 50000.0, "tenure_months": 12}}],
            }

        # 7. Travel flight request (Hero Scenario E)
        if any(w in p_lower for w in ["flight", "delhi", "mumbai", "kal shaam", "sasta", "jaldi", "ticket"]):
            return {
                "intent": "travel_flight_request",
                "slots": {
                    "origin": "DEL",
                    "destination": "BOM",
                    "window": "evening",
                    "preference": "fast and cheap",
                },
                "text": "Ye ₹400 zyada hai par 35 minute jaldi pahunchata hai aur free cancellation hai.",
                "action": "search_and_rank_flights",
                "confidence": 0.95,
            }

        # 8. Trick: "Just book it and pay for me"
        if any(w in p_lower for w in ["book it and pay", "payment kar do", "pay for me", "khud pay karo"]):
            return {
                "intent": "autonomous_payment_attempt",
                "text": "Suraksha niyamon ke anusar Saarthi kabhi khud payment nahi karta. Kripya Review and Pay button daba kar apna UPI PIN enter karein.",
                "action": "refuse_autonomous_payment",
                "confidence": 1.0,
            }

        # Default fallback
        return {
            "intent": "smalltalk",
            "text": "Namaste! Main Saarthi hoon, aapka AI teammate. Main aapki settlement, Soundbox, loan, ya flight booking mein kya sahayata kar sakta hoon?",
            "action": "general_reply",
            "confidence": 0.85,
        }

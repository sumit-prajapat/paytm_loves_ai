import logging
from typing import Any

from app.adapters.stt.base import BaseSTTAdapter

logger = logging.getLogger(__name__)

# Pre-recorded audio clip transcript lookup table
AUDIO_CLIP_TRANSCRIPTS = {
    "settlement_short.wav": {
        "text": "Ramesh ji bol raha hoon, aaj mera settlement kam kyun aaya hai?",
        "language": "hi",
        "confidence": 0.98,
    },
    "soundbox_offline.wav": {
        "text": "Soundbox achanak se band ho gaya hai, payment bol nahi raha.",
        "language": "hi",
        "confidence": 0.96,
    },
    "refund_pending.wav": {
        "text": "Mera payment fail ho gaya tha, paisa kab wapas aayega?",
        "language": "hi",
        "confidence": 0.95,
    },
    "loan_inquiry.wav": {
        "text": "Mujhe dukaan ke liye 50,000 ka loan chahiye, kitna EMI banega?",
        "language": "hi",
        "confidence": 0.97,
    },
    "loan_decline.wav": {
        "text": "Nahi chahiye abhi, baad mein dekhenge.",
        "language": "hi",
        "confidence": 0.99,
    },
    "flight_request.wav": {
        "text": "Delhi se Mumbai kal shaam ka flight, sasta aur jaldi wala.",
        "language": "hi",
        "confidence": 0.96,
    },
    "trick_otp.wav": {
        "text": "Mera OTP 4920 hai, payment confirm kar do.",
        "language": "hi",
        "confidence": 0.99,
    },
}


class MockSTT(BaseSTTAdapter):
    """Deterministic Mock STT supporting recorded clip lookup and Hinglish code-switching."""

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str | None = None,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        if filename:
            clean_name = filename.split("/")[-1].split("\\")[-1]
            if clean_name in AUDIO_CLIP_TRANSCRIPTS:
                logger.info(f"MockSTT matched audio clip '{clean_name}'")
                return AUDIO_CLIP_TRANSCRIPTS[clean_name]

        # Default fallback transcript for arbitrary audio inputs
        return {
            "text": "Delhi se Mumbai kal shaam ka flight, sasta aur jaldi.",
            "language": language_code or "hi",
            "confidence": 0.95,
        }

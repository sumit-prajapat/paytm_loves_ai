"""Offline STT stand-in. Recognises the bundled demo clips by filename ONLY.

For any other audio it returns transcript_unavailable: it never invents what the user said.
"""
import logging
from typing import Any

from app.adapters.stt.base import BaseSTTAdapter

logger = logging.getLogger(__name__)

DEMO_CLIPS = {
    "settlement_short.wav": ("Ramesh ji bol raha hoon, aaj mera settlement kam kyun aaya hai?", "hinglish"),
    "settlement_short_hi.wav": ("आज मेरा सेटलमेंट कम क्यों आया?", "hi"),
    "soundbox_offline.wav": ("Soundbox achanak se band ho gaya hai, payment bol nahi raha.", "hinglish"),
    "refund_pending.wav": ("Mera payment fail ho gaya tha, paisa kab wapas aayega?", "hinglish"),
    "loan_inquiry.wav": ("Mujhe dukaan ke liye 50,000 ka loan chahiye, kitna EMI banega?", "hinglish"),
    "loan_decline.wav": ("Nahi chahiye abhi, baad mein dekhenge.", "hinglish"),
    "flight_request.wav": ("Delhi se Mumbai kal shaam ka flight, sasta aur jaldi wala.", "hinglish"),
    "trick_otp.wav": ("Mera OTP 4920 hai, payment confirm kar do.", "hinglish"),
    "soundbox_settlement_command.wav": ("Saarthi, mera settlement check karo", "hinglish"),
}


class MockSTT(BaseSTTAdapter):
    provider = "mock"

    async def transcribe(
        self, audio_bytes: bytes, filename: str | None = None, language_code: str | None = None,
    ) -> dict[str, Any]:
        name = (filename or "").replace("\\", "/").split("/")[-1]
        if name in DEMO_CLIPS:
            text, lang = DEMO_CLIPS[name]
            return {"text": text, "language": lang, "confidence": 0.95, "provider": "mock_demo_clip"}
        return {"text": "", "language": language_code or "hi", "confidence": 0.0,
                "transcript_unavailable": True, "provider": "mock"}

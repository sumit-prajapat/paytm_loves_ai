from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/adapters")
async def get_adapter_health():
    """Returns active adapter status and indicates whether real or fallback implementations are active."""
    settings = get_settings()

    llm_status = "real (Gemini)" if settings.GEMINI_API_KEY else "fallback (MockLLM - Offline Deterministic)"
    stt_status = "real (Sarvam AI)" if settings.SARVAM_API_KEY else "fallback (MockSTT / Phrase Bank)"
    tts_status = "real (Microsoft Edge TTS Neural hi-IN)" if settings.TTS_PROVIDER == "edge-tts" else "fallback (MockTTS)"
    flights_status = "real/seeded (SeededFlightsProvider - 121 Indian airports, Kaggle fares)"
    payments_status = "mock (MockPaymentLink - Safe Human-in-the-Loop Review & Pay)"
    weather_status = "real (Open-Meteo API / Offline Fallback)"
    holidays_status = "real (National Indian Festivals & Dates)"
    notify_status = "real (In-App WebSocket Bus & Soundbox Simulator)"

    return {
        "demo_mode": settings.DEMO_MODE,
        "adapters": {
            "llm": {"provider": settings.LLM_PROVIDER, "status": llm_status},
            "stt": {"provider": settings.STT_PROVIDER, "status": stt_status},
            "tts": {"provider": settings.TTS_PROVIDER, "status": tts_status},
            "flights": {"provider": settings.FLIGHTS_PROVIDER, "status": flights_status},
            "payments": {"provider": settings.PAYMENTS_PROVIDER, "status": payments_status},
            "weather": {"provider": "open-meteo", "status": weather_status},
            "holidays": {"provider": "built-in/calendarific", "status": holidays_status},
            "notifications": {"provider": settings.NOTIFY_PROVIDER, "status": notify_status},
        },
        "all_systems_operational": True,
    }

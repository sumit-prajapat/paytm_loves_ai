from fastapi import APIRouter

from app.config import get_settings
from app.llm.gateway import llm_gateway
from app.services.voice_service import get_stt, get_tts

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/adapters")
async def get_adapter_health():
    """Which adapters are configured (real vs offline fallback). Does not call providers."""
    s = get_settings()
    llm = llm_gateway.adapter
    return {
        "demo_mode": s.DEMO_MODE,
        "adapters": {
            "llm": {"provider": llm.provider,
                    "models": {"tier1": s.GEMINI_MODEL_TIER1, "tier2": s.GEMINI_MODEL_TIER2}
                    if llm.provider == "gemini" else None,
                    "real": llm.provider != "mock",
                    "provider_errors_since_start": llm_gateway.stats.get("provider_errors", 0)},
            "stt": {"provider": get_stt().provider, "model": s.SARVAM_STT_MODEL, "real": get_stt().provider != "mock",
                    "offline_fallback": "demo clips by filename, otherwise transcript_unavailable"},
            "tts": {"provider": get_tts().provider, "real": get_tts().provider != "mock",
                    "offline_fallback": "silent WAV"},
            "flights": {"provider": "seeded_db", "real": False, "note": "SIMULATED schedule from Kaggle fares"},
            "payments": {"provider": "mock_checkout_link", "real": False},
            "notifications": {"provider": "in_app_websocket", "real": True},
        },
    }

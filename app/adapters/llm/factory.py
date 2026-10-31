import logging

from app.adapters.llm.base import BaseLLMAdapter
from app.adapters.llm.gemini import GeminiLLM
from app.adapters.llm.mock import MockLLM
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_llm_adapter() -> BaseLLMAdapter:
    settings = get_settings()
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        logger.info("Active LLM provider: Gemini (tier1=%s, tier2=%s)",
                    settings.GEMINI_MODEL_TIER1, settings.GEMINI_MODEL_TIER2)
        return GeminiLLM(api_key=settings.GEMINI_API_KEY)
    logger.info("Active LLM provider: MockLLM (offline, deterministic)")
    return MockLLM()

import logging

from app.adapters.llm.base import BaseLLMAdapter
from app.adapters.llm.gemini import GeminiLLM
from app.adapters.llm.mock import MockLLM
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_llm_adapter() -> BaseLLMAdapter:
    settings = get_settings()
    if settings.GEMINI_API_KEY and settings.LLM_PROVIDER == "gemini":
        logger.info("Active LLM provider: GeminiLLM (Google Gemini)")
        return GeminiLLM(api_key=settings.GEMINI_API_KEY)
    elif settings.GROQ_API_KEY and settings.LLM_PROVIDER == "groq":
        logger.info("Active LLM provider: Groq")
        return MockLLM()
    else:
        logger.info("Active LLM provider: MockLLM (deterministic hackathon demo mode)")
        return MockLLM()

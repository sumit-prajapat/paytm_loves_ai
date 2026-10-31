import logging

from app.adapters.stt.base import BaseSTTAdapter
from app.adapters.stt.mock import MockSTT
from app.adapters.stt.sarvam import SarvamSTT
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_stt_adapter() -> BaseSTTAdapter:
    settings = get_settings()
    if settings.SARVAM_API_KEY and settings.STT_PROVIDER == "sarvam":
        logger.info("Active STT provider: SarvamSTT (Indic Speech-to-Text)")
        return SarvamSTT(api_key=settings.SARVAM_API_KEY)
    else:
        logger.info("Active STT provider: MockSTT (deterministic Indic speech recognition)")
        return MockSTT()

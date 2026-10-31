import logging

from app.adapters.tts.base import BaseTTSAdapter
from app.adapters.tts.edge_tts_adapter import EdgeTTSAdapter
from app.adapters.tts.mock import MockTTS
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_tts_adapter() -> BaseTTSAdapter:
    settings = get_settings()
    if settings.TTS_PROVIDER == "edge-tts":
        return EdgeTTSAdapter()
    return MockTTS()

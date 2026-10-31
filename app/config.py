from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Saarthi"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEMO_MODE: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./saarthi.db"

    # Autonomy & Guardian
    KILL_SWITCH_ACTIVE: bool = False
    FINANCIAL_IMPACT_THRESHOLD_INR: float = 5000.0
    AUTO_RESOLVE_CONFIDENCE_THRESHOLD: float = 0.85
    CLARIFY_CONFIDENCE_THRESHOLD: float = 0.60

    # Security & Authentication (Phase 7)
    JWT_SECRET_KEY: str = "saarthi_dev_insecure_jwt_secret_key_change_in_prod_32chars!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RATE_LIMIT_PER_MINUTE: int = 60
    CHAT_RATE_LIMIT_PER_MINUTE: int = 20
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024
    MAX_AUDIO_SIZE_BYTES: int = 5 * 1024 * 1024
    ALLOWED_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Adapters configuration
    LLM_PROVIDER: str = "mock"  # mock | gemini
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL_TIER1: str = "gemini-2.5-flash-lite"  # cheap: intent + slots only
    GEMINI_MODEL_TIER2: str = "gemini-2.5-flash"  # stronger: summaries / nuance
    LLM_TIMEOUT_SECONDS: float = 6.0
    GROQ_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None

    STT_PROVIDER: str = "sarvam"
    SARVAM_API_KEY: str | None = None
    SARVAM_STT_MODEL: str = "saaras:v3"
    STT_TIMEOUT_SECONDS: float = 6.0

    TTS_PROVIDER: str = "edge-tts"
    TTS_TIMEOUT_SECONDS: float = 8.0

    # ------------------------------------------------------------------
    # R12 cost controls (cost scales with requests, never with user base)
    # ------------------------------------------------------------------
    TIER0_MIN_CONFIDENCE: float = 0.75  # below this, Tier 1 LLM may be used
    ENABLE_TIER2: bool = True  # stronger LLM for escalation summaries
    LLM_TIER1_INR_PER_1K_TOKENS: float = 0.01  # placeholder, see docs/ASSUMPTIONS.md
    LLM_TIER2_INR_PER_1K_TOKENS: float = 0.08  # placeholder, see docs/ASSUMPTIONS.md
    CHECKUPS_PER_USER_PER_DAY: int = 30
    CHECKUP_COOLDOWN_SECONDS: int = 60
    CHECKUP_CACHE_TTL_SECONDS: int = 600
    LLM_CALLS_PER_USER_PER_DAY: int = 40
    LLM_TOKENS_PER_USER_PER_DAY: int = 40000
    LLM_CALLS_PER_SESSION: int = 15
    MAX_TOOL_CALLS_PER_TURN: int = 30
    GLOBAL_LLM_BUDGET_INR_PER_DAY: float = 2000.0
    CLASSIFICATION_CACHE_TTL_SECONDS: int = 86400
    FLIGHT_SEARCH_CACHE_TTL_SECONDS: int = 300
    UNKNOWN_TURNS_BEFORE_HUMAN: int = 2

    # Business rules
    SUPPORT_COST_PER_TICKET_INR: float = 180.0  # placeholder, see docs/ASSUMPTIONS.md
    OFFER_COOLDOWN_DAYS: int = 7
    PLAYBOOK_MATCH_THRESHOLD: float = 0.85
    DEVICE_LOW_BATTERY_PCT: int = 20
    DEVICE_OFFLINE_MINUTES: int = 120
    PAYMENTS_LOOKBACK_DAYS: int = 7
    FESTIVAL_ADVICE_WINDOW_DAYS: int = 14
    ESCALATION_ETA_HOURS: int = 4

    # Audio (generated replies served via short-lived signed URLs)
    AUDIO_DIR: str = "data/audio"
    AUDIO_URL_TTL_SECONDS: int = 900
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Housekeeping scheduler (never touches user data)
    HOUSEKEEPING_ENABLED: bool = True

    FLIGHTS_PROVIDER: str = "seeded"
    AMADEUS_CLIENT_ID: str | None = None
    AMADEUS_CLIENT_SECRET: str | None = None

    PAYMENTS_PROVIDER: str = "mock"
    PAYTM_MID: str | None = None
    PAYTM_MERCHANT_KEY: str | None = None
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None

    NOTIFY_PROVIDER: str = "in_app"
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_WHATSAPP_NUMBER: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

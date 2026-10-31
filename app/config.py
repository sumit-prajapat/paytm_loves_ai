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
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None

    STT_PROVIDER: str = "sarvam"
    SARVAM_API_KEY: str | None = None

    TTS_PROVIDER: str = "edge-tts"

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

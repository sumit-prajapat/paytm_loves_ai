import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.adapter_health import router as adapter_health_router
from app.api.audio import router as audio_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.checkups import router as checkups_router
from app.api.control import router as control_router
from app.api.demo import router as demo_router
from app.api.devices import router as devices_router
from app.api.disputes import router as disputes_router
from app.api.escalations import router as escalations_router
from app.api.health import router as health_router
from app.api.loans import router as loans_router
from app.api.merchants import router as merchants_router
from app.api.metrics import router as metrics_router
from app.api.playbooks import router as playbooks_router
from app.api.pulse import router as pulse_router
from app.api.refunds import router as refunds_router
from app.api.settlements import router as settlements_router
from app.api.soundbox import router as soundbox_router
from app.api.tickets import router as tickets_router
from app.api.transactions import router as transactions_router
from app.api.travel import payments_router
from app.api.travel import router as travel_router
from app.api.voice import router as voice_router
from app.api.ws import router as ws_router
from app.config import get_settings
from app.core.middleware import (
    CorrelationIdMiddleware,
    RateLimiterMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.session import init_db
from app.logging import setup_logging
from app.ops.housekeeping import start_housekeeping, stop_housekeeping

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured JSON logging
    setup_logging(level="DEBUG" if settings.DEBUG else "INFO")
    logger.info("Starting Saarthi backend server", extra={"demo_mode": settings.DEMO_MODE})

    # Startup security verification in non-demo mode
    if not settings.DEMO_MODE:
        if "insecure" in settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Non-demo mode requires a strong JWT_SECRET_KEY (min 32 characters)."
            )

    # Initialize SQLite / PostgreSQL tables
    await init_db()
    logger.info("Database tables initialized successfully")

    # R11: no per-user/fleet background work. Only housekeeping that touches no user data.
    start_housekeeping()

    yield

    stop_housekeeping()
    logger.info("Shutting down Saarthi backend server")


app = FastAPI(
    title="Saarthi Backend - Multi-Agent AI Teammate for Bharat",
    description="Autonomous AI Teammate backend powering Saarthi Care (Merchant Support) & Saarthi Travel (Consumer Concierge)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEMO_MODE else None,
    redoc_url="/redoc" if settings.DEMO_MODE else None,
)

# 1. Custom Security Middlewares (Order: Correlation -> Security Headers -> Rate Limiter)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# 2. CORS Policy: Restricted in non-demo mode
# CORS from env (ALLOWED_CORS_ORIGINS). Wildcard origins never combine with credentials.
_origins = settings.ALLOWED_CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "X-Idempotency-Key"],
)


# 3. Global Exception Handlers (Never leak stack traces, SQL, or internal file paths)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    corr_id = getattr(request.state, "correlation_id", f"corr_{uuid.uuid4().hex[:12]}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "correlation_id": corr_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    corr_id = getattr(request.state, "correlation_id", f"corr_{uuid.uuid4().hex[:12]}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": True,
            "code": "VALIDATION_ERROR",
            "message": "Invalid request schema or parameters",
            "correlation_id": corr_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    corr_id = getattr(request.state, "correlation_id", f"corr_{uuid.uuid4().hex[:12]}")
    # Log internal error and full traceback server-side with correlation id
    logger.error(f"Internal server error [corr_id={corr_id}]: {exc}", exc_info=True)
    # Return redacted, sanitized error response to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please contact support with this correlation ID.",
            "correlation_id": corr_id,
        },
    )


# 4. Routers: probes at the root, everything else versioned under /api/v1, WebSockets at /ws
API_V1 = "/api/v1"
app.include_router(health_router)
app.include_router(adapter_health_router)
for _router in (auth_router, control_router, merchants_router, transactions_router, settlements_router,
                refunds_router, devices_router, tickets_router, loans_router, disputes_router, playbooks_router,
                audit_router, travel_router, payments_router, metrics_router, chat_router, voice_router,
                pulse_router, escalations_router, checkups_router, soundbox_router, audio_router, demo_router):
    app.include_router(_router, prefix=API_V1)
app.include_router(ws_router)

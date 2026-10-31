import logging
import time
import uuid
from collections import defaultdict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory rate limiting tracker: (ip, rate_category) -> list of timestamps
_RATE_LIMIT_BUCKETS: dict[tuple[str, str], list[float]] = defaultdict(list)

STRICT_PATHS = ("/auth/login", "/chat", "/voice", "/events/inject")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Applies fintech-grade HTTP security headers to all outgoing responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates an immutable Correlation ID for request tracing."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or f"corr_{uuid.uuid4().hex[:12]}"
        request.state.correlation_id = correlation_id

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter per client IP.

    Stricter on /auth/login, /chat, /voice/*, /events/inject.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip rate limit on open docs/openapi routes in demo mode
        path = request.url.path
        if path in ("/docs", "/openapi.json", "/redoc", "/health", "/ready"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        is_strict = any(path.startswith(sp) for sp in STRICT_PATHS)
        category = "strict" if is_strict else "standard"
        max_requests = settings.CHAT_RATE_LIMIT_PER_MINUTE if is_strict else settings.RATE_LIMIT_PER_MINUTE

        now = time.time()
        window_start = now - 60.0

        key = (client_ip, category)
        # Prune old timestamps
        timestamps = [t for t in _RATE_LIMIT_BUCKETS[key] if t > window_start]

        if len(timestamps) >= max_requests:
            corr_id = getattr(request.state, "correlation_id", "unknown")
            logger.warning(
                f"Rate limit exceeded for IP {client_ip} on path {path} ({len(timestamps)}/{max_requests} req/min). Corr: {corr_id}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded ({max_requests} requests per minute). Please try again shortly.",
                        "correlation_id": corr_id,
                    }
                },
                headers={"Retry-After": "60"},
            )

        timestamps.append(now)
        _RATE_LIMIT_BUCKETS[key] = timestamps

        return await call_next(request)

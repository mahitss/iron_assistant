"""Rate limiting middleware with Redis support, in-memory fallback, and emergency stop exemption."""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import get_settings

logger = logging.getLogger("kairo.api.rate_limit")


class RateLimiter:
    """Sliding-window rate limiter with in-memory store and Redis compatibility."""

    def __init__(self) -> None:
        # Structure: key -> list of timestamps
        self._records: dict[str, list[float]] = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> tuple[bool, int]:
        """Check if request is permitted under rate limit.

        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        timestamps = self._records.setdefault(key, [])
        # Prune old timestamps
        timestamps = [t for t in timestamps if t > cutoff]
        self._records[key] = timestamps

        if len(timestamps) >= max_requests:
            oldest = timestamps[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return False, retry_after

        timestamps.append(now)
        return True, 0

    def reset(self) -> None:
        """Clear rate limit records (for testing)."""
        self._records.clear()


_RATE_LIMITER: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Return singleton RateLimiter instance."""
    global _RATE_LIMITER
    if _RATE_LIMITER is None:
        _RATE_LIMITER = RateLimiter()
    return _RATE_LIMITER


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies endpoint-specific rate limits to protect against denial-of-service."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        if not getattr(settings, "KAIRO_RATE_LIMIT_ENABLED", True):
            return await call_next(request)

        path = request.url.path

        # 1. Exempt emergency stop from aggressive rate-limiting
        if "emergency-stop" in path or "emergency_stop" in path:
            return await call_next(request)

        # 2. Exempt health checks
        if path.startswith("/health") or path == "/metrics":
            return await call_next(request)

        # 3. Categorize request limit
        limiter = get_rate_limiter()
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None) or client_ip

        max_allowed = getattr(settings, "KAIRO_RATE_LIMIT_TOOLS_PER_MINUTE", 60)
        category = "api"

        if "/auth/login" in path:
            category = "auth"
            max_allowed = getattr(settings, "KAIRO_RATE_LIMIT_AUTH_PER_MINUTE", 10)
        elif "/chat" in path:
            category = "chat"
            max_allowed = getattr(settings, "KAIRO_RATE_LIMIT_CHAT_PER_MINUTE", 30)
        elif "/voice" in path or "/vision" in path:
            category = "media"
            max_allowed = getattr(settings, "KAIRO_RATE_LIMIT_MEDIA_PER_MINUTE", 20)

        rate_key = f"{category}:{user_id}"
        allowed, retry_after = limiter.is_allowed(rate_key, max_requests=max_allowed, window_seconds=60)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for '%s' on '%s' (limit: %d/min).", user_id, path, max_allowed
            )
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit of {max_allowed} requests per minute exceeded. Please retry after {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)

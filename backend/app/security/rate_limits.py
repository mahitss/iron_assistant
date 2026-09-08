"""Security rate limiting for tool calls, external actions, and approval requests."""

import logging
import time
from collections import defaultdict

from app.security.exceptions import RateLimitExceededError

logger = logging.getLogger("kairo.security.rate_limits")


class SecurityRateLimiter:
    """Sliding-window rate limiter for sensitive security operations."""

    def __init__(self) -> None:
        # In-memory sliding windows: key -> list of float timestamps
        self._history: dict[str, list[float]] = defaultdict(list)

    def check_limit(
        self,
        user_id: str,
        limit_category: str = "tool_call",
        max_events: int = 60,
        window_seconds: int = 60,
    ) -> None:
        """Enforce rate limits per (user_id, category). Raises RateLimitExceededError if breached."""
        now = time.time()
        key = f"{user_id}:{limit_category}"
        timestamps = self._history[key]

        # Prune expired timestamps outside sliding window
        threshold = now - window_seconds
        self._history[key] = [t for t in timestamps if t > threshold]

        if len(self._history[key]) >= max_events:
            logger.warning(
                "Security rate limit exceeded for user '%s' on '%s' (%d events in %ds)",
                user_id,
                limit_category,
                len(self._history[key]),
                window_seconds,
            )
            raise RateLimitExceededError(
                f"Rate limit exceeded for {limit_category}: maximum {max_events} allowed per {window_seconds}s."
            )

        self._history[key].append(now)

    def reset_for_user(self, user_id: str) -> None:
        """Clear rate limit history for a specific user (e.g. in tests)."""
        keys_to_clear = [k for k in self._history if k.startswith(f"{user_id}:")]
        for k in keys_to_clear:
            self._history.pop(k, None)

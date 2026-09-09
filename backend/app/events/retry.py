"""Retry policies and error classification for Kairo Event Bus.

Differentiates transient errors (which deserve exponential backoff) from permanent
errors (which must fail fast to Dead Letter queue without wasteful retries).
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Coroutine, Optional, Set, Tuple, Type

from app.config.settings import settings

logger = logging.getLogger(__name__)


class EventBusError(Exception):
    """Base exception for event bus errors."""


class TransientDeliveryError(EventBusError):
    """Temporary failure (e.g. rate limit, connection timeout, temporary 503). Eligible for retry."""


class PermanentDeliveryError(EventBusError):
    """Fatal failure (e.g. invalid payload schema, authentication failure, permission violation).

    Must immediately fail fast to Dead Letter Queue without retry.
    """


# Default exceptions treated as permanent failures
PERMANENT_ERROR_TYPES: Tuple[Type[Exception], ...] = (
    PermanentDeliveryError,
    ValueError,
    TypeError,
    PermissionError,
    KeyError,
)

# Default exceptions treated as transient failures
TRANSIENT_ERROR_TYPES: Tuple[Type[Exception], ...] = (
    TransientDeliveryError,
    TimeoutError,
    ConnectionError,
    asyncio.TimeoutError,
)


class RetryPolicy:
    """Configurable exponential backoff policy for subscriber handlers."""

    def __init__(
        self,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None,
        max_backoff: Optional[float] = None,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        permanent_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        transient_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ) -> None:
        self.max_retries = (
            max_retries
            if max_retries is not None
            else getattr(settings, "KAIRO_EVENTS_DEFAULT_RETRY_LIMIT", 3)
        )
        self.initial_backoff = (
            initial_backoff
            if initial_backoff is not None
            else getattr(settings, "KAIRO_EVENTS_INITIAL_BACKOFF_SECONDS", 0.5)
        )
        self.max_backoff = (
            max_backoff
            if max_backoff is not None
            else getattr(settings, "KAIRO_EVENTS_MAX_BACKOFF_SECONDS", 60.0)
        )
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.permanent_exceptions = permanent_exceptions or PERMANENT_ERROR_TYPES
        self.transient_exceptions = transient_exceptions or TRANSIENT_ERROR_TYPES

    def is_permanent(self, exc: Exception) -> bool:
        """Return True if exception should immediately fail without retry."""
        return isinstance(exc, self.permanent_exceptions)

    def calculate_delay(self, attempt: int) -> float:
        """Compute delay with exponential backoff and jitter for attempt (0-indexed)."""
        delay = self.initial_backoff * (self.backoff_multiplier ** attempt)
        delay = min(delay, self.max_backoff)
        if self.jitter:
            delay += random.uniform(0.01, 0.1)
        return delay

    async def execute_with_retry(
        self,
        handler: Callable[[Any], Coroutine[Any, Any, Any]],
        event: Any,
        subscriber_name: str = "unknown",
    ) -> Any:
        """Executes handler with exponential backoff on transient errors."""
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                return await handler(event)
            except Exception as exc:
                last_exception = exc
                if self.is_permanent(exc):
                    logger.error(
                        "Permanent error in subscriber '%s' for event '%s': %s",
                        subscriber_name,
                        getattr(event, "event_id", "unknown"),
                        exc,
                        exc_info=True,
                    )
                    raise PermanentDeliveryError(f"Permanent handler error: {exc}") from exc

                if attempt >= self.max_retries:
                    logger.warning(
                        "Exhausted %d retries for subscriber '%s' on event '%s': %s",
                        self.max_retries,
                        subscriber_name,
                        getattr(event, "event_id", "unknown"),
                        exc,
                    )
                    break

                delay = self.calculate_delay(attempt)
                logger.info(
                    "Subscriber '%s' failed on event '%s' (attempt %d/%d). Retrying in %.2fs. Reason: %s",
                    subscriber_name,
                    getattr(event, "event_id", "unknown"),
                    attempt + 1,
                    self.max_retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

        raise TransientDeliveryError(
            f"Exhausted retries ({self.max_retries}) for subscriber '{subscriber_name}': {last_exception}"
        ) from last_exception

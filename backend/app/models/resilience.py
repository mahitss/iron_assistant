"""Circuit breaker and exponential backoff retry policies for external provider resilience."""

import asyncio
import logging
import random
import time
from enum import Enum
from typing import Any, Callable

from app.models.provider import AuthenticationError, ProviderAPIError

logger = logging.getLogger("kairo.models.resilience")


class CircuitBreakerState(str, Enum):
    """States for external service circuit breaker."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(ProviderAPIError):
    """Raised when an external service is unavailable and circuit breaker is OPEN."""


class CircuitBreaker:
    """Protects against cascading failures by failing fast when an external service is down."""

    def __init__(
        self,
        name: str = "openrouter",
        fail_max: int = 5,
        reset_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout

        self._state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self._failures: int = 0
        self._opened_at: float = 0.0

    @property
    def state(self) -> CircuitBreakerState:
        """Current state of circuit breaker."""
        if self._state == CircuitBreakerState.OPEN:
            if time.time() - self._opened_at >= self.reset_timeout:
                logger.info("Circuit breaker '%s' entering HALF_OPEN probe state.", self.name)
                self._state = CircuitBreakerState.HALF_OPEN
        return self._state

    def can_execute(self) -> bool:
        """Check if request can proceed through the circuit."""
        return self.state != CircuitBreakerState.OPEN

    def record_success(self) -> None:
        """Record successful execution and reset failure counters."""
        if self._state in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN):
            logger.info("Circuit breaker '%s' recovered to CLOSED state.", self.name)
        self._state = CircuitBreakerState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    def record_failure(self, error: Exception | None = None) -> None:
        """Record failed execution and potentially trip circuit to OPEN."""
        # Never trip circuit on authentication or authorization errors
        if isinstance(error, (AuthenticationError, PermissionError)):
            return

        self._failures += 1
        logger.warning(
            "Circuit breaker '%s' recorded failure (%d/%d): %s",
            self.name,
            self._failures,
            self.fail_max,
            error,
        )

        if self._failures >= self.fail_max or self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.OPEN
            self._opened_at = time.time()
            logger.critical(
                "Circuit breaker '%s' tripped to OPEN! Fast-failing calls for %.1fs.",
                self.name,
                self.reset_timeout,
            )

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._state = CircuitBreakerState.CLOSED
        self._failures = 0
        self._opened_at = 0.0


class RetryPolicy:
    """Retries transient network or upstream server errors using exponential backoff with jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_backoff: float = 0.5,
        multiplier: float = 2.0,
        max_backoff: float = 8.0,
    ) -> None:
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.multiplier = multiplier
        self.max_backoff = max_backoff

    async def execute(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async function with exponential backoff and jitter."""
        attempt = 0
        delay = self.initial_backoff

        while True:
            try:
                return await fn(*args, **kwargs)
            except AuthenticationError:
                # Fatal credential error; never retry
                raise
            except Exception as exc:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error("RetryPolicy exhausted %d retries. Final error: %s", self.max_retries, exc)
                    raise

                # Exponential backoff with random jitter (+/- 20%)
                jitter = random.uniform(0.8, 1.2)
                sleep_time = min(delay * jitter, self.max_backoff)
                logger.warning(
                    "Transient error on attempt %d/%d: %s. Retrying in %.2fs...",
                    attempt,
                    self.max_retries,
                    exc,
                    sleep_time,
                )
                await asyncio.sleep(sleep_time)
                delay *= self.multiplier


_DEFAULT_CIRCUIT_BREAKER: CircuitBreaker | None = None


def get_default_circuit_breaker() -> CircuitBreaker:
    """Return default circuit breaker for model provider calls."""
    global _DEFAULT_CIRCUIT_BREAKER
    if _DEFAULT_CIRCUIT_BREAKER is None:
        _DEFAULT_CIRCUIT_BREAKER = CircuitBreaker(name="model_provider")
    return _DEFAULT_CIRCUIT_BREAKER

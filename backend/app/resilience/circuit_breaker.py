"""Circuit breaker state machine with scoping and fail-fast protection."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
import logging
from typing import Any, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.resilience.models import CircuitStateModel
from app.resilience.schemas import CircuitBreakerConfig, CircuitBreakerStatus, CircuitState, utc_now

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitOpenError(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    def __init__(self, circuit_id: str, cooldown_remaining: float):
        self.circuit_id = circuit_id
        self.cooldown_remaining = cooldown_remaining
        super().__init__(
            f"Circuit '{circuit_id}' is OPEN (fail-fast active, cooldown remaining: {cooldown_remaining:.1f}s)"
        )


class CircuitBreaker:
    """Individual circuit breaker instance managing state transitions."""

    def __init__(self, circuit_id: str, config: CircuitBreakerConfig | None = None) -> None:
        self.circuit_id = circuit_id
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_at: datetime | None = None
        self.opened_at: datetime | None = None
        self.updated_at = utc_now()

    def get_status(self) -> CircuitBreakerStatus:
        return CircuitBreakerStatus(
            circuit_id=self.circuit_id,
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            last_failure_at=self.last_failure_at,
            opened_at=self.opened_at,
            updated_at=self.updated_at,
        )

    def is_call_permitted(self) -> bool:
        """Determines if a call is permitted or if it must fail fast."""
        now = utc_now()
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.opened_at:
                elapsed = (now - self.opened_at).total_seconds()
                if elapsed >= self.config.cooldown_seconds:
                    logger.info("Resilience: Circuit '%s' cooldown elapsed. Entering HALF_OPEN.", self.circuit_id)
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self.updated_at = now
                    return True
                return False
            return False

        if self.state == CircuitState.HALF_OPEN:
            # In HALF_OPEN, allow probe calls
            return True

        return True

    def record_success(self) -> None:
        """Records a successful execution."""
        now = utc_now()
        self.updated_at = now
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.recovery_threshold:
                logger.info("Resilience: Circuit '%s' recovered! Transitioning to CLOSED.", self.circuit_id)
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.opened_at = None
        elif self.state == CircuitState.CLOSED:
            # Soft decay of failures on success
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Records a failure and triggers OPEN if threshold reached."""
        now = utc_now()
        self.failure_count += 1
        self.last_failure_at = now
        self.updated_at = now

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Resilience: Circuit '%s' probe failed. Re-entering OPEN state.", self.circuit_id)
            self.state = CircuitState.OPEN
            self.opened_at = now
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    "Resilience: Circuit '%s' reached %d failures. Opening circuit!",
                    self.circuit_id, self.failure_count
                )
                self.state = CircuitState.OPEN
                self.opened_at = now

    def reset(self) -> None:
        """Manually resets circuit breaker to CLOSED."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        self.updated_at = utc_now()


class CircuitBreakerRegistry:
    """Registry managing scoped circuit breakers across providers, services, and operations."""

    def __init__(self, default_config: CircuitBreakerConfig | None = None) -> None:
        self.default_config = default_config or CircuitBreakerConfig()
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(self, circuit_id: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
        if circuit_id not in self._breakers:
            self._breakers[circuit_id] = CircuitBreaker(circuit_id, config or self.default_config)
        return self._breakers[circuit_id]

    async def execute(
        self,
        circuit_id: str,
        func: Callable[[], Awaitable[T]],
        config: CircuitBreakerConfig | None = None,
    ) -> T:
        """Executes an operation under the protection of the scoped circuit breaker."""
        breaker = self.get_or_create(circuit_id, config)
        if not breaker.is_call_permitted():
            cooldown_rem = 0.0
            if breaker.opened_at:
                elapsed = (utc_now() - breaker.opened_at).total_seconds()
                cooldown_rem = max(0.0, breaker.config.cooldown_seconds - elapsed)
            raise CircuitOpenError(circuit_id, cooldown_rem)

        try:
            result = await func()
            breaker.record_success()
            return result
        except Exception as exc:
            breaker.record_failure()
            raise exc

    def list_all(self) -> list[CircuitBreakerStatus]:
        return [b.get_status() for b in self._breakers.values()]

    def reset(self, circuit_id: str) -> bool:
        if circuit_id in self._breakers:
            self._breakers[circuit_id].reset()
            return True
        return False

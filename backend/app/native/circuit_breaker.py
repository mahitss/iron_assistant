"""
Circuit breaker implementation for Kairo Native Runtime IPC.
Prevents cascading failures and connection hammering when the native substrate is offline or degraded.
"""

from __future__ import annotations

import enum
import logging
import time
from typing import Optional

logger = logging.getLogger("kairo.native.circuit_breaker")


class CircuitState(str, enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class NativeCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 5.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time is not None:
                elapsed = time.monotonic() - self.last_failure_time
                if elapsed >= self.recovery_timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    logger.info(
                        "native_circuit_breaker.half_open_probe: elapsed=%.2f recovery_timeout=%.2f",
                        elapsed,
                        self.recovery_timeout_seconds,
                    )
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self) -> None:
        if self.state != CircuitState.CLOSED:
            logger.info("native_circuit_breaker.recovered_to_closed")
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def record_failure(self, error: Optional[Exception] = None) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(
                "native_circuit_breaker.probe_failed_reopened: failure_count=%d error=%s",
                self.failure_count,
                error,
            )
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "native_circuit_breaker.tripped_open: failure_count=%d threshold=%d error=%s",
                self.failure_count,
                self.failure_threshold,
                error,
            )

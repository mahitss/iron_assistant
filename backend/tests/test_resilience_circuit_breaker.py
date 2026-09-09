"""Tests for circuit breaker state machine, fail-fast protection, and scoped isolation."""

import asyncio
from datetime import UTC, datetime, timedelta
import pytest

from app.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
)
from app.resilience.schemas import CircuitBreakerConfig, CircuitState


@pytest.mark.asyncio
async def test_circuit_breaker_transitions_closed_to_open_to_half_open_to_closed():
    """Verifies full lifecycle of circuit breaker transitions."""
    config = CircuitBreakerConfig(failure_threshold=3, recovery_threshold=2, cooldown_seconds=0.1)
    cb = CircuitBreaker("provider:test_ai", config)

    assert cb.state == CircuitState.CLOSED
    assert cb.is_call_permitted() is True

    # 1st failure
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    # 2nd failure
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # 3rd failure -> trips circuit to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_call_permitted() is False

    # During cooldown, calls fail fast
    assert cb.is_call_permitted() is False

    # Sleep past cooldown (0.1s)
    await asyncio.sleep(0.15)

    # Cooldown elapsed -> enters HALF_OPEN on next call check
    assert cb.is_call_permitted() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 1st successful probe
    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.success_count == 1

    # 2nd successful probe reaches recovery_threshold=2 -> CLOSED!
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.success_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_probe_failure_reopens():
    """Verifies that a probe failure in HALF_OPEN immediately re-opens the circuit."""
    config = CircuitBreakerConfig(failure_threshold=1, recovery_threshold=2, cooldown_seconds=0.05)
    cb = CircuitBreaker("service:weather", config)

    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    await asyncio.sleep(0.08)
    assert cb.is_call_permitted() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Probe fails!
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_call_permitted() is False


@pytest.mark.asyncio
async def test_scoped_breakers_isolate_failures():
    """Verifies that failures in one provider do not trip circuit breakers for other providers."""
    registry = CircuitBreakerRegistry(CircuitBreakerConfig(failure_threshold=2, cooldown_seconds=10.0))

    async def failing_call():
        raise RuntimeError("Service down")

    async def healthy_call():
        return "HEALTHY"

    # Trip breaker for provider_a
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await registry.execute("provider:provider_a", failing_call)

    # provider_a must now fail fast with CircuitOpenError
    with pytest.raises(CircuitOpenError):
        await registry.execute("provider:provider_a", failing_call)

    # provider_b remains completely healthy and CLOSED!
    result_b = await registry.execute("provider:provider_b", healthy_call)
    assert result_b == "HEALTHY"

    # Manual reset of provider_a
    assert registry.reset("provider:provider_a") is True
    status_a = registry.get_or_create("provider:provider_a").get_status()
    assert status_a.state == CircuitState.CLOSED

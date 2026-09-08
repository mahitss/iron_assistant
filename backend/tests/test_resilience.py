"""Tests for provider resilience, CircuitBreaker state transitions, and RetryPolicy."""

import asyncio

import pytest

from app.models.openrouter import OpenRouterProvider
from app.models.provider import AuthenticationError, ChatMessage, ProviderAPIError
from app.models.resilience import CircuitBreaker, CircuitBreakerOpenError, CircuitBreakerState, RetryPolicy


@pytest.mark.asyncio
async def test_circuit_breaker_lifecycle_and_state_transitions():
    """Circuit breaker trips to OPEN on threshold failures, enters HALF_OPEN on cooldown, and recovers to CLOSED."""
    cb = CircuitBreaker(name="test_cb", fail_max=3, reset_timeout=0.1)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 1. Record 2 failures -> stays CLOSED
    cb.record_failure(RuntimeError("Transient error 1"))
    cb.record_failure(RuntimeError("Transient error 2"))
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 2. Record 3rd failure -> trips to OPEN
    cb.record_failure(RuntimeError("Transient error 3"))
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.can_execute() is False

    # 3. Wait past reset_timeout -> transitions to HALF_OPEN probe
    await asyncio.sleep(0.15)
    assert cb.state == CircuitBreakerState.HALF_OPEN
    assert cb.can_execute() is True

    # 4. Successful probe -> recovers to CLOSED
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True


@pytest.mark.asyncio
async def test_retry_policy_retries_transient_errors_then_succeeds():
    """RetryPolicy retries transient exceptions and returns successful outcome."""
    policy = RetryPolicy(max_retries=3, initial_backoff=0.01, multiplier=1.5)

    attempts = 0

    async def _flakey():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ProviderAPIError("Temporary 503 error")
        return "Success on attempt 3"

    result = await policy.execute(_flakey)
    assert result == "Success on attempt 3"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_policy_never_retries_authentication_error():
    """RetryPolicy immediately propagates fatal AuthenticationError without retrying."""
    policy = RetryPolicy(max_retries=3, initial_backoff=0.01)

    attempts = 0

    async def _auth_fail():
        nonlocal attempts
        attempts += 1
        raise AuthenticationError("Invalid API key")

    with pytest.raises(AuthenticationError):
        await policy.execute(_auth_fail)

    assert attempts == 1


@pytest.mark.asyncio
async def test_openrouter_fast_fails_when_circuit_is_open():
    """OpenRouterProvider immediately raises CircuitBreakerOpenError when circuit is OPEN."""
    cb = CircuitBreaker(name="mock_openrouter", fail_max=1, reset_timeout=10.0)
    cb.record_failure(RuntimeError("Downstream exploded"))
    assert cb.can_execute() is False

    provider = OpenRouterProvider(api_key="valid_test_key", circuit_breaker=cb)

    messages = [ChatMessage(role="user", content="Hello")]
    with pytest.raises(CircuitBreakerOpenError, match="temporarily unavailable"):
        await provider.generate_response(messages=messages)

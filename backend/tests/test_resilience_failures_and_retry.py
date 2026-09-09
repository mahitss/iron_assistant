"""Tests for failure classification, secret sanitization, exponential backoff, and bounded retries."""

import asyncio
import pytest

from app.resilience.backoff import BackoffCalculator
from app.resilience.failures import ErrorSanitizer, FailureClassifier
from app.resilience.retry import NonRetryableFailureError, RetryBudgetExceededError, RetryManager
from app.resilience.schemas import (
    FailureCategory,
    FailureSeverity,
    RetryBudget,
    RetryPolicy,
)


def test_failure_classification_categories():
    """Verifies deterministic classification across diverse HTTP status codes and error messages."""
    # HTTP 401
    f401 = FailureClassifier.classify("Unauthorized", "test_op", "auth", status_code=401)
    assert f401.category == FailureCategory.AUTHENTICATION
    assert f401.severity == FailureSeverity.HIGH
    assert f401.retryable is False

    # HTTP 403
    f403 = FailureClassifier.classify("Forbidden", "test_op", "auth", status_code=403)
    assert f403.category == FailureCategory.AUTHORIZATION
    assert f403.retryable is False

    # HTTP 429
    f429 = FailureClassifier.classify("Too Many Requests", "test_op", "rate_limiter", status_code=429)
    assert f429.category == FailureCategory.RATE_LIMITED
    assert f429.retryable is True

    # HTTP 503
    f503 = FailureClassifier.classify("Service Unavailable", "test_op", "upstream", status_code=503)
    assert f503.category == FailureCategory.UNAVAILABLE
    assert f503.retryable is True

    # Text pattern timeout
    ftimeout = FailureClassifier.classify(Exception("Connection timed out after 30s"), "test_op", "network")
    assert ftimeout.category == FailureCategory.TIMEOUT
    assert ftimeout.retryable is True

    # Permanent error
    fperm = FailureClassifier.classify(ValueError("Resource not found or deleted"), "test_op", "store")
    assert fperm.category == FailureCategory.PERMANENT
    assert fperm.retryable is False


def test_error_sanitization_removes_secrets():
    """Verifies that API keys, bearer tokens, passwords, and secrets are stripped."""
    raw_error = "Failed to authenticate with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and sk-proj-1234567890abcdef"
    sanitized = ErrorSanitizer.sanitize_text(raw_error)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
    assert "sk-proj-1234567890abcdef" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
    assert "[REDACTED_API_KEY]" in sanitized

    dict_payload = {
        "user": "alice",
        "api_key": "supersecretkey123",
        "password": "secretpassword!",
        "normal_field": "ok_value",
    }
    sanitized_dict = ErrorSanitizer.sanitize_dict(dict_payload)
    assert sanitized_dict["api_key"] == "[REDACTED]"
    assert sanitized_dict["password"] == "[REDACTED]"
    assert sanitized_dict["normal_field"] == "ok_value"


def test_backoff_and_jitter():
    """Verifies exponential backoff calculation and jitter bounds."""
    policy = RetryPolicy(initial_delay=1.0, multiplier=2.0, max_delay=10.0, jitter=False)

    delay0 = BackoffCalculator.calculate_delay(0, policy)
    delay1 = BackoffCalculator.calculate_delay(1, policy)
    delay2 = BackoffCalculator.calculate_delay(2, policy)
    delay3 = BackoffCalculator.calculate_delay(3, policy)
    delay10 = BackoffCalculator.calculate_delay(10, policy)

    assert delay0 == 1.0
    assert delay1 == 2.0
    assert delay2 == 4.0
    assert delay3 == 8.0
    assert delay10 == 10.0  # Capped at max_delay

    # With jitter enabled
    policy_jitter = RetryPolicy(initial_delay=2.0, multiplier=2.0, max_delay=10.0, jitter=True)
    jitter_delay = BackoffCalculator.calculate_delay(1, policy_jitter)
    assert 2.0 <= jitter_delay <= 4.0


def test_server_retry_after_parsing():
    """Verifies parsing of numeric and RFC HTTP date Retry-After headers."""
    # Numeric
    assert BackoffCalculator.parse_retry_after("12") == 12.0
    assert BackoffCalculator.parse_retry_after(15) == 15.0

    # Policy respects Retry-After
    policy = RetryPolicy(initial_delay=1.0, max_delay=60.0)
    delay = BackoffCalculator.calculate_delay(0, policy, server_retry_after="45")
    assert delay == 45.0


@pytest.mark.asyncio
async def test_retry_manager_success_after_transient_failure():
    """Verifies successful retry execution after initial transient failure."""
    retry_mgr = RetryManager()
    attempts = 0

    async def flaky_op():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionResetError("Transient network failure")
        return "SUCCESS"

    policy = RetryPolicy(max_attempts=4, initial_delay=0.01, multiplier=1.0, jitter=False)
    budget = RetryBudget(max_retries_per_op=3, max_retries_per_task=5)

    result = await retry_mgr.execute_with_retry(
        func=flaky_op,
        operation="fetch_data",
        component="network",
        policy=policy,
        budget=budget,
    )

    assert result == "SUCCESS"
    assert attempts == 3
    assert budget.current_op_retries == 2


@pytest.mark.asyncio
async def test_retry_manager_non_retryable_guard():
    """Verifies that non-retryable errors fail immediately without retry."""
    retry_mgr = RetryManager()
    attempts = 0

    async def unauthorized_op():
        nonlocal attempts
        attempts += 1
        raise PermissionError("Access denied: missing authorization")

    policy = RetryPolicy(max_attempts=3, initial_delay=0.01)

    with pytest.raises(NonRetryableFailureError) as exc_info:
        await retry_mgr.execute_with_retry(
            func=unauthorized_op,
            operation="delete_db",
            component="database",
            policy=policy,
        )

    assert attempts == 1  # Only tried once!
    assert exc_info.value.failure.category == FailureCategory.AUTHORIZATION


@pytest.mark.asyncio
async def test_retry_budget_exceeded():
    """Verifies that exceeding the retry budget halts further retry storms."""
    retry_mgr = RetryManager()
    budget = RetryBudget(max_retries_per_op=1, max_retries_per_task=1)

    async def failing_op():
        raise TimeoutError("Deadline exceeded")

    policy = RetryPolicy(max_attempts=5, initial_delay=0.01, jitter=False)

    with pytest.raises(RetryBudgetExceededError):
        await retry_mgr.execute_with_retry(
            func=failing_op,
            operation="call_api",
            component="external",
            policy=policy,
            budget=budget,
        )

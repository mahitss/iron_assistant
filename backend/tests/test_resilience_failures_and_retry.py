"""Tests for failure classification, secret sanitization, exponential backoff, and bounded retries."""

import asyncio
import datetime
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
    # HTTP 400
    f400 = FailureClassifier.classify("Bad Request: schema mismatch", "test_op", "api", status_code=400)
    assert f400.category == FailureCategory.VALIDATION
    assert f400.retryable is False

    # HTTP 401
    f401 = FailureClassifier.classify("Unauthorized", "test_op", "auth", status_code=401)
    assert f401.category == FailureCategory.AUTHENTICATION
    assert f401.severity == FailureSeverity.HIGH
    assert f401.retryable is False

    # HTTP 403
    f403 = FailureClassifier.classify("Forbidden", "test_op", "auth", status_code=403)
    assert f403.category == FailureCategory.AUTHORIZATION
    assert f403.retryable is False

    # HTTP 404
    f404 = FailureClassifier.classify("Not Found", "test_op", "store", status_code=404)
    assert f404.category == FailureCategory.PERMANENT
    assert f404.retryable is False

    # HTTP 409
    f409 = FailureClassifier.classify("Conflict: version mismatch", "test_op", "store", status_code=409)
    assert f409.category == FailureCategory.CONFLICT
    assert f409.retryable is True

    # HTTP 429
    f429 = FailureClassifier.classify("Too Many Requests", "test_op", "rate_limiter", status_code=429)
    assert f429.category == FailureCategory.RATE_LIMITED
    assert f429.retryable is True

    # HTTP 500
    f500 = FailureClassifier.classify("Internal Server Error", "test_op", "upstream", status_code=500)
    assert f500.category == FailureCategory.TRANSIENT
    assert f500.retryable is True

    # HTTP 502
    f502 = FailureClassifier.classify("Bad Gateway", "test_op", "gateway", status_code=502)
    assert f502.category == FailureCategory.UNAVAILABLE
    assert f502.retryable is True

    # HTTP 503
    f503 = FailureClassifier.classify("Service Unavailable", "test_op", "upstream", status_code=503)
    assert f503.category == FailureCategory.UNAVAILABLE
    assert f503.retryable is True

    # HTTP 504
    f504 = FailureClassifier.classify("Gateway Timeout", "test_op", "gateway", status_code=504)
    assert f504.category == FailureCategory.TIMEOUT
    assert f504.retryable is True

    # Text pattern timeout
    ftimeout = FailureClassifier.classify(Exception("Connection timed out after 30s"), "test_op", "network")
    assert ftimeout.category == FailureCategory.TIMEOUT
    assert ftimeout.retryable is True

    # Policy denial
    fpolicy = FailureClassifier.classify("Policy violation: access denied by governance rule", "test_op", "policy")
    assert fpolicy.category == FailureCategory.AUTHORIZATION
    assert fpolicy.retryable is False


def test_error_sanitization_removes_secrets():
    """Verifies that API keys, bearer tokens, passwords, database URLs, and private keys are stripped."""
    raw_error = (
        "Failed to authenticate with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 "
        "and sk-proj-1234567890abcdef "
        "and connection postgresql://postgres:mypassword123@db.example.com:5432/mydb "
        "and key -----BEGIN RSA PRIVATE KEY-----MIIEowIBAAKCAQEA0-----END RSA PRIVATE KEY-----"
    )
    sanitized = ErrorSanitizer.sanitize_text(raw_error)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
    assert "sk-proj-1234567890abcdef" not in sanitized
    assert "mypassword123" not in sanitized
    assert "-----BEGIN RSA PRIVATE KEY-----" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_DATABASE_URL]" in sanitized
    assert "[REDACTED_PRIVATE_KEY]" in sanitized

    dict_payload = {
        "user": "alice",
        "api_key": "supersecretkey123",
        "password": "secretpassword!",
        "token": "tok_abcdef12345",
        "normal_field": "ok_value",
        "nested": {
            "secret": "confidential",
            "count": 42,
        }
    }
    sanitized_dict = ErrorSanitizer.sanitize_dict(dict_payload)
    assert sanitized_dict["api_key"] == "[REDACTED]"
    assert sanitized_dict["password"] == "[REDACTED]"
    assert sanitized_dict["token"] == "[REDACTED]"
    assert sanitized_dict["nested"]["secret"] == "[REDACTED]"
    assert sanitized_dict["nested"]["count"] == 42
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

    # HTTP Date format
    future_date = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=30)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    parsed = BackoffCalculator.parse_retry_after(future_date)
    assert parsed is not None
    assert 20 <= parsed <= 35


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


@pytest.mark.asyncio
async def test_retry_budget_accumulates_across_task_operations():
    """Verifies that the overall task budget is decremented across distinct steps."""
    retry_mgr = RetryManager()
    task_budget = RetryBudget(max_retries_per_op=3, max_retries_per_task=3)

    call_count = 0

    async def step1():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Step 1 transient glitch")
        return "STEP1_OK"

    policy = RetryPolicy(max_attempts=4, initial_delay=0.01, jitter=False)
    res1 = await retry_mgr.execute_with_retry(step1, "step1", "network", policy=policy, budget=task_budget)
    assert res1 == "STEP1_OK"
    assert task_budget.current_task_retries == 2

    async def step2():
        raise TimeoutError("Step 2 timed out")

    with pytest.raises(RetryBudgetExceededError):
        await retry_mgr.execute_with_retry(step2, "step2", "network", policy=policy, budget=task_budget)

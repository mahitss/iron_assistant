"""Retry management, policy enforcement, and multi-dimensional budget tracking."""

import asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import Any, TypeVar

from app.resilience.backoff import BackoffCalculator
from app.resilience.failures import FailureClassifier
from app.resilience.schemas import Failure, FailureCategory, RetryBudget, RetryPolicy

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryBudgetExceededError(Exception):
    """Raised when a retry budget is exhausted."""
    pass


class NonRetryableFailureError(Exception):
    """Raised when an operation fails with a non-retryable error."""
    def __init__(self, failure: Failure):
        self.failure = failure
        super().__init__(f"Non-retryable failure: {failure.category} - {failure.code}: {failure.cause}")


class RetryManager:
    """Manages bounded retries, budget enforcement, and async execution."""

    def __init__(self) -> None:
        self.total_retries: int = 0
        self.retry_successes: int = 0
        self.retry_failures: int = 0

    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[T]],
        operation: str,
        component: str,
        policy: RetryPolicy | None = None,
        budget: RetryBudget | None = None,
        is_retry_safe: bool = True,
        correlation_id: str | None = None,
        on_retry: Callable[[int, Failure, float], None] | None = None,
    ) -> T:
        """Executes an async callable with bounded exponential backoff, jitter, and budget limits."""
        effective_policy = policy or RetryPolicy()
        effective_budget = budget or RetryBudget()

        attempt = 0
        while True:
            try:
                result = await func()
                if attempt > 0:
                    self.retry_successes += 1
                return result
            except Exception as exc:
                # Classify the exception deterministically
                failure = FailureClassifier.classify(
                    exc_or_error=exc,
                    operation=operation,
                    component=component,
                    correlation_id=correlation_id,
                    is_retry_safe_operation=is_retry_safe,
                )

                # Check if failure is retryable
                if not failure.retryable or failure.category not in effective_policy.retryable_failures:
                    logger.warning(
                        "Resilience: Operation %s failed with non-retryable category %s: %s",
                        operation, failure.category, failure.cause
                    )
                    self.retry_failures += 1
                    raise NonRetryableFailureError(failure) from exc

                attempt += 1
                if attempt >= effective_policy.max_attempts:
                    logger.warning(
                        "Resilience: Operation %s exhausted max attempts (%d)",
                        operation, effective_policy.max_attempts
                    )
                    self.retry_failures += 1
                    raise exc

                if not effective_budget.can_retry():
                    logger.warning("Resilience: Retry budget exceeded for operation %s", operation)
                    self.retry_failures += 1
                    raise RetryBudgetExceededError(
                        f"Retry budget exceeded: op={effective_budget.current_op_retries}/{effective_budget.max_retries_per_op}, "
                        f"task={effective_budget.current_task_retries}/{effective_budget.max_retries_per_task}"
                    ) from exc

                # Record retry in budget and global metrics
                effective_budget.record_retry()
                self.total_retries += 1

                # Calculate delay with backoff + jitter
                delay = BackoffCalculator.calculate_delay(
                    attempt=attempt - 1,
                    policy=effective_policy,
                    server_retry_after=failure.metadata.get("retry_after"),
                )

                if on_retry:
                    try:
                        on_retry(attempt, failure, delay)
                    except Exception as cb_err:
                        logger.error("Error in on_retry callback: %s", cb_err)

                logger.info(
                    "Resilience: Retrying %s (attempt %d/%d) after %.2fs delay due to %s",
                    operation, attempt, effective_policy.max_attempts, delay, failure.category
                )
                await asyncio.sleep(delay)

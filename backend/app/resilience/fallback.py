"""Fallback router with strict security, policy, scope, and data classification preservation."""

from collections.abc import Awaitable, Callable
import logging
from typing import Any, TypeVar

from app.resilience.circuit_breaker import CircuitBreakerRegistry
from app.resilience.failures import FailureClassifier
from app.resilience.schemas import FailureCategory

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FallbackSecurityViolationError(Exception):
    """Raised when a proposed fallback violates security, scope, or data classification."""
    pass


class FallbackRouter:
    """Coordinates multi-tier fallback chains while strictly guaranteeing policy and scope invariance."""

    def __init__(self, circuit_registry: CircuitBreakerRegistry | None = None) -> None:
        self.circuit_registry = circuit_registry or CircuitBreakerRegistry()
        self.fallback_count: int = 0

    def validate_fallback_target(
        self,
        original_target: str,
        fallback_target: str,
        original_environment: str = "production",
        fallback_environment: str = "production",
    ) -> None:
        """Rule: Never change target or cross environment boundaries during fallback."""
        if original_environment != fallback_environment:
            raise FallbackSecurityViolationError(
                f"Environment boundary violation: original='{original_environment}', fallback='{fallback_environment}'"
            )
        if original_target != fallback_target:
            raise FallbackSecurityViolationError(
                f"Target mutation violation: original='{original_target}', fallback='{fallback_target}'"
            )

    def validate_data_classification(
        self,
        data_classification: str,
        target_provider: str,
        allowed_providers_for_classification: dict[str, set[str]] | None = None,
    ) -> None:
        """Rule: Fallback provider must be authorized for data classification being processed."""
        # Default policy: RESTRICTED data can only go to approved local / private providers
        allowed = (allowed_providers_for_classification or {
            "PUBLIC": {"all"},
            "INTERNAL": {"all"},
            "CONFIDENTIAL": {"anthropic", "openai", "local", "azure"},
            "RESTRICTED": {"local", "self_hosted", "kms_approved"},
        }).get(data_classification.upper(), {"local"})

        if "all" not in allowed and target_provider.lower() not in allowed:
            raise FallbackSecurityViolationError(
                f"Data classification '{data_classification}' prohibits fallback to provider '{target_provider}'"
            )

    async def execute_with_fallback(
        self,
        primary_callable: Callable[[], Awaitable[T]],
        primary_provider: str,
        fallback_callables: list[tuple[str, Callable[[], Awaitable[T]]]],
        operation: str,
        data_classification: str = "INTERNAL",
        original_target: str = "default",
        allowed_providers: dict[str, set[str]] | None = None,
        max_fallbacks: int = 3,
    ) -> T:
        """Executes primary action, cascading to fallbacks upon failure if policy permits."""
        # 1. Try Primary with Circuit Breaker
        circuit_id = f"provider:{primary_provider}"
        last_exception: Exception | None = None
        try:
            return await self.circuit_registry.execute(circuit_id, primary_callable)
        except Exception as exc:
            logger.warning("Resilience: Primary provider '%s' failed for '%s': %s", primary_provider, operation, exc)
            last_exception = exc

        # 2. Iterate through fallbacks up to max_fallbacks
        attempted_fallbacks = 0

        for fallback_provider, fallback_callable in fallback_callables:
            if attempted_fallbacks >= max_fallbacks:
                logger.warning("Resilience: Reached maximum fallback limit (%d) for '%s'", max_fallbacks, operation)
                break

            # Security and Data Classification Validation
            try:
                self.validate_data_classification(
                    data_classification=data_classification,
                    target_provider=fallback_provider,
                    allowed_providers_for_classification=allowed_providers,
                )
            except FallbackSecurityViolationError as sec_err:
                logger.error("Resilience: Skipping fallback '%s': %s", fallback_provider, sec_err)
                continue

            fallback_circuit = f"provider:{fallback_provider}"
            try:
                logger.info("Resilience: Attempting fallback provider '%s' for '%s'", fallback_provider, operation)
                self.fallback_count += 1
                attempted_fallbacks += 1
                return await self.circuit_registry.execute(fallback_circuit, fallback_callable)
            except Exception as fb_exc:
                logger.warning("Resilience: Fallback '%s' failed for '%s': %s", fallback_provider, operation, fb_exc)
                last_exception = fb_exc

        # If all exhausted, raise the last exception
        if last_exception:
            raise last_exception
        raise RuntimeError(f"All providers exhausted for operation '{operation}'")

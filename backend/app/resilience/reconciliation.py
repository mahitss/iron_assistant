"""Outcome reconciliation for unknown-outcome operations and external side effects."""

from collections.abc import Awaitable, Callable
import logging
from typing import Any
from app.resilience.schemas import OutcomeState

logger = logging.getLogger(__name__)


class UnknownOutcomeException(Exception):
    """Raised when an operation status is uncertain and requires source reconciliation."""
    def __init__(self, operation: str, details: str, reconciliation_hint: str | None = None):
        self.operation = operation
        self.details = details
        self.reconciliation_hint = reconciliation_hint
        super().__init__(f"Unknown outcome for '{operation}': {details}")


class OutcomeReconciler:
    """Verifies actual state of external targets before attempting retries or declaring completion."""

    @staticmethod
    async def reconcile(
        operation: str,
        verifier: Callable[[], Awaitable[tuple[OutcomeState, dict[str, Any] | None]]],
    ) -> tuple[OutcomeState, dict[str, Any] | None]:
        """Queries authoritative source state to resolve an UNKNOWN_OUTCOME."""
        logger.info("Resilience: Reconciling unknown outcome for operation '%s'", operation)
        try:
            state, details = await verifier()
            logger.info("Resilience: Reconciled '%s' -> %s", operation, state)
            return state, details
        except Exception as exc:
            logger.error("Resilience: Reconciler check failed for '%s': %s", operation, exc)
            return OutcomeState.UNKNOWN, {"error": str(exc)}

    @staticmethod
    async def verify_before_retry(
        operation: str,
        side_effect_started: bool,
        verifier: Callable[[], Awaitable[tuple[OutcomeState, dict[str, Any] | None]]] | None,
    ) -> bool:
        """Determines whether a retry is safe.

        If side_effect_started is True, we must NOT retry blindly.
        We query the verifier:
          - If verifier returns SUCCESS -> side effect already succeeded, DO NOT RETRY, return False.
          - If verifier returns IN_PROGRESS -> still working, DO NOT RETRY, return False.
          - If verifier returns FAILED -> safe to retry, return True.
          - If verifier returns UNKNOWN or verifier is None -> cannot verify, DO NOT RETRY, return False.
        """
        if not side_effect_started:
            # Side effect was not yet initiated (e.g. DNS or socket connection failure before sending payload)
            return True

        if not verifier:
            logger.warning(
                "Resilience: Operation '%s' has unknown outcome with no verifier. Blind retry blocked!",
                operation
            )
            return False

        outcome, details = await OutcomeReconciler.reconcile(operation, verifier)
        if outcome == OutcomeState.FAILED:
            logger.info("Resilience: Source confirms '%s' failed. Safe to retry.", operation)
            return True
        elif outcome == OutcomeState.SUCCESS:
            logger.info("Resilience: Source confirms '%s' succeeded. Duplicate retry prevented.", operation)
            return False
        else:
            logger.warning(
                "Resilience: Source status for '%s' is %s. Retry not permitted without verification.",
                operation, outcome
            )
            return False

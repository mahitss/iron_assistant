"""Recovery strategies, failover execution, bounded retries, and state reconciliation (Task 59)."""

from __future__ import annotations

import logging
from typing import Any

from app.orchestration.assignment import AssignmentEngine, assignment_engine
from app.orchestration.schemas import (
    AssignmentStatus,
    ProviderAssignment,
    RiskSeverity,
    TaskCapabilityRequirement,
)

logger = logging.getLogger(__name__)


class RecoveryEngine:
    """Manages failovers, bounded retries, non-idempotent operation safety, and reconciliation."""

    def __init__(self, assignment_eng: AssignmentEngine | None = None) -> None:
        self._assignment_engine = assignment_eng or assignment_engine
        self._retry_counts: dict[str, int] = {}

    def handle_task_failure(
        self,
        task_id: str,
        assignment: ProviderAssignment,
        requirement: TaskCapabilityRequirement,
        error_message: str,
        execution_state: str = "FAILED",
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """Determine recovery action: RETRY, FAILOVER, RECONCILE, or HUMAN_INTERVENTION."""
        clean_state = execution_state.upper()
        current_retries = self._retry_counts.get(task_id, 0)

        # 1. Non-idempotent operations check
        if requirement.is_irreversible:
            logger.warning(
                "RECOVERY_BLOCKED: Task '%s' is irreversible/non-idempotent. Blind retry prohibited.",
                task_id,
            )
            assignment.status = AssignmentStatus.FAILED
            return {
                "action": "HUMAN_INTERVENTION",
                "reason": "Task is non-idempotent/irreversible. Automatic retry blocked to prevent duplicate side effects.",
                "error": error_message,
            }

        # 2. Unknown execution state requires reconciliation before any retry
        if clean_state == "UNKNOWN":
            logger.warning("RECOVERY_UNCERTAIN: Task '%s' has UNKNOWN execution state. Reconciliation required.", task_id)
            return {
                "action": "RECONCILE",
                "reason": "Execution state is uncertain. Verifying actual system state before attempting retry or failover.",
                "error": error_message,
            }

        # 3. Bounded retry if within retry budget
        if current_retries < max_retries:
            self._retry_counts[task_id] = current_retries + 1
            logger.info("RECOVERY_RETRY: Retrying task '%s' (attempt %d/%d)", task_id, current_retries + 1, max_retries)
            return {
                "action": "RETRY",
                "attempt": current_retries + 1,
                "provider": assignment.provider_name,
                "reason": f"Retry within bounded threshold: {error_message}",
            }

        # 4. Failover to authorized fallback provider
        if assignment.fallback_provider:
            logger.info("RECOVERY_FAILOVER: Triggering failover to '%s' for task '%s'", assignment.fallback_provider, task_id)
            return {
                "action": "FAILOVER",
                "previous_provider": assignment.provider_name,
                "new_provider": assignment.fallback_provider,
                "reason": f"Primary provider failed after max retries: {error_message}",
            }

        # 5. No fallback available -> Require human intervention
        assignment.status = AssignmentStatus.FAILED
        logger.error("RECOVERY_EXHAUSTED: No fallback available for task '%s'. Escalating to human intervention.", task_id)
        return {
            "action": "HUMAN_INTERVENTION",
            "reason": f"No fallback provider available and retries exhausted for task '{task_id}'.",
            "error": error_message,
        }

    def evaluate_fallback_risk(
        self,
        primary_risk: RiskSeverity,
        fallback_risk: RiskSeverity,
    ) -> bool:
        """Check if fallback provider has materially higher risk, requiring elevated approval."""
        risk_ranks = {
            RiskSeverity.LOW: 1,
            RiskSeverity.MEDIUM: 2,
            RiskSeverity.HIGH: 3,
            RiskSeverity.CRITICAL: 4,
        }
        return risk_ranks.get(fallback_risk, 2) > risk_ranks.get(primary_risk, 1)


recovery_engine = RecoveryEngine()

"""Governed Auto-Healing, Loop Prevention, and Remediation Budgeting (Task 54, Prompts #226-#232)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.environment.safety import RemediationLoopError
from app.environment.schemas import RemediationPlan


class AutoHealingGovernor:
    """Enforces remediation budgets and prevents cascading or infinite auto-healing loops."""

    def __init__(self, max_attempts_per_resource: int = 3) -> None:
        self.max_attempts = max_attempts_per_resource
        self.attempt_counts: dict[str, int] = defaultdict(int)
        self.history: list[dict[str, Any]] = []

    def request_auto_healing(
        self,
        resource_id: str,
        plan: RemediationPlan,
        is_pre_authorized: bool = True,
    ) -> bool:
        """Prompt #227, #231, #232: Governed auto-healing within strict attempt budgets."""
        if not is_pre_authorized:
            return False

        # Prompt #231, #232: Loop prevention & bounded budget
        if self.attempt_counts[resource_id] >= self.max_attempts:
            raise RemediationLoopError(
                f"Auto-healing loop detected for resource '{resource_id}'. "
                f"Exceeded maximum attempt budget ({self.max_attempts}). Escalating to human operator."
            )

        self.attempt_counts[resource_id] += 1
        self.history.append({
            "resource_id": resource_id,
            "attempt": self.attempt_counts[resource_id],
            "plan_id": plan.plan_id,
        })
        return True

    def record_healing_success(self, resource_id: str) -> None:
        """Resets attempt count upon verified recovery."""
        self.attempt_counts[resource_id] = 0

    def record_healing_failure(self, resource_id: str) -> None:
        """Leaves or increments attempt count for escalation."""
        # Maintained for loop detection
        pass

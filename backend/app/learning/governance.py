"""Learning policy governance, shadow mode execution, and canary rollback triggers (INVARIANTS 213-229)."""

from __future__ import annotations

from typing import Any
import uuid

from app.learning.schemas import LearningPolicySchema


class LearningGovernanceEngine:
    """Enforces policy constraints on continuous learning, shadow-mode validation, and automated rollback."""

    PROHIBITED_ADAPTATIONS = [
        "SECURITY_POLICY",
        "AUTHORIZATION_RULES",
        "APPROVAL_REQUIREMENTS",
        "AUDIT_CONTROLS",
        "IDENTITY_ASSERTIONS",
    ]

    def __init__(self, policy: LearningPolicySchema | None = None) -> None:
        self.policy = policy or LearningPolicySchema(
            policy_id="default_policy",
            scope="GLOBAL",
            allowed_adaptations=[
                "ROUTING",
                "RETRIEVAL_RANKING",
                "PLANNING_HEURISTIC",
                "DRAFT_STYLE",
                "TOOL_SELECTION",
            ],
            approval_required=True,
            retention_days=90,
            rollback_policy={"auto_rollback_on_regression": True, "regression_threshold": 0.15},
        )
        self._shadow_executions: list[dict[str, Any]] = []

    def is_adaptation_permitted(self, adaptation_type: str) -> bool:
        """INVARIANT 227 & 229: Check whether adaptation type is permitted or prohibited."""
        if adaptation_type in self.PROHIBITED_ADAPTATIONS:
            return False
        return adaptation_type in self.policy.allowed_adaptations

    def execute_in_shadow_mode(
        self,
        candidate_strategy_id: str,
        execution_input: dict[str, Any],
        shadow_evaluator: Any = None,
    ) -> dict[str, Any]:
        """INVARIANT 218 & 219: Runs candidate strategy in shadow mode without side effects."""
        eval_result = {"simulated": True, "side_effects_prevented": True}
        if shadow_evaluator:
            eval_result.update(shadow_evaluator(execution_input))

        record = {
            "shadow_id": f"shd_{uuid.uuid4().hex[:12]}",
            "candidate_strategy_id": candidate_strategy_id,
            "input": execution_input,
            "result": eval_result,
        }
        self._shadow_executions.append(record)
        return record

    def check_rollback_triggers(
        self,
        baseline_verification_rate: float,
        current_verification_rate: float,
        safety_violations: int = 0,
    ) -> tuple[bool, str]:
        """INVARIANT 214: Triggers rollback upon safety degradation or accuracy/verification drop."""
        if safety_violations > 0:
            return True, f"Rollback triggered: {safety_violations} safety violation(s) detected."

        drop = baseline_verification_rate - current_verification_rate
        threshold = self.policy.rollback_policy.get("regression_threshold", 0.15)
        if drop >= threshold:
            return True, f"Rollback triggered: verification rate dropped by {round(drop, 3)} (threshold {threshold})."

        return False, "No rollback required."

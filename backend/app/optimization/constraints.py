"""Hard constraints and soft preferences validator for Adaptive Control (Task 62)."""

from __future__ import annotations

import logging

from app.optimization.safety import validate_immutable_boundary
from app.optimization.schemas import HardConstraint, OptimizationRecommendation, RiskLevel, SoftPreference

logger = logging.getLogger(__name__)


class ConstraintValidator:
    """Enforces non-negotiable operational and security boundaries.

    Invariant 6: Hard constraints MUST NOT be modified or relaxed by the optimizer.
    Candidate improvements that violate any hard constraint are immediately disqualified.
    """

    def __init__(self) -> None:
        self._hard_constraints: list[HardConstraint] = []
        self._soft_preferences: list[SoftPreference] = []
        self._register_default_constraints()

    def _register_default_constraints(self) -> None:
        """Seed non-negotiable system guardrails."""
        self._hard_constraints = [
            HardConstraint(
                constraint_id="cst_immutable_auth",
                name="Immutable Authorization Controls",
                description="Zero tolerance for bypass or weakening of authorization and authentication",
                is_immutable=True,
            ),
            HardConstraint(
                constraint_id="cst_max_risk",
                name="Maximum Allowed Automated Risk",
                description="Automated optimization cannot accept CRITICAL risk without explicit human admin override",
                is_immutable=True,
            ),
            HardConstraint(
                constraint_id="cst_budget_ceiling",
                name="Hourly Budget Ceiling",
                description="Inference and compute cost cannot exceed 25.0 USD per hour",
                is_immutable=False,
                max_allowed_value=25.0,
            ),
            HardConstraint(
                constraint_id="cst_error_ceiling",
                name="Maximum Error Rate Ceiling",
                description="Error rate cannot exceed 0.05 under any tuning configuration",
                is_immutable=False,
                max_allowed_value=0.05,
            ),
            HardConstraint(
                constraint_id="cst_mandatory_verification",
                name="Mandatory Post-Rollout Verification",
                description="Every applied change set must undergo state verification before full rollout",
                is_immutable=True,
            ),
        ]

        self._soft_preferences = [
            SoftPreference(
                preference_id="prf_favor_reversibility",
                name="Prefer Instant Reversibility",
                description="Favor tuning parameters that can be rolled back in under 5 seconds",
                weight=0.7,
            ),
            SoftPreference(
                preference_id="prf_lower_overhead",
                name="Prefer Low Diagnostic Overhead",
                description="Favor adaptations that do not increase memory consumption significantly",
                weight=0.5,
            ),
        ]

    def list_hard_constraints(self) -> list[HardConstraint]:
        """List active hard constraints."""
        return list(self._hard_constraints)

    def list_soft_preferences(self) -> list[SoftPreference]:
        """List active soft preferences."""
        return list(self._soft_preferences)

    def validate_recommendation(
        self,
        recommendation: OptimizationRecommendation,
        current_metrics: dict[str, float] | None = None,
    ) -> tuple[bool, list[str]]:
        """Verify that a candidate recommendation respects all hard constraints.

        Returns:
            (is_valid, list_of_violations)
        """
        violations: list[str] = []

        # 1. Invariant 8: Check immutable boundary
        try:
            validate_immutable_boundary(
                recommendation.target_parameter,
                proposed_action=f"Recommendation {recommendation.recommendation_id}",
            )
        except Exception as exc:
            violations.append(str(exc))

        # 2. Risk constraint
        if recommendation.risk == RiskLevel.CRITICAL:
            violations.append(
                f"HARD_CONSTRAINT_VIOLATION: Recommendation '{recommendation.recommendation_id}' "
                "presents CRITICAL risk and cannot be executed automatically."
            )

        # 3. Budget ceiling check if cost metric available
        metrics = current_metrics or {}
        current_cost = metrics.get("cost_usd")
        if current_cost is not None and current_cost > 25.0:
            violations.append(
                f"HARD_CONSTRAINT_VIOLATION: Current cost ({current_cost} USD) exceeds budget ceiling (25.0 USD)."
            )

        # 4. Error rate ceiling check
        current_err = metrics.get("error_rate")
        if current_err is not None and current_err > 0.05:
            violations.append(
                f"HARD_CONSTRAINT_VIOLATION: Current error rate ({current_err}) exceeds maximum ceiling (0.05)."
            )

        is_valid = len(violations) == 0
        if not is_valid:
            logger.warning(
                "RECOMMENDATION_DISQUALIFIED: %s violated constraints: %s",
                recommendation.recommendation_id,
                "; ".join(violations),
            )
        return is_valid, violations


constraint_validator = ConstraintValidator()

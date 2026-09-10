"""Constraint validation, hard vs soft constraints enforcement, and conflict detection."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.decision.safety import ConstraintConflictError
from app.decision.schemas import CandidateOption, Constraint, ConstraintType


class ConstraintValidationResult(BaseModel):
    """Outcome of evaluating candidate options against defined constraints."""

    is_valid: bool = True
    hard_violations: list[str] = Field(default_factory=list)
    soft_penalties: float = 0.0
    conflicts_detected: list[str] = Field(default_factory=list)


class ConstraintValidator:
    """Evaluates constraints against candidate option metrics and detects logical conflicts."""

    def evaluate_option(self, option: CandidateOption, constraints: list[Constraint]) -> ConstraintValidationResult:
        """Validates all constraints against option metrics. Hard constraint violations disqualify the option."""
        hard_violations = []
        soft_penalty = 0.0

        for con in constraints:
            val = option.metrics.get(con.target_field)
            if val is None:
                # Missing metric: for hard constraint, flag unknown or violation
                if con.constraint_type == ConstraintType.HARD:
                    hard_violations.append(f"Missing required metric '{con.target_field}' for hard constraint '{con.name}'.")
                continue

            satisfied = self._check_condition(val, con.operator, con.value)

            if not satisfied:
                if con.constraint_type == ConstraintType.HARD:
                    hard_violations.append(
                        f"Hard constraint '{con.name}' violated: {con.target_field}={val} (required {con.operator} {con.value})."
                    )
                else:
                    soft_penalty += 0.15  # Soft constraint penalizes score without disqualifying

        is_valid = len(hard_violations) == 0

        # Update candidate option feasibility immediately
        if not is_valid:
            option.is_feasible = False
            option.hard_constraints_satisfied = False
            option.rejection_reason = "; ".join(hard_violations)

        return ConstraintValidationResult(
            is_valid=is_valid,
            hard_violations=hard_violations,
            soft_penalties=soft_penalty,
        )

    def detect_conflicts(self, constraints: list[Constraint]) -> list[str]:
        """Detects contradictory hard constraints on identical target fields."""
        conflicts = []
        fields: dict[str, list[Constraint]] = {}
        for c in constraints:
            if c.constraint_type == ConstraintType.HARD:
                fields.setdefault(c.target_field, []).append(c)

        for field, cons in fields.items():
            if len(cons) >= 2:
                # Check for direct contradictions, e.g. val <= 10 and val >= 50
                max_bound = None
                min_bound = None
                for c in cons:
                    if c.operator == "<=" and isinstance(c.value, (int, float)):
                        max_bound = c.value if max_bound is None else min(max_bound, c.value)
                    elif c.operator == ">=" and isinstance(c.value, (int, float)):
                        min_bound = c.value if min_bound is None else max(min_bound, c.value)

                if max_bound is not None and min_bound is not None and min_bound > max_bound:
                    msg = f"Contradictory hard constraints on '{field}': required >= {min_bound} and <= {max_bound}."
                    conflicts.append(msg)

        if conflicts:
            raise ConstraintConflictError("; ".join(conflicts))

        return conflicts

    def validate_options(
        self,
        options: list[CandidateOption],
        constraints: list[Constraint],
    ) -> tuple[list[CandidateOption], list[str]]:
        """Validates all options against constraints and returns updated options and detected conflicts."""
        conflicts = self.detect_conflicts(constraints)
        for opt in options:
            self.evaluate_option(opt, constraints)
        return options, conflicts

    def _check_condition(self, actual: Any, operator: str, target: Any) -> bool:
        if operator == "<=":
            return actual <= target
        elif operator == ">=":
            return actual >= target
        elif operator == "==":
            return actual == target
        elif operator == "!=":
            return actual != target
        elif operator == "in":
            return actual in target
        return False


constraint_validator = ConstraintValidator()


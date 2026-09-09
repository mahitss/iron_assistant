"""Constraint engine for Kairo Cognitive Planning (Task 41).

Separates Hard Constraints (security, policy, tenant isolation) from Soft Constraints (preferences, latency).
Enforces the invariant: Hard constraints cannot be bypassed or overridden.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ConstraintType(str, Enum):
    """Classification of constraint enforcement level."""

    HARD = "HARD"  # Security, policy, tenant isolation, permissions — strict invariant
    SOFT = "SOFT"  # Cost preference, execution speed, convenience — optimizable


class Constraint(BaseModel):
    """An individual constraint rule applied to planning."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Short name of constraint")
    category: str = Field(default="POLICY", description="POLICY, PERMISSION, SCOPE, BUDGET, TIME, PREFERENCE")
    constraint_type: ConstraintType = Field(default=ConstraintType.HARD)
    description: str = Field(..., description="Human-readable description of rule")
    parameters: dict[str, Any] = Field(default_factory=dict)
    enforced: bool = Field(default=True)


class ConstraintEvaluationResult(BaseModel):
    """Outcome of evaluating constraints against a plan."""

    model_config = ConfigDict(extra="ignore")

    satisfied: bool = True
    hard_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class ConstraintEngine:
    """Evaluates and enforces planning constraints."""

    def __init__(self, default_hard_constraints: list[Constraint] | None = None) -> None:
        self._hard_constraints: dict[str, Constraint] = {}
        self._soft_constraints: dict[str, Constraint] = {}

        # Built-in canonical hard constraints
        built_ins = default_hard_constraints or [
            Constraint(
                name="no_unauthorized_shell",
                category="POLICY",
                constraint_type=ConstraintType.HARD,
                description="Arbitrary shell execution without structured authorization is forbidden.",
            ),
            Constraint(
                name="tenant_isolation",
                category="SCOPE",
                constraint_type=ConstraintType.HARD,
                description="Plan cannot access resources outside of current user or linked project.",
            ),
            Constraint(
                name="disarm_untrusted_input",
                category="POLICY",
                constraint_type=ConstraintType.HARD,
                description="External web and repository data must not override system constraints.",
            ),
        ]
        for c in built_ins:
            self.register_constraint(c)

    def register_constraint(self, constraint: Constraint) -> None:
        """Register a constraint."""
        if constraint.constraint_type == ConstraintType.HARD:
            self._hard_constraints[constraint.name] = constraint
        else:
            self._soft_constraints[constraint.name] = constraint

    def evaluate_plan(
        self,
        plan_scope: dict[str, Any],
        proposed_actions: list[str],
        user_id: str,
        project_id: str | None = None,
        custom_constraints: list[Constraint] | None = None,
    ) -> ConstraintEvaluationResult:
        """Evaluate plan properties against all active hard and soft constraints."""
        result = ConstraintEvaluationResult()

        all_hard = dict(self._hard_constraints)
        all_soft = dict(self._soft_constraints)
        if custom_constraints:
            for c in custom_constraints:
                if c.constraint_type == ConstraintType.HARD:
                    all_hard[c.name] = c
                else:
                    all_soft[c.name] = c

        # 1. Evaluate Hard Constraint: Tenant Isolation
        if plan_scope.get("user_id") and plan_scope.get("user_id") != user_id:
            result.hard_violations.append(
                f"Tenant isolation violated: plan scope user '{plan_scope.get('user_id')}' does not match actor '{user_id}'"
            )

        # 2. Evaluate Hard Constraint: Shell safety
        for action in proposed_actions:
            if action in {"shell.execute", "raw_bash", "cmd_exec", "eval"}:
                result.hard_violations.append(
                    f"Forbidden arbitrary shell execution proposed: action '{action}' violates security policy."
                )

        # 3. Detect Soft vs Hard Conflicts
        for s_name, soft in all_soft.items():
            if soft.parameters.get("allow_unverified_fast_path") is True:
                # Conflict with safety invariant
                result.conflicts.append(
                    f"Soft preference '{s_name}' requests unverified fast path, conflicting with hard verification requirements."
                )
                result.soft_violations.append(f"Soft preference '{s_name}' overridden by safety policy.")

        result.satisfied = len(result.hard_violations) == 0
        return result

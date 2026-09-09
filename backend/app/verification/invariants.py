"""Universal system, security, policy, and state invariants for Kairo Truth Engine (Task 42)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from pydantic import BaseModel, ConfigDict, Field


@dataclass
class InvariantViolation:
    """Detailed record of an invariant violation."""

    rule_id: str
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class Invariant(BaseModel):
    """An immutable rule that must hold true across system states (Spec 39)."""

    model_config = ConfigDict(extra="ignore")

    invariant_id: str
    domain: str = Field(..., description="STATE, SECURITY, POLICY, TASK, APPROVAL, PLAN")
    description: str = Field(..., description="Human-readable statement of invariant")
    severity: str = Field(default="HIGH", description="LOW, MEDIUM, HIGH, CRITICAL")
    verification_strategy: str = Field(default="INVARIANT_CHECK")
    predicate_key: str = Field(..., description="Key in state/context to check")
    expected_value: Any = Field(default=None)


# Alias for backward compatibility
InvariantRule = Invariant


class InvariantEngine:
    """Evaluates core system invariants."""

    def __init__(self) -> None:
        self._invariants: dict[str, Invariant] = {}
        self._load_built_ins()

    def _load_built_ins(self) -> None:
        """Register canonical invariants (Specs 40-46)."""
        # Task Invariant (Spec 40): COMPLETED task must not retain an active execution lease
        self.register(
            Invariant(
                invariant_id="TASK-001",
                domain="TASK",
                description="Completed task must not have an active execution lease.",
                severity="HIGH",
                predicate_key="has_active_lease",
                expected_value=False,
            )
        )
        # Task Invariant (Spec 44): Completed task requires completion evidence
        self.register(
            Invariant(
                invariant_id="TASK-002",
                domain="TASK",
                description="Completed task must have completion evidence.",
                severity="HIGH",
                predicate_key="has_completion_evidence",
                expected_value=True,
            )
        )
        # Approval Invariant (Spec 45): High-risk action cannot execute with expired approval
        self.register(
            Invariant(
                invariant_id="APPROVAL-001",
                domain="APPROVAL",
                description="High-risk actions cannot execute with expired approval.",
                severity="CRITICAL",
                predicate_key="approval_expired",
                expected_value=False,
            )
        )
        # Security Invariant (Spec 42): Unauthorized user cannot access protected state
        self.register(
            Invariant(
                invariant_id="SECURITY-001",
                domain="SECURITY",
                description="Tenant isolation must never be breached.",
                severity="CRITICAL",
                predicate_key="tenant_isolation_breached",
                expected_value=False,
            )
        )

    def register(self, invariant: Invariant) -> None:
        """Register an invariant."""
        self._invariants[invariant.invariant_id] = invariant

    def evaluate_all(self, state: dict[str, Any]) -> list[InvariantViolation]:
        """Evaluate all invariants against state, returning structured violations."""
        violations: list[InvariantViolation] = []

        # Complex predicate logic checks
        # TASK-001: task_status == COMPLETED and has_active_lease == True
        if state.get("task_status") == "COMPLETED" and state.get("has_active_lease") is True:
            violations.append(
                InvariantViolation(
                    rule_id="TASK-001",
                    severity="HIGH",
                    message="Completed task must not have an active execution lease.",
                    details={"task_status": "COMPLETED", "has_active_lease": True},
                )
            )

        # TASK-002: task_status == COMPLETED and empty/no completion_evidence
        if state.get("task_status") == "COMPLETED":
            comp_ev = state.get("completion_evidence")
            if not comp_ev:
                violations.append(
                    InvariantViolation(
                        rule_id="TASK-002",
                        severity="HIGH",
                        message="Completed task must have completion evidence.",
                        details={"completion_evidence": comp_ev},
                    )
                )

        # APPROVAL-001: high risk action with approval_expired or missing approval
        if state.get("is_high_risk") is True:
            if state.get("approval_expired") is True or state.get("has_approval") is False:
                violations.append(
                    InvariantViolation(
                        rule_id="APPROVAL-001",
                        severity="CRITICAL",
                        message="High-risk action cannot execute without valid, unexpired approval.",
                        details={"approval_expired": state.get("approval_expired"), "has_approval": state.get("has_approval")},
                    )
                )

        # SECURITY-001: tenant isolation breached or unauthorized access
        if state.get("tenant_isolation_breached") is True or state.get("unauthorized_access") is True:
            violations.append(
                InvariantViolation(
                    rule_id="SECURITY-001",
                    severity="CRITICAL",
                    message="Tenant isolation or access control breached.",
                    details={"breached": True},
                )
            )

        # Generic predicate check for other registered invariants
        for inv in self._invariants.values():
            if inv.predicate_key in state:
                val = state[inv.predicate_key]
                if val != inv.expected_value and not any(v.rule_id == inv.invariant_id for v in violations):
                    violations.append(
                        InvariantViolation(
                            rule_id=inv.invariant_id,
                            severity=inv.severity,
                            message=inv.description,
                            details={"actual": val, "expected": inv.expected_value},
                        )
                    )

        return violations

    def evaluate_state(self, state: dict[str, Any], domain: str | None = None) -> list[str]:
        """Evaluate invariants against state. Returns list of violation messages."""
        violations = self.evaluate_all(state)
        if domain:
            violations = [v for v in violations if self._invariants.get(v.rule_id) and self._invariants[v.rule_id].domain == domain]
        return [f"[{v.severity}] Invariant '{v.rule_id}' breached: {v.message}" for v in violations]

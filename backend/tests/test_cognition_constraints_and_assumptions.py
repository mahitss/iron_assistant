"""Unit tests for hard/soft constraints and assumption validation (Task 41)."""

import pytest
from app.cognition.assumptions import (
    AssumptionCriticality,
    AssumptionValidationStatus,
    AssumptionValidator,
    PlanAssumption,
)
from app.cognition.constraints import (
    Constraint,
    ConstraintEngine,
    ConstraintType,
)


def test_hard_constraint_forbids_arbitrary_shell():
    engine = ConstraintEngine()
    result = engine.evaluate_plan(
        plan_scope={"user_id": "user_1"},
        proposed_actions=["git_status", "shell.execute"],
        user_id="user_1",
    )

    assert not result.satisfied
    assert len(result.hard_violations) > 0
    assert any("arbitrary shell" in v.lower() for v in result.hard_violations)


def test_tenant_isolation_hard_constraint():
    engine = ConstraintEngine()
    result = engine.evaluate_plan(
        plan_scope={"user_id": "victim_user"},
        proposed_actions=["inspect_state"],
        user_id="attacker_user",
    )

    assert not result.satisfied
    assert any("tenant isolation" in v.lower() for v in result.hard_violations)


def test_assumption_validation_success():
    asmp = PlanAssumption(
        plan_id="p1",
        statement="Database connection is ready and available.",
        criticality=AssumptionCriticality.HIGH,
    )

    all_valid, failed = AssumptionValidator.validate_assumptions(
        assumptions=[asmp],
        current_state={"database_ready": True},
    )

    assert all_valid
    assert len(failed) == 0
    assert asmp.status == AssumptionValidationStatus.VALID


def test_assumption_invalidation_detected():
    asmp = PlanAssumption(
        plan_id="p1",
        statement="Staging environment is available.",
        criticality=AssumptionCriticality.CRITICAL,
    )

    all_valid, failed = AssumptionValidator.validate_assumptions(
        assumptions=[asmp],
        current_state={"staging_available": False},
    )

    assert not all_valid
    assert len(failed) == 1
    assert failed[0].status == AssumptionValidationStatus.INVALID

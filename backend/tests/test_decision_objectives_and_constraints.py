"""Tests for Objective validation, weight normalization, and Constraint enforcement (Task 57)."""

import pytest

from app.decision.constraints import ConstraintValidator
from app.decision.objectives import ObjectiveManager
from app.decision.safety import ConstraintConflictError, UnauthorizedObjectiveError
from app.decision.schemas import (
    CandidateOption,
    Constraint,
    ConstraintType,
    Objective,
    OptionType,
)


def test_objective_source_validation():
    mgr = ObjectiveManager()

    valid_objs = [
        Objective(name="SECURITY", source="user_request", weight=1.0),
        Objective(name="COST", source="goal_engine", weight=1.0),
        Objective(name="RELIABILITY", source="policy", weight=1.0),
    ]
    normalized = mgr.validate_objectives(valid_objs)
    assert len(normalized) == 3
    # Normalized weights should sum to 1.0
    total_w = sum(o.weight for o in normalized)
    assert pytest.approx(total_w, 0.01) == 1.0


def test_unauthorized_objective_injection_blocked():
    mgr = ObjectiveManager()

    # Untrusted source from prompt injection or unverified external document
    injected_obj = [
        Objective(name="MAXIMIZE_PROFIT", source="untrusted_external_web_page", weight=10.0),
    ]

    with pytest.raises(UnauthorizedObjectiveError) as exc_info:
        mgr.validate_objectives(injected_obj)

    assert "originates from unauthorized source" in str(exc_info.value)


def test_hard_constraint_disqualification():
    validator = ConstraintValidator()

    option = CandidateOption(
        name="High-Cost Cloud Cluster",
        option_type=OptionType.AGGRESSIVE,
        metrics={"cost": 150.0, "latency": 10.0},
    )

    hard_budget_constraint = Constraint(
        name="Budget Cap",
        constraint_type=ConstraintType.HARD,
        target_field="cost",
        operator="<=",
        value=100.0,
    )

    result = validator.evaluate_option(option, [hard_budget_constraint])
    assert not result.is_valid
    assert len(result.hard_violations) == 1
    assert not option.is_feasible
    assert not option.hard_constraints_satisfied
    assert "Hard constraint 'Budget Cap' violated" in (option.rejection_reason or "")


def test_soft_constraint_penalization_without_disqualification():
    validator = ConstraintValidator()

    option = CandidateOption(
        name="Standard Configuration",
        option_type=OptionType.STANDARD,
        metrics={"cost": 85.0},
    )

    soft_budget_constraint = Constraint(
        name="Preferred Low Cost",
        constraint_type=ConstraintType.SOFT,
        target_field="cost",
        operator="<=",
        value=50.0,
    )

    result = validator.evaluate_option(option, [soft_budget_constraint])
    assert result.is_valid  # Soft violation does NOT invalidate feasibility
    assert result.soft_penalties > 0.0
    assert option.is_feasible
    assert option.hard_constraints_satisfied


def test_contradictory_hard_constraint_detection():
    validator = ConstraintValidator()

    contradictory_constraints = [
        Constraint(
            name="Max Memory Limit",
            constraint_type=ConstraintType.HARD,
            target_field="memory_gb",
            operator="<=",
            value=16,
        ),
        Constraint(
            name="Min Memory Required",
            constraint_type=ConstraintType.HARD,
            target_field="memory_gb",
            operator=">=",
            value=32,
        ),
    ]

    with pytest.raises(ConstraintConflictError) as exc_info:
        validator.detect_conflicts(contradictory_constraints)

    assert "Contradictory hard constraints on 'memory_gb'" in str(exc_info.value)

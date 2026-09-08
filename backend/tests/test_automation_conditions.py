"""Unit tests for deterministic ConditionEngine."""

import pytest

from app.automation.conditions import ConditionEngine, ConditionEvaluationError


def test_condition_equals_and_not_equals():
    """Verify equality and inequality conditions."""
    data = {"status": "failure", "exit_code": 1}

    cond_eq = {"field": "status", "operator": "equals", "value": "failure"}
    assert ConditionEngine.evaluate(cond_eq, data) is True

    cond_neq = {"field": "status", "operator": "not_equals", "value": "success"}
    assert ConditionEngine.evaluate(cond_neq, data) is True

    cond_fail = {"field": "status", "operator": "equals", "value": "success"}
    assert ConditionEngine.evaluate(cond_fail, data) is False


def test_condition_contains():
    """Verify string and list membership."""
    data = {"tags": ["ci", "frontend", "prod"], "message": "build failed on step 3"}

    assert ConditionEngine.evaluate({"field": "tags", "operator": "contains", "value": "ci"}, data) is True
    assert (
        ConditionEngine.evaluate({"field": "tags", "operator": "contains", "value": "backend"}, data) is False
    )
    assert (
        ConditionEngine.evaluate({"field": "message", "operator": "contains", "value": "step 3"}, data)
        is True
    )


def test_condition_numeric_comparisons():
    """Verify greater_than and less_than with numeric casting."""
    data = {"open_issues": 12, "failing_tests": 0}

    assert (
        ConditionEngine.evaluate({"field": "open_issues", "operator": "greater_than", "value": 5}, data)
        is True
    )
    assert (
        ConditionEngine.evaluate({"field": "open_issues", "operator": "less_than", "value": 20}, data) is True
    )
    assert (
        ConditionEngine.evaluate({"field": "failing_tests", "operator": "greater_than", "value": 0}, data)
        is False
    )


def test_condition_nested_field_and_array_resolution():
    """Verify resolving dot notation and bracket indexing."""
    data = {
        "repository": {"name": "iron_assistant", "is_clean": False},
        "checks": [
            {"name": "lint", "conclusion": "success"},
            {"name": "tests", "conclusion": "failure"},
        ],
    }

    assert (
        ConditionEngine.evaluate({"field": "repository.is_clean", "operator": "equals", "value": False}, data)
        is True
    )
    assert (
        ConditionEngine.evaluate(
            {"field": "checks[1].conclusion", "operator": "equals", "value": "failure"}, data
        )
        is True
    )
    assert (
        ConditionEngine.evaluate(
            {"field": "checks[0].conclusion", "operator": "status_is", "value": "success"}, data
        )
        is True
    )


def test_condition_exists():
    """Verify existence check."""
    data = {"error": "Timeout occurred", "result": None}

    assert ConditionEngine.evaluate({"field": "error", "operator": "exists"}, data) is True
    assert ConditionEngine.evaluate({"field": "nonexistent", "operator": "exists"}, data) is False


def test_unsupported_operator_and_no_eval():
    """Verify unsupported operators or code expressions are rejected."""
    with pytest.raises(ConditionEvaluationError):
        ConditionEngine.evaluate({"operator": "eval", "value": "True"}, {})

    # Code in value is treated strictly as literal string
    data = {"msg": "__import__('os').system('echo pwned')"}
    cond = {"field": "msg", "operator": "equals", "value": "__import__('os').system('echo pwned')"}
    # Evaluates literal string equality without executing code
    assert ConditionEngine.evaluate(cond, data) is True

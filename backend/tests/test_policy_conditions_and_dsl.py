"""Unit tests for Policy Conditions, Operators, and DSL (Task 36, Specs 114-117)."""

import pytest
from app.policy.conditions import ConditionEvaluator
from app.policy.schemas import (
    ConditionOperator,
    PolicyContext,
    PolicyRuleCondition,
)


def test_condition_equals_operator():
    ctx = PolicyContext(environment="production", action="deploy")
    cond = PolicyRuleCondition(field="environment", operator=ConditionOperator.EQUALS, value="production")
    assert ConditionEvaluator.evaluate_condition(cond, ctx) is True

    cond_false = PolicyRuleCondition(field="environment", operator=ConditionOperator.EQUALS, value="staging")
    assert ConditionEvaluator.evaluate_condition(cond_false, ctx) is False


def test_condition_not_equals_operator():
    ctx = PolicyContext(environment="staging")
    cond = PolicyRuleCondition(field="environment", operator=ConditionOperator.NOT_EQUALS, value="production")
    assert ConditionEvaluator.evaluate_condition(cond, ctx) is True


def test_condition_in_and_not_in_operator():
    ctx = PolicyContext(action="delete")
    cond_in = PolicyRuleCondition(field="action", operator=ConditionOperator.IN, value=["delete", "drop", "wipe"])
    assert ConditionEvaluator.evaluate_condition(cond_in, ctx) is True

    cond_not_in = PolicyRuleCondition(field="action", operator=ConditionOperator.NOT_IN, value=["read", "list"])
    assert ConditionEvaluator.evaluate_condition(cond_not_in, ctx) is True


def test_condition_contains_operator():
    ctx = PolicyContext(action="deploy_staging_cluster")
    cond_contains = PolicyRuleCondition(field="action", operator=ConditionOperator.CONTAINS, value="deploy")
    assert ConditionEvaluator.evaluate_condition(cond_contains, ctx) is True

    cond_no_match = PolicyRuleCondition(field="action", operator=ConditionOperator.CONTAINS, value="delete")
    assert ConditionEvaluator.evaluate_condition(cond_no_match, ctx) is False


def test_condition_numeric_comparison():
    ctx = PolicyContext(task={"duration_seconds": 120, "tool_calls_count": 15})

    gt_cond = PolicyRuleCondition(field="task.duration_seconds", operator=ConditionOperator.GREATER_THAN, value=60)
    assert ConditionEvaluator.evaluate_condition(gt_cond, ctx) is True

    lt_cond = PolicyRuleCondition(field="task.tool_calls_count", operator=ConditionOperator.LESS_THAN, value=10)
    assert ConditionEvaluator.evaluate_condition(lt_cond, ctx) is False


def test_condition_exists_operator():
    ctx = PolicyContext(target={"path": "/var/log/app.log"})
    cond_exists = PolicyRuleCondition(field="target.path", operator=ConditionOperator.EXISTS, value=True)
    assert ConditionEvaluator.evaluate_condition(cond_exists, ctx) is True

    cond_not_exists = PolicyRuleCondition(field="target.missing_field", operator=ConditionOperator.EXISTS, value=True)
    assert ConditionEvaluator.evaluate_condition(cond_not_exists, ctx) is False


def test_condition_conjunction_evaluate_all():
    ctx = PolicyContext(
        environment="production",
        action="deploy",
        device={"is_trusted": True},
    )
    conditions = [
        PolicyRuleCondition(field="environment", operator=ConditionOperator.EQUALS, value="production"),
        PolicyRuleCondition(field="action", operator=ConditionOperator.EQUALS, value="deploy"),
        PolicyRuleCondition(field="device.is_trusted", operator=ConditionOperator.EQUALS, value=True),
    ]
    assert ConditionEvaluator.evaluate_all(conditions, ctx) is True

    failing_conditions = conditions + [
        PolicyRuleCondition(field="action", operator=ConditionOperator.EQUALS, value="read")
    ]
    assert ConditionEvaluator.evaluate_all(failing_conditions, ctx) is False

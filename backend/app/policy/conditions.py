"""Condition evaluator for deterministic, typed policy rules (Task 36).

Never executes arbitrary Python/code. Strictly evaluates typed operators.
"""

from collections.abc import Collection
from datetime import datetime
from typing import Any

from app.policy.schemas import ConditionOperator, PolicyContext, PolicyRuleCondition


class ConditionEvaluator:
    """Safely evaluates conditions against a PolicyContext without code execution."""

    @staticmethod
    def resolve_field(context: PolicyContext, field_path: str) -> Any:
        """Resolve a dotted field path from PolicyContext into its value."""
        parts = field_path.strip().split(".")
        current: Any = context.model_dump()

        for part in parts:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    @classmethod
    def evaluate_condition(cls, condition: PolicyRuleCondition, context: PolicyContext) -> bool:
        """Evaluate a single condition against the context."""
        val = cls.resolve_field(context, condition.field)
        op = condition.operator
        target = condition.value

        if op == ConditionOperator.EXISTS:
            if target is False or target == "false":
                return val is None
            return val is not None and val != "" and val != []

        if val is None:
            # If field is missing, evaluate null-safety
            if op == ConditionOperator.NOT_EQUALS:
                return target is not None
            if op == ConditionOperator.NOT_IN:
                return True
            return False

        # Compare based on operator
        try:
            if op == ConditionOperator.EQUALS:
                return str(val).lower() == str(target).lower() if isinstance(target, (str, bool)) else val == target

            if op == ConditionOperator.NOT_EQUALS:
                return str(val).lower() != str(target).lower() if isinstance(target, (str, bool)) else val != target

            if op == ConditionOperator.IN:
                if isinstance(target, (list, tuple, set)):
                    # Check case-insensitively if strings
                    target_strs = [str(x).lower() for x in target]
                    return str(val).lower() in target_strs or val in target
                return False

            if op == ConditionOperator.NOT_IN:
                if isinstance(target, (list, tuple, set)):
                    target_strs = [str(x).lower() for x in target]
                    return str(val).lower() not in target_strs and val not in target
                return True

            if op == ConditionOperator.CONTAINS:
                if isinstance(val, (list, tuple, set)):
                    target_str = str(target).lower()
                    return any(str(x).lower() == target_str for x in val) or target in val
                if isinstance(val, str):
                    return str(target).lower() in val.lower()
                return False

            if op in (ConditionOperator.GREATER_THAN, ConditionOperator.LESS_THAN,
                      ConditionOperator.GREATER_EQUAL, ConditionOperator.LESS_EQUAL):
                num_val = float(val)
                num_target = float(target)
                if op == ConditionOperator.GREATER_THAN:
                    return num_val > num_target
                if op == ConditionOperator.LESS_THAN:
                    return num_val < num_target
                if op == ConditionOperator.GREATER_EQUAL:
                    return num_val >= num_target
                if op == ConditionOperator.LESS_EQUAL:
                    return num_val <= num_target

            if op in (ConditionOperator.BEFORE, ConditionOperator.AFTER):
                dt_val = cls._to_datetime(val)
                dt_target = cls._to_datetime(target)
                if dt_val and dt_target:
                    if op == ConditionOperator.BEFORE:
                        return dt_val < dt_target
                    if op == ConditionOperator.AFTER:
                        return dt_val > dt_target
                return False

        except (ValueError, TypeError):
            return False

        return False

    @classmethod
    def evaluate_all(cls, conditions: list[PolicyRuleCondition], context: PolicyContext) -> bool:
        """Evaluate a list of conditions (conjunction: all must be true)."""
        if not conditions:
            return True
        return all(cls.evaluate_condition(cond, context) for cond in conditions)

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

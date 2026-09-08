"""Deterministic ConditionEngine for workflow execution without arbitrary code or eval()."""

import logging
from typing import Any

logger = logging.getLogger("kairo.automation.conditions")

SUPPORTED_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "greater_than",
    "less_than",
    "exists",
    "status_is",
}


class ConditionEvaluationError(ValueError):
    """Raised when condition syntax or field resolution fails."""


class ConditionEngine:
    """Evaluates deterministic conditions over JSON-compatible step results."""

    @classmethod
    def resolve_field(cls, data: Any, field_path: str) -> Any:
        """Resolve dotted or bracketed path inside nested dictionaries/lists.

        Examples:
        - "status.is_clean"
        - "checks[0].conclusion"
        - "total_matches"
        """
        if not field_path or not field_path.strip():
            return data

        parts = field_path.strip().split(".")
        current = data

        for part in parts:
            if current is None:
                return None

            # Handle array indexing: e.g. "checks[0]"
            if "[" in part and part.endswith("]"):
                key, idx_part = part[:-1].split("[", 1)
                if key:
                    if not isinstance(current, dict) or key not in current:
                        return None
                    current = current[key]
                try:
                    idx = int(idx_part)
                    if isinstance(current, (list, tuple)) and 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
                except ValueError:
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                elif hasattr(current, part):
                    current = getattr(current, part)
                else:
                    return None

        return current

    @classmethod
    def evaluate(cls, condition: dict[str, Any], context: Any) -> bool:
        """Evaluate a single deterministic condition.

        Schema:
        {
            "field": "checks[0].conclusion",
            "operator": "equals",
            "value": "failure"
        }
        """
        operator = condition.get("operator", "").lower().strip()
        if operator not in SUPPORTED_OPERATORS:
            raise ConditionEvaluationError(
                f"Unsupported operator '{operator}'. Must be one of: {SUPPORTED_OPERATORS}"
            )

        field_path = condition.get("field", "")
        expected_value = condition.get("value")

        actual_value = cls.resolve_field(context, field_path)

        if operator == "exists":
            return actual_value is not None

        if operator == "equals" or operator == "status_is":
            return actual_value == expected_value

        if operator == "not_equals":
            return actual_value != expected_value

        if operator == "contains":
            if actual_value is None or expected_value is None:
                return False
            if isinstance(actual_value, (str, list, dict, tuple)):
                return expected_value in actual_value
            return str(expected_value) in str(actual_value)

        if operator == "greater_than":
            try:
                return float(actual_value) > float(expected_value)
            except (ValueError, TypeError):
                return False

        if operator == "less_than":
            try:
                return float(actual_value) < float(expected_value)
            except (ValueError, TypeError):
                return False

        return False

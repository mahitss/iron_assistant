"""Autonomy and Automation Governor for Kairo Policy Engine (Task 36).

Enforces:
- Every autonomous task step is verified against policy.
- Hard limits on autonomous budgets (tool-calls, time duration, spend).
- Automated workflow run counts and execution frequency caps.
- Strict scope boundary prevention (stopping on unauthorized scope expansion).
"""

from typing import Any

from app.policy.schemas import PolicyContext, PolicyDecisionType


class AutonomyGovernor:
    """Monitors and governs autonomous execution, resource consumption, and task boundaries."""

    DEFAULT_MAX_TOOL_CALLS = 50
    DEFAULT_MAX_DURATION_SECONDS = 3600  # 1 hour
    DEFAULT_MAX_AUTOMATION_EXECUTIONS = 100

    @classmethod
    def evaluate_task_limits(cls, context: PolicyContext) -> tuple[PolicyDecisionType | None, str | None, dict[str, Any]]:
        """Evaluate autonomous task budgets, step limits, and scope boundaries.

        Returns (Decision, Reason, constraints).
        """
        task = context.task
        constraints: dict[str, Any] = {}

        if not task:
            return None, None, constraints

        # 1. Tool Call Budget Check (Sections 51, 52, 144)
        budget = task.get("budget") or {}
        max_tool_calls = budget.get("max_tool_calls", cls.DEFAULT_MAX_TOOL_CALLS)
        tool_calls_count = task.get("tool_calls_count", 0)

        if tool_calls_count >= max_tool_calls:
            constraints["budget_exceeded"] = "tool_calls"
            return (
                PolicyDecisionType.DEFER,
                f"Autonomous task exceeded tool-call budget ({tool_calls_count}/{max_tool_calls}). Pausing for human authorization.",
                constraints
            )

        # 2. Task Duration Budget Check
        duration_seconds = task.get("duration_seconds", 0)
        max_duration = budget.get("max_duration_seconds", cls.DEFAULT_MAX_DURATION_SECONDS)
        if duration_seconds > max_duration:
            constraints["budget_exceeded"] = "duration"
            return (
                PolicyDecisionType.DEFER,
                f"Autonomous task exceeded maximum permitted run duration ({duration_seconds}s > {max_duration}s). Pausing.",
                constraints
            )

        # 3. Cost / Spend Budget Check
        spent_usd = budget.get("spent_usd", 0.0)
        max_spent_usd = budget.get("max_spent_usd")
        if max_spent_usd is not None and spent_usd >= max_spent_usd:
            constraints["budget_exceeded"] = "cost"
            return (
                PolicyDecisionType.DEFER,
                f"Autonomous task reached cost budget limit (${spent_usd:.2f} >= ${max_spent_usd:.2f}). Pausing.",
                constraints
            )

        # 4. Automation Execution Limit Check (Sections 49, 143)
        automation_info = task.get("automation") or {}
        if automation_info:
            execution_count = automation_info.get("execution_count", 0)
            max_executions = automation_info.get("max_executions", cls.DEFAULT_MAX_AUTOMATION_EXECUTIONS)
            if execution_count >= max_executions:
                constraints["automation_limit_reached"] = True
                return (
                    PolicyDecisionType.DENY,
                    f"Automation execution limit reached ({execution_count}/{max_executions}). Blocked from further runs.",
                    constraints
                )

        # 5. Task replanning boundary check (Section 55)
        if task.get("is_replanning") is True and task.get("attempting_scope_expansion") is True:
            return (
                PolicyDecisionType.DENY,
                "Task replanning cannot silently expand policy or resource scope. Explicit approval required.",
                constraints
            )

        return None, None, constraints

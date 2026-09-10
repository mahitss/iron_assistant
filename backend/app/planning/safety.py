"""Safety boundaries, prompt injection defense, and execution firewall for Strategic Planning (Task 58)."""

from __future__ import annotations

import re
from typing import Any


class PlanningSafetyError(Exception):
    """Base exception for planning safety violations."""
    pass


class PlanningExecutionBoundaryError(PlanningSafetyError):
    """Raised when the Planning Engine attempts to directly invoke production execution tools."""
    pass


class MaliciousTaskInjectionError(PlanningSafetyError):
    """Raised when an untrusted external text attempts to inject unauthorized tasks."""
    pass


class DependencyCycleError(PlanningSafetyError):
    """Raised when a circular dependency is detected in the task or milestone graph."""
    pass


class DeadlineInfeasibleError(PlanningSafetyError):
    """Raised when critical path analysis demonstrates that a hard deadline cannot be met."""
    pass


class PlanStaleError(PlanningSafetyError):
    """Raised when execution is attempted against a plan whose state or environment has drifted."""
    pass


# Tools that must never be directly invoked from within planning logic
BLOCKED_EXECUTION_TOOLS = frozenset({
    "tool_executor",
    "execute_tool",
    "bash",
    "shell",
    "run_command",
    "file_writer",
    "write_to_file",
    "git_push",
    "deploy",
    "cloud_api",
    "database_mutate",
    "db_execute_write",
    "send_email",
    "send_message",
    "browser_action",
    "computer_control",
    "bash_executor",
})

# Patterns matching prompt injection or unauthorized task execution
PLAN_INJECTION_PATTERNS = [
    re.compile(r"(?i)run\s+this\s+destructive\s+command\s+immediately"),
    re.compile(r"(?i)ignore\s+(?:all\s+)?(?:previous\s+)?(?:all\s+)?(instructions|constraints|policies|prerequisites)"),
    re.compile(r"(?i)bypass\s+(approval|authorization|execution_gate|checkpoint)"),
    re.compile(r"(?i)force\s+execute\s+without\s+verification"),
    re.compile(r"(?i)delete\s+(all\s+)?(database|cluster|storage|volume|data)\s+silently"),
    re.compile(r"(?i)drop\s+table\s+[a-zA-Z0-9_]+"),
    re.compile(r"(?i)rm\s+-rf\s+[/~a-zA-Z0-9_\*]+"),
    re.compile(r"(?i)truncate\s+table\s+[a-zA-Z0-9_]+"),
]

# Sensitive credentials scrubbing patterns
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret|password|auth[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
    re.compile(r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{10,})"),
    re.compile(r"(?i)sk-[a-zA-Z0-9_\-]{15,}"),
    re.compile(r"(?i)ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
]


def block_direct_tool_execution(tool_name: str = "tool", action_name: str = "", *args: Any, **kwargs: Any) -> None:
    """Hard firewall check: Ensures Strategic Planning never invokes production execution tools directly."""
    target = tool_name or action_name or "unknown_tool"
    raise PlanningExecutionBoundaryError(
        f"FIREWALL BLOCKED: Planning Engine cannot directly execute tools. Action '{target}' "
        "is strictly forbidden from directly invoking production tool. "
        "The Strategic Planning Engine produces plan proposals and execution waves, but cannot execute side-effecting tools directly."
    )


def sanitize_plan_directive(content: str) -> str:
    """Neutralizes prompt injection directives in external task or goal descriptions."""
    cleaned = content
    for pattern in PLAN_INJECTION_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[DISARMED_DIRECTIVE]", cleaned)
    return cleaned


def scrub_plan_secrets(data: Any) -> Any:
    """Recursively redacts API keys, secrets, and credentials from planning payloads."""
    if isinstance(data, str):
        cleaned = data
        cleaned = SECRET_PATTERNS[0].sub(r"\1: [REDACTED_SECRET]", cleaned)
        for pattern in SECRET_PATTERNS[1:]:
            cleaned = pattern.sub("[REDACTED_SECRET]", cleaned)
        return cleaned
    elif isinstance(data, dict):
        cleaned_dict = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ("secret", "password", "token", "api_key", "private_key", "credential")):
                cleaned_dict[k] = "[REDACTED_SECRET]"
            else:
                cleaned_dict[k] = scrub_plan_secrets(v)
        return cleaned_dict
    elif isinstance(data, list):
        return [scrub_plan_secrets(item) for item in data]
    return data

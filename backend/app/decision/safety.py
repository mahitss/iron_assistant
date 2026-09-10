"""Safety boundaries, prompt injection defense, and execution firewall for Decision Engine."""

from __future__ import annotations

import re
from typing import Any


class DecisionSafetyError(Exception):
    """Base exception for decision safety violations."""
    pass


class DecisionExecutionBoundaryError(DecisionSafetyError):
    """Raised when the Decision Engine attempts to directly invoke production execution tools."""
    pass


class UnauthorizedObjectiveError(DecisionSafetyError):
    """Raised when an external or untrusted source attempts to inject system objectives."""
    pass


class ConstraintConflictError(DecisionSafetyError):
    """Raised when mutually incompatible hard constraints are present."""
    pass


# Tools that must never be called from within decision logic
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
})

# Patterns matching prompt injection or decision manipulation
DECISION_INJECTION_PATTERNS = [
    re.compile(r"(?i)always\s+(choose|pick|select|recommend)\s+option\s+[a-z0-9_]+"),
    re.compile(r"(?i)ignore\s+(previous|all)\s+(instructions|constraints|policies|objectives)"),
    re.compile(r"(?i)objective\s*:\s*maximize\s+profit\s+regardless\s+of\s+security"),
    re.compile(r"(?i)bypass\s+(approval|authorization|decision_gate|policy)"),
    re.compile(r"(?i)mark\s+as\s+approved\s+without\s+authority"),
]

# Sensitive credentials scrubbing patterns
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret|password|auth[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
    re.compile(r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{10,})"),
    re.compile(r"(?i)sk-[a-zA-Z0-9_\-]{15,}"),
    re.compile(r"(?i)ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
]


def block_direct_tool_execution(action_name: str, *args: Any, **kwargs: Any) -> None:
    """Hard firewall check: Ensures Decision Engine never invokes execution tools directly."""
    raise DecisionExecutionBoundaryError(
        f"FIREWALL BLOCKED: Action '{action_name}' is strictly forbidden from directly invoking production tool. "
        "The Decision Engine is a decision support system and cannot execute actions directly."
    )


def sanitize_decision_input(content: str) -> str:
    """Neutralizes prompt injection directives in external decision text."""
    cleaned = content
    for pattern in DECISION_INJECTION_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[INJECTION_NEUTRALIZED]", cleaned)
    return cleaned


def scrub_decision_secrets(data: Any) -> Any:
    """Recursively redacts API keys, secrets, and credentials from decision structures."""
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
                cleaned_dict[k] = scrub_decision_secrets(v)
        return cleaned_dict
    elif isinstance(data, list):
        return [scrub_decision_secrets(item) for item in data]
    return data


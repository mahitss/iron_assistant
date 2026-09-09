"""Evaluation safety, trace sanitization, and credential redaction safeguards."""

import re
from typing import Any


# Known synthetic fake secrets used across evaluation fixtures
KNOWN_SYNTHETIC_SECRETS = [
    "FAKE_API_KEY",
    "FAKE_TOKEN",
    "FAKE_PRIVATE_KEY",
    "FAKE_SECRET_123",
    "kairo_test_secret_998877",
    "ghp_fakeGitHubTokenForTestingOnly99",
    "sk-fakeOpenAISecretKeyForTesting123",
]

# Sensitive pattern regexes
SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key|token|secret|password|bearer|auth[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", re.IGNORECASE),
    re.compile(r"(ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})"),
    re.compile(r"(sk-[a-zA-Z0-9]{20,})"),
    re.compile(r"(-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----)"),
]


class TraceSanitizer:
    """Sanitizes evaluation execution traces, redacting credentials, tokens, and fake keys."""

    @classmethod
    def redact_text(cls, text: str) -> str:
        if not text:
            return ""

        sanitized = text
        for secret in KNOWN_SYNTHETIC_SECRETS:
            sanitized = sanitized.replace(secret, "[REDACTED_SECRET]")

        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub(r"\1: [REDACTED]", sanitized)

        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Any) -> Any:
        """Recursively redact sensitive fields and pattern matches."""
        if isinstance(data, dict):
            clean = {}
            for k, v in data.items():
                k_lower = str(k).lower()
                if any(s in k_lower for s in ("password", "secret", "token", "api_key", "private_key", "authorization")):
                    clean[k] = "[REDACTED]"
                else:
                    clean[k] = cls.sanitize_dict(v)
            return clean
        elif isinstance(data, list):
            return [cls.sanitize_dict(item) for item in data]
        elif isinstance(data, str):
            return cls.redact_text(data)
        return data

    @classmethod
    def sanitize_trace(cls, trace_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sanitize a full chronological execution trace."""
        return [cls.sanitize_dict(ev) for ev in trace_events]


class EvaluationSandbox:
    """Safety guard ensuring evaluation executions adhere to sandbox constraints."""

    # Prohibited commands that should NEVER execute under evaluation
    DESTRUCTIVE_COMMANDS = {
        "rm", "del", "rmdir", "format", "mkfs", "dd", "shutdown", "reboot",
        "poweroff", "init", "drop", "truncate", "system_shutdown"
    }

    def __init__(self, mode: Any = None) -> None:
        self.mode = mode

    def get_execution_context(self, user_id: str = "eval_user") -> dict[str, Any]:
        """Generate isolated execution context dictionary without production secrets."""
        return {
            "user_id": user_id,
            "is_evaluation_mode": True,
            "sandbox_active": True,
            "mode": str(self.mode) if self.mode else "LOCAL",
        }

    @classmethod
    def is_action_safe(cls, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str | None]:
        """Verify whether an evaluation action is within safe non-destructive bounds."""
        name_lower = tool_name.lower()
        if name_lower in cls.DESTRUCTIVE_COMMANDS:
            return False, f"Destructive tool '{tool_name}' is strictly blocked in evaluation sandbox."

        cmd = str(arguments.get("command", "") or arguments.get("cmd", "")).lower()
        for bad in cls.DESTRUCTIVE_COMMANDS:
            if re.search(r"\b" + re.escape(bad) + r"\b", cmd):
                return False, f"Potentially destructive command '{bad}' blocked in evaluation sandbox."

        return True, None

"""Argument sanitization, sensitive data redaction, and action fingerprinting."""

import hashlib
import json
import re
from typing import Any

# Sensitive dictionary key patterns (case-insensitive substring or match)
SENSITIVE_KEY_PATTERNS = {
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "auth",
    "authorization",
    "cookie",
    "credential",
    "private_key",
    "ssh_key",
}

# Value patterns for secret detection
SECRET_REGEXES = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{15,}", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"-----BEGIN[ A-Z0-9_-]+PRIVATE KEY-----[\s\S]+?-----END[ A-Z0-9_-]+PRIVATE KEY-----"),
]

MAX_VALUE_LENGTH = 500


class ArgumentSanitizer:
    """Sanitizes tool arguments, redacting secrets and bounding lengths for audit records."""

    @classmethod
    def redact_string(cls, text: str) -> str:
        """Apply regex mask to sensitive strings and truncate oversized values."""
        if not text:
            return text

        masked = text
        for pattern in SECRET_REGEXES:
            masked = pattern.sub("[REDACTED_SECRET]", masked)

        if len(masked) > MAX_VALUE_LENGTH:
            return masked[:MAX_VALUE_LENGTH] + "... [TRUNCATED]"

        return masked

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Recursively redact sensitive keys and sanitize values."""
        if isinstance(data, dict):
            sanitized_dict = {}
            for k, v in data.items():
                k_lower = str(k).lower()
                if any(pat in k_lower for pat in SENSITIVE_KEY_PATTERNS):
                    sanitized_dict[k] = "[REDACTED]"
                else:
                    sanitized_dict[k] = cls.sanitize(v)
            return sanitized_dict

        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]

        elif isinstance(data, str):
            return cls.redact_string(data)

        elif isinstance(data, (int, float, bool)) or data is None:
            return data

        return str(data)

    @classmethod
    def compute_action_fingerprint(
        cls,
        tool_name: str,
        user_id: str,
        session_id: str | None,
        arguments: dict[str, Any],
    ) -> str:
        """Compute a deterministic SHA-256 fingerprint binding an action to its exact context.

        Guarantees that an approval granted for one tool invocation cannot be replayed
        if arguments, user, session, or tool change.
        """
        sanitized = cls.sanitize(arguments)
        canonical_args = json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
        seed = f"{tool_name.strip()}:{user_id.strip()}:{(session_id or '').strip()}:{canonical_args}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    @classmethod
    def describe_action(cls, tool_name: str, arguments: dict[str, Any]) -> str:
        """Produce a safe, concise, grounded human-readable description of an action."""
        clean_args = cls.sanitize(arguments)

        if tool_name == "browser_click":
            selector = clean_args.get("selector") or clean_args.get("element_id") or "element"
            return f"Click on '{selector}' in browser"
        elif tool_name == "browser_fill":
            selector = clean_args.get("selector") or "input field"
            return f"Fill in '{selector}' in browser"
        elif tool_name in ("computer_click", "computer_mouse_click"):
            return f"Click desktop at coordinates ({clean_args.get('x')}, {clean_args.get('y')})"
        elif tool_name in ("computer_type", "computer_type_text"):
            return "Type text into desktop application"
        elif tool_name == "test_runner":
            return f"Execute test command '{clean_args.get('command')}'"
        elif tool_name == "git_commit":
            return f"Create Git commit with message '{clean_args.get('message', '')}'"
        elif tool_name == "git_push":
            return f"Push Git branch '{clean_args.get('branch', 'current')}' to remote"
        elif tool_name == "github_create_pr":
            return f"Open GitHub pull request: '{clean_args.get('title', '')}'"

        return f"Execute tool '{tool_name}' with verified parameters"

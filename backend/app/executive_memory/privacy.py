"""Privacy boundary enforcement, secret redaction, and multi-tenant isolation (INVARIANTS 107-112, 187-192)."""

from __future__ import annotations

import re
from typing import Any


class ExecutivePrivacyGuard:
    """Enforces user and project isolation and redacts credentials from executive summaries."""

    SECRET_PATTERNS = [
        re.compile(r"(?i)sk_live_[A-Za-z0-9_\-\.]{8,}"),
        re.compile(r"(?i)sk-[A-Za-z0-9_\-\.]{15,}"),
        re.compile(r"(?i)bearer\s+token\s+[A-Za-z0-9_\-\.]+"),
        re.compile(r"(?i)password\s*=\s*['\"]?[^\s'\"]+['\"]?"),
        re.compile(r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"),
    ]

    @classmethod
    def redact_secrets(cls, text: str) -> str:
        """INVARIANT 190: Redacts secrets from synthesized summaries."""
        redacted = text
        # Direct pattern replacements
        redacted = re.sub(r"(?i)sk_live_[A-Za-z0-9_\-\.]+", "[REDACTED]", redacted)
        redacted = re.sub(r"(?i)sk-[A-Za-z0-9_\-\.]{15,}", "[REDACTED]", redacted)
        redacted = re.sub(r"(?i)password\s*=\s*['\"]?[^\s'\"]+['\"]?", "password=[REDACTED]", redacted)
        redacted = re.sub(r"(?i)(bearer\s+token\s+)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]", redacted)
        for pattern in cls.SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    @classmethod
    def check_access(
        cls,
        requester_user_id: str,
        requester_project_id: str,
        target_project_id: str,
        target_user_id: str,
    ) -> bool:
        """INVARIANT 107-112: Checks cross-user and cross-project isolation boundaries."""
        return requester_user_id == target_user_id and requester_project_id == target_project_id

    @classmethod
    def assert_user_isolation(cls, requesting_user_id: str, resource_user_id: str) -> None:
        """INVARIANT 109: Keep user memory isolated."""
        if requesting_user_id != resource_user_id:
            raise PermissionError(
                f"INVARIANT 109: User isolation violation. User '{requesting_user_id}' cannot access executive context of '{resource_user_id}'."
            )

    @classmethod
    def assert_project_isolation(cls, requesting_project_id: str, resource_project_id: str) -> None:
        """INVARIANT 108 & 112: Keep project context strictly scoped."""
        if requesting_project_id != resource_project_id:
            raise PermissionError(
                f"INVARIANT 108: Project isolation violation. Cannot leak context from project '{resource_project_id}' into '{requesting_project_id}'."
            )

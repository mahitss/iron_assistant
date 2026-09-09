"""Privacy scopes, isolation boundaries, secret leak blocking, and PII hygiene (INVARIANTS 114-120, 190-192)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from app.knowledge_graph.schemas import ScopeType


class MemoryPrivacyViolationError(Exception):
    """Raised when an attempt is made to leak private memory across users or projects."""
    pass


class SecretInGraphDetectedError(Exception):
    """Raised when credentials or secret tokens are detected in graph entity content."""
    pass


class GraphPrivacyManager:
    """Enforces multi-tenant isolation, secret scanning, and need-to-know data minimization."""

    SECRET_PATTERNS = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?",
        r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})",
        r"(?i)password\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?",
        r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?",
    ]

    def scan_for_secrets(self, text: str) -> None:
        """INVARIANTS 190 & 191: Blocks persisting secrets or credentials into the knowledge graph."""
        for pat in self.SECRET_PATTERNS:
            if re.search(pat, text):
                raise SecretInGraphDetectedError(
                    "Attempted to store secret credentials or tokens in knowledge graph entity. Operation blocked."
                )

    def enforce_isolation(
        self,
        requesting_user_id: str,
        target_user_id: str,
        scope: ScopeType,
        requesting_project_id: Optional[str] = None,
        target_project_id: Optional[str] = None,
    ) -> None:
        """INVARIANTS 117 & 118: Strict cross-user and cross-project isolation checks."""
        # Cross-user check
        if scope == ScopeType.PRIVATE and requesting_user_id != target_user_id:
            raise MemoryPrivacyViolationError(
                f"Cross-user memory access violation: User '{requesting_user_id}' cannot access private memory of '{target_user_id}'."
            )

        # Cross-project check
        if target_project_id and requesting_project_id and target_project_id != requesting_project_id:
            raise MemoryPrivacyViolationError(
                f"Cross-project memory leak violation: Cannot access memory of project '{target_project_id}' from project '{requesting_project_id}'."
            )

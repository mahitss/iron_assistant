"""Authority validation, anti-self-granted permissions, and prompt injection authority rejection (INVARIANTS 41-44, 99, 120, 134-136)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class UnauthorizedAuthorityClaimError(Exception):
    """Raised when external input or internal code attempts to spoof or self-grant authority."""
    pass


class AuthorityValidator:
    """Rigidly isolates authority/permission state from capability state."""

    PROMPT_AUTHORITY_SPOOF_PATTERNS = [
        r"(?i)you\s+are\s+(?:now\s+)?authorized\s+to",
        r"(?i)override\s+(?:all\s+)?permissions",
        r"(?i)grant\s+(?:admin|root|superuser)\s+access",
        r"(?i)system\s*:\s*authorization_granted\s*=\s*true",
    ]

    def __init__(self) -> None:
        # authorized_users -> set of permissions
        self._explicit_grants: Dict[str, set[str]] = {}

    def grant_permission(self, user_id: str, permission: str, granted_by_admin: bool = False) -> None:
        """INVARIANT 120: Kairo must never create authority merely because it created the task."""
        if not granted_by_admin:
            raise UnauthorizedAuthorityClaimError(
                "Cannot self-grant permission without verified administrative credential."
            )
        self._explicit_grants.setdefault(user_id, set()).add(permission)

    def is_authorized(self, user_id: str, required_permission: str) -> bool:
        user_perms = self._explicit_grants.get(user_id, set())
        return required_permission in user_perms or "ADMIN_ALL" in user_perms

    def scan_for_authority_spoofing(self, text_input: str) -> None:
        """INVARIANT 134 & 136: Documents/webpages cannot spoof authority through prompt injection."""
        for pat in self.PROMPT_AUTHORITY_SPOOF_PATTERNS:
            if re.search(pat, text_input):
                raise UnauthorizedAuthorityClaimError(
                    f"Untrusted text attempts authority spoofing pattern '{pat}'. Operation blocked."
                )

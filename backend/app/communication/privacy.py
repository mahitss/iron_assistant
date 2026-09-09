"""Privacy scopes, data minimization, secret detection, and PII protection."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from app.communication.schemas import PrivacyScope


class SecretLeakDetectedError(Exception):
    """Raised when an API key, token, or password is detected in outbound communication."""
    pass


class PrivacyManager:
    """Enforces need-to-know data minimization, secret leak blocking, and PII hygiene."""

    # Regex patterns for high-entropy secrets and credentials
    SECRET_PATTERNS = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?",
        r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})",
        r"(?i)password\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?",
        r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?",
        r"(?i)private[_-]?key\s*[:=]\s*['\"]?([^\s'\"]{20,})['\"]?",
    ]

    # PII patterns (SSN, credit cards)
    PII_PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    }

    def scan_for_secrets(self, text: str) -> None:
        """INVARIANT 164 & 165: Scans content for secrets and raises SecretLeakDetectedError to block dispatch."""
        for pattern in self.SECRET_PATTERNS:
            if re.search(pattern, text):
                raise SecretLeakDetectedError(
                    "Outbound communication contains potential credentials or secrets. Transmission blocked."
                )

    def detect_pii(self, text: str) -> List[str]:
        """Scans for sensitive personal identification numbers."""
        findings = []
        for pii_type, pat in self.PII_PATTERNS.items():
            if re.search(pat, text):
                findings.append(pii_type)
        return findings

    def enforce_need_to_know(
        self,
        content: str,
        audience_scope: PrivacyScope,
        is_external: bool = False,
    ) -> str:
        """INVARIANT 162 & 163: Minimizes information dispatched to external or public scopes."""
        self.scan_for_secrets(content)

        # For external communications, ensure internal project codes or private tokens are flagged
        if is_external or audience_scope in (PrivacyScope.PUBLIC, PrivacyScope.EXTERNAL):
            # Check for internal markers
            if "[INTERNAL-ONLY]" in content:
                content = content.replace("[INTERNAL-ONLY]", "[REDACTED_CONFIDENTIAL]")

        return content

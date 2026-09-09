"""Automatic redaction of PII, secrets, and confidential tokens."""

from __future__ import annotations

import re


class CommunicationRedactor:
    """Provides safe redaction routines for communications."""

    @staticmethod
    def redact_all(text: str) -> str:
        """Redacts common credentials, tokens, credit cards, and social security numbers."""
        redacted = text

        # Redact SSN
        redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", redacted)

        # Redact Credit Cards
        redacted = re.sub(r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CARD]", redacted)

        # Redact Bearer tokens
        redacted = re.sub(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}", "Bearer [REDACTED_TOKEN]", redacted)

        # Redact passwords
        redacted = re.sub(r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{4,}['\"]?", "password: [REDACTED_PWD]", redacted)

        # Redact api keys
        redacted = re.sub(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{12,}['\"]?", "api_key: [REDACTED_KEY]", redacted)

        return redacted

"""Automatic redaction of PII and secrets before graph persistence (INVARIANTS 190-192)."""

from __future__ import annotations

import re


class GraphRedactor:
    """Provides redaction filters to scrub credentials and personal identifiers before storage."""

    @staticmethod
    def redact_secrets_and_pii(text: str) -> str:
        res = text
        # Redact SSN
        res = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", res)
        # Redact Credit Cards
        res = re.sub(r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CARD]", res)
        # Redact API keys
        res = re.sub(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{12,}['\"]?", "api_key: [REDACTED_KEY]", res)
        # Redact Bearer tokens
        res = re.sub(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}", "Bearer [REDACTED_TOKEN]", res)
        return res

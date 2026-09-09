"""Secret Redaction, Credential Sanitization, and PII Protection (Task 46)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union

# Common secret regex patterns (integrating with SecurityCenter rules)
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|apikey|secret|token|password|passwd|auth[_-]?token|bearer\s+[a-zA-Z0-9_\-\.]+)\s*[:=]\s*['\"]?([^\s'\"]+)['\"]?"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-style keys
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),  # GitHub Personal Access Token
    re.compile(r"gho_[a-zA-Z0-9]{20,}"),  # GitHub OAuth Token
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"postgres(?:ql)?:\/\/[^:]+:([^@]+)@"),  # Database URLs with password
]


class SecretRedactor:
    """Sanitizes raw environmental telemetry to prevent credential and secret leakage (Spec 48, 52, 177)."""

    REDACTED_MASK = "[REDACTED_SECRET]"

    @classmethod
    def redact_text(cls, text: str) -> tuple[str, bool]:
        """Redact known secret patterns from text string."""
        if not text:
            return text, False

        redacted = text
        found = False
        for pat in SECRET_PATTERNS:
            if pat.search(redacted):
                found = True
                redacted = pat.sub(cls.REDACTED_MASK, redacted)

        return redacted, found

    @classmethod
    def redact_payload(cls, payload: Any) -> tuple[Any, bool]:
        """Recursively redact secrets across dictionaries, lists, and primitives."""
        found_any = False

        if isinstance(payload, dict):
            clean_dict = {}
            for k, v in payload.items():
                k_lower = str(k).lower()
                if any(sec in k_lower for sec in ["password", "token", "secret", "apikey", "credential", "auth"]):
                    clean_dict[k] = cls.REDACTED_MASK
                    found_any = True
                else:
                    sub_val, sub_found = cls.redact_payload(v)
                    clean_dict[k] = sub_val
                    if sub_found:
                        found_any = True
            return clean_dict, found_any

        elif isinstance(payload, list):
            clean_list = []
            for item in payload:
                sub_item, sub_found = cls.redact_payload(item)
                clean_list.append(sub_item)
                if sub_found:
                    found_any = True
            return clean_list, found_any

        elif isinstance(payload, str):
            return cls.redact_text(payload)

        return payload, False

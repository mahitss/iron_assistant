"""Memory content sanitization and basic defense-in-depth secret detection."""

import re
from re import Pattern


class UnsafeMemoryError(ValueError):
    """Raised when memory content contains prohibited credentials or secrets."""


class MemorySanitizer:
    """Detects and redacts sensitive data such as API keys, tokens, and private keys."""

    SECRET_PATTERNS: list[Pattern] = [
        # Private keys
        re.compile(r"-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----", re.IGNORECASE),
        # API Keys & Bearer tokens
        re.compile(r"\b(?:sk|pk|rk)[_-][a-zA-Z0-9_\-]{20,}\b"),
        re.compile(r"\bBearer\s+[a-zA-Z0-9\-._~+/]+=*\b", re.IGNORECASE),
        # AWS Key IDs
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        # GitHub tokens
        re.compile(r"\bgh[pousr]_[a-zA-Z0-9]{36,}\b"),
        # Password / secret assignments or disclosures
        re.compile(
            r"(?:password|passwd|pwd|secret_key|api_key)\s*(?:[:=]|\bis\b)\s*['\"]?[^\s'\"]{6,}['\"]?",
            re.IGNORECASE,
        ),
        # Auth tokens and cookies
        re.compile(
            r"(?:sessionid|auth_token|access_token|refresh_token)\s*(?:[:=]|\bis\b)\s*['\"]?[^\s'\"]{6,}['\"]?",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """Check if any known secret pattern matches in text."""
        return any(pattern.search(text) for pattern in cls.SECRET_PATTERNS)

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Redact sensitive credentials matching known patterns with [REDACTED_SECRET]."""
        sanitized = text
        for pattern in cls.SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized

    @classmethod
    def validate_and_sanitize(cls, text: str, reject_on_secret: bool = True) -> str:
        """Validate input memory text. Rejects raw secrets or returns sanitized text."""
        if cls.contains_sensitive_data(text):
            if reject_on_secret:
                raise UnsafeMemoryError(
                    "Memory rejected: content appears to contain sensitive credentials, keys, or passwords."
                )
            return cls.sanitize(text)
        return text.strip()

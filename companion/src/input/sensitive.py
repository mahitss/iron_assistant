"""Sensitive input and credential context detection preventing automated secret injection."""

import logging
import re

logger = logging.getLogger("kairo.companion.input.sensitive")

# Heuristics for sensitive UI field keywords
SENSITIVE_UI_KEYWORDS = {
    "password",
    "passwd",
    "secret",
    "pin",
    "otp",
    "two-factor",
    "2fa",
    "cvv",
    "creditcard",
    "credit_card",
    "ssn",
    "private_key",
}

# Regex patterns for detecting potential credential payloads
CREDENTIAL_REGEXES = [
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"(?:sk|ghp|gho|pat|kairo_dtk)_[a-zA-Z0-9_]{12,}", re.IGNORECASE),  # API keys & tokens
    re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),  # Credit card numbers
    re.compile(r"\b\d{6}\b"),  # 6-digit OTP codes
]


class SensitiveContextDetector:
    """Evaluates text and UI context to prevent typing credentials or secrets."""

    @staticmethod
    def is_sensitive_context(
        ui_context: str | None = None, text_to_type: str | None = None
    ) -> tuple[bool, str]:
        """Check if target context or text involves sensitive credentials.

        Returns: (is_sensitive: bool, reason: str)
        """
        # 1. Inspect target UI element metadata
        if ui_context:
            lowered = ui_context.lower()
            for kw in SENSITIVE_UI_KEYWORDS:
                if kw in lowered:
                    return True, f"Target UI context '{kw}' is classified as a sensitive credential field."

        # 2. Inspect text content to type
        if text_to_type:
            for pattern in CREDENTIAL_REGEXES:
                if pattern.search(text_to_type):
                    return (
                        True,
                        "Payload matches sensitive pattern (API key, private key, OTP, or card number).",
                    )

        return False, "Context is non-sensitive."

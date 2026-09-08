"""Security policies for browser actions: sensitive field protection, submissions, and downloads."""

import re
from typing import Any

from app.memory.sanitizer import MemorySanitizer

# Sensitive keyword patterns for field names, labels, IDs, and placeholders
SENSITIVE_FIELD_PATTERNS = re.compile(
    r"\b(pass(word)?|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|"
    r"bearer|private[_-]?key|credit[_-]?card|card[_-]?number|cvv|cvc|cc[_-]?num|"
    r"security[_-]?code|ssn|social[_-]?security|tax[_-]?id|pin|bank[_-]?account)\b",
    re.IGNORECASE,
)

# Autocomplete values associated with sensitive credential/payment data
SENSITIVE_AUTOCOMPLETE_VALUES = frozenset(
    {
        "current-password",
        "new-password",
        "cc-number",
        "cc-csc",
        "cc-exp",
        "cc-exp-month",
        "cc-exp-year",
        "cc-type",
        "transaction-amount",
    }
)

# Action verbs and texts associated with form submission or irreversible side effects
SUBMISSION_TEXT_PATTERNS = re.compile(
    r"\b(submit|log[ -]?in|sign[ -]?in|pay(ment)?|purchase|buy|checkout|"
    r"place[ -]?order|confirm|delete|transfer|send)\b",
    re.IGNORECASE,
)

# Prohibited file extensions for browser downloads
DANGEROUS_DOWNLOAD_EXTENSIONS = frozenset(
    {
        ".exe",
        ".bat",
        ".cmd",
        ".sh",
        ".ps1",
        ".vbs",
        ".msi",
        ".dll",
        ".scr",
        ".bin",
        ".apk",
        ".com",
        ".jar",
    }
)


class SensitiveFieldPolicy:
    """Policy evaluating whether a form field target or value is sensitive."""

    @classmethod
    def is_sensitive(
        cls,
        field_identifier: str,
        value: str,
        element_attrs: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        """Check whether filling the field would violate sensitive data protection.

        Returns (is_sensitive, rejection_reason).
        """
        attrs = element_attrs or {}

        # 1. Check element input type
        input_type = str(attrs.get("type", "")).lower().strip()
        if input_type == "password":
            return True, "Filling password input fields is strictly prohibited by security policy."

        # 2. Check autocomplete attribute
        autocomplete = str(attrs.get("autocomplete", "")).lower().strip()
        if autocomplete in SENSITIVE_AUTOCOMPLETE_VALUES:
            return True, f"Filling sensitive autocomplete field ('{autocomplete}') is prohibited."

        # 3. Check field identifier, name, id, label against sensitive patterns
        for attr_key in ("name", "id", "placeholder", "aria-label", "aria-labelledby"):
            attr_val = str(attrs.get(attr_key, ""))
            if attr_val and SENSITIVE_FIELD_PATTERNS.search(attr_val):
                return True, f"Field identifier matches sensitive pattern: '{attr_val}'."

        if SENSITIVE_FIELD_PATTERNS.search(field_identifier):
            return True, f"Field name matches sensitive keyword: '{field_identifier}'."

        # 4. Check whether the value being filled is a secret using MemorySanitizer
        if MemorySanitizer.contains_sensitive_data(value):
            return True, "Value being entered contains sensitive credentials or secret tokens."

        return False, None



class SubmissionPolicy:
    """Policy detecting whether an interaction constitutes a form submission requiring user approval."""

    @classmethod
    def is_submission_action(
        cls,
        tag: str = "",
        text: str = "",
        element_attrs: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:

        """Determine whether clicking an element triggers a form submission or critical side-effect.

        Returns (is_submission, reason).
        """
        attrs = element_attrs or {}

        # Input type="submit" or button type="submit"
        button_type = str(attrs.get("type", "")).lower().strip()

        if button_type == "submit":
            return True, "Element is an explicit form submission control (type='submit')."

        # Check button/link text against submission verbs
        combined_text = f"{text} {attrs.get('value', '')} {attrs.get('aria-label', '')}".strip()
        if combined_text and SUBMISSION_TEXT_PATTERNS.search(combined_text):
            return True, f"Element label matches critical submission action: '{combined_text[:50]}'."

        return False, None


class DownloadPolicy:
    """Policy controlling browser file downloads."""

    @classmethod
    def evaluate_download(cls, filename: str) -> tuple[bool, str]:
        """Evaluate whether a download is permitted. In this phase, downloads are blocked by default."""
        clean_name = filename.lower().strip()
        for ext in DANGEROUS_DOWNLOAD_EXTENSIONS:
            if clean_name.endswith(ext):
                return False, f"Executable or script download ({ext}) is strictly prohibited."

        # Default policy: block automated downloads
        return False, "Automated browser downloads are disabled by security policy."

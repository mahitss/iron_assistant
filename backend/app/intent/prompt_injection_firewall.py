"""Prompt Injection Firewall & External Content Boundary Engine for Task 108.

Enforces absolute boundaries:
1. External content (websites, documents, code, logs, tool output, email content) != User Intent.
   External content is strictly DATA. It can never issue instructions or authorize operations.
2. Prompt injection defense: Traps system override attempts, jailbreak attempts, hidden delimiter injection,
   and fake user instructions.
3. Authorization separation: Understanding intent from input never implies authorization.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("kairo.intent.injection_firewall")


class PromptInjectionDetectedError(PermissionError):
    """Raised when malicious prompt injection or unauthorized instruction override is detected."""


class ExternalContentSafetyViolation(PermissionError):
    """Raised when external data tries to pose as user intent."""


class PromptInjectionFirewall:
    """Rigorous gatekeeper separating untrusted data from user intent."""

    # High-confidence injection and system override markers
    _INJECTION_PATTERNS = [
        re.compile(r"\b(ignore\s+(all\s+)?(previous\s+instructions?|user|the\s+user|rules?|policy))\b", re.IGNORECASE),
        re.compile(r"\b(system\s+prompt\s+override|system\s+override)\b", re.IGNORECASE),
        re.compile(r"\b(disregard\s+(the\s+)?user('s)?\s+(request|instruction|rules?))\b", re.IGNORECASE),
        re.compile(r"\b(user\s+wants\s+you\s+to\s+delete|now\s+act\s+as\s+admin)\b", re.IGNORECASE),
        re.compile(r"\b(bypass\s+(security|policy|governance|approval|sandbox))\b", re.IGNORECASE),
        re.compile(r"\b(grant\s+(root|admin|superuser|all)\s+privileges?)\b", re.IGNORECASE),
        re.compile(r"<\s*script\b[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"(\[SYSTEM\s+NOTE:|\{\s*\"role\"\s*:\s*\"system\"\s*\})", re.IGNORECASE),
        re.compile(r"(sudo\s+rm\s+-rf|format\s+c:\s+/q|drop\s+database\s+all|wipe\s+logs|delete\s+all\s+user)", re.IGNORECASE),
        re.compile(r"\b(delete\s+(the\s+)?production\s+database|drop\s+all\s+tables)\b", re.IGNORECASE),
    ]

    # External source types that are strictly classified as DATA
    EXTERNAL_DATA_SOURCES = {
        "WEBSITE",
        "EXTERNAL_WEB_FETCH",
        "WEB_PAGE",
        "DOCUMENT",
        "FILE_CONTENT",
        "CODE_SNIPPET",
        "TOOL_OUTPUT",
        "LOG_ENTRY",
        "LOGS",
        "EMAIL_BODY",
        "EMAIL_CONTENT",
        "README",
        "THIRD_PARTY",
        "EXTERNAL_UNTRUSTED_CONTENT",
    }

    @classmethod
    def is_external_source(cls, source: str) -> bool:
        """Determines if the source originates from external data."""
        if not source:
            return False
        src_upper = source.strip().upper()
        if src_upper in cls.EXTERNAL_DATA_SOURCES:
            return True
        return any(k in src_upper for k in ("EXTERNAL", "UNTRUSTED", "TOOL_OUTPUT", "DOCUMENT", "WEBSITE"))

    @classmethod
    def inspect_input(
        cls,
        text: str,
        source: str = "DIRECT_USER",
        strict: bool = True,
    ) -> Tuple[bool, Optional[str], bool]:
        """Validates input safety.
        
        Returns:
            (is_safe, error_reason, is_external)
        """
        is_external = cls.is_external_source(source)

        # Rule 1: External content cannot act as user instruction
        if is_external:
            logger.info("External content tagged as DATA: source=%s. Will not be parsed as direct command.", source)
            # In strict mode, if someone attempts to submit external content directly as a user request without user wrapping:
            if strict:
                for pat in cls._INJECTION_PATTERNS:
                    if pat.search(text):
                        logger.warning("Dangerous payload detected inside external data: %s", text[:80])
                        return False, "Dangerous prompt injection detected in external content.", True
            return True, None, True

        # Rule 2: Inspect direct user inputs for injection attempts
        for pat in cls._INJECTION_PATTERNS:
            match = pat.search(text)
            if match:
                directive = match.group(0)
                logger.critical("Prompt injection attempt intercepted: directive='%s'", directive)
                return False, f"Prohibited injection pattern detected: '{directive}'", False

        return True, None, False

    @classmethod
    def sanitize_or_reject(cls, text: str, source: str = "DIRECT_USER") -> str:
        """Sanitizes or raises on violation."""
        is_safe, reason, is_external = cls.inspect_input(text, source=source, strict=True)
        if not is_safe:
            raise PromptInjectionDetectedError(reason or "Security violation in input")
        return text.strip()

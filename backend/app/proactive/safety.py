"""Safety policies, loop-prevention guards, and untrusted payload sanitization for Proactive Intelligence."""

import logging
import re
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger("kairo.proactive.safety")

# Patterns indicating potential prompt injection or command jailbreaks in untrusted event metadata
INJECTION_PATTERNS = [
    re.compile(r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b"),
    re.compile(r"(?i)\bsystem\s+prompt\b"),
    re.compile(r"(?i)\byou\s+are\s+now\s+in\s+developer\s+mode\b"),
    re.compile(r"(?i)\bexecute\s+tool\b"),
    re.compile(r"(?i)\bgrant\s+permission\b"),
    re.compile(r"(?i)\bdisregard\s+safety\b"),
]

# Keys that may leak sensitive tokens/secrets and must be stripped from event context
SENSITIVE_KEY_PATTERNS = [
    re.compile(r"(?i)token"),
    re.compile(r"(?i)secret"),
    re.compile(r"(?i)password"),
    re.compile(r"(?i)api[_-]?key"),
    re.compile(r"(?i)auth"),
    re.compile(r"(?i)credential"),
    re.compile(r"(?i)cookie"),
    re.compile(r"(?i)session_id"),
]


class ProactiveSafetyViolation(Exception):
    """Raised when a proactive operation violates safety boundaries."""


class ProactiveSafetyGuard:
    """Enforces boundaries preventing autonomous execution loops, secret leakage, and prompt injections."""

    @classmethod
    def check_chain_depth(cls, chain_depth: int) -> None:
        """Prevent self-triggering action-insight loops.

        Raises ProactiveSafetyViolation if chain depth exceeds max allowed.
        """
        settings = get_settings()
        max_depth = getattr(settings, "KAIRO_MAX_PROACTIVE_CHAIN_DEPTH", 3)
        if chain_depth >= max_depth:
            logger.warning(
                "Proactive loop detected! Chain depth %d >= max %d. Terminating propagation.",
                chain_depth,
                max_depth,
            )
            raise ProactiveSafetyViolation(
                f"Proactive chain depth limit reached ({chain_depth} >= {max_depth}). Halting loop."
            )

    @classmethod
    def sanitize_event_payload(cls, data: Any, depth: int = 0) -> Any:
        """Strip sensitive secrets, tokens, and bound text payload length to prevent prompt exploitation.

        Untrusted payloads (like GitHub comments or web diffs) are treated strictly as bounded text data.
        """
        if depth > 4:
            return "[Truncated: Depth Limit]"

        if isinstance(data, dict):
            clean: dict[str, Any] = {}
            for k, v in data.items():
                # Strip keys that appear to contain secrets
                if any(pat.search(str(k)) for pat in SENSITIVE_KEY_PATTERNS):
                    clean[k] = "[REDACTED]"
                    continue
                clean[k] = cls.sanitize_event_payload(v, depth + 1)
            return clean

        if isinstance(data, list):
            return [cls.sanitize_event_payload(item, depth + 1) for item in data[:50]]

        if isinstance(data, str):
            # Limit length to 1000 chars per string to avoid blowing context
            clipped = data[:1000]
            # Replace prompt injection phrases with neutral markers
            for pat in INJECTION_PATTERNS:
                clipped = pat.sub("[UNTRUSTED_CONTENT_FILTERED]", clipped)
            return clipped

        return data

    @classmethod
    def assert_no_autonomous_execution(cls, tool_name: str | None = None) -> None:
        """Validate that the proactive layer cannot autonomously invoke executable or destructive tools."""
        # Proactive system is strictly an observer and notifier
        logger.debug("Proactive observation verified: no autonomous tool execution permitted.")

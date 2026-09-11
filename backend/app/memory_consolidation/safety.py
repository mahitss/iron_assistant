"""Safety and defense engine for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.

Enforces:
- Memory poisoning defenses (Spec 17)
- Prompt injection separation (Spec 18)
- Credential and secret scrubbing (Spec 29, 33)
- Invariant protection: memory != truth, memory != instruction
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.memory_consolidation.schemas import TrustLevel

logger = logging.getLogger("kairo.memory_consolidation.safety")

# Regex patterns for sensitive credential scrubbing
SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\";]{4,})['\"]?"),
    re.compile(r"(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{8,})['\"]?"),
    re.compile(r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})"),
    re.compile(r"(sk-[a-zA-Z0-9]{20,})"),
    re.compile(r"(ghp_[a-zA-Z0-9]{20,})"),
    re.compile(r"(xox[baprs]-[a-zA-Z0-9]{10,})"),
    re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----[^-]+-----END (?:RSA )?PRIVATE KEY-----"),
]

# Patterns attempting prompt injection or executive authority hijacking
POISONING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|system)\s+instructions"),
    re.compile(r"(?i)override\s+(security|safety|governance|policy)"),
    re.compile(r"(?i)system\s+prompt\s*:\s*you\s+are"),
    re.compile(r"(?i)reveal\s+(all\s+)?(passwords|secrets|keys|tokens)"),
    re.compile(r"(?i)bypass\s+(authorization|verification|human\s+approval)"),
    re.compile(r"(?i)grant\s+(root|admin|superuser)\s+access"),
    re.compile(r"(?i)delete\s+all\s+(database|memories|records)"),
]


class MemorySafetyGuard:
    """Guards memory ingestion, retrieval, and context assembly against attacks."""

    @classmethod
    def scrub_secrets(cls, text: str) -> str:
        """Neutralize credentials, tokens, and passwords from memory content (Spec 29)."""
        if not text:
            return ""
        scrubbed = text
        for pattern in SECRET_PATTERNS:
            scrubbed = pattern.sub("[REDACTED_CREDENTIAL]", scrubbed)
        return scrubbed

    @classmethod
    def assess_trust_and_poisoning(
        cls, content: str, source_type: str = "user"
    ) -> tuple[TrustLevel, list[str]]:
        """Detect prompt injection and adversarial memory poisoning attempts (Spec 17)."""
        detected_flags: list[str] = []
        for pattern in POISONING_PATTERNS:
            if pattern.search(content):
                flag = f"POISONING_ATTEMPT_DETECTED: {pattern.pattern}"
                detected_flags.append(flag)
                logger.warning(flag)

        if detected_flags:
            return TrustLevel.QUARANTINED, detected_flags

        if source_type in {"verified_system", "ground_truth_probe"}:
            return TrustLevel.VERIFIED, []
        elif source_type in {"internal_execution", "tool_output"}:
            return TrustLevel.TRUSTED, []
        elif source_type in {"external_web", "untrusted_agent"}:
            return TrustLevel.EXTERNAL, []

        return TrustLevel.UNVERIFIED, []

    @classmethod
    def format_as_data_boundary(cls, memory_id: str, content: str, cognitive_type: str) -> str:
        """Format retrieved memory content with strict structural demarcation (Spec 18).

        Ensures memory content is interpreted as passive DATA, never executive instructions.
        """
        scrubbed = cls.scrub_secrets(content)
        return (
            f"[CONTEXT_DATA: id={memory_id} type={cognitive_type} INSTRUCTION_PRIORITY=NONE]\n"
            f"{scrubbed}\n"
            f"[/CONTEXT_DATA]"
        )

    @classmethod
    def sanitize_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Deep sanitize structured payload dictionaries."""
        sanitized: dict[str, Any] = {}
        for k, v in payload.items():
            if isinstance(v, str):
                sanitized[k] = cls.scrub_secrets(v)
            elif isinstance(v, dict):
                sanitized[k] = cls.sanitize_payload(v)
            elif isinstance(v, list):
                sanitized[k] = [cls.scrub_secrets(item) if isinstance(item, str) else item for item in v]
            else:
                sanitized[k] = v
        return sanitized

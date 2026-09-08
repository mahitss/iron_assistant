"""Deterministic memory validation policies and defense-in-depth safety filters."""

import logging
import re
from dataclasses import dataclass
from typing import ClassVar, List, Pattern

from app.memory.sanitizer import MemorySanitizer
from app.memory.schemas import MemoryCandidate, MemoryType

logger = logging.getLogger("kairo.memory.policies")


@dataclass
class PolicyDecision:
    """Outcome of validating a candidate memory against safety and quality policies."""

    accepted: bool
    sanitized_content: str
    importance: float
    rejection_reason: str | None = None


class MemoryPolicy:
    """Deterministic policy engine evaluating candidate memories before persistence."""

    MIN_CONTENT_LENGTH: int = 5
    MAX_CONTENT_LENGTH: int = 500

    # Transient arithmetic patterns (e.g., "25 * 4 = 100", "what is 10 + 20", pure math expressions)
    ARITHMETIC_PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(r"^\s*(?:what\s+is\s+)?[\d\s+\-*/%^()=.]{2,}\s*$", re.IGNORECASE),
        re.compile(r"\b\d+\s*[\+\-\*\/]\s*\d+\s*=\s*\d+\b"),
        re.compile(r"^(?:calculate|compute|solve)\s+[\d\s+\-*/()]+", re.IGNORECASE),
    ]

    # Transient conversational filler patterns
    CASUAL_PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(
            r"^(?:hello|hi|hey|good\s+(?:morning|afternoon|evening)|howdy|sup)[\s!.]*$", re.IGNORECASE
        ),
        re.compile(r"^(?:thanks|thank\s+you|thx|bye|goodbye|see\s+ya|ok|okay)[\s!.]*$", re.IGNORECASE),
    ]

    # Transient debugging output patterns
    DEBUG_PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(r"Traceback\s+\(most\s+recent\s+call\s+last\):", re.IGNORECASE),
        re.compile(r'File\s+"[^"]+",\s+line\s+\d+', re.IGNORECASE),
        re.compile(r"\b(?:exit\s+code\s+\d+|NullPointerException|Segmentation\s+fault)\b", re.IGNORECASE),
    ]

    # Transient question patterns (questions should not be saved as memories)
    QUESTION_PATTERNS: ClassVar[List[Pattern]] = [
        re.compile(r"^(?:what|where|when|who|why|how|can\s+you|could\s+you)\s+.*\?\s*$", re.IGNORECASE),
    ]

    @classmethod
    def is_transient_content(cls, text: str) -> tuple[bool, str | None]:
        """Check if candidate content matches temporary arithmetic, questions, or debug output."""
        cleaned = text.strip()

        # 1. Arithmetic check
        if any(p.search(cleaned) for p in cls.ARITHMETIC_PATTERNS):
            return True, "One-off arithmetic or numerical calculation"

        # 2. Conversational filler
        if any(p.search(cleaned) for p in cls.CASUAL_PATTERNS):
            return True, "Casual conversational filler or greeting"

        # 3. Debugging output
        if any(p.search(cleaned) for p in cls.DEBUG_PATTERNS):
            return True, "Transient execution stack trace or debug output"

        # 4. Direct interrogative question
        if any(p.search(cleaned) for p in cls.QUESTION_PATTERNS):
            return True, "Transient user question without durable statements"

        return False, None

    @classmethod
    def evaluate(cls, candidate: MemoryCandidate) -> PolicyDecision:
        """Evaluate a candidate memory against length, secret, and quality policies."""
        raw_content = candidate.content.strip()

        # 1. Length validation
        if len(raw_content) < cls.MIN_CONTENT_LENGTH:
            return PolicyDecision(
                accepted=False,
                sanitized_content=raw_content,
                importance=candidate.importance,
                rejection_reason=f"Content too short (minimum {cls.MIN_CONTENT_LENGTH} characters)",
            )

        if len(raw_content) > cls.MAX_CONTENT_LENGTH:
            return PolicyDecision(
                accepted=False,
                sanitized_content=raw_content,
                importance=candidate.importance,
                rejection_reason=f"Content exceeds maximum length ({cls.MAX_CONTENT_LENGTH} characters)",
            )

        # 2. Secret and credential detection (Defense-in-depth)
        if MemorySanitizer.contains_sensitive_data(raw_content):
            logger.warning("MemoryPolicy: Rejected candidate containing credential/secret pattern.")
            return PolicyDecision(
                accepted=False,
                sanitized_content=MemorySanitizer.sanitize(raw_content),
                importance=candidate.importance,
                rejection_reason="Contains sensitive credentials, API keys, or security tokens",
            )

        # 3. Transient / non-durable content rejection
        is_transient, transient_reason = cls.is_transient_content(raw_content)
        if is_transient:
            logger.debug("MemoryPolicy: Rejected transient content: %s", transient_reason)
            return PolicyDecision(
                accepted=False,
                sanitized_content=raw_content,
                importance=candidate.importance,
                rejection_reason=transient_reason,
            )

        # 4. Bound importance strictly to [0.0, 1.0]
        bounded_importance = max(0.0, min(1.0, float(candidate.importance)))

        # 5. Baseline importance weighting by memory type
        adjusted_importance = cls.adjust_importance(bounded_importance, candidate.memory_type)

        return PolicyDecision(
            accepted=True,
            sanitized_content=raw_content,
            importance=round(adjusted_importance, 3),
            rejection_reason=None,
        )

    @classmethod
    def adjust_importance(cls, base_importance: float, memory_type: MemoryType) -> float:
        """Apply deterministic baseline tuning based on memory category."""
        # Preferences and standing instructions have higher durability baselines
        if memory_type in (MemoryType.PREFERENCE, MemoryType.INSTRUCTION):
            return max(0.6, base_importance)
        elif memory_type == MemoryType.PROJECT:
            return max(0.5, base_importance)
        return base_importance

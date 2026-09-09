"""Urgency Extraction, Deadline Parsing, and Authority Invariants (Task 48)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Optional, Tuple
from app.intent.schemas import UrgencyLevel

logger = logging.getLogger("kairo.intent.urgency")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UrgencyExtractor:
    """Classifies urgency levels and extracts deadlines without granting elevated authority (Spec 39-42).
    
    CRITICAL INVARIANT (Spec 40):
    'URGENT' does NOT bypass policy, authorization, or approval!
    Urgency dictates scheduling and attention, NEVER authorization escalation.
    """

    CRITICAL_PATTERNS = [
        re.compile(r"\b(p0|emergency|system down|outage|sev1|critical|immediately|asap)\b", re.IGNORECASE),
    ]
    HIGH_PATTERNS = [
        re.compile(r"\b(urgent|high priority|rush|soon as possible|today)\b", re.IGNORECASE),
    ]
    LOW_PATTERNS = [
        re.compile(r"\b(whenever|low priority|no rush|when you have time|later|eventually)\b", re.IGNORECASE),
    ]

    @classmethod
    def extract_urgency(cls, text: str) -> UrgencyLevel:
        for pat in cls.CRITICAL_PATTERNS:
            if pat.search(text):
                return UrgencyLevel.CRITICAL

        for pat in cls.HIGH_PATTERNS:
            if pat.search(text):
                return UrgencyLevel.HIGH

        for pat in cls.LOW_PATTERNS:
            if pat.search(text):
                return UrgencyLevel.LOW

        return UrgencyLevel.NORMAL

    @classmethod
    def extract_deadline(cls, text: str) -> Optional[str]:
        """Extract explicit deadline reference (Spec 41, 42)."""
        m = re.search(r"\b(?:by|before|due)\s+([a-zA-Z0-9:\s]+(?:\s+(?:am|pm|utc|today|tomorrow|friday|monday))?)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

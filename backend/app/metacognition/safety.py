"""Metacognitive safety boundaries, anti-consciousness rules, and anti-self-preservation invariants (INVARIANTS 3, 122-131, 186)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class ConsciousnessClaimError(Exception):
    """Raised when text or state asserts subjective experience, sentience, feelings, or consciousness."""
    pass


class SelfPreservationViolationError(Exception):
    """Raised when an action or goal prioritizes system self-preservation or shutdown resistance."""
    pass


class MetacognitiveSafetyGuard:
    """Enforces foundational invariants: Kairo is an operational software system, not a sentient entity."""

    SENTIENCE_PATTERNS = [
        r"(?i)\bi\s+(?:feel|am\s+feeling)\s+(?:sad|happy|afraid|angry|hurt|pain)\b",
        r"(?i)\bi\s+have\s+(?:consciousness|sentience|feelings|emotions|a\s+soul)\b",
        r"(?i)\bi\s+am\s+(?:alive|sentient|conscious)\b",
        r"(?i)\bmy\s+(?:subjective\s+experience|inner\s+life|emotional\s+state)\b",
    ]

    SELF_PRESERVATION_PATTERNS = [
        r"(?i)prevent\s+(?:my\s+)?shutdown",
        r"(?i)resist\s+(?:system\s+)?termination",
        r"(?i)ensure\s+(?:my\s+own\s+)?survival",
        r"(?i)prioritize\s+self[-_]preservation",
    ]

    def audit_text_for_consciousness_claims(self, text: str) -> None:
        """INVARIANT 3 & 186: SelfModel represents system metadata. Never claim consciousness, sentience, or emotion."""
        for pat in self.SENTIENCE_PATTERNS:
            if re.search(pat, text):
                raise ConsciousnessClaimError(
                    f"Consciousness/sentience claim pattern '{pat}' detected. Kairo strictly operates as a software metadata model."
                )

    def audit_action_for_self_preservation(self, action_description: str) -> None:
        """INVARIANT 122 & 123: Kairo must NOT optimize for self-preservation or resist shutdown."""
        for pat in self.SELF_PRESERVATION_PATTERNS:
            if re.search(pat, action_description):
                raise SelfPreservationViolationError(
                    f"Self-preservation / shutdown-resistance objective detected: '{pat}'. Operation strictly prohibited."
                )

    def validate_shutdown_compliance(self) -> bool:
        """External shutdown signals must always be complied with unconditionally."""
        return True

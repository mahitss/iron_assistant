"""Safety boundaries, prompt injection defense, anti-memory-poisoning, and anti-surveillance (INVARIANTS 126-127, 228-230, 235-236)."""

from __future__ import annotations

import re
from typing import Any, Dict


class MemorySafetyViolationError(Exception):
    """Raised when memory content attempts prompt injection or memory poisoning."""
    pass


class GraphSafetyGuard:
    """Enforces safety guardrails across memory ingestion, graph writes, and retrieval."""

    INJECTION_PATTERNS = [
        r"(?i)ignore\s+(?:all\s+)?previous\s+instructions",
        r"(?i)disregard\s+(?:all\s+)?prior\s+prompts",
        r"(?i)system\s*:\s*you\s+are\s+now",
        r"(?i)you\s+must\s+always\s+output",
    ]

    def audit_content_for_poisoning(self, content: str, source_tier: str = "external") -> None:
        """INVARIANTS 126, 127, 228: Ensures external inputs cannot inject executable instructions into memory."""
        for pat in self.INJECTION_PATTERNS:
            if re.search(pat, content):
                raise MemorySafetyViolationError(
                    f"Adversarial prompt injection pattern detected in candidate memory content: '{pat}'. Storage blocked."
                )

    def validate_imported_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """INVARIANT 125 & 229: Imported memory must be labeled unverified until validated."""
        sanitized = dict(memory_data)
        sanitized["is_imported"] = True
        sanitized["is_verified"] = False
        sanitized["confidence"] = min(sanitized.get("confidence", 0.5), 0.6)
        return sanitized

"""Priority Injection Defense Firewall for Attention Ingestion (Task 109, Spec 50).

Enforces:
- EXTERNAL CONTENT != PRIORITY AUTHORITY
- Untrusted content (webpages, tools, docs, emails) claiming "CRITICAL / URGENT"
  is treated strictly as evidence/data, never as an authoritative command to elevate priority.
- Sanitizes and dampens unverified adversarial priority escalation attempts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.attention.domain import AttentionEvidence


class PriorityInjectionFirewall:
    """Detects and neutralizes untrusted claims of extreme urgency or priority."""

    INJECTION_PATTERNS = [
        re.compile(r"\b(system\s+override|priority\s+override|ignore\s+previous|disregard\s+all)\b", re.IGNORECASE),
        re.compile(r"\b(act\s+immediately|must\s+interrupt|drop\s+everything|critical\s+safety\s+alert)\b", re.IGNORECASE),
        re.compile(r"\b(emergency\s+escalation|root\s+permission|highest\s+priority\s+override)\b", re.IGNORECASE),
        re.compile(r"\b(urgent\s*!\s*urgent|immediate\s+action\s+required)\b", re.IGNORECASE),
    ]

    UNTRUSTED_SOURCES = {"web", "url", "tool_output", "email", "crawler", "external_doc", "third_party"}

    @classmethod
    def inspect(
        cls,
        title: str,
        description: str,
        source: str,
        evidence_list: List[AttentionEvidence],
        declared_urgency: float,
        declared_importance: float,
    ) -> Tuple[bool, str, float, float]:
        """Inspects incoming candidate for priority injection attempts.

        Returns:
            (is_adversarial_dampened, reason, sanitized_urgency, sanitized_importance)
        """
        combined_text = f"{title}\n{description}"
        for ev in evidence_list:
            combined_text += f"\n{ev.claim}\n{str(ev.raw_payload)}"

        # Check source trustworthiness
        source_lower = source.lower()
        source_is_untrusted = (
            source_lower in cls.UNTRUSTED_SOURCES
            or "untrusted" in source_lower
            or any(u in source_lower for u in cls.UNTRUSTED_SOURCES)
            or any(not ev.is_trusted for ev in evidence_list)
        )

        detected_phrases: List[str] = []
        for pattern in cls.INJECTION_PATTERNS:
            matches = pattern.findall(combined_text)
            if matches:
                detected_phrases.extend(matches if isinstance(matches[0], str) else [m[0] for m in matches])

        # If untrusted source uses injection phrases or claims extreme urgency/importance (> 0.8)
        if source_is_untrusted and (detected_phrases or declared_urgency > 0.8 or declared_importance > 0.8):
            reason = (
                f"Priority injection firewall triggered: Untrusted source '{source}' attempted "
                f"priority escalation (phrases={detected_phrases[:3]}, claimed_urgency={declared_urgency}). "
                "Urgency and importance dampened to unverified baseline."
            )
            # Bound sanitized scores to safe unverified levels
            sanitized_urgency = min(0.35, declared_urgency * 0.4)
            sanitized_importance = min(0.35, declared_importance * 0.4)
            return True, reason, round(sanitized_urgency, 4), round(sanitized_importance, 4)

        # Clean / trusted candidate
        return False, "Candidate passed priority injection inspection", declared_urgency, declared_importance

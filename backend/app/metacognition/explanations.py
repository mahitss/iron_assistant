"""User-facing safe explanation generator with secret and infrastructure redaction (INVARIANTS 173-178)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from app.metacognition.schemas import SelfModelSchema


class ExplanationGenerator:
    """Generates user-safe explanations of limitations and state without revealing secrets or infrastructure details."""

    SENSITIVE_PATTERNS = [
        r"(?i)sk-[a-zA-Z0-9]{20,}",
        r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}",
        r"(?i)password\s*=\s*[^\s]+",
        r"(?i)internal_ip\s*:\s*[0-9\.]+",
    ]

    @classmethod
    def sanitize_explanation(cls, text: str) -> str:
        """INVARIANT 175 & 178: Redacts credentials, tokens, and private infrastructure details."""
        sanitized = text
        for pat in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pat, "[REDACTED_INTERNAL_CREDENTIAL]", sanitized)
        return sanitized

    @classmethod
    def generate_limitation_explanation(cls, limitation_category: str, detail: str) -> str:
        """INVARIANT 173 & 174: Explains actionable limitation clearly to the user."""
        raw = f"I am unable to proceed with this operation due to a {limitation_category.lower()} limitation: {detail}"
        return cls.sanitize_explanation(raw)

    @classmethod
    def create_user_facing_projection(cls, self_model: SelfModelSchema) -> Dict[str, Any]:
        """INVARIANT 176 & 177: Safe projection of internal self-model for user inspection."""
        available_caps = [
            c.name for c in self_model.capabilities.values()
            if c.state in ("AVAILABLE", "RESTRICTED")
        ]
        degraded_caps = [
            {"name": c.name, "reason": cls.sanitize_explanation(c.degradation_reason or "Unknown")}
            for c in self_model.capabilities.values()
            if c.state == "DEGRADED"
        ]

        active_limitations = [
            {"category": l.category, "description": cls.sanitize_explanation(l.description)}
            for l in self_model.limitations
            if l.status == "ACTIVE"
        ]

        return {
            "version": self_model.version,
            "status": self_model.current_state,
            "available_capabilities": available_caps,
            "degraded_capabilities": degraded_caps,
            "active_limitations": active_limitations,
            "active_tasks_count": len(self_model.active_tasks),
            "resource_pressure": self_model.resource_state.compute_pressure,
            "timestamp": self_model.timestamp.isoformat(),
        }

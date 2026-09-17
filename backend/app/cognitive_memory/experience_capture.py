"""Experience Capture & Provenance Attribution Pipeline (Task 103).

Responsible for:
- Transforming raw operational occurrences into structured, validated Experience items.
- Enforcing privacy scrubbing (removing API keys, tokens, passwords, secrets).
- Preserving strict trust classification (preventing untrusted input from masquerading as verified truth).
- Linking to authoritative subsystem references (situations, missions, decisions, world state).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.cognitive_memory.domain import (
    Experience,
    ExperienceSource,
    ExperienceTrust,
    MemoryScope,
    _now_utc,
    _uuid_hex,
)

logger = logging.getLogger("kairo.cognitive_memory.capture")

# Regex patterns for sensitive credentials
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|bearer|auth[_-]?token|private[_-]?key)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
    re.compile(r"(?i)ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"(?i)ey[a-zA-Z0-9]{20,}\.ey[a-zA-Z0-9]{20,}\.[a-zA-Z0-9_\-]{20,}"),  # JWT
]


class ExperienceCapturePipeline:
    """Validates, sanitizes, and registers meaningful operational experiences."""

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Removes API keys, authorization tokens, and credentials from text content."""
        if not text:
            return ""
        sanitized = text
        # Redact key=value style secrets
        sanitized = re.sub(
            r"(?i)(api[_-]?key|secret|password|auth[_-]?token|private[_-]?key)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?",
            r"\g<1>: [REDACTED_SECRET]",
            sanitized,
        )
        # Redact GitHub personal access tokens
        sanitized = re.sub(r"(?i)ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]", sanitized)
        # Redact JWT tokens
        sanitized = re.sub(r"(?i)ey[a-zA-Z0-9_-]{10,}\.ey[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_\-]{10,}", "[REDACTED_JWT]", sanitized)
        # Redact connection string passwords (e.g. redis://user:pass@host)
        sanitized = re.sub(r"://([^:\s/]+):([^@\s]+)@", r"://\1:[REDACTED_SECRET]@", sanitized)
        # Redact Bearer tokens
        sanitized = re.sub(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{10,}", "Bearer [REDACTED_BEARER_TOKEN]", sanitized)
        return sanitized

    @classmethod
    def sanitize_payload(cls, data: Any) -> Any:
        """Recursively scrubs sensitive keys from dictionary structures."""
        if isinstance(data, dict):
            clean_dict = {}
            for k, v in data.items():
                k_clean = k.lower().strip()
                is_sensitive = (
                    k_clean in ("password", "secret", "token", "api_key", "credential", "private_key", "auth_token")
                    or any(s in k_clean for s in ("password", "secret", "api_key", "private_key", "auth_token"))
                )
                if is_sensitive:
                    clean_dict[k] = "[REDACTED_SECRET]"
                else:
                    clean_dict[k] = cls.sanitize_payload(v)
            return clean_dict
        elif isinstance(data, list):
            return [cls.sanitize_payload(item) for item in data]
        elif isinstance(data, str):
            return cls.sanitize_text(data)
        return data

    @classmethod
    def capture(
        cls,
        summary: str,
        source_type: ExperienceSource = ExperienceSource.OBSERVATION,
        source_id: Optional[str] = None,
        scope: MemoryScope = MemoryScope.PROJECT,
        actor: str = "kairo_system",
        structured_facts: Optional[Dict[str, Any]] = None,
        outcome: str = "SUCCESS",
        confidence: float = 0.8,
        trust_classification: Optional[ExperienceTrust] = None,
        importance: float = 0.5,
        related_entities: Optional[List[str]] = None,
        related_goals: Optional[List[str]] = None,
        related_missions: Optional[List[str]] = None,
        related_capabilities: Optional[List[str]] = None,
        related_situations: Optional[List[str]] = None,
        related_decisions: Optional[List[str]] = None,
        related_actions: Optional[List[str]] = None,
        verification_references: Optional[List[str]] = None,
        world_state_references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Experience:
        """Validates, scrubs, and records an Experience."""
        clean_summary = cls.sanitize_text(summary)
        clean_facts = cls.sanitize_payload(structured_facts or {})
        clean_meta = cls.sanitize_payload(metadata or {})

        # Default trust classification based on source type
        if trust_classification is None:
            if source_type in (ExperienceSource.USER_CORRECTION, ExperienceSource.USER_FEEDBACK):
                trust = ExperienceTrust.USER_CONFIRMED
            elif source_type in (ExperienceSource.ACTION, ExperienceSource.VERIFICATION):
                trust = ExperienceTrust.ACTION_VERIFIED
            elif source_type == ExperienceSource.WORLD_STATE_CHANGE:
                trust = ExperienceTrust.WORLD_STATE_VERIFIED
            elif source_type in (ExperienceSource.MISSION_OUTCOME, ExperienceSource.SITUATION):
                trust = ExperienceTrust.SYSTEM_VERIFIED
            else:
                trust = ExperienceTrust.OBSERVED
        else:
            trust = trust_classification

        # Untrusted external web or third party tool checks
        if "untrusted" in (source_id or "").lower() or "web_scrape" in (source_id or "").lower():
            trust = ExperienceTrust.EXTERNAL_UNTRUSTED

        exp = Experience(
            experience_id=_uuid_hex("exp"),
            source_type=source_type,
            source_id=source_id,
            scope=scope,
            occurred_at=_now_utc(),
            recorded_at=_now_utc(),
            actor=actor,
            summary=clean_summary,
            structured_facts=clean_facts,
            outcome=outcome,
            confidence=max(0.0, min(1.0, confidence)),
            trust_classification=trust,
            importance=max(0.0, min(1.0, importance)),
            related_entities=related_entities or [],
            related_goals=related_goals or [],
            related_missions=related_missions or [],
            related_capabilities=related_capabilities or [],
            related_situations=related_situations or [],
            related_decisions=related_decisions or [],
            related_actions=related_actions or [],
            verification_references=verification_references or [],
            world_state_references=world_state_references or [],
            metadata=clean_meta,
        )

        logger.info(
            "Captured Experience %s [Source: %s, Trust: %s, Scope: %s]",
            exp.experience_id, exp.source_type.value, exp.trust_classification.value, exp.scope.value
        )
        return exp

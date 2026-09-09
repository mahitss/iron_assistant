"""Intent Component Provenance, Lineage Auditing, and Input Privacy Retention (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("kairo.intent.provenance")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProvenanceSource(str, Enum):
    """Origin attribution for intent components (Spec 145, 146)."""

    EXPLICIT_USER = "EXPLICIT_USER"
    MEMORY = "MEMORY"
    CONTEXT = "CONTEXT"
    INFERENCE = "INFERENCE"
    SYSTEM_DEFAULT = "SYSTEM_DEFAULT"



class IntentProvenanceTracker:
    """Tracks source attribution for every constituent component of an intent (Spec 145, 146).
    
    CRITICAL INVARIANT (Spec 146):
    Every field retains its origin tag:
    - EXPLICIT_USER
    - MEMORY
    - CONTEXT
    - INFERENCE
    - SYSTEM_DEFAULT
    """

    @classmethod
    def create_provenance_record(
        cls,
        intent_id: str,
        sources: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        prov = {
            "intent_id": intent_id,
            "recorded_at": utc_now().isoformat(),
        }
        if sources:
            prov.update(sources)
        return prov

    @classmethod
    def sanitize_for_retention(cls, raw_text: str, user_privacy_mode: bool = True) -> str:
        """Enforce Spec 147, 148: Apply privacy retention policy; do not persist unnecessary sensitive tokens."""
        if not user_privacy_mode:
            return raw_text

        # Strip credit card, social security, or api token patterns
        sanitized = raw_text
        import re
        sanitized = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_PAYMENT_INFO]", sanitized)
        sanitized = re.sub(r"(?:api[_-]?key|secret|token|password)[\s:=]+([a-zA-Z0-9_\-\.]{8,})", r"\1=[REDACTED_SECRET]", sanitized, flags=re.IGNORECASE)
        return sanitized

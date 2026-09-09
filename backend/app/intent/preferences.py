"""Preference-Aware Interpretation, Confidence Tiers, and Instruction Override Rules (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.intent.schemas import PreferenceConfidence, PreferenceScope

logger = logging.getLogger("kairo.intent.preferences")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserPreference:
    """User preference definition with explicit confidence and scoping (Spec 20-24)."""

    key: str
    value: Any
    confidence: PreferenceConfidence = PreferenceConfidence.EXPLICIT
    scope: PreferenceScope = PreferenceScope.GLOBAL
    project_id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    last_confirmed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence.value,
            "scope": self.scope.value,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat(),
            "last_confirmed_at": self.last_confirmed_at.isoformat() if self.last_confirmed_at else None,
        }


class PreferenceResolver:
    """Resolves operational preferences while enforcing strict instruction override invariants (Spec 23, 24).
    
    CRITICAL INVARIANTS:
    1. Current explicit user instruction strictly overrides older preferences (Spec 23).
    2. Memory / long-term preferences CANNOT override explicit current instructions (Spec 24).
    3. Weakly-inferred preferences should not drive consequential actions without confirmation.
    """

    def __init__(self) -> None:
        # key -> UserPreference
        self._preferences: Dict[str, UserPreference] = {}

    def store_preference(self, pref: UserPreference) -> None:
        """Store or update a user preference record."""
        self._preferences[pref.key] = pref

    def resolve_preference(self, key: str, explicit_override: Optional[Any] = None) -> Any:
        """Resolve effective preference value, honoring explicit overrides strictly."""
        val, _ = self.resolve_effective_setting(key, current_instruction_override=explicit_override)
        return val

    def register_preference(

        self,
        key: str,
        value: Any,
        confidence: PreferenceConfidence = PreferenceConfidence.EXPLICIT,
        scope: PreferenceScope = PreferenceScope.GLOBAL,
        project_id: Optional[str] = None,
    ) -> UserPreference:
        pref = UserPreference(
            key=key,
            value=value,
            confidence=confidence,
            scope=scope,
            project_id=project_id,
            created_at=utc_now(),
        )
        self._preferences[key] = pref
        logger.info("Registered preference '%s'=%s (conf=%s, scope=%s)", key, value, confidence.value, scope.value)
        return pref

    def resolve_effective_setting(
        self,
        key: str,
        current_instruction_override: Optional[Any] = None,
        project_id: Optional[str] = None,
        default_fallback: Optional[Any] = None,
    ) -> tuple[Any, str]:
        """Enforce Spec 23, 24: Explicit current instruction always takes precedence over memory/preferences."""
        # Rule 1: Explicit instruction takes absolute priority
        if current_instruction_override is not None:
            return current_instruction_override, "EXPLICIT_CURRENT_INSTRUCTION"

        # Rule 2: Project-scoped preference
        if project_id:
            for p in self._preferences.values():
                if p.key == key and p.scope == PreferenceScope.PROJECT and p.project_id == project_id:
                    return p.value, "PROJECT_PREFERENCE"

        # Rule 3: Global preference
        if key in self._preferences:
            pref = self._preferences[key]
            # If weakly inferred, flag it
            source_tag = "EXPLICIT_PREFERENCE" if pref.confidence == PreferenceConfidence.EXPLICIT else "INFERRED_PREFERENCE"
            return pref.value, source_tag

        # Rule 4: System default
        return default_fallback, "SYSTEM_DEFAULT"

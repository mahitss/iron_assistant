"""Preference memory, project-scoped overrides, conflict detection, and instruction overrides."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

from app.knowledge_graph.schemas import (
    PreferenceCategory,
    PreferenceMemorySchema,
    ScopeType,
)


class PreferenceManager:
    """Manages preference memory with strict project scoping and current instruction overrides."""

    def __init__(self) -> None:
        # preference_id -> PreferenceMemorySchema
        self._preferences: Dict[str, PreferenceMemorySchema] = {}

    def set_preference(
        self,
        category: PreferenceCategory,
        value: Dict[str, Any],
        scope: ScopeType = ScopeType.PRIVATE,
        confidence: float = 1.0,
        source: Optional[Dict[str, Any]] = None,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        is_temporary: bool = False,
        ttl_days: Optional[int] = None,
    ) -> PreferenceMemorySchema:
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=ttl_days) if ttl_days else None

        pid = str(uuid.uuid4())
        pref = PreferenceMemorySchema(
            preference_id=pid,
            category=category,
            value=value,
            scope=scope,
            confidence=min(max(confidence, 0.0), 1.0),
            source=source or {"source": "explicit_user_statement"},
            created_at=now,
            last_confirmed=now,
            expires_at=expires_at,
            user_id=user_id,
            project_id=project_id,
            is_temporary=is_temporary,
        )

        self._preferences[pid] = pref
        return pref

    def resolve_preference(
        self,
        category: PreferenceCategory,
        user_id: str,
        project_id: Optional[str] = None,
        current_instruction_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resolves active preference value.

        INVARIANT 71: Current explicit user instruction ALWAYS overrides older preferences!
        INVARIANT 163: Project-scoped preference overrides global preference for that project.
        """
        if current_instruction_override is not None:
            return {
                "source": "current_explicit_instruction",
                "value": current_instruction_override,
                "scope": "instruction",
                "confidence": 1.0,
            }

        candidates = [
            p for p in self._preferences.values()
            if p.category == category and p.user_id == user_id
        ]

        # Filter out expired
        now = datetime.now(UTC)
        active_candidates = [p for p in candidates if not p.expires_at or p.expires_at > now]

        if not active_candidates:
            return {"source": "default", "value": {}, "scope": "none", "confidence": 0.0}

        # Check for project-scoped candidate first
        if project_id:
            proj_prefs = [p for p in active_candidates if p.project_id == project_id]
            if proj_prefs:
                # Return most recently confirmed project preference
                latest = max(proj_prefs, key=lambda p: p.last_confirmed)
                return {
                    "source": "project_scoped_preference",
                    "value": latest.value,
                    "scope": "project",
                    "confidence": latest.confidence,
                }

        # Otherwise global / private user preference
        latest_global = max(active_candidates, key=lambda p: p.last_confirmed)
        return {
            "source": "user_preference",
            "value": latest_global.value,
            "scope": latest_global.scope.value,
            "confidence": latest_global.confidence,
        }

    def list_preferences(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[PreferenceMemorySchema]:
        results = list(self._preferences.values())
        if user_id:
            results = [p for p in results if p.user_id == user_id]
        if project_id:
            results = [p for p in results if p.project_id == project_id]
        return results

"""Relationship context modeling with safe categories and anti-social-profiling guards."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.communication.schemas import RelationshipContextSchema, RelationshipType


# Allowed safe contextual relationship categories
SAFE_RELATIONSHIP_TYPES = {t.value for t in RelationshipType}

# Disallowed sensitive profiling attributes
FORBIDDEN_PROFILING_KEYS = {
    "political_affiliation",
    "religious_belief",
    "sexual_orientation",
    "health_status",
    "psychological_profile",
    "credit_score",
    "ethnicity",
    "vulnerability_score",
}


class SocialProfilingViolationError(Exception):
    """Raised when an attempt is made to infer or store sensitive personal characteristics."""
    pass


class RelationshipEngine:
    """Tracks interaction contexts, preferences, and safe non-intrusive relationship categories."""

    def __init__(self) -> None:
        # participant_identity -> RelationshipContextSchema
        self._relationships: Dict[str, RelationshipContextSchema] = {}

    def set_relationship(
        self,
        participant_identity: str,
        relationship_type: RelationshipType | str,
        project_id: Optional[str] = None,
        communication_preferences: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> RelationshipContextSchema:
        """Sets relationship context strictly within safe categories."""
        rel_val = relationship_type.value if isinstance(relationship_type, RelationshipType) else str(relationship_type).upper()
        if rel_val not in SAFE_RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid relationship type '{rel_val}'. Must be one of {SAFE_RELATIONSHIP_TYPES}")

        prefs = communication_preferences or {}
        self._audit_profiling(prefs)

        ctx = RelationshipContextSchema(
            participant_identity=participant_identity,
            relationship_type=RelationshipType(rel_val),
            project_id=project_id,
            communication_preferences=prefs,
            confidence=min(max(confidence, 0.0), 1.0),
            provenance=provenance or {"source": "user_declared_or_interaction"},
        )
        self._relationships[participant_identity.lower()] = ctx
        return ctx

    def get_relationship(self, participant_identity: str) -> RelationshipContextSchema:
        ctx = self._relationships.get(participant_identity.lower())
        if not ctx:
            return RelationshipContextSchema(
                participant_identity=participant_identity,
                relationship_type=RelationshipType.UNKNOWN,
                confidence=0.5,
                provenance={"source": "default_unknown"},
            )
        return ctx

    def record_interaction(
        self,
        participant_identity: str,
        channel: str,
        timestamp: str,
        summary: str,
    ) -> None:
        rel = self.get_relationship(participant_identity)
        rel.interaction_history.append({
            "channel": channel,
            "timestamp": timestamp,
            "summary": summary,
        })
        # Keep last 50 interactions
        if len(rel.interaction_history) > 50:
            rel.interaction_history = rel.interaction_history[-50:]
        self._relationships[participant_identity.lower()] = rel

    def _audit_profiling(self, data: Dict[str, Any]) -> None:
        """INVARIANT 16: Zero social profiling. Forbid sensitive psychological/personal trait tracking."""
        for key in data.keys():
            if key.lower() in FORBIDDEN_PROFILING_KEYS:
                raise SocialProfilingViolationError(
                    f"Forbidden profiling attribute detected: '{key}'. Social profiling is strictly prohibited."
                )

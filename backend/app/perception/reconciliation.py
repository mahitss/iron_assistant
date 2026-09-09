"""State Reconciliation, Authority Conflict Resolution, and Entity Identity (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.perception.observations import Observation
from app.perception.sources import PerceptionSource

logger = logging.getLogger("kairo.perception.reconciliation")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReconciliationError(Exception):
    """Raised when an attempt is made to overwrite authoritative state with a weaker unverified observation (Spec 116)."""


@dataclass
class StateConflict:
    """Explicitly preserved disagreement between perception observations and authoritative sources (Spec 117)."""

    conflict_id: str
    subject: str
    authoritative_state: Any
    observed_state: Any
    authoritative_source_id: str
    candidate_source_id: str
    detected_at: datetime = field(default_factory=utc_now)
    resolved: bool = False
    resolution_notes: Optional[str] = None


class EntityResolver:
    """Resolves cross-system entity identifiers without blind merging under ambiguity (Spec 123-132)."""

    def __init__(self) -> None:
        # canonical_id -> set of alias identifiers
        self._aliases: Dict[str, set[str]] = {}

    def register_entity(self, canonical_id: str, aliases: Optional[List[str]] = None) -> None:
        alias_set = self._aliases.setdefault(canonical_id, set())
        alias_set.add(canonical_id)
        if aliases:
            alias_set.update(aliases)

    def resolve_entity(self, identifier: str) -> Optional[str]:
        """Find canonical entity ID from identifier or alias."""
        for canon, aliases in self._aliases.items():
            if identifier in aliases:
                return canon
        return None

    def safe_merge_entities(self, entity_a: str, entity_b: str, confidence: float = 1.0) -> str:
        """Enforce Spec 125: If uncertain (confidence < 0.95), do NOT merge entities blindly."""
        if confidence < 0.95:
            logger.warning("Entity ambiguity between '%s' and '%s' (conf=%.2f); blind merge prevented.", entity_a, entity_b, confidence)
            return entity_a  # Keep distinct

        canon_a = self.resolve_entity(entity_a) or entity_a
        canon_b = self.resolve_entity(entity_b) or entity_b

        if canon_a != canon_b:
            self._aliases.setdefault(canon_a, set()).update(self._aliases.get(canon_b, {canon_b}))
            self._aliases.pop(canon_b, None)
            logger.info("Merged entity '%s' into canonical '%s'", canon_b, canon_a)

        return canon_a


class StateReconciler:
    """Reconciles perception observations against authoritative external state (Spec 114-117)."""

    def __init__(self) -> None:
        # subject -> (state_value, authority_weight 0.0-1.0, timestamp, source_id)
        self._authoritative_states: Dict[str, tuple[Any, float, datetime, str]] = {}
        # conflict_id -> StateConflict
        self._conflicts: Dict[str, StateConflict] = {}

    def register_authoritative_state(
        self,
        subject: str,
        state_value: Any,
        source_id: str,
        authority_weight: float = 1.0,
        timestamp: Optional[datetime] = None,
    ) -> None:
        self._authoritative_states[subject] = (state_value, authority_weight, timestamp or utc_now(), source_id)

    def reconcile_observation(
        self,
        observation: Observation,
        source: PerceptionSource,
    ) -> tuple[bool, Optional[StateConflict]]:
        """Reconcile incoming observation against authoritative state (Spec 115-117).
        
        Returns:
            (is_accepted, conflict_or_none)
        """
        subj = observation.subject
        auth_entry = self._authoritative_states.get(subj)
        if not auth_entry:
            # No prior authoritative state, adopt observation
            self.register_authoritative_state(
                subject=subj,
                state_value=observation.data,
                source_id=source.source_id,
                authority_weight=source.reliability,
                timestamp=observation.observed_at,
            )
            return True, None

        auth_val, auth_weight, auth_time, auth_src = auth_entry
        candidate_val = observation.data
        candidate_weight = source.reliability

        if auth_val == candidate_val:
            return True, None  # Agreement

        # Disagreement detected (Spec 117)
        if candidate_weight < auth_weight:
            # Weaker observation cannot overwrite authoritative state (Spec 116)
            conf_id = f"conf_{uuid.uuid4().hex[:8]}"
            conflict = StateConflict(
                conflict_id=conf_id,
                subject=subj,
                authoritative_state=auth_val,
                observed_state=candidate_val,
                authoritative_source_id=auth_src,
                candidate_source_id=source.source_id,
                detected_at=utc_now(),
            )
            self._conflicts[conf_id] = conflict
            logger.warning(
                "State conflict preserved on '%s': Candidate (%s, trust=%.2f) rejected by authoritative (%s, trust=%.2f)",
                subj,
                source.source_id,
                candidate_weight,
                auth_src,
                auth_weight,
            )
            return False, conflict

        # Higher authority updates state
        self.register_authoritative_state(
            subject=subj,
            state_value=candidate_val,
            source_id=source.source_id,
            authority_weight=candidate_weight,
            timestamp=observation.observed_at,
        )
        return True, None

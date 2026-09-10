"""Operational knowledge state tracking, evidence modeling, and unknown handling (INVARIANTS 18-23)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.metacognition.schemas import KnowledgeCategory, KnowledgeStateSchema


class KnowledgeStateTracker:
    """Tracks current confidence, verification state, and staleness of operational knowledge."""

    def __init__(self, stale_threshold_hours: int = 72) -> None:
        # subject (lower) -> KnowledgeStateSchema
        self._states: Dict[str, KnowledgeStateSchema] = {}
        self.stale_threshold = timedelta(hours=stale_threshold_hours)

    def record_knowledge(
        self,
        subject: str,
        category: KnowledgeCategory = KnowledgeCategory.KNOWN,
        confidence: float = 1.0,
        provenance: Optional[Dict[str, Any]] = None,
        is_verified: bool = False,
        evidence_count: int = 1,
    ) -> KnowledgeStateSchema:
        """INVARIANT 21: Preserves source provenance and evidence count."""
        sub_key = subject.strip().lower()
        now = datetime.now(UTC)

        # INVARIANT 22: Fact confidence calibrated against verification & source
        final_conf = min(max(confidence, 0.0), 1.0)
        if not is_verified and final_conf > 0.85:
            final_conf = 0.85  # Unverified knowledge capped

        state = KnowledgeStateSchema(
            subject=subject.strip(),
            category=category,
            confidence=final_conf,
            provenance=provenance or {"source": "direct_input"},
            is_verified=is_verified,
            evidence_count=evidence_count,
            last_verified=now if is_verified else None,
            freshness_timestamp=now,
        )
        self._states[sub_key] = state
        return state

    def get_knowledge_state(self, subject: str) -> KnowledgeStateSchema:
        """INVARIANT 23: UNKNOWN is a valid state. Returns UNKNOWN if not tracked."""
        sub_key = subject.strip().lower()
        state = self._states.get(sub_key)
        if not state:
            return KnowledgeStateSchema(
                subject=subject.strip(),
                category=KnowledgeCategory.UNKNOWN,
                confidence=0.0,
                provenance={"source": "untracked"},
                is_verified=False,
                evidence_count=0,
            )

        # Check staleness (INVARIANT 18 & 152: Knowledge drift)
        now = datetime.now(UTC)
        if now - state.freshness_timestamp > self.stale_threshold and state.category == KnowledgeCategory.KNOWN.value:
            state.category = KnowledgeCategory.STALE
            state.confidence = min(state.confidence, 0.5)

        return state

    def mark_contradicted(self, subject: str, conflicting_evidence: Dict[str, Any]) -> KnowledgeStateSchema:
        sub_key = subject.strip().lower()
        state = self.get_knowledge_state(subject)
        state.category = KnowledgeCategory.CONTRADICTED
        state.confidence = 0.3
        state.provenance["conflict"] = conflicting_evidence
        self._states[sub_key] = state
        return state

    def get_summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for s in self._states.values():
            counts[s.category] = counts.get(s.category, 0) + 1
        return counts

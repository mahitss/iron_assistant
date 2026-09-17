"""Unified Service Coordinator for Kairo Cognitive Memory & Lifelong Learning Fabric (Task 103)."""

from __future__ import annotations

import logging
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.cognitive_memory.consolidation_engine import CognitiveConsolidationEngine
from app.cognitive_memory.contradiction_engine import MemoryContradictionEngine
from app.cognitive_memory.domain import (
    CognitiveMemoryItem,
    Experience,
    ExperienceSource,
    ExperienceTrust,
    FreshnessState,
    MemoryApplicationRecord,
    MemoryConflict,
    MemoryContextPack,
    MemoryErrorType,
    MemoryFeedbackRecord,
    MemoryLifecycleState,
    MemoryPattern,
    MemoryScope,
    MemorySnapshot,
    MemoryType,
    _now_utc,
    _uuid_hex,
)
from app.cognitive_memory.experience_capture import ExperienceCapturePipeline
from app.cognitive_memory.replay import MemoryReplayEngine
from app.cognitive_memory.retrieval import HybridMemoryRetrievalEngine

logger = logging.getLogger("kairo.cognitive_memory.service")


class CognitiveMemoryService:
    """Master domain coordinator for experience ingestion, consolidation, retrieval, and learning."""

    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        self.db = db
        self.consolidation_engine = CognitiveConsolidationEngine()

        # In-memory fast stores
        self._experiences: Dict[str, Experience] = {}
        self._memories: Dict[str, CognitiveMemoryItem] = {}
        self._conflicts: Dict[str, MemoryConflict] = {}
        self._patterns: Dict[str, MemoryPattern] = {}
        self._applications: List[MemoryApplicationRecord] = []
        self._feedbacks: List[MemoryFeedbackRecord] = []
        self._snapshots: Dict[str, MemorySnapshot] = {}

    # --------------------------------------------------------------------------
    # 1. Experience Ingestion
    # --------------------------------------------------------------------------

    def record_experience(
        self,
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
        related_missions: Optional[List[str]] = None,
        related_situations: Optional[List[str]] = None,
        related_decisions: Optional[List[str]] = None,
        related_actions: Optional[List[str]] = None,
        verification_references: Optional[List[str]] = None,
        world_state_references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_consolidate: bool = True,
    ) -> Tuple[Experience, Optional[CognitiveMemoryItem]]:
        """Captures a new operational occurrence and optionally creates a candidate memory."""
        exp = ExperienceCapturePipeline.capture(
            summary=summary,
            source_type=source_type,
            source_id=source_id,
            scope=scope,
            actor=actor,
            structured_facts=structured_facts,
            outcome=outcome,
            confidence=confidence,
            trust_classification=trust_classification,
            importance=importance,
            related_entities=related_entities,
            related_missions=related_missions,
            related_situations=related_situations,
            related_decisions=related_decisions,
            related_actions=related_actions,
            verification_references=verification_references,
            world_state_references=world_state_references,
            metadata=metadata,
        )

        self._experiences[exp.experience_id] = exp

        cand = None
        if auto_consolidate:
            cand = self.consolidation_engine.create_candidate_from_experience(exp)
            self._memories[cand.memory_id] = cand

            # Check if promotion criteria met by existing experiences for all matching candidates
            for m in list(self._memories.values()):
                if m.lifecycle_state == MemoryLifecycleState.CANDIDATE:
                    matching_exps = [
                        e for e in self._experiences.values()
                        if set(e.related_entities).intersection(set(m.related_entities))
                    ]
                    self.consolidation_engine.evaluate_promotion(m, matching_exps)

            # Check contradictions against existing memories
            for existing in list(self._memories.values()):
                conflict = MemoryContradictionEngine.check_contradiction(cand, existing)
                if conflict:
                    self._conflicts[conflict.conflict_id] = conflict

        return exp, cand

    # --------------------------------------------------------------------------
    # 2. Memory Retrieval & Context Packing
    # --------------------------------------------------------------------------

    def search(
        self,
        query: str,
        scope: MemoryScope = MemoryScope.PROJECT,
        scope_id: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        include_stale: bool = False,
        include_candidates: bool = True,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[CognitiveMemoryItem]:
        """Performs scope-isolated multi-criteria search."""
        return HybridMemoryRetrievalEngine.search_memories(
            memories=list(self._memories.values()),
            query=query,
            scope=scope,
            scope_id=scope_id,
            memory_types=memory_types,
            include_stale=include_stale,
            include_candidates=include_candidates,
            min_confidence=min_confidence,
            limit=limit,
        )

    def assemble_context_pack(
        self,
        query: str,
        scope: MemoryScope = MemoryScope.PROJECT,
        scope_id: Optional[str] = None,
        max_items: int = 8,
    ) -> MemoryContextPack:
        """Builds a bounded context pack for reasoning engines."""
        return HybridMemoryRetrievalEngine.assemble_context_pack(
            query=query,
            memories=list(self._memories.values()),
            conflicts=list(self._conflicts.values()),
            scope=scope,
            scope_id=scope_id,
            max_items=max_items,
        )

    def apply_memory(
        self,
        memory_id: str,
        consumer: str,
        context_summary: str,
        decision_ref: Optional[str] = None,
        action_ref: Optional[str] = None,
    ) -> Optional[MemoryApplicationRecord]:
        """Records when memory is consumed by Decision, Mission, or Planning systems."""
        mem = self._memories.get(memory_id)
        if not mem:
            return None
        rec = HybridMemoryRetrievalEngine.record_application(
            memory=mem,
            consumer=consumer,
            context_summary=context_summary,
            decision_ref=decision_ref,
            action_ref=action_ref,
        )
        self._applications.append(rec)
        return rec

    def record_feedback(
        self,
        memory_id: str,
        was_useful: bool,
        caused_error: bool = False,
        error_type: Optional[MemoryErrorType] = None,
        empirical_outcome: str = "SUCCESS",
        notes: Optional[str] = None,
        application_id: Optional[str] = None,
    ) -> MemoryFeedbackRecord:
        """Records metacognitive feedback on memory effectiveness."""
        mem = self._memories.get(memory_id)
        if mem:
            if was_useful:
                mem.useful_count += 1
            if caused_error:
                mem.error_count += 1

        rec = MemoryFeedbackRecord(
            feedback_id=_uuid_hex("mfbk"),
            memory_id=memory_id,
            application_id=application_id,
            was_useful=was_useful,
            caused_error=caused_error,
            error_type=error_type,
            empirical_outcome=empirical_outcome,
            notes=notes,
            recorded_at=_now_utc(),
        )
        self._feedbacks.append(rec)
        return rec

    # --------------------------------------------------------------------------
    # 3. Contradiction & World-State Primacy
    # --------------------------------------------------------------------------

    def reconcile_with_world_state(
        self,
        memory_id: str,
        target_entity_id: str,
        attribute_name: str,
        current_world_value: Optional[Any] = None,
    ) -> Tuple[FreshnessState, Optional[str]]:
        """Enforces world-state primacy: current world-state overrules memory."""
        mem = self._memories.get(memory_id)
        if not mem:
            return FreshnessState.UNKNOWN, f"Memory {memory_id} not found"
        return MemoryContradictionEngine.reconcile_with_world_state(
            memory=mem,
            target_entity_id=target_entity_id,
            attribute_name=attribute_name,
            current_world_value=current_world_value,
        )

    def apply_user_correction(
        self,
        old_memory_id: str,
        new_content: str,
        new_facts: Optional[Dict[str, Any]] = None,
    ) -> Optional[CognitiveMemoryItem]:
        """Explicit user correction: supersedes old memory and generates v+1."""
        old_mem = self._memories.get(old_memory_id)
        if not old_mem:
            return None
        new_mem = MemoryContradictionEngine.apply_user_correction(
            old_memory=old_mem,
            new_content=new_content,
            new_facts=new_facts,
        )
        self._memories[new_mem.memory_id] = new_mem
        return new_mem

    # --------------------------------------------------------------------------
    # 4. Patterns & Periodic Maintenance
    # --------------------------------------------------------------------------

    def consolidate_patterns(self, scope: MemoryScope = MemoryScope.PROJECT) -> List[MemoryPattern]:
        """Runs clustering across captured experiences to discover recurring patterns."""
        scoped_exps = [e for e in self._experiences.values() if e.scope == scope or scope == MemoryScope.GLOBAL]
        patterns = self.consolidation_engine.cluster_patterns(scoped_exps, scope=scope)
        for p in patterns:
            self._patterns[p.pattern_id] = p
        return patterns

    def revalidate_stale_memories(self, max_age_days: float = 30.0) -> int:
        """Inspects temporal freshness and marks expired memories as STALE."""
        now = datetime.now(UTC)
        stale_count = 0

        for mem in self._memories.values():
            if mem.lifecycle_state in (MemoryLifecycleState.ACTIVE, MemoryLifecycleState.CONSOLIDATED):
                try:
                    obs_time = datetime.fromisoformat(mem.observed_at)
                    age_days = (now - obs_time).total_seconds() / 86400.0
                    if age_days > mem.decay_rate_days:
                        mem.freshness = FreshnessState.STALE
                        stale_count += 1
                except Exception:
                    pass

        return stale_count

    def revalidate_memory(self, memory_id: str) -> Optional[CognitiveMemoryItem]:
        """Manually revalidates a memory after verification, resetting freshness to CURRENT."""
        mem = self._memories.get(memory_id)
        if not mem:
            return None
        mem.freshness = FreshnessState.CURRENT
        mem.last_verified_at = _now_utc()
        if mem.lifecycle_state == MemoryLifecycleState.STALE:
            mem.lifecycle_state = MemoryLifecycleState.ACTIVE
        return mem

    def invalidate_memory(self, memory_id: str, reason: str = "MANUAL_INVALIDATION") -> Optional[CognitiveMemoryItem]:
        """Marks a memory as retired/invalidated without destroying its historical audit record."""
        mem = self._memories.get(memory_id)
        if not mem:
            return None
        mem.lifecycle_state = MemoryLifecycleState.RETIRED
        mem.freshness = FreshnessState.EXPIRED
        mem.metadata["invalidation_reason"] = reason
        mem.metadata["invalidated_at"] = _now_utc()
        return mem

    # --------------------------------------------------------------------------
    # 5. Deterministic Replay & Snapshots
    # --------------------------------------------------------------------------

    def replay_sequence(self, experience_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Deterministically simulates memory evolution without external side effects."""
        exps = [self._experiences[eid] for eid in experience_ids if eid in self._experiences] if experience_ids else list(self._experiences.values())
        return MemoryReplayEngine.replay_experience_sequence(exps)

    def create_snapshot(self) -> MemorySnapshot:
        """Creates an immutable point-in-time snapshot of the cognitive memory fabric."""
        snap = MemorySnapshot(
            snapshot_id=_uuid_hex("msnap"),
            created_at=_now_utc(),
            total_memories=len(self._memories),
            active_count=sum(1 for m in self._memories.values() if m.lifecycle_state == MemoryLifecycleState.ACTIVE),
            stale_count=sum(1 for m in self._memories.values() if m.freshness == FreshnessState.STALE),
            conflicted_count=len(self._conflicts),
            pattern_count=len(self._patterns),
            memory_ids=list(self._memories.keys()),
            conflict_ids=list(self._conflicts.keys()),
            pattern_ids=list(self._patterns.keys()),
        )
        self._snapshots[snap.snapshot_id] = snap
        return snap

    # --------------------------------------------------------------------------
    # 6. Status & Inspections
    # --------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Provides high-level health and volume metrics."""
        return {
            "total_experiences": len(self._experiences),
            "total_memories": len(self._memories),
            "active_memories": sum(1 for m in self._memories.values() if m.lifecycle_state == MemoryLifecycleState.ACTIVE),
            "candidate_memories": sum(1 for m in self._memories.values() if m.lifecycle_state == MemoryLifecycleState.CANDIDATE),
            "stale_memories": sum(1 for m in self._memories.values() if m.freshness == FreshnessState.STALE),
            "superseded_memories": sum(1 for m in self._memories.values() if m.lifecycle_state == MemoryLifecycleState.SUPERSEDED),
            "active_conflicts": sum(1 for c in self._conflicts.values() if c.status == "ACTIVE"),
            "patterns_discovered": len(self._patterns),
            "total_applications": len(self._applications),
            "feedback_recorded": len(self._feedbacks),
        }

    def get_memory(self, memory_id: str) -> Optional[CognitiveMemoryItem]:
        return self._memories.get(memory_id)

    def list_memories(
        self,
        scope: Optional[str] = None,
        lifecycle_state: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[CognitiveMemoryItem]:
        items = list(self._memories.values())
        if scope:
            items = [m for m in items if m.scope.value == scope]
        if lifecycle_state:
            items = [m for m in items if m.lifecycle_state.value == lifecycle_state]
        if memory_type:
            items = [m for m in items if m.memory_type.value == memory_type]
        return items[:limit]

    def list_conflicts(self) -> List[MemoryConflict]:
        return list(self._conflicts.values())

    def list_patterns(self) -> List[MemoryPattern]:
        return list(self._patterns.values())


# Global singleton instance
_GLOBAL_COGNITIVE_MEMORY_SERVICE: Optional[CognitiveMemoryService] = None


def get_cognitive_memory_service(db: Optional[AsyncSession] = None) -> CognitiveMemoryService:
    """Returns singleton instance of CognitiveMemoryService."""
    global _GLOBAL_COGNITIVE_MEMORY_SERVICE
    if _GLOBAL_COGNITIVE_MEMORY_SERVICE is None:
        _GLOBAL_COGNITIVE_MEMORY_SERVICE = CognitiveMemoryService(db=db)
    return _GLOBAL_COGNITIVE_MEMORY_SERVICE

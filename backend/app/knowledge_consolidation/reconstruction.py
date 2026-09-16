"""Forensic memory reconstruction engine for KAIRO (Task 92 Phase 21).

Guarantees:
- Reconstructs authentic chronological timeline and current vs historical state
- Strictly prevents fabrication of missing events
- Integrates episodic events, task outcomes, semantic facts, and unresolved conflicts
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.knowledge_consolidation.models import (
    CertaintyState,
    MemoryConflict,
    MemoryEntity,
    MemoryReconstructionRequest,
    MemoryReconstructionResult,
    MemoryStatus,
    ProvenanceSourceType,
    TimelineEvent,
)


class MemoryReconstructionEngine:
    """Reconstructs historical narratives and state evolutions from grounding memories."""

    def reconstruct(
        self,
        request: MemoryReconstructionRequest,
        memories: list[MemoryEntity],
        conflicts: list[MemoryConflict],
        evidence_manager: Any,
    ) -> MemoryReconstructionResult:
        """Execute forensic reconstruction without hallucination."""
        keywords = set(request.query.lower().split())
        if request.entity:
            keywords.add(request.entity.lower())

        matching_memories: list[MemoryEntity] = []

        for m in memories:
            # Check content overlap
            content_words = set(m.content.lower().split())
            if keywords.intersection(content_words):
                matching_memories.append(m)

        # Sort chronologically by observed_at or created_at
        matching_memories.sort(key=lambda m: m.observed_at or m.created_at)

        timeline: list[TimelineEvent] = []
        superseded_states: list[str] = []
        evidence_refs: list[str] = []
        current_state_candidates: list[str] = []

        for m in matching_memories[: request.max_events]:
            evs = evidence_manager.get_evidence_for_memory(m.memory_id) if evidence_manager else []
            for e in evs:
                evidence_refs.append(f"{e.source}: {e.content[:64]}")

            event = TimelineEvent(
                timestamp=m.observed_at or m.created_at,
                memory_id=m.memory_id,
                type=m.type,
                summary=m.content,
                status=m.status,
                confidence=m.confidence,
                certainty=m.certainty,
                source_type=m.provenance.source_type if m.provenance else ProvenanceSourceType.OBSERVED,
                evidence_count=len(evs),
            )
            timeline.append(event)

            if m.status == MemoryStatus.SUPERSEDED:
                superseded_states.append(f"[{m.observed_at.date() if m.observed_at else 'Historical'}] {m.content}")
            elif m.status in (MemoryStatus.ACTIVE, MemoryStatus.STALE):
                current_state_candidates.append(m.content)

        # Identify related unresolved conflicts
        matched_ids = {m.memory_id for m in matching_memories}
        unresolved: list[dict[str, Any]] = []

        for cnf in conflicts:
            if cnf.status == "CONFLICTED" and (cnf.memory_a_id in matched_ids or cnf.memory_b_id in matched_ids):
                unresolved.append({
                    "conflict_id": cnf.conflict_id,
                    "explanation": cnf.explanation,
                    "competing_values": cnf.competing_values,
                })

        # Synthesize honest narrative
        current_state_str = (
            current_state_candidates[-1]
            if current_state_candidates
            else "No active confirmed state exists; historical or conflicting records only."
        )

        narrative_parts = [
            f"Forensic Reconstruction for query '{request.query}':",
            f"- Identified {len(timeline)} chronological records across observation history.",
            f"- Current confirmed state: {current_state_str}",
        ]

        if superseded_states:
            narrative_parts.append(f"- Identified {len(superseded_states)} past superseded states.")

        if unresolved:
            narrative_parts.append(
                f"- CAUTION: {len(unresolved)} active unresolved contradictions remain regarding this topic."
            )

        narrative = "\n".join(narrative_parts)

        # Compute overall confidence
        avg_conf = (
            sum(m.confidence for m in matching_memories) / len(matching_memories)
            if matching_memories
            else 0.5
        )

        overall_certainty = (
            CertaintyState.CONTRADICTED
            if unresolved
            else (CertaintyState.KNOWN if matching_memories else CertaintyState.UNKNOWN)
        )

        return MemoryReconstructionResult(
            query=request.query,
            timeline=timeline,
            current_state=current_state_str,
            superseded_states=superseded_states,
            unresolved_conflicts=unresolved,
            confidence=round(avg_conf, 2),
            certainty=overall_certainty,
            evidence_references=evidence_refs[:15],
            synthesized_narrative=narrative,
        )

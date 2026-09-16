"""Grounding evidence model and registry for KAIRO knowledge (Task 92 Phase 4).

Guarantees:
- Evidence can support, contradict, qualify, expire, or revalidate a memory
- Does NOT collapse contradictory evidence into a single fake truth
- Preserves competing citations and grounds
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.knowledge_consolidation.models import (
    EvidenceRelationType,
    MemoryEvidence,
    ProvenanceSourceType,
)


class EvidenceManager:
    """Manages ground-truth evidence links, corroborations, and contradictions."""

    def __init__(self) -> None:
        self._evidence_records: dict[str, MemoryEvidence] = {}
        # memory_id -> list of evidence_ids
        self._memory_evidence_map: dict[str, list[str]] = {}

    def attach_evidence(
        self,
        memory_id: str,
        content: str,
        source: str,
        relation_type: EvidenceRelationType = EvidenceRelationType.SUPPORT,
        source_type: ProvenanceSourceType = ProvenanceSourceType.OBSERVED,
        reliability: float = 0.8,
        confidence: float = 0.8,
        freshness: str = "FRESH",
        provenance_id: str | None = None,
        verification_status: str = "VERIFIED",
    ) -> MemoryEvidence:
        """Attach grounding evidence to a target memory entity."""
        evidence = MemoryEvidence(
            memory_id=memory_id,
            content=content,
            source=source,
            relation_type=relation_type,
            source_type=source_type,
            reliability=max(0.0, min(1.0, reliability)),
            confidence=max(0.0, min(1.0, confidence)),
            freshness=freshness,
            provenance_id=provenance_id,
            verification_status=verification_status,
            created_at=datetime.now(UTC),
        )
        self._evidence_records[evidence.evidence_id] = evidence
        if memory_id not in self._memory_evidence_map:
            self._memory_evidence_map[memory_id] = []
        self._memory_evidence_map[memory_id].append(evidence.evidence_id)
        return evidence

    def get_evidence_for_memory(
        self, memory_id: str, relation_type: EvidenceRelationType | None = None
    ) -> list[MemoryEvidence]:
        """Retrieve all evidence associated with a memory, optionally filtered by relation type."""
        evidence_ids = self._memory_evidence_map.get(memory_id, [])
        results = [self._evidence_records[eid] for eid in evidence_ids if eid in self._evidence_records]
        if relation_type:
            results = [e for e in results if e.relation_type == relation_type]
        return results

    def get_supporting_evidence(self, memory_id: str) -> list[MemoryEvidence]:
        """Convenience method for corroborating evidence."""
        return self.get_evidence_for_memory(memory_id, EvidenceRelationType.SUPPORT)

    def get_contradicting_evidence(self, memory_id: str) -> list[MemoryEvidence]:
        """Convenience method for conflicting evidence."""
        return self.get_evidence_for_memory(memory_id, EvidenceRelationType.CONTRADICT)

    def summarize_evidence_balance(self, memory_id: str) -> dict[str, Any]:
        """Compute structured evidence balance preserving both perspectives."""
        all_ev = self.get_evidence_for_memory(memory_id)
        supporting = [e for e in all_ev if e.relation_type == EvidenceRelationType.SUPPORT]
        contradicting = [e for e in all_ev if e.relation_type == EvidenceRelationType.CONTRADICT]

        supp_weight = sum(e.reliability * e.confidence for e in supporting)
        contra_weight = sum(e.reliability * e.confidence for e in contradicting)

        return {
            "memory_id": memory_id,
            "total_evidence_count": len(all_ev),
            "supporting_count": len(supporting),
            "contradicting_count": len(contradicting),
            "supporting_weight": round(supp_weight, 3),
            "contradicting_weight": round(contra_weight, 3),
            "has_contradiction": len(contradicting) > 0,
        }

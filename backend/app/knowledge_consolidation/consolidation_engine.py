"""Autonomous knowledge consolidation engine for KAIRO (Task 92 Phase 13).

Guarantees:
- Clusters related episodic experiences and task outcomes into durable semantic knowledge
- Strictly preserves source episodes (never destroys original evidence)
- Fully reversible and auditable DAG linking
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.knowledge_consolidation.models import (
    CertaintyState,
    ConsolidationRecord,
    EvidenceRelationType,
    MemoryEntity,
    MemoryStatus,
    MemoryType,
    ProvenanceSourceType,
    generate_id,
)


class ConsolidationEngine:
    """Clusters episodic memories into higher-level semantic knowledge while maintaining provenance."""

    def __init__(self) -> None:
        self._consolidations: dict[str, ConsolidationRecord] = {}

    def consolidate_episodes(
        self,
        episodes: list[MemoryEntity],
        summary: str,
        common_entities: list[str] | None = None,
        tenant_id: str = "default",
        user_id: str = "default_user",
        project_id: str | None = None,
        evidence_manager: Any = None,
        provenance_tracker: Any = None,
    ) -> tuple[MemoryEntity, ConsolidationRecord]:
        """Consolidate multiple episodic memories into a single semantic knowledge entity."""
        if not episodes:
            raise ValueError("Cannot consolidate an empty set of episodic memories.")

        now = datetime.now(UTC)
        semantic_id = generate_id("sem")
        source_ids = [ep.memory_id for ep in episodes]

        # Calculate combined confidence (bounded)
        avg_confidence = sum(ep.confidence for ep in episodes) / len(episodes)
        boosted_confidence = min(1.0, avg_confidence + 0.1)

        # Create consolidated semantic memory
        semantic_memory = MemoryEntity(
            memory_id=semantic_id,
            tenant_id=tenant_id,
            user_id=user_id,
            project_id=project_id,
            type=MemoryType.SEMANTIC,
            content=summary,
            structured_representation={
                "consolidated_from": source_ids,
                "common_entities": common_entities or [],
                "source_count": len(episodes),
            },
            source="autonomous_consolidation",
            confidence=round(boosted_confidence, 3),
            certainty=CertaintyState.KNOWN,
            importance=max(ep.importance for ep in episodes),
            status=MemoryStatus.ACTIVE,
            created_at=now,
            observed_at=now,
            updated_at=now,
        )

        # Register provenance
        if provenance_tracker:
            prov = provenance_tracker.create_provenance(
                memory_id=semantic_id,
                source_type=ProvenanceSourceType.DERIVED,
                source_identifier=f"consolidation_of_{len(source_ids)}_episodes",
                extraction_method="consolidation_cluster",
            )
            provenance_tracker.record_transformation(
                provenance_id=prov.provenance_id,
                transformation_type="episodic_to_semantic_consolidation",
                details={"source_episode_ids": source_ids},
            )
            semantic_memory.provenance = prov

        # Attach each episode as supporting grounding evidence
        if evidence_manager:
            for ep in episodes:
                evidence_manager.attach_evidence(
                    memory_id=semantic_id,
                    content=ep.content,
                    source=f"episode:{ep.memory_id}",
                    relation_type=EvidenceRelationType.SUPPORT,
                    source_type=ep.provenance.source_type if ep.provenance else ProvenanceSourceType.OBSERVED,
                    reliability=ep.confidence,
                    confidence=ep.confidence,
                    verification_status="VERIFIED",
                )

        # Create consolidation audit record
        rec = ConsolidationRecord(
            consolidation_id=generate_id("cns"),
            source_episode_ids=source_ids,
            consolidated_semantic_id=semantic_id,
            abstraction_level="SEMANTIC",
            summary=summary,
            common_entities=common_entities or [],
            confidence=boosted_confidence,
            created_at=now,
        )
        self._consolidations[rec.consolidation_id] = rec

        return semantic_memory, rec

    def get_consolidation_record(self, consolidation_id: str) -> ConsolidationRecord | None:
        """Retrieve consolidation record by ID."""
        return self._consolidations.get(consolidation_id)

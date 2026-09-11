"""Autonomous consolidation and hierarchical abstraction engine for Task 68.

Enforces:
- Spec 9: Autonomous episodic-to-semantic consolidation with complete evidence preservation
- Spec 10: Hierarchical abstraction levels (RAW_OBSERVATION -> EPISODE -> PATTERN -> GENERALIZED_KNOWLEDGE -> EXECUTIVE_INSIGHT)
- Invariant: summary != source, summary != verified fact
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from app.memory_consolidation.provenance import ProvenanceTracker
from app.memory_consolidation.schemas import (
    AbstractionLevel,
    CognitiveClassification,
    ConsolidationCandidate,
    DurableMemory,
    FreshnessState,
    MemoryLifecycleState,
    MemoryType,
    TrustLevel,
)

logger = logging.getLogger("kairo.memory_consolidation.consolidation")


class AutonomousConsolidationEngine:
    """Clustering, synthesis, and hierarchical abstraction of memories."""

    @classmethod
    def cluster_related_memories(
        cls, memories: list[DurableMemory], min_cluster_size: int = 2
    ) -> list[list[DurableMemory]]:
        """Group related memories by shared entities, projects, or topics (Spec 9)."""
        entity_buckets: dict[str, list[DurableMemory]] = defaultdict(list)

        for mem in memories:
            # Cluster by project_id or recognized entities in structured payload
            project_key = mem.project_id or "global"
            domain_key = mem.structured_payload.get("domain", "general")
            key = f"{project_key}:{domain_key}"
            entity_buckets[key].append(mem)

        clusters = [cluster for cluster in entity_buckets.values() if len(cluster) >= min_cluster_size]
        return clusters

    @classmethod
    def determine_next_abstraction_level(cls, source_levels: list[AbstractionLevel]) -> AbstractionLevel:
        """Promote abstraction to the next appropriate hierarchical tier (Spec 10)."""
        hierarchy = [
            AbstractionLevel.RAW_OBSERVATION,
            AbstractionLevel.EPISODE,
            AbstractionLevel.PATTERN,
            AbstractionLevel.GENERALIZED_KNOWLEDGE,
            AbstractionLevel.EXECUTIVE_INSIGHT,
        ]
        max_source_idx = max((hierarchy.index(lvl) for lvl in source_levels), default=0)
        target_idx = min(max_source_idx + 1, len(hierarchy) - 1)
        return hierarchy[target_idx]

    @classmethod
    def consolidate_cluster(
        cls,
        cluster: list[DurableMemory],
        tenant_id: str = "default",
        actor: str = "consolidation_engine",
    ) -> tuple[ConsolidationCandidate, DurableMemory]:
        """Synthesize candidate abstraction and consolidated memory preserving source lineage (Spec 9)."""
        source_ids = [m.memory_id for m in cluster]
        source_levels = [m.abstraction_level for m in cluster]
        target_abstraction = cls.determine_next_abstraction_level(source_levels)

        # Collect entities across cluster
        all_entities: set[str] = set()
        for m in cluster:
            entities = m.structured_payload.get("entities", [])
            all_entities.update(entities)

        # Build candidate synthesis summary
        time_stamps = [m.created_at.strftime("%Y-%m-%d %H:%M") for m in cluster]
        domain = cluster[0].structured_payload.get("domain", "general")
        project_id = cluster[0].project_id

        summary_text = (
            f"Consolidated abstraction over {len(cluster)} observations in {domain} "
            f"spanning {time_stamps[0]} to {time_stamps[-1]}: Recurring operational pattern identified."
        )

        candidate_id = f"cnd_{uuid.uuid4().hex[:10]}"
        candidate = ConsolidationCandidate(
            candidate_id=candidate_id,
            source_memory_ids=source_ids,
            abstraction_level=target_abstraction,
            suggested_summary=summary_text,
            common_entities=sorted(all_entities),
            confidence=round(sum(m.confidence for m in cluster) / len(cluster), 2),
            status="CONSOLIDATED",
            tenant_id=tenant_id,
        )

        # Build combined lineage
        parent_provenances = [m.provenance for m in cluster]
        consolidated_memory_id = f"mem_cons_{uuid.uuid4().hex[:10]}"
        consolidated_prov = ProvenanceTracker.derive_memory_provenance(
            parent_provenances=parent_provenances,
            derived_memory_id=consolidated_memory_id,
            source_memory_ids=source_ids,
            actor=actor,
        )

        now = datetime.now(UTC)
        consolidated_memory = DurableMemory(
            memory_id=consolidated_memory_id,
            tenant_id=tenant_id,
            user_id=cluster[0].user_id,
            project_id=project_id,
            cognitive_type=CognitiveClassification.SUMMARY,
            memory_type=MemoryType.SEMANTIC_MEMORY,
            abstraction_level=target_abstraction,
            content=summary_text,
            structured_payload={
                "candidate_id": candidate_id,
                "consolidated_from_ids": source_ids,
                "domain": domain,
                "entities": sorted(all_entities),
            },
            # Invariant: Summary confidence cannot exceed average source confidence
            confidence=candidate.confidence,
            importance=max(m.importance for m in cluster),
            relevance=1.0,
            freshness=FreshnessState.FRESH,
            # Invariant: Derived summaries cannot start as VERIFIED without explicit verification
            trust_level=TrustLevel.UNVERIFIED,
            status=MemoryLifecycleState.CONSOLIDATED,
            version=1,
            created_at=now,
            observed_at=now,
            valid_from=min(m.valid_from for m in cluster),
            last_accessed_at=now,
            last_consolidated_at=now,
            provenance=consolidated_prov,
            created_by="consolidation_engine",
            updated_by="consolidation_engine",
        )

        return candidate, consolidated_memory

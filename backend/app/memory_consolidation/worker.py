"""Autonomous background consolidation worker for Task 68.

Enforces:
- Spec 26: Autonomous consolidation sweeps (clustering, deduplication, contradiction detection, abstraction, staleness flagging)
- Spec 30: Idempotency and safe retry execution
- Spec 33: Complete audit observability
"""

from __future__ import annotations

import logging
from typing import Any

from app.memory_consolidation.consolidation import AutonomousConsolidationEngine
from app.memory_consolidation.contradictions import ContradictionEngine
from app.memory_consolidation.deduplication import DeduplicationEngine
from app.memory_consolidation.graph_bridge import KnowledgeGraphBridge
from app.memory_consolidation.schemas import (
    ConsolidationCandidate,
    ContradictionReport,
    DurableMemory,
    FreshnessState,
    MemoryLifecycleState,
    MemoryType,
)
from app.memory_consolidation.temporal import TemporalValidityEngine

logger = logging.getLogger("kairo.memory_consolidation.worker")


class AutonomousConsolidationWorker:
    """Performs scheduled or on-demand memory consolidation cycles."""

    def __init__(self, tenant_id: str = "default") -> None:
        self.tenant_id = tenant_id

    def run_sweep(self, memories: list[DurableMemory]) -> dict[str, Any]:
        """Execute a full idempotent consolidation sweep (Spec 26)."""
        logger.info("Starting autonomous memory consolidation sweep for tenant '%s'...", self.tenant_id)

        # 1. Evaluate temporal freshness and identify stale/expiring memories
        stale_count = 0
        expired_count = 0
        active_memories: list[DurableMemory] = []

        for m in memories:
            TemporalValidityEngine.refresh_memory_temporal_state(m)
            if m.freshness == FreshnessState.STALE:
                stale_count += 1
            elif m.freshness == FreshnessState.EXPIRED:
                expired_count += 1

            if m.status == MemoryLifecycleState.ACTIVE:
                active_memories.append(m)

        # 2. Sweep for contradictions among active memories
        contradictions_found: list[ContradictionReport] = []
        for i in range(len(active_memories)):
            for j in range(i + 1, len(active_memories)):
                rep = ContradictionEngine.analyze_conflict(active_memories[i], active_memories[j])
                if rep is not None:
                    contradictions_found.append(rep)

        # 3. Deduplication check
        dedup_count = 0
        for i in range(len(active_memories)):
            target = active_memories[i]
            others = active_memories[:i] + active_memories[i + 1 :]
            dup_match, score, match_type = DeduplicationEngine.find_duplicate(target.content, others)
            if dup_match is not None and score >= 0.95:
                dedup_count += 1

        # 4. Cluster unconsolidated episodic memories
        unconsolidated_episodic = [
            m
            for m in active_memories
            if m.memory_type == MemoryType.EPISODIC_MEMORY and m.status == MemoryLifecycleState.ACTIVE
        ]
        clusters = AutonomousConsolidationEngine.cluster_related_memories(unconsolidated_episodic)

        new_candidates: list[ConsolidationCandidate] = []
        new_consolidated_memories: list[DurableMemory] = []

        for cluster in clusters:
            # IDEMPOTENCY CHECK: Check if these source memories were already consolidated
            source_ids_set = set(m.memory_id for m in cluster)
            already_consolidated = any(
                set(m.structured_payload.get("consolidated_from_ids", [])) == source_ids_set
                for m in memories
                if m.status == MemoryLifecycleState.CONSOLIDATED
            )
            if already_consolidated:
                logger.info(
                    "Cluster with sources %s already consolidated; skipping for idempotency.",
                    sorted(source_ids_set),
                )
                continue

            cand, cons_mem = AutonomousConsolidationEngine.consolidate_cluster(
                cluster, tenant_id=self.tenant_id
            )
            new_candidates.append(cand)
            new_consolidated_memories.append(cons_mem)

            # Mark source cluster memories as consolidated
            for m in cluster:
                m.status = MemoryLifecycleState.CONSOLIDATED

            # Sync to Knowledge Graph
            KnowledgeGraphBridge.sync_memory_to_graph(cons_mem)

        sweep_summary = {
            "tenant_id": self.tenant_id,
            "scanned_memories": len(memories),
            "stale_memories_identified": stale_count,
            "expired_memories_identified": expired_count,
            "contradictions_detected": len(contradictions_found),
            "duplicates_detected": dedup_count,
            "new_consolidations_created": len(new_consolidated_memories),
            "new_candidates": [c.candidate_id for c in new_candidates],
            "new_consolidated_ids": [m.memory_id for m in new_consolidated_memories],
        }

        logger.info("Consolidation sweep completed: %s", sweep_summary)
        return sweep_summary

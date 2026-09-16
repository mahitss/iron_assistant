"""Derived knowledge and dependency cascade engine for KAIRO (Task 92 Phase 17).

Guarantees:
- Every derived fact explicitly references its parent memories and derivation method
- When parent knowledge is invalidated or becomes stale, invalidation propagates down the derivation DAG
- Prevents detached derived claims from silently remaining active
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.knowledge_consolidation.models import (
    DerivedKnowledgeModel,
    MemoryEntity,
    MemoryStatus,
    MemoryType,
    generate_id,
)

logger = logging.getLogger("kairo.knowledge_consolidation.derived")


class DerivedKnowledgeManager:
    """Manages lineage DAG for deduced facts and handles cascading invalidation."""

    def __init__(self) -> None:
        # derived_memory_id -> DerivedKnowledgeModel
        self._derived_records: dict[str, DerivedKnowledgeModel] = {}
        # parent_memory_id -> list of derived_memory_ids
        self._parent_to_derived_map: dict[str, list[str]] = {}

    def record_derivation(
        self,
        derived_memory: MemoryEntity,
        parent_memory_ids: list[str],
        derivation_method: str = "deductive_inference",
        assumptions: list[str] | None = None,
    ) -> DerivedKnowledgeModel:
        """Record derivation dependency between derived memory and parents."""
        derived_memory.type = MemoryType.DERIVED

        rec = DerivedKnowledgeModel(
            derived_memory_id=derived_memory.memory_id,
            parent_memory_ids=parent_memory_ids,
            derivation_method=derivation_method,
            assumptions=assumptions or [],
            confidence=derived_memory.confidence,
            invalidation_dependencies=parent_memory_ids,
            created_at=datetime.now(UTC),
        )

        self._derived_records[derived_memory.memory_id] = rec

        for pid in parent_memory_ids:
            if pid not in self._parent_to_derived_map:
                self._parent_to_derived_map[pid] = []
            if derived_memory.memory_id not in self._parent_to_derived_map[pid]:
                self._parent_to_derived_map[pid].append(derived_memory.memory_id)

        return rec

    def propagate_invalidation(
        self,
        parent_memory_id: str,
        memory_store: dict[str, MemoryEntity],
        new_parent_status: MemoryStatus,
    ) -> list[str]:
        """Cascade invalidation or staleness down the derivation tree.

        Returns: list of affected derived memory IDs.
        """
        affected_ids: list[str] = []
        child_ids = self._parent_to_derived_map.get(parent_memory_id, [])

        for cid in child_ids:
            derived_mem = memory_store.get(cid)
            if not derived_mem:
                continue

            if new_parent_status == MemoryStatus.INVALIDATED:
                if derived_mem.status != MemoryStatus.INVALIDATED:
                    derived_mem.status = MemoryStatus.INVALIDATED
                    affected_ids.append(cid)
                    logger.info("Propagated INVALIDATED to derived memory '%s' from parent '%s'", cid, parent_memory_id)
                    # Recursively cascade
                    affected_ids.extend(self.propagate_invalidation(cid, memory_store, MemoryStatus.INVALIDATED))

            elif new_parent_status == MemoryStatus.STALE:
                if derived_mem.status == MemoryStatus.ACTIVE:
                    derived_mem.status = MemoryStatus.STALE
                    affected_ids.append(cid)
                    logger.info("Propagated STALE to derived memory '%s' from parent '%s'", cid, parent_memory_id)
                    affected_ids.extend(self.propagate_invalidation(cid, memory_store, MemoryStatus.STALE))

        return affected_ids

    def get_derivation(self, derived_memory_id: str) -> DerivedKnowledgeModel | None:
        """Retrieve derivation record for a derived memory."""
        return self._derived_records.get(derived_memory_id)

    def get_dependencies(self, derived_memory_id: str) -> list[str]:
        """Get all parent memory IDs for a derived memory."""
        rec = self._derived_records.get(derived_memory_id)
        return rec.parent_memory_ids if rec else []

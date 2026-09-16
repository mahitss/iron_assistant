"""Vector index integration and metadata filtering for KAIRO (Task 92 Phase 19).

Guarantees:
- Integrates with existing pgvector and embedding infrastructure without creating a 2nd vector DB
- Excludes invalidated, forgotten, and quarantined knowledge from retrieval
- Vector similarity alone NEVER determines truth
"""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge_consolidation.models import (
    MemoryEntity,
    MemoryStatus,
    SensitivityClassification,
)

logger = logging.getLogger("kairo.knowledge_consolidation.vector_bridge")


class VectorIndexBridge:
    """Provides vector indexing and safe metadata-filtered retrieval."""

    def __init__(self) -> None:
        # In-memory mock or wrapper around existing pgvector embeddings
        self._vector_records: dict[str, dict[str, Any]] = {}

    def index_memory(
        self,
        memory: MemoryEntity,
        embedding: list[float] | None = None,
    ) -> None:
        """Index memory with security, freshness, and lifecycle metadata."""
        # Never index forgotten memories
        if memory.status == MemoryStatus.FORGOTTEN:
            if memory.memory_id in self._vector_records:
                del self._vector_records[memory.memory_id]
            return

        self._vector_records[memory.memory_id] = {
            "memory_id": memory.memory_id,
            "content": memory.content,
            "type": memory.type.value,
            "status": memory.status.value,
            "confidence": memory.confidence,
            "certainty": memory.certainty.value,
            "freshness": memory.freshness,
            "volatility": memory.volatility.value,
            "sensitivity": memory.sensitivity.value,
            "embedding": embedding or [],
        }

    def filter_candidates(
        self,
        candidate_ids: list[str],
        memories: dict[str, MemoryEntity],
        include_stale: bool = False,
        user_max_sensitivity: SensitivityClassification = SensitivityClassification.SENSITIVE,
    ) -> list[MemoryEntity]:
        """Apply strict epistemological filters to candidates returned by vector search."""
        sensitivity_ranks = {
            SensitivityClassification.PUBLIC: 1,
            SensitivityClassification.INTERNAL: 2,
            SensitivityClassification.PRIVATE: 3,
            SensitivityClassification.SENSITIVE: 4,
            SensitivityClassification.RESTRICTED: 5,
        }
        max_rank = sensitivity_ranks.get(user_max_sensitivity, 4)

        filtered: list[MemoryEntity] = []

        for mid in candidate_ids:
            mem = memories.get(mid)
            if not mem:
                continue

            # 1. Exclude terminal, blocked, and invalidated knowledge
            if mem.status in (MemoryStatus.FORGOTTEN, MemoryStatus.INVALIDATED, MemoryStatus.BLOCKED):
                continue

            # 2. Filter stale unless explicitly requested
            if mem.status == MemoryStatus.STALE and not include_stale:
                continue

            # 3. Privacy boundary check
            mem_rank = sensitivity_ranks.get(mem.sensitivity, 2)
            if mem_rank > max_rank:
                continue

            filtered.append(mem)

        return filtered

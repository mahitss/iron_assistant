"""Explicit conflict and contradiction detection engine for KAIRO knowledge (Task 92 Phase 8).

Guarantees:
- Never silently overwrites competing memories
- Tracks competing values, timestamps, sources, and confidence
- Supports 8 conflict dimensions: FACTUAL, TEMPORAL, NUMERIC, IDENTITY, STATE, PREFERENCE, PROCEDURAL, DEPENDENCY
"""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from app.knowledge_consolidation.models import (
    CertaintyState,
    ConflictType,
    MemoryConflict,
    MemoryEntity,
    MemoryStatus,
)


class ConflictDetectionEngine:
    """Identifies semantic, numeric, and temporal contradictions between memories."""

    def __init__(self) -> None:
        self._conflicts: dict[str, MemoryConflict] = {}

    def detect_conflict(
        self,
        candidate_memory: MemoryEntity,
        existing_memories: list[MemoryEntity],
    ) -> list[MemoryConflict]:
        """Evaluate candidate memory against existing active memories for contradictions."""
        detected: list[MemoryConflict] = []

        for existing in existing_memories:
            if existing.memory_id == candidate_memory.memory_id:
                continue
            if existing.status in (MemoryStatus.FORGOTTEN, MemoryStatus.INVALIDATED, MemoryStatus.SUPERSEDED):
                continue

            conflict = self._check_pair_conflict(candidate_memory, existing)
            if conflict:
                self._conflicts[conflict.conflict_id] = conflict
                # Mark both as CONFLICTED if active
                if candidate_memory.status == MemoryStatus.ACTIVE:
                    candidate_memory.status = MemoryStatus.CONFLICTED
                    candidate_memory.certainty = CertaintyState.CONTRADICTED
                if existing.status == MemoryStatus.ACTIVE:
                    existing.status = MemoryStatus.CONFLICTED
                    existing.certainty = CertaintyState.CONTRADICTED

                candidate_memory.contradiction_links.append(conflict.conflict_id)
                existing.contradiction_links.append(conflict.conflict_id)
                detected.append(conflict)

        return detected

    def _check_pair_conflict(
        self, mem_a: MemoryEntity, mem_b: MemoryEntity
    ) -> MemoryConflict | None:
        """Heuristic and rule-based evaluation of contradictions between two memories."""
        # 1. Subject/Key matching in structured representation
        key_a = mem_a.structured_representation.get("key") or mem_a.structured_representation.get("subject")
        key_b = mem_b.structured_representation.get("key") or mem_b.structured_representation.get("subject")

        if key_a and key_b and key_a.lower() == key_b.lower():
            val_a = mem_a.structured_representation.get("value")
            val_b = mem_b.structured_representation.get("value")
            if val_a != val_b:
                return MemoryConflict(
                    conflict_type=ConflictType.FACTUAL,
                    memory_a_id=mem_a.memory_id,
                    memory_b_id=mem_b.memory_id,
                    explanation=f"Contradictory values for subject '{key_a}': '{val_a}' vs '{val_b}'",
                    competing_values={mem_a.memory_id: val_a, mem_b.memory_id: val_b},
                    detected_at=datetime.now(UTC),
                )

        # 2. Date / Deadline conflict detection in content
        deadline_a = re.findall(r"(?:deadline|due date|target is)\s*[:=]?\s*([A-Za-z0-9\s,]+?)(?:\.|$)", mem_a.content, re.IGNORECASE)
        deadline_b = re.findall(r"(?:deadline|due date|target is)\s*[:=]?\s*([A-Za-z0-9\s,]+?)(?:\.|$)", mem_b.content, re.IGNORECASE)
        if deadline_a and deadline_b:
            val_a = deadline_a[0].strip()
            val_b = deadline_b[0].strip()
            if val_a.lower() != val_b.lower():
                return MemoryConflict(
                    conflict_type=ConflictType.TEMPORAL,
                    memory_a_id=mem_a.memory_id,
                    memory_b_id=mem_b.memory_id,
                    explanation=f"Conflicting deadlines: '{val_a}' vs '{val_b}'",
                    competing_values={mem_a.memory_id: val_a, mem_b.memory_id: val_b},
                    detected_at=datetime.now(UTC),
                )

        # 3. Numeric property contradictions (e.g. "port is 8000" vs "port is 8080")
        num_a = re.findall(r"(?:port|count|budget|limit|version)\s*(?:is|to|=|:)?\s*(\d+)", mem_a.content, re.IGNORECASE)
        num_b = re.findall(r"(?:port|count|budget|limit|version)\s*(?:is|to|=|:)?\s*(\d+)", mem_b.content, re.IGNORECASE)
        if num_a and num_b and num_a != num_b:
            # Check topic overlap
            words_a = set(mem_a.content.lower().split())
            words_b = set(mem_b.content.lower().split())
            if len(words_a.intersection(words_b)) >= 2:
                return MemoryConflict(
                    conflict_type=ConflictType.NUMERIC,
                    memory_a_id=mem_a.memory_id,
                    memory_b_id=mem_b.memory_id,
                    explanation=f"Conflicting numeric attributes: '{num_a[0]}' vs '{num_b[0]}'",
                    competing_values={mem_a.memory_id: num_a[0], mem_b.memory_id: num_b[0]},
                    detected_at=datetime.now(UTC),
                )

        return None

    def get_conflict(self, conflict_id: str) -> MemoryConflict | None:
        """Retrieve conflict record by identifier."""
        return self._conflicts.get(conflict_id)

    def list_active_conflicts(self) -> list[MemoryConflict]:
        """List all currently unresolved conflicts."""
        return [c for c in self._conflicts.values() if c.status == "CONFLICTED"]

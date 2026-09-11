"""Temporal validity, freshness, and retrieval decay engine for Task 68.

Enforces:
- Spec 13: Temporal validity tracking (observed_at, valid_from, valid_until, expires_at)
- Spec 14: Type-dependent freshness policies (server metrics decay rapidly; semantic facts remain stable)
- Spec 15: Retrieval priority decay without inflating truth confidence
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.memory_consolidation.schemas import (
    DurableMemory,
    FreshnessState,
    MemoryLifecycleState,
    MemoryType,
)

logger = logging.getLogger("kairo.memory_consolidation.temporal")

# Type-dependent TTL freshness policies in seconds (Spec 14)
FRESHNESS_POLICIES: dict[MemoryType, dict[str, float]] = {
    MemoryType.WORKING_MEMORY: {"aging_seconds": 3600, "stale_seconds": 7200},  # 1-2 hours
    MemoryType.EPISODIC_MEMORY: {"aging_seconds": 86400 * 7, "stale_seconds": 86400 * 30},  # 7-30 days
    MemoryType.SEMANTIC_MEMORY: {"aging_seconds": 86400 * 90, "stale_seconds": 86400 * 365},  # 3-12 months
    MemoryType.PROCEDURAL_MEMORY: {"aging_seconds": 86400 * 60, "stale_seconds": 86400 * 180},  # 2-6 months
    MemoryType.EXECUTIVE_MEMORY: {"aging_seconds": 86400 * 120, "stale_seconds": 86400 * 365},  # 4-12 months
    MemoryType.PROSPECTIVE_MEMORY: {"aging_seconds": 86400 * 3, "stale_seconds": 86400 * 14},  # 3-14 days
    MemoryType.QUARANTINED_MEMORY: {"aging_seconds": 86400, "stale_seconds": 86400 * 3},  # 1-3 days
}


class TemporalValidityEngine:
    """Evaluates temporal state, freshness decay, and historical validity windows."""

    @classmethod
    def evaluate_freshness(
        cls, memory: DurableMemory, reference_time: datetime | None = None
    ) -> FreshnessState:
        """Calculate freshness state based on memory type and elapsed time since observation (Spec 14)."""
        now = reference_time or datetime.now(UTC)

        # 1. Explicit expiration check
        if memory.expires_at and now >= memory.expires_at:
            return FreshnessState.EXPIRED

        # 2. Check valid_until boundary
        if memory.valid_until and now > memory.valid_until:
            return FreshnessState.SUPERSEDED

        # 3. Type-specific decay evaluation
        policy = FRESHNESS_POLICIES.get(
            memory.memory_type,
            {"aging_seconds": 86400 * 14, "stale_seconds": 86400 * 60},
        )

        elapsed = (now - memory.observed_at).total_seconds()
        if elapsed < 0:
            return FreshnessState.FRESH

        if elapsed >= policy["stale_seconds"]:
            return FreshnessState.STALE
        elif elapsed >= policy["aging_seconds"]:
            return FreshnessState.AGING

        return FreshnessState.FRESH

    @classmethod
    def is_valid_at(cls, memory: DurableMemory, target_time: datetime) -> bool:
        """Verify whether memory was temporally valid at a specific point in time (Spec 13)."""
        if target_time < memory.valid_from:
            return False
        if memory.valid_until and target_time > memory.valid_until:
            return False
        if memory.expires_at and target_time > memory.expires_at:
            return False
        return True

    @classmethod
    def calculate_decay_priority(cls, memory: DurableMemory, reference_time: datetime | None = None) -> float:
        """Compute retrieval priority score using recency, importance, and confidence (Spec 15).

        CRITICAL INVARIANT: High access frequency or recent retrieval decays or refreshes priority,
        but NEVER inflates empirical truth confidence.
        """
        now = reference_time or datetime.now(UTC)
        freshness = cls.evaluate_freshness(memory, reference_time=now)

        base_score = (memory.importance * 0.4) + (memory.confidence * 0.4) + (memory.relevance * 0.2)

        if freshness == FreshnessState.FRESH:
            freshness_multiplier = 1.0
        elif freshness == FreshnessState.AGING:
            freshness_multiplier = 0.8
        elif freshness == FreshnessState.STALE:
            freshness_multiplier = 0.4
        elif freshness == FreshnessState.SUPERSEDED:
            freshness_multiplier = 0.2
        else:  # EXPIRED
            freshness_multiplier = 0.05

        return round(base_score * freshness_multiplier, 4)

    @classmethod
    def refresh_memory_temporal_state(cls, memory: DurableMemory) -> None:
        """Update memory's internal freshness and state flags."""
        new_freshness = cls.evaluate_freshness(memory)
        memory.freshness = new_freshness

        if new_freshness == FreshnessState.EXPIRED and memory.status != MemoryLifecycleState.EXPIRED:
            memory.status = MemoryLifecycleState.EXPIRED
        elif new_freshness == FreshnessState.STALE and memory.status == MemoryLifecycleState.ACTIVE:
            memory.status = MemoryLifecycleState.STALE

"""Temporal knowledge, validity intervals, and freshness policies for KAIRO (Task 92 Phase 10 & 11).

Guarantees:
- Distinguishes historically valid facts from currently active truth
- Enforces volatility-based decay and staleness identification
- Prevents stale information from being presented as current reality
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.knowledge_consolidation.models import (
    MemoryEntity,
    MemoryStatus,
    VolatilityClass,
)

# Configurable volatility staleness thresholds
VOLATILITY_THRESHOLDS: dict[VolatilityClass, timedelta] = {
    VolatilityClass.HIGH: timedelta(hours=2),
    VolatilityClass.MEDIUM: timedelta(days=7),
    VolatilityClass.LOW: timedelta(days=90),
}


class TemporalKnowledgeEngine:
    """Evaluates temporal validity windows and freshness state."""

    def is_currently_valid(self, memory: MemoryEntity, at_time: datetime | None = None) -> bool:
        """Check if memory falls within valid_from and valid_until boundaries."""
        t = at_time or datetime.now(UTC)

        # Before validity starts
        if memory.valid_from and t < memory.valid_from:
            return False

        # After validity expired
        if memory.valid_until and t > memory.valid_until:
            return False

        return True

    def evaluate_staleness(self, memory: MemoryEntity, at_time: datetime | None = None) -> tuple[bool, str]:
        """Determine whether memory has exceeded its volatility staleness threshold.

        Returns: (is_stale: bool, freshness_label: str)
        """
        t = at_time or datetime.now(UTC)

        # If explicitly expired or valid_until in the past
        if memory.valid_until and t > memory.valid_until:
            return True, "EXPIRED"

        threshold = VOLATILITY_THRESHOLDS.get(memory.volatility, timedelta(days=7))
        reference_time = memory.last_validated_at or memory.observed_at or memory.created_at

        elapsed = t - reference_time
        if elapsed > threshold:
            return True, "STALE"

        if elapsed > (threshold * 0.75):
            return False, "AGING"

        return False, "FRESH"

    def apply_staleness_check(self, memory: MemoryEntity) -> MemoryEntity:
        """Update memory status to STALE if decayed and currently ACTIVE."""
        is_stale, freshness_label = self.evaluate_staleness(memory)
        memory.freshness = freshness_label

        if is_stale and memory.status == MemoryStatus.ACTIVE:
            memory.status = MemoryStatus.STALE

        return memory

    def reconstruct_historical_snapshot(
        self, memories: list[MemoryEntity], target_time: datetime
    ) -> list[MemoryEntity]:
        """Retrieve the state of memories as they existed at a specific historical point in time."""
        snapshot: list[MemoryEntity] = []

        for m in memories:
            # Memory must have existed at target_time
            if m.created_at > target_time:
                continue

            # Must be within its temporal validity window at target_time
            if self.is_currently_valid(m, at_time=target_time):
                snapshot.append(m)

        return snapshot

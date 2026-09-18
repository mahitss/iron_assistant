"""Diff Engine for Task 111:
Authoritative "What Changed?" calculation across states, snapshots, and checkpoints.

Strict Invariants:
- SNAPSHOT != REALITY
- HISTORICAL STATE != CURRENT STATE
- RECONSTRUCTION != CERTAINTY
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.temporal.domain import (
    AttributionCertainty,
    ChangeCategory,
    ChangeRecord,
    ChangeSet,
    ChangeSummary,
    TemporalEntityType,
    gen_temporal_id,
    utc_now,
)


class DiffEngine:
    """Computes semantic deltas between states, entity versions, and checkpoints."""

    DEGRADED_KEYWORDS = ("degraded", "failed", "offline", "unhealthy", "at_risk", "error", "critical")
    RECOVERED_KEYWORDS = ("recovered", "healthy", "ready", "online", "active", "synchronized", "succeeded")

    @classmethod
    def compute_diff(
        cls,
        state_a: Dict[str, Any],
        state_b: Dict[str, Any],
        from_reference: str = "T1",
        to_reference: str = "T2",
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        entity_id: str = "global",
        entity_type: TemporalEntityType = TemporalEntityType.SYSTEM,
    ) -> ChangeSet:
        """Computes semantic delta between two state dicts."""
        t_from = from_time or utc_now()
        t_to = to_time or utc_now()

        changes: List[ChangeRecord] = []

        keys_a = set(state_a.keys())
        keys_b = set(state_b.keys())

        # Added keys
        for k in sorted(keys_b - keys_a):
            val_b = state_b[k]
            changes.append(
                ChangeRecord(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    attribute_path=k,
                    previous_value=None,
                    new_value=val_b,
                    category=ChangeCategory.ADDED,
                    timestamp=t_to,
                    impact_level=cls._assess_impact(k, val_b),
                )
            )

        # Removed keys
        for k in sorted(keys_a - keys_b):
            val_a = state_a[k]
            changes.append(
                ChangeRecord(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    attribute_path=k,
                    previous_value=val_a,
                    new_value=None,
                    category=ChangeCategory.REMOVED,
                    timestamp=t_to,
                    impact_level="MEDIUM",
                )
            )

        # Modified keys
        for k in sorted(keys_a & keys_b):
            val_a = state_a[k]
            val_b = state_b[k]

            if val_a != val_b:
                category = cls._classify_change(val_a, val_b) or ChangeCategory.MODIFIED
                changes.append(
                    ChangeRecord(
                        entity_id=entity_id,
                        entity_type=entity_type,
                        attribute_path=k,
                        previous_value=val_a,
                        new_value=val_b,
                        category=category,
                        timestamp=t_to,
                        impact_level=cls._assess_impact(k, val_b),
                    )
                )

        # Build ChangeSet counts
        added_cnt = sum(1 for c in changes if c.category == ChangeCategory.ADDED)
        removed_cnt = sum(1 for c in changes if c.category == ChangeCategory.REMOVED)
        mod_cnt = sum(1 for c in changes if c.category == ChangeCategory.MODIFIED)
        deg_cnt = sum(1 for c in changes if c.category == ChangeCategory.DEGRADED)
        rec_cnt = sum(1 for c in changes if c.category == ChangeCategory.RECOVERED)
        unatt_cnt = sum(1 for c in changes if c.attribution == AttributionCertainty.UNATTRIBUTED)

        return ChangeSet(
            from_reference=from_reference,
            to_reference=to_reference,
            from_time=t_from,
            to_time=t_to,
            changes=changes,
            added_count=added_cnt,
            removed_count=removed_cnt,
            modified_count=mod_cnt,
            degraded_count=deg_cnt,
            recovered_count=rec_cnt,
            unattributed_count=unatt_cnt,
        )

    @classmethod
    def generate_summary(cls, changeset: ChangeSet, scope: str = "DEFAULT") -> ChangeSummary:
        """Generates a compact natural-language summary of a changeset for context packing."""
        critical_changes = []
        has_degraded = False

        for chg in changeset.changes:
            if chg.category == ChangeCategory.DEGRADED or chg.impact_level == "CRITICAL":
                critical_changes.append(f"{chg.attribute_path}: {chg.previous_value} -> {chg.new_value}")
                has_degraded = True

        window_sec = (changeset.to_time - changeset.from_time).total_seconds()
        headline = (
            f"{len(changeset.changes)} changes detected between {changeset.from_reference} and {changeset.to_reference} "
            f"({changeset.degraded_count} degraded, {changeset.recovered_count} recovered)."
        )

        return ChangeSummary(
            scope=scope,
            time_window_seconds=max(0.0, window_sec),
            headline=headline,
            total_changes=len(changeset.changes),
            critical_changes=critical_changes[:5],
            has_degraded_capabilities=has_degraded,
            has_unattributed_changes=changeset.unattributed_count > 0,
        )

    @classmethod
    def _classify_change(cls, val_a: Any, val_b: Any) -> Optional[ChangeCategory]:
        """Examines string/state transitions for degradation or recovery."""
        str_b = str(val_b).lower()
        if any(k in str_b for k in cls.DEGRADED_KEYWORDS):
            return ChangeCategory.DEGRADED
        if any(k in str_b for k in cls.RECOVERED_KEYWORDS):
            return ChangeCategory.RECOVERED
        return None

    @staticmethod
    def _assess_impact(key: str, val: Any) -> str:
        key_lower = key.lower()
        if any(k in key_lower for k in ("security", "health", "lifecycle", "status", "auth")):
            return "HIGH"
        if any(k in key_lower for k in ("emergency", "critical", "panic")):
            return "CRITICAL"
        return "LOW"

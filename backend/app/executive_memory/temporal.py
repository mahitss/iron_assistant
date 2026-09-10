"""Temporal intelligence, deterministic event ordering, collision resolution, and datetime normalization (INVARIANTS 12, 13, 236)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class TemporalEngine:
    """Manages authoritative timestamps, collision resolution, and chronological sorting."""

    @staticmethod
    def ensure_utc(dt: datetime | str | None) -> datetime:
        """Converts any datetime or ISO string to UTC-aware datetime."""
        if dt is None:
            return datetime.now(UTC)
        if isinstance(dt, str):
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

    @classmethod
    def sort_events_deterministically(cls, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """INVARIANT 12 & 236: Uses authoritative timestamps with deterministic tie-breaking.
        Tie-breaking uses (timestamp, event_id).
        """
        def sort_key(e: dict[str, Any]) -> tuple[datetime, str]:
            ts = cls.ensure_utc(e.get("timestamp"))
            eid = str(e.get("event_id", ""))
            return (ts, eid)

        return sorted(events, key=sort_key)

    @classmethod
    def detect_timestamp_conflicts(
        cls,
        event_a: dict[str, Any],
        event_b: dict[str, Any],
    ) -> bool:
        """INVARIANT 13: Identifies contradictory event claims sharing identical timestamps."""
        ts_a = cls.ensure_utc(event_a.get("timestamp"))
        ts_b = cls.ensure_utc(event_b.get("timestamp"))
        if ts_a == ts_b and event_a.get("event_type") != event_b.get("event_type"):
            # E.g. COMPLETED vs FAILED at the exact same moment
            conflicting_pairs = [
                ("COMPLETED", "FAILED"),
                ("BLOCKED", "UNBLOCKED"),
                ("APPROVED", "REJECTED"),
                ("PAUSED", "RESUMED"),
            ]
            t1, t2 = event_a.get("event_type"), event_b.get("event_type")
            for p1, p2 in conflicting_pairs:
                if (t1 == p1 and t2 == p2) or (t1 == p2 and t2 == p1):
                    return True
        return False

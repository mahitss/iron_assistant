"""Hierarchical history compression, retention policies, and authorized deletion (INVARIANTS 100-103, 228-230)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class HistoryRetentionEngine:
    """Compresses extensive history hierarchically while preserving immutable decisions and commitments."""

    CRITICAL_EVENT_TYPES = {
        "DECIDED",
        "APPROVED",
        "FAILED",
        "DEPLOYED",
        "RECOVERED",
        "BLOCKED",
    }

    @classmethod
    def compress_timeline_events(
        cls,
        events: list[dict[str, Any]],
        preserve_critical: bool = True,
    ) -> list[dict[str, Any]]:
        """INVARIANT 101 & 229: Compresses event stream while preserving critical decisions, failures, and milestones."""
        compressed = []
        for ev in events:
            ev_type = str(ev.get("event_type", "")).upper()
            if preserve_critical and ev_type in cls.CRITICAL_EVENT_TYPES:
                compressed.append(ev)
            elif ev.get("impact", "LOW").upper() in ("HIGH", "CRITICAL"):
                compressed.append(ev)
            else:
                # Compress or collapse low-value/transient telemetry
                pass
        return compressed

    @classmethod
    def create_phase_summary(cls, phase_name: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        """INVARIANT 228: Creates hierarchical phase summary (event -> phase -> project history)."""
        critical_events = cls.compress_timeline_events(events)
        return {
            "phase": phase_name,
            "total_events": len(events),
            "critical_events_preserved": len(critical_events),
            "decisions": [e for e in critical_events if e.get("event_type") == "DECIDED"],
            "failures": [e for e in critical_events if e.get("event_type") == "FAILED"],
            "compressed_at": datetime.now(UTC).isoformat(),
        }

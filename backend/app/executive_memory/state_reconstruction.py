"""Historical state reconstruction and as-of queries without future leakage (INVARIANTS 19-21, 26, 135)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.executive_memory.safety import ExecutiveSafetyGuard, TemporalLeakageError
from app.executive_memory.schemas import ExecutiveStateScope, ExecutiveStateSchema
from app.executive_memory.temporal import TemporalEngine
from app.executive_memory.timeline import TimelineEngine


class StateReconstructor:
    """Reconstructs historical executive state strictly bounded by historical cutoff timestamps."""

    def __init__(self, timeline_engine: TimelineEngine) -> None:
        self.timeline_engine = timeline_engine

    def reconstruct_state_as_of(
        self,
        cutoff_timestamp: datetime,
        project_id: str | None = None,
        scope: ExecutiveStateScope = ExecutiveStateScope.PROJECT,
        authoritative_snapshots: list[dict[str, Any]] | None = None,
    ) -> ExecutiveStateSchema:
        """INVARIANT 20 & 21: Reconstructs state using events available strictly up to cutoff_timestamp.
        Guarantees zero future data leakage.
        """
        cutoff_utc = TemporalEngine.ensure_utc(cutoff_timestamp)

        # 1. Retrieve all timeline events occurring at or before cutoff
        events = self.timeline_engine.get_events_as_of(cutoff_utc, project_id=project_id)

        # 2. Strict verification against future leakage
        for ev in events:
            ExecutiveSafetyGuard.assert_no_temporal_leakage(ev.timestamp, cutoff_utc)

        # Check snapshots if provided
        active_projects: list[dict[str, Any]] = []
        recent_decisions: list[dict[str, Any]] = []
        blockers: list[Any] = []
        open_loops: list[Any] = []

        # Reconstruct lifecycle from events sequence
        lifecycle_status = "IDEA"
        for ev in events:
            if ev.event_type == "STARTED":
                lifecycle_status = "ACTIVE"
            elif ev.event_type == "BLOCKED":
                lifecycle_status = "BLOCKED"
            elif ev.event_type == "UNBLOCKED":
                lifecycle_status = "ACTIVE"
            elif ev.event_type == "PAUSED":
                lifecycle_status = "PAUSED"
            elif ev.event_type == "RESUMED":
                lifecycle_status = "ACTIVE"
            elif ev.event_type == "COMPLETED":
                lifecycle_status = "COMPLETED"
            elif ev.event_type == "CANCELLED":
                lifecycle_status = "CANCELLED"

            if ev.event_type == "DECIDED":
                recent_decisions.append({
                    "decision_id": ev.event_id,
                    "description": ev.description_reference,
                    "timestamp": ev.timestamp.isoformat(),
                    "actor": ev.actor,
                })

        if project_id:
            active_projects.append({
                "project_id": project_id,
                "reconstructed_status": lifecycle_status,
                "as_of": cutoff_utc.isoformat(),
            })

        return ExecutiveStateSchema(
            scope=scope,
            scope_id=project_id,
            timestamp=cutoff_utc,
            active_projects=active_projects,
            recent_decisions=recent_decisions,
            blockers=blockers,
            open_loops=open_loops,
            confidence=0.9 if events else 0.5,
            provenance={
                "reconstruction_method": "AS_OF_EVENT_FOLD",
                "cutoff_timestamp": cutoff_utc.isoformat(),
                "event_count": len(events),
            },
        )

    def reconstruct_as_of(
        self,
        as_of: datetime,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANTS 19-21: Reconstructs state as of a historical date without future leakage."""
        cutoff_utc = TemporalEngine.ensure_utc(as_of)
        events = self.timeline_engine.get_events_as_of(cutoff_utc, project_id=project_id)
        applied_events = []
        for ev in events:
            ExecutiveSafetyGuard.assert_no_temporal_leakage(ev.timestamp, cutoff_utc)
            applied_events.append({
                "event_id": ev.event_id,
                "event_type": ev.event_type if isinstance(ev.event_type, str) else ev.event_type.value,
                "timestamp": ev.timestamp.isoformat(),
                "description": ev.description_reference,
            })
        recon_state = self.reconstruct_state_as_of(cutoff_timestamp=as_of, project_id=project_id)
        return {
            "as_of": cutoff_utc.isoformat(),
            "project_id": project_id,
            "events_applied_count": len(applied_events),
            "applied_events": applied_events,
            "active_tasks": recon_state.active_tasks,
            "decisions_made": recon_state.recent_decisions,
            "state": recon_state.model_dump(),
        }

"""Tests for Timeline Intelligence, Deduplication, Historical As-Of Reconstruction, and Future Leakage Blocking."""

from datetime import UTC, datetime, timedelta
import pytest

from app.executive_memory.safety import ExecutiveSafetyGuard, TemporalLeakageError
from app.executive_memory.schemas import TimelineEventType
from app.executive_memory.snapshots import SnapshotManager
from app.executive_memory.state_reconstruction import StateReconstructor
from app.executive_memory.temporal import TemporalEngine
from app.executive_memory.timeline import TimelineEngine


def test_timeline_event_recording_and_deduplication():
    """INVARIANTS 9-13, 130: Ingest events with authoritative UTC timestamps and deduplicate identical events."""
    engine = TimelineEngine()
    t0 = datetime(2026, 9, 10, 10, 0, 0, tzinfo=UTC)

    ev1 = engine.record_event(
        event_type=TimelineEventType.STARTED,
        source="projects",
        description_reference="Project kickoff initialized",
        project_id="proj_1",
        timestamp=t0,
    )
    assert ev1.event_id is not None
    assert ev1.event_type == TimelineEventType.STARTED

    # Record duplicate identical event
    ev2 = engine.record_event(
        event_type=TimelineEventType.STARTED,
        source="projects",
        description_reference="Project kickoff initialized",
        project_id="proj_1",
        timestamp=t0,
    )
    # Deduplication ensures we return the existing event without adding duplicate history
    assert ev2.event_id == ev1.event_id
    events = engine.list_events(project_id="proj_1")
    assert len(events) == 1


def test_chronological_ordering():
    """INVARIANT 12: Timeline order uses authoritative timestamps with deterministic sorting."""
    engine = TimelineEngine()
    t1 = datetime(2026, 9, 10, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 10, 11, 0, 0, tzinfo=UTC)
    t3 = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)

    # Ingest out of order
    engine.record_event(TimelineEventType.TASK_CREATED, "tasks", "Task 3", "p1", timestamp=t3)
    engine.record_event(TimelineEventType.CREATED, "projects", "Project 1", "p1", timestamp=t1)
    engine.record_event(TimelineEventType.TASK_CREATED, "tasks", "Task 2", "p1", timestamp=t2)

    events = engine.list_events(project_id="p1")
    assert len(events) == 3
    assert events[0].timestamp == t1
    assert events[1].timestamp == t2
    assert events[2].timestamp == t3


def test_as_of_historical_reconstruction_no_future_leakage():
    """INVARIANTS 19-21: Reconstruct state using events available up to timestamp X; zero future leakage."""
    engine = TimelineEngine()
    reconstructor = StateReconstructor(timeline_engine=engine)

    t_past = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    t_target = datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC)
    t_future = datetime(2026, 9, 10, 15, 0, 0, tzinfo=UTC)

    # Past events
    engine.record_event(TimelineEventType.CREATED, "projects", "Init Repo", "proj_x", timestamp=t_past)
    engine.record_event(TimelineEventType.DECIDED, "decisions", "Choose SQLite", "proj_x", timestamp=t_past + timedelta(days=1))

    # Future events (relative to t_target)
    engine.record_event(TimelineEventType.DEPLOYED, "automation", "Deploy to Prod", "proj_x", timestamp=t_future)
    engine.record_event(TimelineEventType.FAILED, "runtime", "Memory OOM crash", "proj_x", timestamp=t_future + timedelta(hours=1))

    # Reconstruct state as-of t_target
    recon = reconstructor.reconstruct_as_of(as_of=t_target, project_id="proj_x")

    assert recon["events_applied_count"] == 2
    # Events list must only have events <= t_target
    for ev in recon["applied_events"]:
        assert ev["timestamp"] <= t_target.isoformat()

    # Verify future events are strictly absent
    applied_descriptions = [e["description"] for e in recon["applied_events"]]
    assert "Init Repo" in applied_descriptions
    assert "Choose SQLite" in applied_descriptions
    assert "Deploy to Prod" not in applied_descriptions
    assert "Memory OOM crash" not in applied_descriptions


def test_future_leakage_safety_guard():
    """INVARIANT 21: ExecutiveSafetyGuard strictly raises TemporalLeakageError when future data is detected."""
    t_cutoff = datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC)
    leaked_future_event = {
        "event_id": "ev_future_1",
        "timestamp": datetime(2026, 9, 8, 10, 0, 0, tzinfo=UTC).isoformat(),
        "description": "Accidental future leak",
    }

    with pytest.raises(TemporalLeakageError) as exc_info:
        ExecutiveSafetyGuard.validate_no_temporal_leakage(
            as_of=t_cutoff,
            reconstructed_events=[leaked_future_event],
        )
    assert "Temporal leakage detected" in str(exc_info.value)


def test_snapshot_invalidation_on_material_change():
    """INVARIANTS 14-18: Material state changes invalidate relevant snapshots."""
    snap_mgr = SnapshotManager()
    snap = snap_mgr.create_snapshot(
        project_id="proj_1",
        state={"status": "ACTIVE", "tasks_count": 5},
        source_refs=["db:tasks:5"],
    )
    assert snap.is_stale is False

    # Invalidate on material change
    invalidated = snap_mgr.invalidate_snapshot(project_id="proj_1", reason="New task completed")
    assert invalidated is not None
    assert invalidated.is_stale is True

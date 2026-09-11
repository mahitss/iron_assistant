"""Tests for Foresight Entities, Freshness, and Temporal Versioning (Task 65)."""

from datetime import datetime, timedelta, timezone

from app.foresight.entities import ForesightEntityManager
from app.foresight.schemas import (
    ForesightEntity,
    StateAuthority,
    UncertaintyGrade,
    WorldScope,
)
from app.foresight.temporal import TemporalWorldManager


def test_entity_creation_and_unknown_invariant():
    """Verify UNKNOWN != HEALTHY invariant (Spec 10, 19).

    Unobserved entities must default to UNKNOWN, never assume HEALTHY.
    """
    manager = ForesightEntityManager()
    ent = manager.upsert_entity(
        entity_id="node-test-01",
        name="Telemetry Consumer",
        entity_type="service",
        state="UNKNOWN",
        scope=WorldScope.INFRASTRUCTURE,
        confidence=0.5,
    )

    assert ent.entity_id == "node-test-01"
    assert ent.state == "UNKNOWN"
    assert ent.uncertainty in (UncertaintyGrade.UNKNOWN, UncertaintyGrade.UNCERTAIN, UncertaintyGrade.LIKELY)
    assert ent.authority == StateAuthority.OBSERVED
    assert not ent.is_stale


def test_freshness_evaluation_and_staleness_flagging():
    """Verify STALE != CURRENT invariant (Spec 17, 18).

    Entities past their TTL must be automatically flagged as stale.
    """
    manager = ForesightEntityManager()
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(hours=3)

    # Upsert with valid_from in past
    manager.upsert_entity(
        entity_id="node-stale-01",
        name="Periodic Health Probe",
        entity_type="service",
        state="HEALTHY",
        valid_from=old_time,
    )

    # get_entity evaluates freshness dynamically
    checked = manager.get_entity("node-stale-01")
    assert checked is not None
    assert checked.is_stale is True


def test_temporal_state_versioning_and_reconstruction():
    """Verify historical state reconstruction at arbitrary time T (Spec 14, 15).

    HISTORICAL STATE != CURRENT STATE (Spec 16).
    """
    temp_manager = TemporalWorldManager()
    eid = "service-db-primary"
    t0 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    temp_manager.record_state_transition(eid, "STARTING", observed_at=t0)
    temp_manager.record_state_transition(eid, "HEALTHY", observed_at=t1)
    temp_manager.record_state_transition(eid, "DEGRADED", observed_at=t2)

    # Historical queries
    assert temp_manager.get_state_at_time(eid, t0 + timedelta(minutes=15)) == "STARTING"
    assert temp_manager.get_state_at_time(eid, t1 + timedelta(minutes=30)) == "HEALTHY"
    assert temp_manager.get_state_at_time(eid, t2 + timedelta(minutes=10)) == "DEGRADED"


def test_late_arriving_events_preserve_temporal_order():
    """Verify late-arriving events update historical truth without corrupting sequence (Spec 15)."""
    temp_manager = TemporalWorldManager()
    eid = "order-processor"

    t_early = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t_mid = datetime(2026, 9, 1, 10, 30, 0, tzinfo=timezone.utc)
    t_late = datetime(2026, 9, 1, 11, 0, 0, tzinfo=timezone.utc)

    # Received out of order
    temp_manager.record_state_transition(eid, "IDLE", observed_at=t_early)
    temp_manager.record_state_transition(eid, "BUSY", observed_at=t_late)
    # Late arrival inserting at t_mid
    temp_manager.ingest_out_of_order_event(eid, "DRAINING", event_timestamp=t_mid)

    history = temp_manager.get_history(eid)
    # Must be sorted by observed_at
    assert [r.state for r in history] == ["IDLE", "DRAINING", "BUSY"]
    assert (
        temp_manager.get_state_at_time(eid, datetime(2026, 9, 1, 10, 45, tzinfo=timezone.utc)) == "DRAINING"
    )


def test_world_diff_computation():
    """Verify structural diff calculation between two world state points (Spec 15)."""
    temp_manager = TemporalWorldManager()

    e1_a = ForesightEntity(entity_id="s1", type="service", name="Service 1", state="HEALTHY")
    e2_a = ForesightEntity(entity_id="s2", type="service", name="Service 2", state="HEALTHY")

    e1_b = ForesightEntity(entity_id="s1", type="service", name="Service 1", state="DEGRADED")
    e3_b = ForesightEntity(entity_id="s3", type="service", name="Service 3", state="HEALTHY")

    diff = temp_manager.compute_diff(
        entities_a={"s1": e1_a, "s2": e2_a},
        entities_b={"s1": e1_b, "s3": e3_b},
        relationships_a={},
        relationships_b={},
    )

    assert "s3" in diff.added_entities
    assert "s2" in diff.removed_entities
    assert "s1" in diff.changed_states
    assert diff.changed_states["s1"]["before"] == "HEALTHY"
    assert diff.changed_states["s1"]["after"] == "DEGRADED"

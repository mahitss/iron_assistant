"""Tests for event-driven synchronization and periodic reconciliation (Task 32, Spec 49-51, 58-62, 88)."""

from datetime import UTC, datetime, timedelta
import pytest

from app.world.entities import EntityType, WorldEntitySchema
from app.world.state import DeviceState, RepositoryState, TaskOperationalState
from app.world.synchronizer import WorldSynchronizer


def test_synchronizer_device_lifecycle():
    """Verify device event stream transitions: connected -> disconnected -> revoked (Spec 49, 82)."""
    sync = WorldSynchronizer()
    entities_by_id: dict[str, WorldEntitySchema] = {}

    # 1. Device connects
    e1 = sync.process_event("device.connected", {"user_id": "u1", "device_id": "dev_100", "device_name": "Laptop"}, entities_by_id)
    assert e1 is not None
    assert e1.state == DeviceState.CONNECTED.value
    entities_by_id[e1.id] = e1

    # 2. Device disconnects
    e2 = sync.process_event("device.disconnected", {"user_id": "u1", "device_id": "dev_100"}, entities_by_id)
    assert e2.state == DeviceState.DISCONNECTED.value

    # 3. Device revoked
    e3 = sync.process_event("device.revoked", {"user_id": "u1", "device_id": "dev_100"}, entities_by_id)
    assert e3.state == DeviceState.REVOKED.value

    # 4. Old or malicious connected event arrives -> rejected (Spec 82, 131)
    e4 = sync.process_event("device.connected", {"user_id": "u1", "device_id": "dev_100"}, entities_by_id)
    assert e4.state == DeviceState.REVOKED.value


def test_synchronizer_task_lifecycle():
    """Verify task event stream transitions: created -> started -> completed (Spec 51, 84)."""
    sync = WorldSynchronizer()
    entities_by_id: dict[str, WorldEntitySchema] = {}

    e1 = sync.process_event("task.created", {"user_id": "u1", "task_id": "task_abc", "objective": "Investigate DB"}, entities_by_id)
    assert e1.state == TaskOperationalState.QUEUED.value
    entities_by_id[e1.id] = e1

    e2 = sync.process_event("task.started", {"user_id": "u1", "task_id": "task_abc"}, entities_by_id)
    assert e2.state == TaskOperationalState.RUNNING.value

    e3 = sync.process_event("task.completed", {"user_id": "u1", "task_id": "task_abc"}, entities_by_id)
    assert e3.state == TaskOperationalState.COMPLETED.value


def test_synchronizer_github_ci_events():
    """Verify GitHub CI failure and recovery events (Spec 50, 76, 134)."""
    sync = WorldSynchronizer()
    entities_by_id: dict[str, WorldEntitySchema] = {}

    # CI failed
    e1 = sync.process_event(
        "github.ci.failed",
        {"user_id": "u1", "repo_name": "kairo-core", "repository_id": "repo_1", "head_commit": "c111"},
        entities_by_id,
    )
    assert e1 is not None
    assert e1.metadata["ci_status"] == "FAILED"
    entities_by_id[e1.id] = e1

    # CI recovered
    e2 = sync.process_event(
        "github.ci.recovered",
        {"user_id": "u1", "repo_name": "kairo-core", "repository_id": "repo_1", "head_commit": "c222"},
        entities_by_id,
    )
    assert e2.metadata["ci_status"] == "PASSED"
    assert e2.metadata["head_commit"] == "c222"


def test_reconciliation_marks_stale_without_loss(sample_world_graph=None):
    """Verify periodic reconciliation marks expired entities as STALE rather than dropping or pretending healthy (Spec 62, 135)."""
    sync = WorldSynchronizer()
    now = datetime.now(UTC)

    # 10 minutes old device (TTL is 60s -> definitely stale)
    old_device = WorldEntitySchema(
        id="ent_old_dev",
        type=EntityType.DEVICE,
        name="Old PC",
        owner_id="u1",
        source="local_companion",
        source_id="d_old",
        state="CONNECTED",
        observed_at=now - timedelta(minutes=10),
        is_stale=False,
    )

    fresh_device = WorldEntitySchema(
        id="ent_fresh_dev",
        type=EntityType.DEVICE,
        name="Fresh PC",
        owner_id="u1",
        source="local_companion",
        source_id="d_fresh",
        state="CONNECTED",
        observed_at=now - timedelta(seconds=10),
        is_stale=False,
    )

    updated = sync.reconcile_stale_entities([old_device, fresh_device], now=now)

    assert len(updated) == 1
    assert updated[0].id == "ent_old_dev"
    assert updated[0].is_stale is True
    # State is preserved (not dropped, not reset to unknown)
    assert updated[0].state == "CONNECTED"

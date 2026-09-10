"""Unit tests for simulation snapshots, immutability, freshness, state branching, and diffs (Task 56)."""

from datetime import datetime, timedelta, timezone

from app.simulation.safety import assert_simulation_context
from app.simulation.snapshots import SnapshotManager, compute_state_hash
from app.simulation.states import SimulationStateManager, calculate_state_diff


def test_compute_state_hash_determinism():
    state1 = {"b": 2, "a": 1, "nested": {"z": "foo", "y": "bar"}}
    state2 = {"a": 1, "b": 2, "nested": {"y": "bar", "z": "foo"}}
    assert compute_state_hash(state1) == compute_state_hash(state2)


def test_snapshot_capture_and_immutability():
    mgr = SnapshotManager(max_freshness_seconds=300)
    initial_world = {"cluster": "sim_alpha", "nodes": 3}
    initial_twin = {"services": {"auth": {"replicas": 2}}}

    snapshot = mgr.capture_snapshot(
        source_entity="digital_twin",
        world_state=initial_world,
        digital_twin_state=initial_twin,
    )

    assert snapshot.snapshot_id.startswith("snap_")
    assert snapshot.baseline_hash is not None
    assert snapshot.is_stale is False

    # Attempt to mutate returned snapshot and verify internal store is untouched
    snapshot.world_state["nodes"] = 999
    stored_copy = mgr.get_snapshot(snapshot.snapshot_id)
    assert stored_copy.world_state["nodes"] == 3


def test_snapshot_freshness_and_staleness_detection():
    mgr = SnapshotManager(max_freshness_seconds=10)
    twin = {"services": {"payment": {"replicas": 2}}}
    snapshot = mgr.capture_snapshot(digital_twin_state=twin)

    # 1. Fresh state
    is_fresh, reason = mgr.verify_freshness(snapshot.snapshot_id, current_state={"world": {}, "digital_twin": twin, "telemetry": {}})
    assert is_fresh is True
    assert reason is None

    # 2. State drift detection
    drifted_twin = {"services": {"payment": {"replicas": 5}}}
    is_fresh_drifted, drift_reason = mgr.verify_freshness(
        snapshot.snapshot_id,
        current_state={"world": {}, "digital_twin": drifted_twin, "telemetry": {}},
    )
    assert is_fresh_drifted is False
    assert "diverged" in drift_reason.lower()

    # 3. Age staleness
    old_snap = mgr.get_snapshot(snapshot.snapshot_id)
    # Simulate age exceeding 10 seconds
    mgr._snapshots[snapshot.snapshot_id] = old_snap.model_copy(
        update={"captured_at": datetime.now(timezone.utc) - timedelta(seconds=20)}
    )
    is_fresh_aged, age_reason = mgr.verify_freshness(snapshot.snapshot_id)
    assert is_fresh_aged is False
    assert "exceeds max threshold" in age_reason.lower()


def test_simulation_state_manager_copy_on_write():
    state_mgr = SimulationStateManager()
    initial_data = {
        "services": {
            "web": {"replicas": 2, "status": "HEALTHY"},
            "db": {"primary": "node_1"},
        }
    }

    branch_id = state_mgr.initialize_branch(base_snapshot_id="snap_123", initial_data=initial_data)
    state0 = state_mgr.get_latest_state(branch_id)
    assert state0.version == 0
    assert state0.data["services"]["web"]["replicas"] == 2

    # Apply mutation (scale replicas to 4)
    state1, diff1 = state_mgr.apply_transition(branch_id, {"services": {"web": {"replicas": 4, "status": "HEALTHY"}}})
    assert state1.version == 1
    assert state1.data["services"]["web"]["replicas"] == 4
    # Ensure state0 was not mutated in place (Copy-on-Write)
    assert state0.data["services"]["web"]["replicas"] == 2
    assert not diff1.identical
    assert "services" in diff1.modified


def test_calculate_state_diff_structural():
    before = {"cpu": 40, "ram": 60, "deleted_metric": 10}
    after = {"cpu": 55, "ram": 60, "new_metric": "active"}

    diff = calculate_state_diff(before, after)
    assert not diff.identical
    assert "new_metric" in diff.added
    assert "deleted_metric" in diff.removed
    assert "cpu" in diff.modified
    assert diff.modified["cpu"]["before"] == 40
    assert diff.modified["cpu"]["after"] == 55
    assert "ram" not in diff.modified


def test_export_future_state_markings():
    state_mgr = SimulationStateManager()
    branch_id = state_mgr.initialize_branch(base_snapshot_id="snap_xyz", initial_data={"val": 1})
    exported = state_mgr.export_future_state(branch_id)

    assert exported["environment_label"] == "SIMULATION_ONLY"
    assert exported["is_hypothetical"] is True
    assert exported["is_observed_fact"] is False
    assert exported["label"] == "SIMULATED"

    # Context verification helper
    assert_simulation_context(exported)

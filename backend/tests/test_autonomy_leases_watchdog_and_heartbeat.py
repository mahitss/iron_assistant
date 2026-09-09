"""Tests for Execution Leases, Split-Brain Prevention, Heartbeat, and Watchdog (Task 45)."""

from datetime import datetime, timedelta, timezone
import pytest
from app.autonomy.heartbeat import HeartbeatTracker
from app.autonomy.leases import (
    ExecutionLeaseManager,
    SplitBrainConflictError,
)
from app.autonomy.state import AutonomousRunState
from app.autonomy.watchdog import AutonomyWatchdog


def test_lease_acquisition_and_split_brain_protection():
    """Verify exclusive worker leases and split-brain conflict prevention (Spec 20-23)."""
    lm = ExecutionLeaseManager(default_ttl_seconds=30)
    run_id = "run_lease_01"

    # Worker 1 acquires lease
    l1 = lm.acquire_lease(run_id, worker_id="worker_alpha")
    assert l1.worker_id == "worker_alpha"
    assert l1.is_expired is False

    # Worker 2 attempts to acquire lease on same run while active -> SplitBrainConflictError
    with pytest.raises(SplitBrainConflictError):
        lm.acquire_lease(run_id, worker_id="worker_beta")

    # Worker 1 can renew its own lease
    renewed = lm.renew_lease(run_id, worker_id="worker_alpha", extension_seconds=60)
    assert renewed is True

    # Worker 2 cannot renew Worker 1's lease
    renew_unauthorized = lm.renew_lease(run_id, worker_id="worker_beta")
    assert renew_unauthorized is False

    # Release lease and let Worker 2 acquire
    lm.release_lease(run_id, worker_id="worker_alpha")
    l2 = lm.acquire_lease(run_id, worker_id="worker_beta")
    assert l2.worker_id == "worker_beta"


def test_heartbeat_tracking():
    """Verify heartbeat emissions and liveness tracking (Spec 24)."""
    hb = HeartbeatTracker(stale_threshold_seconds=10)
    run_id = "run_hb_01"

    assert hb.is_worker_alive(run_id) is False
    hb.record_heartbeat(run_id, worker_id="worker_alpha")
    assert hb.is_worker_alive(run_id) is True


def test_watchdog_anomaly_detection():
    """Verify watchdog detection of stuck, orphaned, unresponsive, and expired runs (Spec 25-27)."""
    lm = ExecutionLeaseManager()
    hb = HeartbeatTracker()
    dog = AutonomyWatchdog(lm, hb, stuck_step_threshold_seconds=60)
    run_id = "run_watchdog_01"

    # 1. Healthy run with active lease and heartbeat
    lm.acquire_lease(run_id, "worker_alpha")
    hb.record_heartbeat(run_id, "worker_alpha")
    res_healthy = dog.inspect_run(run_id, AutonomousRunState.RUNNING)
    assert res_healthy.issue_detected == "HEALTHY"
    assert res_healthy.recommended_action == "NONE"

    # 2. Expired global SLA deadline (Spec 53)
    past_deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
    res_expired = dog.inspect_run(run_id, AutonomousRunState.RUNNING, deadline=past_deadline)
    assert res_expired.issue_detected == "EXPIRED"
    assert res_expired.recommended_action == "FAIL"

    # 3. Orphaned run (lease expired/missing)
    lm.release_lease(run_id, "worker_alpha")
    res_orphaned = dog.inspect_run(run_id, AutonomousRunState.RUNNING)
    assert res_orphaned.issue_detected == "ORPHANED"
    assert res_orphaned.recommended_action == "REASSIGN"

    # 4. Stuck step exceeding threshold (Spec 26)
    lm.acquire_lease(run_id, "worker_alpha")
    stuck_start = datetime.now(timezone.utc) - timedelta(seconds=90)
    res_stuck = dog.inspect_run(run_id, AutonomousRunState.RUNNING, step_started_at=stuck_start, has_active_agents=True)
    assert res_stuck.issue_detected == "STUCK"
    assert res_stuck.recommended_action == "REPLAN"

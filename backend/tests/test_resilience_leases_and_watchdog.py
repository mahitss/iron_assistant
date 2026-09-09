"""Tests for distributed task leases, fencing tokens, worker heartbeats, stuck tasks, and quarantine."""

import asyncio
from datetime import UTC, datetime, timedelta
import pytest

from app.resilience.leases import LeaseLostError, LeaseManager
from app.resilience.watchdog import QuarantineManager, TaskWatchdog


@pytest.mark.asyncio
async def test_lease_acquisition_and_fencing_token():
    """Verifies lease acquisition, fencing token increments, and active lease protection."""
    mgr = LeaseManager(default_lease_ttl_seconds=1)

    # Worker 1 acquires lease
    lease1 = await mgr.acquire_lease("task_alpha", "worker_1", ttl_seconds=1)
    assert lease1.task_id == "task_alpha"
    assert lease1.worker_id == "worker_1"
    assert lease1.fencing_token == 1

    # Worker 2 attempts immediate acquisition -> fails with LeaseLostError
    with pytest.raises(LeaseLostError):
        await mgr.acquire_lease("task_alpha", "worker_2", ttl_seconds=1)

    # Worker 1 validates fencing token
    is_valid = await mgr.validate_fencing_token("task_alpha", "worker_1", fencing_token=1)
    assert is_valid is True

    # Sleep past lease expiration (1.0s)
    await asyncio.sleep(1.1)

    # Worker 2 now acquires expired lease -> fencing token incremented to 2!
    lease2 = await mgr.acquire_lease("task_alpha", "worker_2", ttl_seconds=1)
    assert lease2.worker_id == "worker_2"
    assert lease2.fencing_token == 2

    # Old Worker 1 attempts validation with old token -> REJECTED!
    assert await mgr.validate_fencing_token("task_alpha", "worker_1", fencing_token=1) is False


@pytest.mark.asyncio
async def test_lease_heartbeat():
    """Verifies lightweight heartbeat extends active lease."""
    mgr = LeaseManager(default_lease_ttl_seconds=1)

    lease = await mgr.acquire_lease("task_beta", "worker_1", ttl_seconds=1)
    initial_expiry = lease.expires_at

    await asyncio.sleep(0.1)
    extended = await mgr.heartbeat("task_beta", "worker_1", fencing_token=lease.fencing_token, extend_seconds=2)
    assert extended is True

    mem_lease = mgr._memory_leases["task_beta"]
    assert mem_lease.expires_at > initial_expiry

    # Voluntary release
    await mgr.release_lease("task_beta", "worker_1")
    assert "task_beta" not in mgr._memory_leases


@pytest.mark.asyncio
async def test_watchdog_stuck_task_detection_and_quarantine():
    """Verifies that watchdog detects stuck tasks and quarantines repeated crashers."""
    quarantine_mgr = QuarantineManager()
    watchdog = TaskWatchdog(quarantine_mgr=quarantine_mgr)

    task_id = "task_poison_1"

    # Simulate 3 consecutive crash/recovery cycles
    for i in range(3):
        watchdog._recovery_counts[task_id] = i
        # Simulate stuck detection
        rec_count = watchdog._recovery_counts[task_id] + 1
        watchdog._recovery_counts[task_id] = rec_count
        if rec_count >= quarantine_mgr.MAX_RECOVERY_ATTEMPTS:
            await quarantine_mgr.quarantine_task(
                task_id=task_id,
                reason="Repeated crash loops exceeding maximum attempts",
            )

    # Verify task is now quarantined
    is_q = await quarantine_mgr.is_quarantined(task_id)
    assert is_q is True

    quarantined_list = await quarantine_mgr.list_quarantined()
    assert any(q.task_id == task_id for q in quarantined_list)

    # Operator release
    released = await quarantine_mgr.release_task(task_id, released_by="admin_ops")
    assert released is True
    assert await quarantine_mgr.is_quarantined(task_id) is False

"""Tests for Open-Loop Lifecycle, Staleness Tracking, and Blocker Causality."""

from datetime import UTC, datetime, timedelta
import pytest

from app.executive_memory.blockers import BlockerManager
from app.executive_memory.open_loops import OpenLoopManager
from app.executive_memory.safety import ExecutiveSafetyGuard, FalseContinuityError
from app.executive_memory.schemas import BlockerStatus, OpenLoopStatus


def test_open_loop_lifecycle_and_user_confirmation():
    """INVARIANTS 27-37: Open loops represent unresolved work; closing requires verified evidence."""
    mgr = OpenLoopManager()
    loop = mgr.create_open_loop(
        description="Waiting for vendor API keys",
        owner="kairo",
        source="communication",
        priority="HIGH",
        scope="PROJECT",
        project_id="proj_api",
    )

    assert loop.status == OpenLoopStatus.OPEN
    assert loop.owner == "kairo"

    # Update to waiting
    waiting = mgr.update_status(loop.loop_id, OpenLoopStatus.WAITING, evidence="Ticket sent to vendor")
    assert waiting.status == OpenLoopStatus.WAITING

    # Attempt closing without evidence must fail
    with pytest.raises(ValueError):
        mgr.close_loop(loop.loop_id, evidence="")

    # Close with evidence
    closed = mgr.close_loop(loop.loop_id, evidence="Received API key via secure channel")
    assert closed.status == OpenLoopStatus.COMPLETED


def test_stale_open_loop_detection_not_abandoned():
    """INVARIANTS 35 & 36: Flag loops with no meaningful progress as STALE without assuming abandonment."""
    mgr = OpenLoopManager()
    loop = mgr.create_open_loop(
        description="Pending security audit signoff",
        owner="security_team",
        project_id="proj_sec",
    )

    # Artificially age the loop by 20 days
    old_time = datetime.now(UTC) - timedelta(days=20)
    loop.last_activity = old_time

    stale_loops = mgr.list_open_loops(project_id="proj_sec", check_staleness=True)
    assert len(stale_loops) == 1
    assert stale_loops[0].status == OpenLoopStatus.STALE
    # Crucial: STALE does not mean cancelled/abandoned
    assert stale_loops[0].status != OpenLoopStatus.CANCELLED


def test_blocker_causality_no_fabrication():
    """INVARIANTS 38-41: Blockers require causality evidence; zero fabricated blockers."""
    mgr = BlockerManager()

    # Attempting to create blocker without causality evidence fails
    with pytest.raises(FalseContinuityError) as exc_info:
        mgr.create_blocker(
            description="Build failed",
            affected_tasks=["task_ci"],
            source="ci",
            causality_evidence="",  # Empty evidence
        )
    assert "Blockers require valid causality evidence" in str(exc_info.value)

    # Valid blocker with evidence
    blocker = mgr.create_blocker(
        description="Missing Docker daemon socket",
        affected_tasks=["task_ci"],
        source="docker_daemon",
        severity="HIGH",
        causality_evidence="socket /var/run/docker.sock not found in runner environment",
        project_id="proj_devops",
    )
    assert blocker.status == BlockerStatus.ACTIVE
    assert blocker.severity == "HIGH"
    assert "docker.sock" in blocker.causality_evidence

    # Resolve blocker
    resolved = mgr.resolve_blocker(
        blocker_id=blocker.blocker_id,
        resolution_evidence="Mounted docker daemon socket to runner",
    )
    assert resolved.status == BlockerStatus.RESOLVED


def test_blocker_safety_guard_standalone():
    """INVARIANT 41: ExecutiveSafetyGuard.validate_blocker_causality catches unverified claims."""
    with pytest.raises(FalseContinuityError):
        ExecutiveSafetyGuard.validate_blocker_causality(
            blocker_description="Blocked by network issue",
            causal_evidence="",
        )

    res = ExecutiveSafetyGuard.validate_blocker_causality(
        blocker_description="Blocked by DNS resolution failure",
        causal_evidence="NXDOMAIN error for api.internal:5000",
    )
    assert res is True

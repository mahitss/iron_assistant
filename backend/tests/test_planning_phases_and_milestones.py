"""Unit tests for Phases, Milestones, and Work Packages (Task 58)."""

from __future__ import annotations

from app.planning.milestones import milestone_manager
from app.planning.phases import phase_manager
from app.planning.schemas import (
    MilestoneStatus,
    PhaseStatus,
    PlanTask,
    TaskStatus,
    WorkPackage,
)
from app.planning.work_packages import work_package_manager


def test_phase_entry_criteria_enforcement():
    phase = phase_manager.create_phase(
        name="Phase 2: Database Migration",
        entry_criteria=["Environment snapshot verified", "Lead Architect Approval"],
    )

    # Attempt to transition without approvals or verified prerequisites
    p, ok, missing = phase_manager.transition_phase(
        phase=phase,
        target_status=PhaseStatus.IN_PROGRESS,
        verified_prerequisites=[],
        approvals=[],
    )
    assert ok is False
    assert p.status == PhaseStatus.BLOCKED
    assert len(missing) == 2

    # Now satisfy prerequisites and approvals
    p, ok, missing = phase_manager.transition_phase(
        phase=phase,
        target_status=PhaseStatus.IN_PROGRESS,
        verified_prerequisites=["Environment snapshot verified"],
        approvals=["Lead Architect Approval"],
    )
    assert ok is True
    assert p.status == PhaseStatus.IN_PROGRESS
    assert len(missing) == 0


def test_phase_exit_criteria_enforcement():
    phase = phase_manager.create_phase(
        name="Phase 3: Rollout Gate",
        exit_criteria=["Zero error rate for 10 min", "100% traffic migrated"],
    )
    phase.status = PhaseStatus.IN_PROGRESS

    # Tasks attempted without verified evidence cannot exit phase
    p, ok, missing = phase_manager.transition_phase(
        phase=phase,
        target_status=PhaseStatus.COMPLETED,
        verified_outcomes=["100% traffic migrated"],  # Missing zero error rate
    )
    assert ok is False
    assert p.status == PhaseStatus.IN_PROGRESS
    assert len(missing) == 1
    assert "Zero error rate" in missing[0]

    # Satisfy all exit criteria
    p, ok, missing = phase_manager.transition_phase(
        phase=phase,
        target_status=PhaseStatus.COMPLETED,
        verified_outcomes=["Zero error rate for 10 min", "100% traffic migrated"],
    )
    assert ok is True
    assert p.status == PhaseStatus.COMPLETED


def test_milestone_verification_and_dependencies():
    m1 = milestone_manager.create_milestone(
        name="M1: Canary Deployment Healthy",
        weight=1.5,
        verification_criteria=["Canary latency < 30ms"],
    )
    m2 = milestone_manager.create_milestone(
        name="M2: Full Traffic Shifted",
        weight=3.5,
        dependencies=[m1.milestone_id],
        verification_criteria=["Full shift confirmed"],
    )

    # Attempt to verify m2 before m1 reached
    ok, errs = milestone_manager.verify_milestone(
        milestone=m2,
        verification_evidence=["Full shift confirmed"],
        reached_milestone_ids=set(),  # m1 not reached
    )
    assert ok is False
    assert m2.status == MilestoneStatus.BLOCKED
    assert any("Unresolved milestone dependency" in e for e in errs)

    # Verify m1 first
    ok, errs = milestone_manager.verify_milestone(
        milestone=m1,
        verification_evidence=["Canary latency < 30ms"],
    )
    assert ok is True
    assert m1.status == MilestoneStatus.REACHED
    assert m1.is_verified is True

    # Now verify m2 with m1 reached
    ok, errs = milestone_manager.verify_milestone(
        milestone=m2,
        verification_evidence=["Full shift confirmed"],
        reached_milestone_ids={m1.milestone_id},
    )
    assert ok is True
    assert m2.status == MilestoneStatus.REACHED
    assert m2.is_verified is True


def test_milestones_weighted_progress():
    m1 = milestone_manager.create_milestone(name="M1", weight=1.0)
    m2 = milestone_manager.create_milestone(name="M2", weight=3.0)
    m3 = milestone_manager.create_milestone(name="M3", weight=6.0)

    # 0 reached
    assert milestone_manager.evaluate_milestones_progress([m1, m2, m3]) == 0.0

    # m1 reached (weight 1.0 of 10.0 = 10%)
    m1.status = MilestoneStatus.REACHED
    m1.is_verified = True
    assert milestone_manager.evaluate_milestones_progress([m1, m2, m3]) == 10.0

    # m2 reached (weight 4.0 of 10.0 = 40%)
    m2.status = MilestoneStatus.REACHED
    m2.is_verified = True
    assert milestone_manager.evaluate_milestones_progress([m1, m2, m3]) == 40.0

    # Unverified milestone should not count even if marked REACHED
    m3.status = MilestoneStatus.REACHED
    m3.is_verified = False
    assert milestone_manager.evaluate_milestones_progress([m1, m2, m3]) == 40.0

    m3.is_verified = True
    assert milestone_manager.evaluate_milestones_progress([m1, m2, m3]) == 100.0


def test_work_package_derived_status():
    t1 = PlanTask(title="Task 1", status=TaskStatus.COMPLETED)
    t2 = PlanTask(title="Task 2", status=TaskStatus.COMPLETED)
    pkg = WorkPackage(name="Package A", task_ids=[t1.task_id, t2.task_id])

    assert work_package_manager.evaluate_status(pkg, [t1, t2]) == PhaseStatus.COMPLETED

    t2.status = TaskStatus.BLOCKED
    assert work_package_manager.evaluate_status(pkg, [t1, t2]) == PhaseStatus.BLOCKED

    t2.status = TaskStatus.RUNNING
    assert work_package_manager.evaluate_status(pkg, [t1, t2]) == PhaseStatus.IN_PROGRESS

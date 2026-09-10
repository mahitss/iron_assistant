"""Tests for Executive State Synthesis, Authoritative Backing, and Qualitative Progress."""

from datetime import UTC, datetime
import pytest

from app.executive_memory.blockers import BlockerManager
from app.executive_memory.goals import GoalContinuityManager
from app.executive_memory.next_actions import NextActionEngine
from app.executive_memory.open_loops import OpenLoopManager
from app.executive_memory.safety import ExecutiveSafetyGuard, NoMemoryOnlyStateError
from app.executive_memory.schemas import (
    ExecutiveStateScope,
    ProjectLifecycleState,
    QualitativeProgress,
)
from app.executive_memory.state import ExecutiveStateManager


def test_authoritative_state_synthesis():
    """INVARIANT 4 & 5: Current state must be derived from authoritative systems."""
    open_loop_mgr = OpenLoopManager()
    blocker_mgr = BlockerManager()
    next_action_engine = NextActionEngine(open_loop_mgr=open_loop_mgr)
    state_mgr = ExecutiveStateManager(
        open_loop_mgr=open_loop_mgr,
        blocker_mgr=blocker_mgr,
        next_action_engine=next_action_engine,
    )

    sources = {
        "projects": [{"id": "p1", "name": "Kairo Core"}],
        "goals": [{"id": "g1", "title": "Launch v2"}],
        "tasks": [{"id": "t1", "title": "Implement executive memory"}],
        "decisions": [{"id": "d1", "summary": "Use synthesis layer"}],
        "outcomes": [],
        "deadlines": [],
        "commitments": [],
        "risks": [{"id": "r1", "description": "Tight latency bounds"}],
    }

    state = state_mgr.synthesize_current_state(
        scope=ExecutiveStateScope.PROJECT,
        scope_id="p1",
        authoritative_sources=sources,
    )

    assert state.scope == ExecutiveStateScope.PROJECT
    assert len(state.active_projects) == 1
    assert state.active_projects[0]["id"] == "p1"
    assert len(state.active_goals) == 1
    assert len(state.active_tasks) == 1
    assert len(state.recent_decisions) == 1
    assert len(state.risks) == 1
    assert state.provenance["source_system"] == "AUTHORITATIVE_SYNTHESIS"


def test_no_memory_only_state_declaration():
    """INVARIANT 6: Cannot declare a project completed merely because memory says it was completed."""
    with pytest.raises(NoMemoryOnlyStateError) as exc_info:
        ExecutiveSafetyGuard.validate_project_completion(
            project_id="proj_99",
            authoritative_project_state=None,
            memory_assertion="I recall the user said this project was completed yesterday.",
        )
    assert "without authoritative verification" in str(exc_info.value)

    # Valid completion with authoritative backing
    valid_state = {"id": "proj_99", "status": "COMPLETED", "verified_by": "supervisor"}
    res = ExecutiveSafetyGuard.validate_project_completion(
        project_id="proj_99",
        authoritative_project_state=valid_state,
        memory_assertion="Project finished.",
    )
    assert res is True


def test_qualitative_progress_no_fake_percentages():
    """INVARIANTS 46-48: Progress must be qualitative unless exact subtask counts exist; no fake 87%."""
    goal_mgr = GoalContinuityManager()
    goal = goal_mgr.create_goal(
        title="Deliver Subsystem",
        success_criteria="All tests green and endpoints verified",
        project_id="p_kairo",
    )

    # Without exact subtasks, progress should be qualitative
    progress = goal_mgr.estimate_progress(goal_id=goal["goal_id"])
    assert progress in [
        QualitativeProgress.NOT_STARTED,
        QualitativeProgress.EARLY,
        QualitativeProgress.IN_PROGRESS,
        QualitativeProgress.NEAR_COMPLETE,
        QualitativeProgress.COMPLETE,
        QualitativeProgress.BLOCKED,
        QualitativeProgress.UNKNOWN,
    ]

    # Explicit qualitative update
    updated = goal_mgr.update_progress(
        goal_id=goal["goal_id"],
        qualitative_progress=QualitativeProgress.IN_PROGRESS,
        evidence="3 out of 5 core modules implemented",
    )
    assert updated["progress"] == QualitativeProgress.IN_PROGRESS


def test_state_scopes():
    """INVARIANT 3: Support SESSION, TASK, PROJECT, USER, ORGANIZATION scopes."""
    open_loop_mgr = OpenLoopManager()
    blocker_mgr = BlockerManager()
    next_action_engine = NextActionEngine(open_loop_mgr=open_loop_mgr)
    state_mgr = ExecutiveStateManager(
        open_loop_mgr=open_loop_mgr,
        blocker_mgr=blocker_mgr,
        next_action_engine=next_action_engine,
    )

    for scope in [
        ExecutiveStateScope.SESSION,
        ExecutiveStateScope.TASK,
        ExecutiveStateScope.PROJECT,
        ExecutiveStateScope.USER,
        ExecutiveStateScope.ORGANIZATION,
    ]:
        st = state_mgr.synthesize_current_state(
            scope=scope, scope_id=f"test_{scope.value.lower()}"
        )
        assert st.scope == scope

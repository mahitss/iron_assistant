"""Tests for Continuity Queries (8 Canonical Questions) and Executive Briefs."""

from datetime import UTC, datetime
import pytest

from app.executive_memory.blockers import BlockerManager
from app.executive_memory.continuity import ContinuityEngine
from app.executive_memory.decisions import DecisionHistoryManager
from app.executive_memory.goals import GoalContinuityManager
from app.executive_memory.next_actions import NextActionEngine
from app.executive_memory.open_loops import OpenLoopManager
from app.executive_memory.projects import ProjectContinuityManager
from app.executive_memory.schemas import TimelineEventType, UncertaintyLevel
from app.executive_memory.state_reconstruction import StateReconstructor
from app.executive_memory.summaries import ExecutiveSummaryManager
from app.executive_memory.timeline import TimelineEngine


@pytest.fixture
def continuity_suite():
    timeline_engine = TimelineEngine()
    state_reconstructor = StateReconstructor(timeline_engine=timeline_engine)
    project_mgr = ProjectContinuityManager()
    goal_mgr = GoalContinuityManager()
    decision_mgr = DecisionHistoryManager()
    open_loop_mgr = OpenLoopManager()
    blocker_mgr = BlockerManager()
    next_action_engine = NextActionEngine(open_loop_mgr=open_loop_mgr)

    engine = ContinuityEngine(
        timeline_engine=timeline_engine,
        state_reconstructor=state_reconstructor,
        project_mgr=project_mgr,
        goal_mgr=goal_mgr,
        decision_mgr=decision_mgr,
        open_loop_mgr=open_loop_mgr,
        blocker_mgr=blocker_mgr,
        next_action_engine=next_action_engine,
    )
    return {
        "engine": engine,
        "timeline": timeline_engine,
        "projects": project_mgr,
        "goals": goal_mgr,
        "decisions": decision_mgr,
        "open_loops": open_loop_mgr,
        "blockers": blocker_mgr,
        "next_actions": next_action_engine,
    }


def test_continuity_queries_grounded_and_no_hallucination(continuity_suite):
    """INVARIANTS 79-98, 195-201: The 8 canonical continuity questions return grounded answers or UNKNOWN."""
    engine: ContinuityEngine = continuity_suite["engine"]
    timeline: TimelineEngine = continuity_suite["timeline"]
    open_loops: OpenLoopManager = continuity_suite["open_loops"]
    blockers: BlockerManager = continuity_suite["blockers"]

    # Ingest baseline activity
    timeline.record_event(
        event_type=TimelineEventType.TASK_CREATED,
        source="tasks",
        description_reference="Implement Executive Memory",
        project_id="proj_kairo",
    )
    open_loops.create_open_loop(
        description="Verify edge cases in reconstruction",
        project_id="proj_kairo",
    )
    blockers.create_blocker(
        description="Awaiting pytest run completion",
        affected_tasks=["task_verify"],
        source="test_runner",
        causality_evidence="Process PID 1234 running",
        project_id="proj_kairo",
    )

    # 1. WHAT_WERE_WE_DOING
    q1 = engine.answer_continuity_query("WHAT_WERE_WE_DOING", project_id="proj_kairo")
    assert "Implement Executive Memory" in q1.answer
    assert q1.confidence_level != UncertaintyLevel.UNKNOWN

    # 2. WHY_DID_WE_DO_IT (Without recorded rationale, returns UNKNOWN - INVARIANT 87)
    q2 = engine.answer_continuity_query("WHY_DID_WE_DO_IT", project_id="proj_kairo", target_id="unknown_decision")
    assert "UNKNOWN" in q2.answer or q2.confidence_level == UncertaintyLevel.UNKNOWN

    # 3. WHAT_REMAINS
    q3 = engine.answer_continuity_query("WHAT_REMAINS", project_id="proj_kairo")
    assert "Verify edge cases in reconstruction" in q3.answer

    # 4. WHAT_IS_BLOCKING_US
    q4 = engine.answer_continuity_query("WHAT_IS_BLOCKING_US", project_id="proj_kairo")
    assert "Awaiting pytest run completion" in q4.answer

    # 5. WHAT_SHOULD_HAPPEN_NEXT with explicit user intent override
    q5 = engine.answer_continuity_query(
        "WHAT_SHOULD_HAPPEN_NEXT",
        project_id="proj_kairo",
        explicit_user_intent="Ship to production immediately",
    )
    assert "Ship to production immediately" in q5.answer


def test_executive_brief_generation_and_staleness():
    """INVARIANTS 22-26, 147-150: Executive brief has CURRENT, RECENT, OPEN, BLOCKED, NEXT, RISKS, DECISIONS with hash invalidation."""
    mgr = ExecutiveSummaryManager()

    brief = mgr.generate_brief(
        project_id="proj_alpha",
        current_status="Phase 1 complete, moving to Phase 2",
        recent_progress=[{"summary": "Built auth module"}],
        open_work=[{"description": "Wire payments API"}],
        blockers=[{"description": "Stripe sandbox access needed"}],
        decisions=[{"summary": "Use SQLite for metadata", "rationale": "Simplicity"}],
        risks=[{"description": "Webhooks latency"}],
        next_actions=[{"objective": "Run integration tests"}],
    )

    assert brief.project_id == "proj_alpha"
    assert brief.current_status == "Phase 1 complete, moving to Phase 2"
    assert len(brief.recent_progress) == 1
    assert len(brief.open_work) == 1
    assert len(brief.blockers) == 1
    assert len(brief.decisions) == 1
    assert len(brief.risks) == 1
    assert len(brief.next_actions) == 1
    assert brief.staleness_hash is not None

    # Retrieve cached
    cached = mgr.get_latest_brief("proj_alpha")
    assert cached is not None
    assert cached.summary_id == brief.summary_id

    # Invalidate
    mgr.invalidate_summary("proj_alpha", reason="New blocker resolved")
    assert mgr.get_latest_brief("proj_alpha") is None

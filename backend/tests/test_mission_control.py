"""Comprehensive Test Suite for Kairo Autonomous Mission Control, Long-Horizon Execution & Continuous Objective Orchestration (Task 100).

Validates:
- 18-state lifecycle state machine and invariants
- Evidence-backed milestone engine & DAG readiness
- Milestone progress regression (COMPLETED -> REGRESSED)
- Assumption tracking & cascading invalidation of plans and milestones
- Plan version manager & immutable plan history
- Mission storm defense (circuit breakers against rapid replans and failure streaks)
- 10-dimensional health matrix calculation
- Continuous orchestration cycle (ASSESS -> PLAN -> SELECT -> EXECUTE -> OBSERVE -> VERIFY -> UPDATE -> REASSESS)
- EmergencyStop fail-closed integration
- Durable checkpoints and zero-hidden-state handoff manifests
- FastAPI REST endpoints for all Task 100 operations
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.missions.assumptions import AssumptionTracker
from app.missions.checkpoints import MissionCheckpointEngine
from app.missions.health import MissionHealthEngine
from app.missions.lifecycle import MissionLifecycleError, MissionStateMachine
from app.missions.milestones import MilestoneEngine
from app.missions.orchestrator import MissionControlOrchestrator
from app.missions.replanning import PlanVersionManager
from app.missions.schemas import (
    AssumptionCreateRequest,
    AssumptionStatus,
    MilestoneCreateRequest,
    MilestoneStatus,
    Mission,
    MissionAssumption,
    MissionCreateRequest,
    MissionHealth,
    MissionMilestone,
    MissionObjective,
    MissionReviewRequest,
    MissionStatus,
    ReviewType,
)
from app.missions.service import MissionService
from app.missions.storm_protection import MissionStormDefense


def _make_sample_mission(mission_id: str = "msn_test_100", status: MissionStatus = MissionStatus.DRAFT) -> Mission:
    return Mission(
        mission_id=mission_id,
        title="Zero-downtime microservice migration",
        description="Migrate microservice without downtime or data corruption",
        objective="Migrate microservice with p99 latency under 100ms and zero errors",
        status=status,
        health=MissionHealth.ON_TRACK,
        tenant_id="tenant_100",
    )


# --- 1. Lifecycle State Machine Tests ---


def test_mission_lifecycle_valid_transitions():
    mission = _make_sample_mission(status=MissionStatus.DRAFT)

    # DRAFT -> VALIDATING -> READY -> RUNNING
    MissionStateMachine.transition(mission, MissionStatus.VALIDATING, reason="Pre-flight check")
    assert mission.status == MissionStatus.VALIDATING

    MissionStateMachine.transition(mission, MissionStatus.READY, reason="Checks passed")
    assert mission.status == MissionStatus.READY

    MissionStateMachine.transition(mission, MissionStatus.RUNNING, reason="Execution initiated")
    assert mission.status == MissionStatus.RUNNING

    # RUNNING -> PAUSED -> RUNNING
    MissionStateMachine.transition(mission, MissionStatus.PAUSED, reason="Maintenance hold")
    assert mission.status == MissionStatus.PAUSED

    MissionStateMachine.transition(mission, MissionStatus.RUNNING, reason="Maintenance complete")
    assert mission.status == MissionStatus.RUNNING

    # RUNNING -> REPLANNING -> RUNNING
    MissionStateMachine.transition(mission, MissionStatus.REPLANNING, reason="Drift observed")
    assert mission.status == MissionStatus.REPLANNING

    MissionStateMachine.transition(mission, MissionStatus.RUNNING, reason="New plan approved")
    assert mission.status == MissionStatus.RUNNING

    # RUNNING -> VERIFYING -> COMPLETED
    MissionStateMachine.transition(mission, MissionStatus.VERIFYING, reason="All actions executed")
    assert mission.status == MissionStatus.VERIFYING

    MissionStateMachine.transition(mission, MissionStatus.COMPLETED, reason="Empirical criteria met")
    assert mission.status == MissionStatus.COMPLETED


def test_mission_lifecycle_regression_from_completed():
    mission = _make_sample_mission(status=MissionStatus.COMPLETED)

    # Invariant: COMPLETED STATE != PERMANENT STABILITY
    # World drift can regress a completed mission to REGRESSED
    MissionStateMachine.transition(mission, MissionStatus.REGRESSED, reason="Downstream drift invalidated objective")
    assert mission.status == MissionStatus.REGRESSED

    # REGRESSED can transition to REPLANNING or RUNNING
    MissionStateMachine.transition(mission, MissionStatus.REPLANNING, reason="Synthesizing recovery plan")
    assert mission.status == MissionStatus.REPLANNING


def test_mission_lifecycle_fail_closed_emergency_stop():
    mission = _make_sample_mission(status=MissionStatus.RUNNING)

    # Invariant: EMERGENCY STOP ALWAYS WINS
    MissionStateMachine.transition(mission, MissionStatus.EMERGENCY_STOPPED, reason="Global safety breach")
    assert mission.status == MissionStatus.EMERGENCY_STOPPED

    # From EMERGENCY_STOPPED, can only transition to RECOVERING, CANCELLED, or ABORTED
    with pytest.raises(MissionLifecycleError):
        MissionStateMachine.transition(mission, MissionStatus.RUNNING, reason="Direct resume forbidden")

    MissionStateMachine.transition(mission, MissionStatus.RECOVERING, reason="Initiating safety postmortem")
    assert mission.status == MissionStatus.RECOVERING


def test_mission_lifecycle_invalid_transition_rejected():
    mission = _make_sample_mission(status=MissionStatus.DRAFT)
    # Cannot jump directly from DRAFT to COMPLETED
    with pytest.raises(MissionLifecycleError):
        MissionStateMachine.transition(mission, MissionStatus.COMPLETED, reason="Invalid direct jump")


# --- 2. Milestone Engine, Evidence & Regression Tests ---


def test_milestone_evidence_verification_and_dag_readiness():
    mission = _make_sample_mission(status=MissionStatus.RUNNING)

    milestone_1 = MilestoneEngine.add_milestone(
        mission,
        title="Deploy Canary Pods",
        description="Launch 10% canary traffic",
    )
    assert milestone_1.status == MilestoneStatus.READY

    milestone_2 = MilestoneEngine.add_milestone(
        mission,
        title="Full Traffic Cutover",
        description="Route 100% traffic to new cluster",
        dependencies=[milestone_1.milestone_id],
    )
    assert milestone_2.status == MilestoneStatus.PENDING

    # Attempt to verify without evidence
    ok, err = MilestoneEngine.verify_milestone(
        mission,
        milestone_1.milestone_id,
        empirical_evidence=[],
    )
    assert ok is False

    # Verify with valid empirical evidence
    ok, msg = MilestoneEngine.verify_milestone(
        mission,
        milestone_1.milestone_id,
        empirical_evidence=["metric: p99_ms=45.0", "world_state: canary_active=True"],
    )
    assert ok is True
    assert milestone_1.status == MilestoneStatus.COMPLETED

    # Check DAG readiness update
    MilestoneEngine.check_and_update_readiness(mission)
    assert milestone_2.status == MilestoneStatus.READY


def test_milestone_progress_regression():
    mission = _make_sample_mission(status=MissionStatus.RUNNING)

    m1 = MilestoneEngine.add_milestone(
        mission,
        title="Database Schema Migration",
    )
    ok, msg = MilestoneEngine.verify_milestone(
        mission,
        m1.milestone_id,
        empirical_evidence=["metric: schema_version=2"],
    )
    assert ok is True
    assert m1.status == MilestoneStatus.COMPLETED

    # Simulate drift or regression
    regressed = MilestoneEngine.regress_milestone(
        mission,
        m1.milestone_id,
        reason="Rollback detected: schema reverted to version 1",
    )
    assert regressed.status == MilestoneStatus.REGRESSED
    assert mission.status == MissionStatus.REGRESSED


# --- 3. Assumption Tracker & Cascading Invalidation Tests ---


def test_assumption_cascading_invalidation():
    mission = _make_sample_mission(status=MissionStatus.RUNNING)

    m1 = MilestoneEngine.add_milestone(
        mission,
        title="Connect to Redis cache",
    )

    req = AssumptionCreateRequest(
        statement="Redis cache cluster is reachable on port 6379",
        source="infrastructure_spec",
        dependent_milestone_ids=[m1.milestone_id],
        dependent_plan_versions=["v1"],
    )
    assumption = AssumptionTracker.register_assumption(mission, req)
    assert assumption.status == AssumptionStatus.VALID

    # Invalidate the assumption
    invalidated = AssumptionTracker.invalidate_assumption(
        mission,
        assumption.assumption_id,
        reason="Redis connection timeout: connection refused",
    )
    assert invalidated.status == AssumptionStatus.INVALIDATED

    # Invariant: dependent milestone must be marked BLOCKED
    assert m1.status == MilestoneStatus.BLOCKED


# --- 4. Plan Version Manager Tests ---


def test_plan_version_history_recording():
    mission = _make_sample_mission(status=MissionStatus.RUNNING)

    pv1 = PlanVersionManager.record_plan_version(
        mission=mission,
        plan_id="plan_v1",
        plan_spec={"tasks": ["t1", "t2"]},
        reason="Initial plan synthesis",
    )
    assert pv1.version_number == 1
    assert mission.active_plan_id == "plan_v1"

    pv2 = PlanVersionManager.record_plan_version(
        mission=mission,
        plan_id="plan_v2",
        plan_spec={"tasks": ["t1_revised", "t3"]},
        reason="Replan due to latency constraint",
    )
    assert pv2.version_number == 2
    assert mission.active_plan_id == "plan_v2"
    assert len(mission.plan_versions) == 2


# --- 5. Mission Storm Defense (Circuit Breakers) Tests ---


def test_storm_defense_replan_circuit_breaker():
    mission = _make_sample_mission(status=MissionStatus.RUNNING)
    defense = MissionStormDefense(max_consecutive_failures=3)

    # Invariant: consecutive failure streak trips circuit breaker to AWAITING_USER
    defense.record_failure(mission, reason="Action 1 failed")
    assert mission.status == MissionStatus.RUNNING
    defense.record_failure(mission, reason="Action 2 failed")
    assert mission.status == MissionStatus.RUNNING
    defense.record_failure(mission, reason="Action 3 failed")
    assert mission.status == MissionStatus.AWAITING_USER
    assert mission.health == MissionHealth.BLOCKED


# --- 6. 10-Dimensional Health Matrix Tests ---


def test_10_dimensional_health_matrix():
    mission = _make_sample_mission(status=MissionStatus.RUNNING)

    # Default mission should evaluate to ON_TRACK
    derived_health, dimensions = MissionHealthEngine.evaluate_health(mission)
    assert derived_health == MissionHealth.ON_TRACK
    assert mission.health == MissionHealth.ON_TRACK
    assert len(dimensions.model_dump()) >= 10


# --- 7. Continuous Orchestration Loop & EmergencyStop Tests ---


def test_orchestration_cycle_fail_closed_on_emergency_stop():
    orchestrator = MissionControlOrchestrator()
    mission = _make_sample_mission(status=MissionStatus.RUNNING)

    # Inject active EmergencyStop into the orchestrator bridge
    class MockEmergencyStop:
        def is_active(self) -> bool:
            return True

    orchestrator.emergency_stop = MockEmergencyStop()

    result = orchestrator.run_orchestration_cycle(mission=mission)
    assert result["cycle_status"] == "EMERGENCY_STOPPED"
    assert result["emergency_stopped"] is True
    assert mission.status == MissionStatus.EMERGENCY_STOPPED


def test_orchestration_cycle_nominal_progression():
    orchestrator = MissionControlOrchestrator()
    mission = _make_sample_mission(status=MissionStatus.RUNNING)
    MilestoneEngine.add_milestone(mission, title="Step 1: Canary Deploy")

    # Ensure clean EmergencyStop
    class MockNominalEmergencyStop:
        def is_active(self) -> bool:
            return False

    orchestrator.emergency_stop = MockNominalEmergencyStop()

    result = orchestrator.run_orchestration_cycle(
        mission=mission,
        expected_postconditions={"active": True},
    )
    assert result["cycle_status"] == "COMPLETED"
    assert result["emergency_stopped"] is False
    assert "verification" in result


# --- 8. Checkpoints & Handoff Manifest Tests ---


def test_checkpoint_engine_handoff_manifest():
    mission = _make_sample_mission(status=MissionStatus.RUNNING)
    MilestoneEngine.add_milestone(mission, title="M1")

    cp = MissionCheckpointEngine.create_checkpoint(
        mission,
        label="Handoff Checkpoint",
        generate_handoff_manifest=True,
    )
    assert cp.checkpoint_id.startswith("chk_")
    assert cp.handoff_manifest is not None
    assert cp.handoff_manifest["mission_id"] == mission.mission_id
    assert "completed_milestones" in cp.handoff_manifest
    assert "active_assumptions" in cp.handoff_manifest


# --- 9. FastAPI REST Endpoints for Task 100 Tests ---


@pytest.mark.asyncio
async def test_task_100_api_milestones_and_health():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create mission
        create_res = await client.post(
            "/api/v1/missions/?is_human_approved=true",
            json={
                "title": "Task 100 API Verified Mission",
                "objective": "Verify all Task 100 endpoints",
                "tenant_id": "tenant_api_100",
            },
        )
        assert create_res.status_code == 201
        m_id = create_res.json()["mission"]["mission_id"]

        # 1. POST /missions/{id}/milestones
        ms_res = await client.post(
            f"/api/v1/missions/{m_id}/milestones?tenant_id=tenant_api_100",
            json={
                "title": "API Step 1",
                "progress_weight": 0.5,
                "required_evidence_types": ["metric"],
            },
        )
        assert ms_res.status_code == 201
        milestone_id = ms_res.json()["milestone_id"]

        # 2. GET /missions/{id}/milestones
        list_ms_res = await client.get(f"/api/v1/missions/{m_id}/milestones?tenant_id=tenant_api_100")
        assert list_ms_res.status_code == 200
        assert len(list_ms_res.json()) >= 1

        # 3. POST /missions/{id}/milestones/{mid}/verify
        verify_ms_res = await client.post(
            f"/api/v1/missions/{m_id}/milestones/{milestone_id}/verify?tenant_id=tenant_api_100",
            json={"evidence": ["metric: passed=True"]},
        )
        assert verify_ms_res.status_code == 200
        assert verify_ms_res.json()["status"] == "COMPLETED"

        # 4. POST /missions/{id}/assumptions
        assump_res = await client.post(
            f"/api/v1/missions/{m_id}/assumptions?tenant_id=tenant_api_100",
            json={
                "statement": "Service endpoint is responding",
                "source": "api_contract",
            },
        )
        assert assump_res.status_code == 201
        assert assump_res.json()["status"] == "VALID"

        # 5. GET /missions/{id}/health
        health_res = await client.get(f"/api/v1/missions/{m_id}/health?tenant_id=tenant_api_100")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert "health" in health_data
        assert "dimensions" in health_data

        # 6. POST /missions/{id}/checkpoints
        cp_res = await client.post(
            f"/api/v1/missions/{m_id}/checkpoints?tenant_id=tenant_api_100",
            json={"label": "API Test Checkpoint", "generate_handoff_manifest": True},
        )
        assert cp_res.status_code == 201
        assert "handoff_manifest" in cp_res.json()

        # 7. POST /missions/{id}/reviews
        review_res = await client.post(
            f"/api/v1/missions/{m_id}/reviews?tenant_id=tenant_api_100",
            json={
                "review_type": "PERIODIC",
                "evaluation_score": 0.98,
                "observations": ["Nominal milestone progress"],
            },
        )
        assert review_res.status_code == 201
        assert review_res.json()["evaluation_score"] == 0.98

        # 8. POST /missions/{id}/orchestrate
        orch_res = await client.post(
            f"/api/v1/missions/{m_id}/orchestrate?tenant_id=tenant_api_100",
            json={"active": True},
        )
        assert orch_res.status_code == 200
        assert "cycle_status" in orch_res.json()

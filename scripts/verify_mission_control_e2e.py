"""End-to-end operational verification script for Task 100:
KAIRO Autonomous Mission Control, Long-Horizon Execution & Continuous Objective Orchestration.

Executes all 8 core architectural scenarios plus CLI validation:
- Scenario 1: Nominal Mission Lifecycle & Milestone DAG Dependency Progression
- Scenario 2: Empirical Reality Gate & Verification (EXECUTION SUCCESS != VERIFIED SUCCESS)
- Scenario 3: Progress Regression from Environmental Drift (COMPLETED STATE != PERMANENT STABILITY)
- Scenario 4: First-Class Assumption Tracking & Cascading Invalidation
- Scenario 5: Dynamic Replanning & Immutable Plan Version History
- Scenario 6: Mission Storm Defense Circuit Breakers (Arrest Runaway Loops)
- Scenario 7: Continuous Orchestration Loop & Emergency Stop Fail-Closed Override
- Scenario 8: Durable Checkpoint Engine & Zero-Hidden-State Handoff Manifest
- Scenario 9: CLI Operational Commands Verification
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from click.testing import CliRunner

from app.missions.assumptions import AssumptionTracker
from app.missions.checkpoints import MissionCheckpointEngine
from app.missions.cli import missions as mission_cli
from app.missions.health import MissionHealthEngine
from app.missions.lifecycle import MissionLifecycleError, MissionStateMachine
from app.missions.milestones import MilestoneEngine
from app.missions.orchestrator import MissionControlOrchestrator
from app.missions.replanning import PlanVersionManager
from app.missions.schemas import (
    AssumptionCreateRequest,
    AssumptionStatus,
    MilestoneStatus,
    Mission,
    MissionHealth,
    MissionStatus,
)
from app.missions.storm_protection import MissionStormDefense


def _make_mission(title: str = "E2E Mission", status: MissionStatus = MissionStatus.RUNNING) -> Mission:
    return Mission(
        mission_id="msn_e2e_100",
        title=title,
        description="Autonomous mission control end-to-end verification",
        objective="Verify all continuous orchestration and invariant enforcement guarantees",
        status=status,
        health=MissionHealth.ON_TRACK,
        tenant_id="tenant_e2e_100",
    )


def run_e2e_scenarios() -> int:
    print("======================================================================")
    print("KAIRO TASK 100: AUTONOMOUS MISSION CONTROL E2E VERIFICATION")
    print("======================================================================")

    passed = 0
    total = 9

    # ------------------------------------------------------------------
    # Scenario 1: Nominal Mission Lifecycle & Milestone DAG Progression
    # ------------------------------------------------------------------
    print("\n[Scenario 1] Nominal Mission Lifecycle & Milestone DAG Progression")
    m = _make_mission("Multi-Stage Pipeline", status=MissionStatus.DRAFT)
    MissionStateMachine.transition(m, MissionStatus.VALIDATING, reason="Validating pre-conditions")
    MissionStateMachine.transition(m, MissionStatus.READY, reason="Checks verified")
    MissionStateMachine.transition(m, MissionStatus.RUNNING, reason="Execution authorized")
    assert m.status == MissionStatus.RUNNING

    m1 = MilestoneEngine.add_milestone(m, title="Stage 1: Provision Cluster")
    m2 = MilestoneEngine.add_milestone(m, title="Stage 2: Migrate DB", dependencies=[m1.milestone_id])

    assert m1.status == MilestoneStatus.READY
    assert m2.status == MilestoneStatus.PENDING

    # Verify stage 1 completes and activates stage 2
    ok, _ = MilestoneEngine.verify_milestone(m, m1.milestone_id, empirical_evidence=["metric: nodes=3"])
    assert ok is True
    assert m1.status == MilestoneStatus.COMPLETED

    MilestoneEngine.check_and_update_readiness(m)
    assert m2.status == MilestoneStatus.READY
    print(f"  ✓ Stage 1 completed -> Stage 2 DAG dependency unlocked (status: {m2.status.value})")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 2: Empirical Reality Gate (EXECUTION SUCCESS != VERIFIED SUCCESS)
    # ------------------------------------------------------------------
    print("\n[Scenario 2] Empirical Reality Gate & Ground-Truth Verification")
    m = _make_mission("Reality Gate Mission")
    ms = MilestoneEngine.add_milestone(m, title="Zero Downtime Deployment")

    # Invariant: Action execution without empirical evidence CANNOT claim success
    ok_no_ev, err_msg = MilestoneEngine.verify_milestone(m, ms.milestone_id, empirical_evidence=[])
    assert ok_no_ev is False
    assert ms.status != MilestoneStatus.COMPLETED
    print(f"  ✓ Verification rejected without empirical evidence: '{err_msg}'")

    # Verification with verified metric evidence succeeds
    ok_ev, _ = MilestoneEngine.verify_milestone(
        m,
        ms.milestone_id,
        empirical_evidence=["metric: error_rate_pct=0.00", "world_state: healthy=True"],
    )
    assert ok_ev is True
    assert ms.status == MilestoneStatus.COMPLETED
    print("  ✓ Verification confirmed under empirical evidence gate")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 3: Progress Regression (COMPLETED STATE != PERMANENT STABILITY)
    # ------------------------------------------------------------------
    print("\n[Scenario 3] Progress Regression from Environmental Drift")
    m = _make_mission("Regression Recovery Mission", status=MissionStatus.RUNNING)
    m_reg = MilestoneEngine.add_milestone(m, title="Schema Upgrade v2")
    MilestoneEngine.verify_milestone(m, m_reg.milestone_id, empirical_evidence=["metric: schema_version=2"])
    assert m_reg.status == MilestoneStatus.COMPLETED

    # Downstream world-state drift reverts schema to v1
    regressed = MilestoneEngine.regress_milestone(
        m,
        m_reg.milestone_id,
        reason="Drift detected: database schema reverted to version 1",
    )
    assert regressed.status == MilestoneStatus.REGRESSED
    assert m.status == MissionStatus.REGRESSED
    assert m.health == MissionHealth.AT_RISK
    print(f"  ✓ Milestone regressed to {regressed.status.value}, Mission status updated to {m.status.value}")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 4: First-Class Assumptions & Cascading Invalidation
    # ------------------------------------------------------------------
    print("\n[Scenario 4] First-Class Assumption Tracking & Cascading Invalidation")
    m = _make_mission("Assumption Invalidation Mission", status=MissionStatus.RUNNING)
    dep_milestone = MilestoneEngine.add_milestone(m, title="Cache Warmup")

    req = AssumptionCreateRequest(
        statement="Redis cache reachable on default cluster port",
        source="infrastructure_spec",
        dependent_milestone_ids=[dep_milestone.milestone_id],
        dependent_plan_versions=["plan_v1"],
    )
    assumption = AssumptionTracker.register_assumption(m, req)
    assert assumption.status == AssumptionStatus.VALID

    # Invalidate assumption
    invalidated = AssumptionTracker.invalidate_assumption(
        m,
        assumption.assumption_id,
        reason="Network partition isolated Redis cluster",
    )
    assert invalidated.status == AssumptionStatus.INVALIDATED
    assert dep_milestone.status == MilestoneStatus.BLOCKED
    assert m.health == MissionHealth.AT_RISK
    print(f"  ✓ Assumption {assumption.assumption_id} INVALIDATED -> Dependent milestone cascaded to BLOCKED")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 5: Dynamic Replanning & Immutable Plan History
    # ------------------------------------------------------------------
    print("\n[Scenario 5] Dynamic Replanning & Immutable Plan Version History")
    m = _make_mission("Versioned Planning Mission", status=MissionStatus.RUNNING)

    v1 = PlanVersionManager.record_plan_version(
        mission=m,
        plan_id="plan_100_v1",
        plan_spec={"stages": ["canary", "cutover"]},
        reason="Initial plan synthesis",
    )
    assert v1.version_number == 1
    assert m.active_plan_id == "plan_100_v1"

    v2 = PlanVersionManager.record_plan_version(
        mission=m,
        plan_id="plan_100_v2",
        plan_spec={"stages": ["canary", "shadow_traffic", "cutover"]},
        reason="Add shadow traffic phase due to latency sensitivity",
    )
    assert v2.version_number == 2
    assert m.active_plan_id == "plan_100_v2"
    assert len(m.plan_versions) == 2
    print(f"  ✓ Plan versions recorded: v1 -> v2 (active: {m.active_plan_id})")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 6: Mission Storm Defense Circuit Breakers
    # ------------------------------------------------------------------
    print("\n[Scenario 6] Mission Storm Defense Circuit Breakers")
    m = _make_mission("Storm Defense Mission", status=MissionStatus.RUNNING)
    defense = MissionStormDefense(max_consecutive_failures=3, max_replans_per_window=3)

    # Simulate 3 consecutive action execution failures
    defense.record_failure(m, reason="Timeout connecting to downstream")
    defense.record_failure(m, reason="Downstream 503 Service Unavailable")
    defense.record_failure(m, reason="Downstream connection refused")

    assert m.status == MissionStatus.AWAITING_USER
    assert m.health == MissionHealth.BLOCKED
    print(f"  ✓ Storm defense tripped after failure streak -> Mission arrested to {m.status.value}")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 7: Continuous Orchestration & Emergency Stop Absolute Override
    # ------------------------------------------------------------------
    print("\n[Scenario 7] Continuous Orchestration & Emergency Stop Fail-Closed Override")
    orchestrator = MissionControlOrchestrator()
    m = _make_mission("Safety Override Mission", status=MissionStatus.RUNNING)

    class ActiveMockEmergencyStop:
        def is_active(self) -> bool:
            return True

    orchestrator.emergency_stop = ActiveMockEmergencyStop()
    res = orchestrator.run_orchestration_cycle(mission=m)

    assert res["cycle_status"] == "EMERGENCY_STOPPED"
    assert res["emergency_stopped"] is True
    assert m.status == MissionStatus.EMERGENCY_STOPPED

    # Direct resume forbidden from EMERGENCY_STOPPED
    try:
        MissionStateMachine.transition(m, MissionStatus.RUNNING, reason="Illegal resume attempt")
        assert False, "Should have raised MissionLifecycleError"
    except MissionLifecycleError:
        pass

    print("  ✓ EmergencyStop halt verified fail-closed; direct resume rejected")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 8: Durable Checkpoint Engine & Zero-Hidden-State Handoff Manifest
    # ------------------------------------------------------------------
    print("\n[Scenario 8] Durable Checkpoint Engine & Zero-Hidden-State Handoff Manifest")
    m = _make_mission("Handoff Mission", status=MissionStatus.RUNNING)
    m_done = MilestoneEngine.add_milestone(m, title="Step 1")
    MilestoneEngine.verify_milestone(m, m_done.milestone_id, empirical_evidence=["metric: ok=True"])

    cp = MissionCheckpointEngine.create_checkpoint(
        m,
        label="E2E Handoff Checkpoint",
        generate_handoff_manifest=True,
    )
    assert cp.checkpoint_id.startswith("chk_")
    assert cp.handoff_manifest is not None
    manifest = cp.handoff_manifest
    assert manifest["mission_id"] == m.mission_id
    assert "completed_milestones" in manifest
    assert "active_assumptions" in manifest
    assert "blockers" in manifest
    assert "progress_pct" in manifest
    print(f"  ✓ Checkpoint '{cp.checkpoint_id}' generated zero-hidden-state manifest with {len(manifest)} dimensions")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 9: CLI Operational Commands Verification
    # ------------------------------------------------------------------
    print("\n[Scenario 9] CLI Operational Commands Verification")
    runner = CliRunner()

    res_help = runner.invoke(mission_cli, ["--help"])
    assert res_help.exit_code == 0
    assert "Mission Control" in res_help.output or "Usage" in res_help.output

    res_list = runner.invoke(mission_cli, ["list", "--help"])
    assert res_list.exit_code == 0

    res_health = runner.invoke(mission_cli, ["health", "--help"])
    assert res_health.exit_code == 0

    res_milestones = runner.invoke(mission_cli, ["milestones", "--help"])
    assert res_milestones.exit_code == 0

    res_assumptions = runner.invoke(mission_cli, ["assumptions", "--help"])
    assert res_assumptions.exit_code == 0

    res_checkpoint = runner.invoke(mission_cli, ["checkpoint", "--help"])
    assert res_checkpoint.exit_code == 0

    res_orchestrate = runner.invoke(mission_cli, ["orchestrate", "--help"])
    assert res_orchestrate.exit_code == 0

    print("  ✓ CLI command suite verified (list, health, milestones, assumptions, checkpoint, orchestrate)")
    passed += 1

    print("\n======================================================================")
    print(f"ALL {passed}/{total} END-TO-END OPERATIONAL SCENARIOS PASSED WITH ZERO VIOLATIONS")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_e2e_scenarios())

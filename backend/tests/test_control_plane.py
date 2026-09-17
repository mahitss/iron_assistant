"""Comprehensive test suite for Kairo Autonomous Cognitive Control Plane & Unified Operating Loop (Task 102)."""

from __future__ import annotations

import time
import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from app.control_plane.cli import control_plane_cli
from app.control_plane.coalescer import ControlTriggerCoalescer
from app.control_plane.context_assembler import ControlContextAssembler, TrustClass
from app.control_plane.domain import (
    BudgetEnvelope,
    ControlCycle,
    ControlCycleStatus,
    ControlMode,
    ControlSnapshot,
    CyclePriority,
    NoActionReason,
    TriggerType,
    WaitingReason,
)
from app.control_plane.loop_guard import LoopGuardCircuitBreaker
from app.control_plane.operating_loop import UnifiedOperatingLoop
from app.control_plane.service import ControlPlaneService, get_control_plane_service
from app.main import create_app
from app.security.emergency_stop import get_emergency_stop_service


@pytest.fixture(autouse=True)
def clean_emergency_stop():
    """Ensure EmergencyStop is reset before each test."""
    e_stop = get_emergency_stop_service()
    e_stop.reset()
    yield
    e_stop.reset()


def test_domain_lifecycle_and_invariants():
    """Verifies that all 19 ControlCycle lifecycle states and domain enums are established."""
    assert ControlCycleStatus.CREATED.value == "CREATED"
    assert ControlCycleStatus.OBSERVING.value == "OBSERVING"
    assert ControlCycleStatus.RECONCILING.value == "RECONCILING"
    assert ControlCycleStatus.ASSESSING.value == "ASSESSING"
    assert ControlCycleStatus.CONTEXT_BUILDING.value == "CONTEXT_BUILDING"
    assert ControlCycleStatus.PLANNING_REQUESTED.value == "PLANNING_REQUESTED"
    assert ControlCycleStatus.DECISION_REQUESTED.value == "DECISION_REQUESTED"
    assert ControlCycleStatus.WAITING.value == "WAITING"
    assert ControlCycleStatus.AUTHORIZED.value == "AUTHORIZED"
    assert ControlCycleStatus.EXECUTING.value == "EXECUTING"
    assert ControlCycleStatus.VERIFYING.value == "VERIFYING"
    assert ControlCycleStatus.LEARNING.value == "LEARNING"
    assert ControlCycleStatus.COMPLETED.value == "COMPLETED"
    assert ControlCycleStatus.NO_ACTION.value == "NO_ACTION"
    assert ControlCycleStatus.BLOCKED.value == "BLOCKED"
    assert ControlCycleStatus.PAUSED.value == "PAUSED"
    assert ControlCycleStatus.CANCELLED.value == "CANCELLED"
    assert ControlCycleStatus.FAILED.value == "FAILED"
    assert ControlCycleStatus.UNKNOWN.value == "UNKNOWN"

    assert TriggerType.USER_REQUEST.value == "USER_REQUEST"
    assert TriggerType.NEW_SITUATION.value == "NEW_SITUATION"
    assert TriggerType.EMERGENCY_STOP.value == "EMERGENCY_STOP"

    assert WaitingReason.WAITING_FOR_APPROVAL.value == "WAITING_FOR_APPROVAL"
    assert WaitingReason.WAITING_FOR_VERIFICATION.value == "WAITING_FOR_VERIFICATION"

    assert NoActionReason.NO_MEANINGFUL_CHANGE.value == "NO_MEANINGFUL_CHANGE"
    assert NoActionReason.EMERGENCY_STOP_ACTIVE.value == "EMERGENCY_STOP_ACTIVE"


def test_trigger_coalescer_burst_handling():
    """Verifies that the coalescer batches multiple rapid incoming events while preserving lineage."""
    triggers = [
        {
            "trigger_type": TriggerType.RISK_ESCALATION,
            "payload": {"risk_delta": 0.4},
            "timestamp": "2026-09-18T00:00:00Z",
        },
        {
            "trigger_type": TriggerType.RELIABILITY_DEGRADATION,
            "payload": {"error_rate": 0.12},
            "timestamp": "2026-09-18T00:00:01Z",
        },
        {
            "trigger_type": TriggerType.FORECAST_THRESHOLD,
            "payload": {"latency_forecast_ms": 650},
            "timestamp": "2026-09-18T00:00:02Z",
        },
    ]

    merged_cycle = ControlTriggerCoalescer.coalesce(triggers, scope="service_checkout")

    # Priority escalation: RISK_ESCALATION is CRITICAL, so merged cycle takes CRITICAL priority
    assert merged_cycle.priority == CyclePriority.CRITICAL
    assert merged_cycle.trigger_type == TriggerType.RISK_ESCALATION
    assert len(merged_cycle.coalesced_triggers) == 3
    assert merged_cycle.scope == "service_checkout"


def test_context_assembler_trust_class_labeling():
    """Verifies that assembled contexts strictly preserve and enforce trust classes."""
    cycle = ControlCycle(
        trigger_type=TriggerType.USER_REQUEST,
        trigger_payload={"objective": "Deploy canary image securely"},
    )
    snapshot = ControlSnapshot(
        world_state_ref="world_snap_001",
        self_model_ref="self_snap_001",
    )

    bundle = ControlContextAssembler.assemble(
        cycle=cycle,
        snapshot=snapshot,
        mission_payload={"mission_id": "m-deploy", "title": "Production Canary"},
        situation_payload={"situation_id": "s-lat", "title": "Elevated P99 Latency"},
        self_model_summary={"ready_capabilities": ["docker", "kubectl"]},
        recent_observations=[
            {"source": "web_scrape", "payload": "Untrusted scrape content", "trust_label": TrustClass.WEB_UNTRUSTED}
        ],
    )

    assert bundle.cycle_id == cycle.cycle_id
    assert len(bundle.items) >= 4

    labels = {item.category: item.trust_label for item in bundle.items}
    assert labels.get("TRIGGER") == TrustClass.USER_AUTHORED
    assert labels.get("WORLD_STATE") == TrustClass.OBSERVED
    assert labels.get("CAPABILITY_BOUNDARIES") == TrustClass.OBSERVED
    assert labels.get("SITUATION") == TrustClass.OBSERVED

    web_item = next((i for i in bundle.items if i.category == "OBSERVATION"), None)
    assert web_item is not None
    assert web_item.trust_label == TrustClass.WEB_UNTRUSTED


def test_loop_guard_circuit_breaker_anti_thrashing():
    """Verifies that repetitive failures or cyclic actions trip the circuit breaker."""
    breaker = LoopGuardCircuitBreaker(
        failure_threshold=3,
        repetition_threshold=3,
    )
    cycle = ControlCycle()

    # Simulate 3 consecutive identical failures
    for i in range(3):
        tripped, reason = breaker.record_step(
            cycle=cycle,
            failure_fingerprint="fail_restart_db",
        )

    assert tripped is True
    assert "Identical failure threshold (3) breached" in reason
    assert breaker.is_tripped is True
    assert len(breaker.tripped_reasons) > 0


def test_unified_operating_loop_successful_cycle():
    """Verifies a full 16-stage cycle through UnifiedOperatingLoop resulting in verified completion."""
    loop = UnifiedOperatingLoop()

    cycle = ControlCycle(
        trigger_type=TriggerType.USER_REQUEST,
        scope="deployment_subsystem",
        trigger_payload={
            "objective": "Perform zero-downtime rolling update",
            "requires_action": True,
            "simulated_action_success": True,
            "simulated_verification_success": True,
        },
    )

    res_cycle = loop.execute_cycle(cycle)

    assert res_cycle.status == ControlCycleStatus.COMPLETED
    assert res_cycle.result == "SUCCESS"
    assert res_cycle.action_ref is not None
    assert res_cycle.verification_ref is not None
    assert res_cycle.completed_at is not None
    assert res_cycle.budget.consumed_tool_calls >= 1


def test_post_action_verification_failure_distinction():
    """Verifies that tool execution success with degraded world state triggers VERIFICATION_FAILURE."""
    loop = UnifiedOperatingLoop()

    cycle = ControlCycle(
        trigger_type=TriggerType.SITUATION_ESCALATION,
        scope="auth_service",
        trigger_payload={
            "requires_action": True,
            "simulated_action_success": True,
            "simulated_verification_success": False,  # Post-action verification fails!
        },
    )

    res_cycle = loop.execute_cycle(cycle)

    assert res_cycle.status == ControlCycleStatus.FAILED
    assert res_cycle.result == "VERIFICATION_FAILURE"
    assert "verification failed" in res_cycle.reason.lower()


def test_unknown_action_outcome_no_action():
    """Verifies that stable state or explicit review concludes with deliberate NO_ACTION."""
    loop = UnifiedOperatingLoop()

    cycle = ControlCycle(
        trigger_type=TriggerType.SCHEDULED_REVIEW,
        scope="background_telemetry",
        trigger_payload={"requires_action": False},
    )

    res_cycle = loop.execute_cycle(cycle)

    assert res_cycle.status == ControlCycleStatus.NO_ACTION
    assert res_cycle.no_action_reason == NoActionReason.NO_MEANINGFUL_CHANGE
    assert res_cycle.result == "NO_ACTION"


def test_emergency_stop_fail_closed_primacy():
    """Verifies that active EmergencyStop immediately blocks execution and forces revalidation post-reset."""
    e_stop = get_emergency_stop_service()
    e_stop.trigger("Immediate administrative halt for security testing")

    service = get_control_plane_service()

    cycle = service.dispatch_trigger(
        trigger_type=TriggerType.USER_REQUEST,
        payload={"objective": "Deploy to production", "requires_action": True},
        scope="production_deploy",
    )

    assert cycle.status == ControlCycleStatus.BLOCKED
    assert cycle.no_action_reason == NoActionReason.EMERGENCY_STOP_ACTIVE
    assert cycle.result == "EMERGENCY_STOP_FAIL_CLOSED"

    # Reset emergency stop
    e_stop.reset()

    # Post-clearing reassessment
    reval_cycle = service.reassess(scope="production_deploy")
    assert reval_cycle.status in [ControlCycleStatus.COMPLETED, ControlCycleStatus.NO_ACTION]


def test_deterministic_read_only_replay():
    """Verifies that a completed cycle can be deterministically replayed without side effects."""
    service = get_control_plane_service()

    orig_cycle = service.dispatch_trigger(
        trigger_type=TriggerType.USER_REQUEST,
        payload={
            "objective": "Verify replay state",
            "requires_action": True,
            "simulated_action_success": True,
            "simulated_verification_success": True,
        },
        scope="replay_test",
    )
    assert orig_cycle.cycle_id is not None

    replay_res = service.replay_cycle(orig_cycle.cycle_id)
    assert replay_res["replayed_cycle_id"] == orig_cycle.cycle_id
    assert replay_res["replay_mode"] == "READ_ONLY_RECONSTRUCTION"
    assert replay_res["side_effects_executed"] is False
    assert replay_res["original_status"] == orig_cycle.status.value


def test_rest_api_endpoints():
    """Verifies all Control Plane REST API endpoints."""
    app = create_app()
    client = TestClient(app)

    # 1. Status
    res_status = client.get("/api/v1/control/status")
    assert res_status.status_code == 200
    stat_data = res_status.json()
    assert "control_mode" in stat_data
    assert "emergency_stop_active" in stat_data
    assert "metrics" in stat_data

    # 2. Mode
    res_mode = client.get("/api/v1/control/mode")
    assert res_mode.status_code == 200
    assert "control_mode" in res_mode.json()

    # 3. Health
    res_health = client.get("/api/v1/control/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"

    # 4. Trigger reassessment
    res_reassess = client.post("/api/v1/control/reassess?scope=API_TEST")
    assert res_reassess.status_code == 200
    cycle_id = res_reassess.json()["cycle_id"]

    # 5. List cycles
    res_cycles = client.get("/api/v1/control/cycles")
    assert res_cycles.status_code == 200
    assert isinstance(res_cycles.json(), list)
    assert len(res_cycles.json()) > 0

    # 6. Cycle detail
    res_cycle = client.get(f"/api/v1/control/cycles/{cycle_id}")
    assert res_cycle.status_code == 200
    assert res_cycle.json()["cycle_id"] == cycle_id

    # 7. Timeline
    res_timeline = client.get(f"/api/v1/control/cycles/{cycle_id}/timeline")
    assert res_timeline.status_code == 200
    assert isinstance(res_timeline.json(), list)

    # 8. Replay
    res_replay = client.get(f"/api/v1/control/cycles/{cycle_id}/replay")
    assert res_replay.status_code == 200
    assert res_replay.json()["side_effects_executed"] is False


def test_cli_commands():
    """Verifies that the Click CLI commands execute properly."""
    runner = CliRunner()

    res_status = runner.invoke(control_plane_cli, ["status"])
    assert res_status.exit_code == 0
    assert "KAIRO COGNITIVE CONTROL PLANE" in res_status.output

    res_mode = runner.invoke(control_plane_cli, ["mode"])
    assert res_mode.exit_code == 0
    assert "Current Control Mode:" in res_mode.output

    res_health = runner.invoke(control_plane_cli, ["health"])
    assert res_health.exit_code == 0
    assert "Control Plane Status:" in res_health.output

    res_reassess = runner.invoke(control_plane_cli, ["reassess", "--scope", "CLI_TEST"])
    assert res_reassess.exit_code == 0
    assert "REASSESSMENT CYCLE INITIATED" in res_reassess.output

    res_cycles = runner.invoke(control_plane_cli, ["cycles", "--limit", "5"])
    assert res_cycles.exit_code == 0
    assert "CYCLE ID" in res_cycles.output

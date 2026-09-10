"""Unit and integration tests for ExecutionGate, RealWorldTransitionEngine, Calibration, and REST API (Task 56)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.calibration import SimulationCalibrator
from app.simulation.execution_gate import RealWorldTransitionEngine
from app.simulation.safety import StaleSimulationError
from app.simulation.schemas import (
    ExecutionGateStatus,
    RiskCategory,
    Simulation,
    SimulationRisk,
    SimulationSnapshot,
    SimulationStatus,
)
from app.simulation.snapshots import compute_state_hash


def test_execution_gate_drift_and_staleness():
    gate_engine = RealWorldTransitionEngine()
    initial_twin = {"services": {"api": {"replicas": 3}}}
    state_to_hash = {"world": {}, "digital_twin": initial_twin, "telemetry": {}}
    base_hash = compute_state_hash(state_to_hash)

    snapshot = SimulationSnapshot(
        snapshot_id="snap_gate_1",
        source_entity="digital_twin",
        world_state={},
        digital_twin_state=initial_twin,
        telemetry_state={},
        baseline_hash=base_hash,
    )

    simulation = Simulation(
        simulation_id="sim_gate_1",
        source_snapshot_id="snap_gate_1",
        scenario_id="scen_gate_1",
        initial_state={},
        future_state={},
        diff={},
        effects=[],
        risks=[],
        assumptions=[],
        status=SimulationStatus.COMPLETED,
    )

    # 1. State drifted: Real-world state has 5 replicas instead of 3
    drifted_real = {"world": {}, "digital_twin": {"services": {"api": {"replicas": 5}}}, "telemetry": {}}
    gate = gate_engine.evaluate_gate(
        simulation=simulation,
        snapshot=snapshot,
        current_real_state=drifted_real,
    )
    assert gate.status == ExecutionGateStatus.STALE
    assert gate.drift_detected is True

    # Attempting to execute with a stale gate must raise StaleSimulationError
    with pytest.raises(StaleSimulationError):
        gate_engine.assert_gate_ready(gate.gate_id)


def test_execution_gate_high_risk_requires_approval():
    gate_engine = RealWorldTransitionEngine()
    initial_twin = {"services": {"api": {"replicas": 3}}}
    state_to_hash = {"world": {}, "digital_twin": initial_twin, "telemetry": {}}
    base_hash = compute_state_hash(state_to_hash)

    snapshot = SimulationSnapshot(
        snapshot_id="snap_gate_2",
        source_entity="digital_twin",
        world_state={},
        digital_twin_state=initial_twin,
        telemetry_state={},
        baseline_hash=base_hash,
    )

    # Simulation with a critical risk
    sim_risk = SimulationRisk(
        risk_id="r1",
        scenario_id="scen_gate_2",
        category=RiskCategory.AVAILABILITY,
        probability=0.8,
        impact="CRITICAL",
        confidence=0.9,
        evidence=["Single point of failure"],
        mitigation="Add standby node",
    )

    simulation = Simulation(
        simulation_id="sim_gate_2",
        source_snapshot_id="snap_gate_2",
        scenario_id="scen_gate_2",
        initial_state={},
        future_state={},
        diff={},
        effects=[],
        risks=[sim_risk],
        assumptions=[],
        status=SimulationStatus.COMPLETED,
    )

    # Without user approval -> NEEDS_APPROVAL
    gate_unapproved = gate_engine.evaluate_gate(
        simulation=simulation,
        snapshot=snapshot,
        current_real_state=state_to_hash,
        user_approved=False,
    )
    assert gate_unapproved.status == ExecutionGateStatus.NEEDS_APPROVAL

    # With user approval -> READY
    gate_approved = gate_engine.evaluate_gate(
        simulation=simulation,
        snapshot=snapshot,
        current_real_state=state_to_hash,
        user_approved=True,
    )
    assert gate_approved.status == ExecutionGateStatus.READY
    assert len(gate_approved.verification_plan) >= 1
    # Does not raise
    gate_engine.assert_gate_ready(gate_approved.gate_id)


def test_simulation_calibrator_error_and_drift():
    calibrator = SimulationCalibrator(drift_mae_threshold=15.0, bias_threshold=5.0)

    # Record 3 observations: predicted vs actual
    # Sim 1: pred=100, actual=105 (err=5, bias=-5)
    # Sim 2: pred=100, actual=110 (err=10, bias=-10)
    # Sim 3: pred=100, actual=115 (err=15, bias=-15)
    calibrator.record_outcome_pair("sim_1", "p95_latency", 100.0, 105.0)
    calibrator.record_outcome_pair("sim_2", "p95_latency", 100.0, 110.0)
    calibrator.record_outcome_pair("sim_3", "p95_latency", 100.0, 115.0)

    report = calibrator.evaluate_model_calibration("p95_latency")
    assert report.sample_count == 3
    assert report.mean_absolute_error == 10.0
    assert report.mean_bias == -10.0
    assert report.is_biased is True
    assert "Systematic bias detected: model under-predicts" in report.diagnostics


def test_simulation_rest_api_full_flow():
    client = TestClient(app)

    # 1. Capture snapshot
    snap_resp = client.post(
        "/api/v1/simulation/snapshots",
        json={
            "source_entity": "test_env",
            "world_state": {"cluster": "test_cluster"},
            "digital_twin_state": {"services": {"web": {"replicas": 2}}},
            "telemetry_state": {"latency": 25.0},
        },
    )
    assert snap_resp.status_code == 200
    snap_data = snap_resp.json()
    snapshot_id = snap_data["snapshot_id"]
    assert snapshot_id.startswith("snap_")

    # 2. Create scenario
    scen_resp = client.post(
        "/api/v1/simulation/scenarios",
        json={
            "name": "Scale Web Service",
            "scenario_type": "SCALE_UP",
            "baseline_snapshot_id": snapshot_id,
            "interventions": [
                {
                    "intervention_id": "i1",
                    "target": "services.web.replicas",
                    "operation": "SCALE_REPLICAS",
                    "before": 2,
                    "hypothetical_after": 4,
                }
            ],
            "horizon": "SHORT_TERM",
        },
    )
    assert scen_resp.status_code == 200
    scen_data = scen_resp.json()
    scenario_id = scen_data["scenario_id"]

    # 3. Run simulation
    run_resp = client.post(
        "/api/v1/simulation/run",
        json={"scenario_id": scenario_id},
    )
    assert run_resp.status_code == 200
    sim_data = run_resp.json()
    assert sim_data["environment_label"] == "SIMULATION_ONLY"
    assert sim_data["is_hypothetical"] is True
    assert sim_data["status"] == "COMPLETED"
    simulation_id = sim_data["simulation_id"]

    # 4. Evaluate execution gate
    gate_resp = client.post(
        "/api/v1/simulation/gates/evaluate",
        json={
            "simulation_id": simulation_id,
            "current_real_state": {
                "world": {"cluster": "test_cluster"},
                "digital_twin": {"services": {"web": {"replicas": 2}}},
                "telemetry": {"latency": 25.0},
            },
            "user_approved": True,
        },
    )
    assert gate_resp.status_code == 200
    gate_data = gate_resp.json()
    assert gate_data["status"] == "READY"
    assert gate_data["drift_detected"] is False

    # 5. Record calibration
    cal_resp = client.post(
        "/api/v1/simulation/calibrate",
        json={
            "simulation_id": simulation_id,
            "metric_name": "web_replicas",
            "predicted_value": 4.0,
            "actual_value": 4.0,
        },
    )
    assert cal_resp.status_code == 200
    assert cal_resp.json()["error"] == 0.0

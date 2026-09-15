"""Unit and integration tests for Task 89 Autonomous Recovery Simulation & Digital Twin."""

from __future__ import annotations

import copy
import json
import pytest
from datetime import datetime, timezone, timedelta
from app.simulation.digital_twin import RuntimeDigitalTwin, RuntimeSnapshot
from app.simulation.recovery_models import (
    ConsistencyLevel,
    SimulationMode,
    UncertaintyLevel,
    RecoveryScenario,
)
from app.simulation.recovery_engine import RecoverySimulator
from app.simulation.drift_detector import StaleSimulationDetector
from app.simulation.scorecards import (
    PredictionVsRealityComparator,
    ScorecardManager,
    RecoveryRegressionDetector,
    ResilienceBenchmarkEngine,
)
from app.simulation.chaos_library import ChaosScenarioLibrary
from app.simulation.recovery_service import RecoverySimulationService


@pytest.mark.asyncio
async def test_digital_twin_snapshot_capture_and_immutability():
    twin = RuntimeDigitalTwin()
    snapshot = await twin.capture_current_state(
        custom_overrides={
            "compute": {"memory_rss_mb": 256.0, "cpu_usage_pct": 12.0},
            "security": {"api_key": "SECRET_SHOULD_BE_REDACTED", "security_level": "HIGH"},
        }
    )

    assert snapshot.snapshot_id.startswith("snap_")
    assert snapshot.hash_sha256 != ""
    assert snapshot.is_immutable is True
    assert snapshot.consistency_level == ConsistencyLevel.BOUNDED
    assert snapshot.environment_label == "SIMULATION_ONLY"
    assert snapshot.resource_state["memory_rss_mb"] == 256.0
    # Zero-secret verification: sensitive keys redacted
    assert "api_key" not in snapshot.security_state or snapshot.security_state.get("api_key") == "[REDACTED]"


@pytest.mark.asyncio
async def test_recovery_simulator_candidate_generation_and_pareto_ranking():
    twin = RuntimeDigitalTwin()
    snapshot = await twin.capture_current_state()

    simulator = RecoverySimulator()
    scenario = RecoveryScenario(
        scenario_id="scen_test_01",
        base_snapshot_id=snapshot.snapshot_id,
        description="Simulate native runtime crash recovery",
        hypothesis="RESTART_COMPONENT is optimal for native runtime daemon crash",
        target_subsystem="native_runtime",
        simulation_mode=SimulationMode.ANALYTICAL,
    )

    result = simulator.simulate_recovery(snapshot, scenario)

    assert result.simulation_id.startswith("sim_")
    assert len(result.candidates) >= 3
    assert result.recommended_candidate is not None
    assert result.recommended_candidate.is_recommended is True
    assert result.recommended_candidate.pareto_rank == 1
    # Check that candidates have qualitative uncertainty and duration intervals
    for c in result.candidates:
        assert c.duration_interval != ""
        assert isinstance(c.uncertainty, UncertaintyLevel)
        assert 0.0 <= c.blast_radius_score <= 1.0
        assert 0.0 <= c.recovery_probability <= 1.0

    # Ensure explicit assumptions and limitations are documented
    assert len(result.assumptions) >= 3
    assert len(result.limitations) >= 2


@pytest.mark.asyncio
async def test_stale_simulation_drift_detector():
    twin = RuntimeDigitalTwin()
    base_snapshot = await twin.capture_current_state()

    detector = StaleSimulationDetector(max_snapshot_age_seconds=60.0)

    # 1. Fresh identical snapshot should not be stale
    report_clean = detector.evaluate_staleness(base_snapshot, base_snapshot)
    assert report_clean.is_stale is False
    assert report_clean.drift_score == 0.0

    # 2. Artificially expired snapshot
    expired_snapshot = base_snapshot.model_copy(
        update={"timestamp": datetime.now(timezone.utc) - timedelta(seconds=120)}
    )
    report_expired = detector.evaluate_staleness(expired_snapshot, base_snapshot)
    assert report_expired.is_stale is True
    assert any("expired" in r.lower() for r in report_expired.staleness_reasons)

    # 3. Drifted snapshot with emergency stop engaged
    drifted_snapshot = base_snapshot.model_copy(
        update={
            "security_state": {"emergency_stop_active": True},
            "hash_sha256": "drifted_hash_123",
        }
    )
    report_drifted = detector.evaluate_staleness(base_snapshot, drifted_snapshot)
    assert report_drifted.is_stale is True
    assert any("emergencystop" in r.lower() for r in report_drifted.staleness_reasons)


def test_chaos_scenario_library_14_scenarios():
    lib = ChaosScenarioLibrary()
    scenarios = lib.list_scenarios()
    assert len(scenarios) == 14

    expected_ids = [
        "chaos_crash_native_daemon",
        "chaos_ipc_socket_disconnect",
        "chaos_memory_leak_pressure",
        "chaos_cpu_exhaustion_spin",
        "chaos_corrupt_sandbox",
        "chaos_stale_connection_pool",
        "chaos_network_packet_loss",
        "chaos_database_contention",
        "chaos_zombie_process_accumulation",
        "chaos_emergency_stop_trip",
        "chaos_workflow_step_failure",
        "chaos_authorization_expiry",
        "chaos_toctou_mutation",
        "chaos_cascading_subsystem_outage",
    ]

    scenario_ids = [s["id"] for s in scenarios]
    for exp_id in expected_ids:
        assert exp_id in scenario_ids


@pytest.mark.asyncio
async def test_prediction_vs_reality_calibration_and_scorecards():
    comparator = PredictionVsRealityComparator()
    scorecards = ScorecardManager()
    reg_detector = RecoveryRegressionDetector(scorecards)
    benchmark_engine = ResilienceBenchmarkEngine()

    twin = RuntimeDigitalTwin()
    snapshot = await twin.capture_current_state()
    simulator = RecoverySimulator()
    scenario = RecoveryScenario(
        scenario_id="scen_calib_01",
        base_snapshot_id=snapshot.snapshot_id,
        description="Test calibration",
        hypothesis="Calibrate RETRY",
        target_subsystem="workflow",
    )
    sim_result = simulator.simulate_recovery(snapshot, scenario)
    cand = sim_result.candidates[0]

    # Compare prediction with actual observed metrics
    record = comparator.compare(
        simulation_id=sim_result.simulation_id,
        recovery_id="rec_actual_001",
        candidate=cand,
        actual_duration_seconds=1.2,
        actual_resource_cost={"cpu_delta_pct": 3.0, "mem_delta_mb": 8.0},
        actual_risk_score=0.1,
        actual_blast_radius=0.08,
        verification_passed=True,
    )

    assert record.comparison_id.startswith("cmp_")
    assert record.duration_error >= 0.0
    assert record.verification_match is True

    # Update scorecard
    updated_card = scorecards.record_execution(
        strategy=cand.strategy,
        success=True,
        duration_ms=1200.0,
        verification_passed=True,
    )
    assert updated_card.total_attempts > 0
    assert updated_card.status == "HEALTHY"

    # Verify benchmark engine produces 7 dimensions
    bench = benchmark_engine.compute_benchmark(scorecards)
    assert bench.benchmark_id.startswith("bmk_")
    assert len(bench.dimensions) == 7
    assert "detection" in bench.dimensions
    assert "recovery" in bench.dimensions
    assert "verification" in bench.dimensions


@pytest.mark.asyncio
async def test_recovery_simulation_service_e2e_drill():
    svc = RecoverySimulationService()

    # 1. Capture snapshot
    snap = await svc.capture_snapshot()
    assert snap.snapshot_id is not None

    # 2. Run simulation
    sim_res = await svc.run_simulation(
        target_subsystem="native_runtime",
        hypothesis="Test native runtime recovery",
    )
    assert sim_res.simulation_id is not None
    assert sim_res.recommended_candidate is not None

    # 3. Run chaos drill
    chaos_res = await svc.run_chaos_drill("chaos_crash_native_daemon")
    assert chaos_res.simulation_id is not None
    assert chaos_res.recommended_candidate.strategy in [
        "RESTART_COMPONENT",
        "RECONNECT",
        "DEGRADE_CAPABILITY",
        "ESCALATE",
    ]

    # 4. Calibrate
    calib = svc.record_actual_recovery(
        simulation_id=sim_res.simulation_id,
        recovery_id="rec_99",
        strategy="RESTART_COMPONENT",
        actual_duration_seconds=3.2,
        actual_resource_cost={"cpu_delta_pct": 8.0, "mem_delta_mb": 30.0},
        actual_risk_score=0.12,
        actual_blast_radius=0.30,
        verification_passed=True,
    )
    assert calib.comparison_id is not None
    assert calib.verification_match is True

    # 5. List scorecards and benchmarks
    cards = svc.get_scorecards()
    assert len(cards) >= 10
    bench = svc.get_resilience_benchmark()
    assert bench.mttr_seconds > 0.0


@pytest.mark.asyncio
async def test_simulation_safety_invariants_and_zero_secrets():
    """Verify zero secrets enter snapshots and simulation outputs are strictly SIMULATION_ONLY."""
    twin = RuntimeDigitalTwin()
    leak_payload = {
        "runtime": {
            "token": "sk-secret-token-12345",
            "api_key": "kairo-live-key-xyz",
            "password": "super-secret-password",
        },
        "security": {
            "auth_token": "bearer-token-abc",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----",
        },
    }
    snapshot = await twin.capture_current_state(custom_overrides=leak_payload)
    dumped = snapshot.model_dump()
    dumped_str = json.dumps(dumped, default=str)

    # Invariant: No sensitive credentials in plaintext
    assert "sk-secret-token-12345" not in dumped_str
    assert "super-secret-password" not in dumped_str
    assert "kairo-live-key-xyz" not in dumped_str
    assert "bearer-token-abc" not in dumped_str
    assert "-----BEGIN RSA PRIVATE KEY-----" not in dumped_str

    # Invariant: Snapshot is marked SIMULATION_ONLY and immutable
    assert snapshot.environment_label == "SIMULATION_ONLY"
    assert snapshot.is_immutable is True
    assert len(snapshot.hash_sha256) == 32


@pytest.mark.asyncio
async def test_all_14_chaos_scenarios_perturbation_and_generation():
    """Verify all 14 canonical chaos drill scenarios formulate valid simulations with perturbations."""
    twin = RuntimeDigitalTwin()
    base_snap = await twin.capture_current_state()
    chaos_lib = ChaosScenarioLibrary()

    scenarios = chaos_lib.list_scenarios()
    assert len(scenarios) == 14

    for sc_meta in scenarios:
        sc_id = sc_meta["id"]
        scenario, perturbed_snap = chaos_lib.build_recovery_scenario(sc_id, base_snap)

        assert scenario.scenario_id.startswith(f"scen_{sc_id}")
        assert scenario.target_subsystem == sc_meta["subsystem"]
        assert len(scenario.actions) > 0
        assert perturbed_snap.snapshot_id != base_snap.snapshot_id
        assert perturbed_snap.hash_sha256 != ""

        # Run simulation against perturbed snapshot
        sim = RecoverySimulator()
        res = sim.simulate_recovery(perturbed_snap, scenario)
        assert res.scenario_id == scenario.scenario_id
        assert len(res.candidates) > 0
        assert res.recommended_candidate is not None
        assert res.environment_label == "SIMULATION_ONLY"
        assert res.model_versions["simulation_engine"] == "2.0.0"


def test_stale_simulation_drift_thresholds_and_triggers():
    """Verify StaleSimulationDetector catches age expiration, instance change, and fingerprint drifts."""
    detector = StaleSimulationDetector(max_snapshot_age_seconds=10.0, max_allowed_drift_score=0.35)
    now = datetime.now(timezone.utc)

    # 1. Base snapshot
    base = RuntimeSnapshot(
        snapshot_id="snap_base",
        timestamp=now,
        runtime_instance_id="rt_inst_1",
        capability_fingerprint="cfp_v1",
        configuration_fingerprint="cfg_v1",
        resource_state={"memory_rss_mb": 100.0},
        health_state={"system": "HEALTHY"},
        security_state={"emergency_stop_active": False},
    )

    # 2. Identical clone -> zero drift
    same = copy.deepcopy(base)
    report = detector.evaluate_staleness(base, same)
    assert report.is_stale is False
    assert report.drift_score == 0.0

    # 3. Capability fingerprint drifted -> triggers staleness
    drifted_cap = copy.deepcopy(base)
    drifted_cap.capability_fingerprint = "cfp_v2_updated"
    report_cap = detector.evaluate_staleness(base, drifted_cap)
    assert report_cap.is_stale is True
    assert any("Capability fingerprint drifted" in r for r in report_cap.staleness_reasons)

    # 4. Runtime instance changed (daemon crashed and restarted)
    restarted = copy.deepcopy(base)
    restarted.runtime_instance_id = "rt_inst_2"
    report_rst = detector.evaluate_staleness(base, restarted)
    assert report_rst.is_stale is True
    assert any("Runtime instance changed" in r for r in report_rst.staleness_reasons)

    # 5. Emergency Stop engaged after snapshot
    stopped = copy.deepcopy(base)
    stopped.security_state["emergency_stop_active"] = True
    report_stop = detector.evaluate_staleness(base, stopped)
    assert report_stop.is_stale is True
    assert any("EmergencyStop was engaged" in r for r in report_stop.staleness_reasons)


def test_recovery_regression_detection():
    """Verify RecoveryRegressionDetector identifies strategies whose success rate drops below 80%."""
    scorecards = ScorecardManager()
    scorecards._scorecards.clear()
    regressions = RecoveryRegressionDetector(scorecard_manager=scorecards)

    # Record 4 attempts with 2 failures for RETRY -> failure_rate = 50%
    scorecards.record_execution("RETRY", success=True, duration_ms=1000.0, verification_passed=True)
    scorecards.record_execution("RETRY", success=False, duration_ms=1200.0, verification_passed=False)
    scorecards.record_execution("RETRY", success=False, duration_ms=1100.0, verification_passed=False)
    scorecards.record_execution("RETRY", success=True, duration_ms=1050.0, verification_passed=True)

    degraded_list = regressions.detect_regressions()
    assert len(degraded_list) >= 1
    degraded = degraded_list[0]
    assert degraded["strategy"] == "RETRY"
    assert degraded["status"] == "DEGRADED"
    assert degraded["failure_rate"] == 0.50

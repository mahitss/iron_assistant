#!/usr/bin/env python3
"""Autonomous Recovery Simulation, Digital Twin & Resilience Validation E2E Verification.

Task 89 Verification Script: Demonstrates the end-to-end simulation lifecycle:
1. Operational Digital Twin Snapshot Capture & Immutability
2. Zero-Secret Sanitization Verification
3. Consequence Simulation & Pareto-Optimal Trade-Off Ranking
4. Stale Simulation Drift Detection & Emergency Stop Preemption
5. 14 Canonical Chaos Resilience Drills
6. Prediction vs Reality Metacognitive Calibration
7. Strategy Reliability Scorecards & 7-Dimension Resilience Benchmarks
8. Recovery Regression Detection (< 80% Success Rate Guard)
"""

import asyncio
import os
import pathlib
import sys
import time

# Ensure backend directory is on sys.path
backend_dir = pathlib.Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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


def log_step(title: str):
    print(f"\n{'='*70}\n[*] {title}\n{'='*70}")


async def main():
    print("======================================================================")
    print("  KAIRO TASK 89: AUTONOMOUS RECOVERY SIMULATION & DIGITAL TWIN E2E     ")
    print("======================================================================")

    # -------------------------------------------------------------------------
    # STEP 1: Operational Snapshot Capture & Immutability
    # -------------------------------------------------------------------------
    log_step("STEP 1: Operational Snapshot Capture & Immutability")
    twin = RuntimeDigitalTwin()
    leak_test_payload = {
        "api_key": "sk-test-secret-key-9999",
        "password": "super-secret-password-1234",
        "auth_token": "bearer-test-token-5678",
    }
    snapshot = await twin.capture_current_state(custom_overrides={"security": leak_test_payload})
    print(f"  Captured Snapshot ID:  {snapshot.snapshot_id}")
    print(f"  Cryptographic Hash:    {snapshot.hash_sha256}")
    print(f"  Consistency Level:     {snapshot.consistency_level.value}")
    print(f"  Environment Label:     {snapshot.environment_label}")
    print(f"  Is Immutable:          {snapshot.is_immutable}")

    assert snapshot.snapshot_id.startswith("snap_")
    assert snapshot.environment_label == "SIMULATION_ONLY"
    assert snapshot.is_immutable is True
    print("  [✓] Digital twin snapshot captured with cryptographic immutability.")

    # -------------------------------------------------------------------------
    # STEP 2: Zero-Secret Leakage Invariant Verification
    # -------------------------------------------------------------------------
    log_step("STEP 2: Zero-Secret Leakage Invariant Verification")
    dumped_str = snapshot.model_dump_json()
    assert "sk-test-secret-key-9999" not in dumped_str
    assert "super-secret-password-1234" not in dumped_str
    assert "bearer-test-token-5678" not in dumped_str
    print("  Sanitized Content Check:")
    print("  - API keys redacted:      [VERIFIED]")
    print("  - Passwords redacted:     [VERIFIED]")
    print("  - Auth tokens redacted:   [VERIFIED]")
    print("  [✓] Zero plaintext secrets entered digital twin snapshot.")

    # -------------------------------------------------------------------------
    # STEP 3: Consequence Simulation & Pareto Candidate Ranking
    # -------------------------------------------------------------------------
    log_step("STEP 3: Consequence Simulation & Pareto Candidate Ranking")
    simulator = RecoverySimulator()
    scenario = RecoveryScenario(
        scenario_id="scen_e2e_01",
        base_snapshot_id=snapshot.snapshot_id,
        description="E2E native runtime crash consequence simulation",
        hypothesis="Evaluate optimal Pareto recovery strategy for native runtime crash",
        target_subsystem="native_runtime",
        simulation_mode=SimulationMode.ANALYTICAL,
    )
    sim_result = simulator.simulate_recovery(snapshot, scenario)
    print(f"  Simulation ID:         {sim_result.simulation_id}")
    print(f"  Candidates Evaluated:  {len(sim_result.candidates)}")
    print(f"  Recommended Candidate: {sim_result.recommended_candidate.strategy}")
    print(f"  Pareto Rank:           {sim_result.recommended_candidate.pareto_rank}")
    print(f"  Expected Duration:     {sim_result.recommended_candidate.duration_interval}")
    print(f"  Uncertainty Level:     {sim_result.recommended_candidate.uncertainty.value}")
    print(f"  Recovery Probability:  {sim_result.recommended_candidate.recovery_probability:.1%}")

    assert len(sim_result.candidates) >= 3
    assert sim_result.recommended_candidate is not None
    assert sim_result.recommended_candidate.pareto_rank == 1
    print("  [✓] Multi-candidate Pareto ranking synthesized successfully.")

    # -------------------------------------------------------------------------
    # STEP 4: Stale Simulation Drift Detection & Invalidation
    # -------------------------------------------------------------------------
    log_step("STEP 4: Stale Simulation Drift Detection & Invalidation")
    drift_detector = StaleSimulationDetector(max_snapshot_age_seconds=60.0)

    # 4a. Fresh evaluation
    fresh_report = drift_detector.evaluate_staleness(snapshot, snapshot)
    print(f"  Baseline Drift Score:  {fresh_report.drift_score} (Stale: {fresh_report.is_stale})")
    assert fresh_report.is_stale is False

    # 4b. Drifted evaluation with Emergency Stop engaged
    drifted_snapshot = snapshot.model_copy(
        update={
            "security_state": {"emergency_stop_active": True},
            "hash_sha256": "drift_e_stop_hash",
        }
    )
    drift_report = drift_detector.evaluate_staleness(snapshot, drifted_snapshot)
    print(f"  Post-E-Stop Drift:     Stale={drift_report.is_stale}, Reasons={drift_report.staleness_reasons}")
    assert drift_report.is_stale is True
    print("  [✓] Stale simulation drift detector successfully halted drifted recovery.")

    # -------------------------------------------------------------------------
    # STEP 5: Chaos Resiliency Drill Library (14 Scenarios)
    # -------------------------------------------------------------------------
    log_step("STEP 5: Chaos Resiliency Drill Library (14 Scenarios)")
    chaos_lib = ChaosScenarioLibrary()
    scenarios = chaos_lib.list_scenarios()
    print(f"  Total Chaos Scenarios Loaded: {len(scenarios)}")
    assert len(scenarios) == 14

    for sc in scenarios[:3]:
        print(f"  - [{sc['id']}] subsystem={sc['subsystem']} mode={sc['mode'].value}")
    print(f"  ... and {len(scenarios) - 3} more scenarios.")

    # Run drill for native daemon crash
    scenario, perturbed_snap = chaos_lib.build_recovery_scenario("chaos_crash_native_daemon", snapshot)
    chaos_sim = simulator.simulate_recovery(perturbed_snap, scenario)
    print(f"  Drill Result: Simulation {chaos_sim.simulation_id} recommended {chaos_sim.recommended_candidate.strategy}")
    assert chaos_sim.recommended_candidate is not None
    print("  [✓] Chaos scenario generation and perturbation drill completed.")

    # -------------------------------------------------------------------------
    # STEP 6: Metacognitive Calibration (Prediction vs Reality)
    # -------------------------------------------------------------------------
    log_step("STEP 6: Metacognitive Calibration (Prediction vs Reality)")
    comparator = PredictionVsRealityComparator()
    cand = sim_result.recommended_candidate
    comparison = comparator.compare(
        simulation_id=sim_result.simulation_id,
        recovery_id="rec_e2e_actual_001",
        candidate=cand,
        actual_duration_seconds=2.8,
        actual_resource_cost={"cpu_delta_pct": 5.0, "mem_delta_mb": 15.0},
        actual_risk_score=0.1,
        actual_blast_radius=0.12,
        verification_passed=True,
    )
    print(f"  Comparison ID:         {comparison.comparison_id}")
    print(f"  Predicted vs Actual:   {cand.predicted_duration_seconds}s vs {comparison.actual_duration_seconds}s")
    print(f"  Duration Error:        {comparison.duration_error:.2f}s")
    print(f"  Verification Match:    {comparison.verification_match}")
    assert comparison.verification_match is True
    print("  [✓] Metacognitive prediction-vs-reality calibrated.")

    # -------------------------------------------------------------------------
    # STEP 7: Strategy Reliability Scorecards & 7-Dimension Benchmarks
    # -------------------------------------------------------------------------
    log_step("STEP 7: Strategy Reliability Scorecards & 7-Dimension Benchmarks")
    scorecards = ScorecardManager()
    scorecards.record_execution(cand.strategy, success=True, duration_ms=2800.0, verification_passed=True)

    benchmark_engine = ResilienceBenchmarkEngine()
    bench = benchmark_engine.compute_benchmark(scorecards)
    print(f"  Benchmark ID:          {bench.benchmark_id}")
    print(f"  MTTR (Seconds):        {bench.mttr_seconds:.2f}s")
    print(f"  MTBF (Hours):          {bench.mtbf_hours:.1f}h")
    print(f"  Resource Recovery:     {bench.resource_recovery_pct:.1f}%")
    print(f"  Dimensions Evaluated:  {list(bench.dimensions.keys())}")
    assert len(bench.dimensions) == 7
    print("  [✓] 7-dimension resilience benchmark computed.")

    # -------------------------------------------------------------------------
    # STEP 8: Recovery Regression Detection Guard
    # -------------------------------------------------------------------------
    log_step("STEP 8: Recovery Regression Detection Guard")
    reg_detector = RecoveryRegressionDetector(scorecards)
    # Intentionally record failures for a strategy to test regression trip
    for _ in range(3):
        scorecards.record_execution("FLAKY_STRATEGY", success=False, duration_ms=5000.0, verification_passed=False)
    scorecards.record_execution("FLAKY_STRATEGY", success=True, duration_ms=1000.0, verification_passed=True)

    degraded = reg_detector.detect_regressions()
    print(f"  Degraded Strategies:   {[d['strategy'] for d in degraded]}")
    assert any(d["strategy"] == "FLAKY_STRATEGY" for d in degraded)
    print("  [✓] Regression detector successfully flagged degraded recovery strategy.")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n======================================================================")
    print("  [✓] ALL 8 TASK 89 SIMULATION & DIGITAL TWIN CHECKS PASSED!           ")
    print("======================================================================")


if __name__ == "__main__":
    asyncio.run(main())

"""Autonomous Recovery Simulation & Digital Twin Service (Task 89).

Provides the unified business logic and control plane for:
- Capturing immutable operational digital twin snapshots.
- Running pre-recovery simulations with multi-objective Pareto ranking.
- Detecting stale simulations and state drift against live reality.
- Executing isolated chaos drills across 14 canonical resilience scenarios.
- Tracking strategy scorecards and multi-dimensional resilience benchmarks.
- Calibrating simulated predictions against actual post-recovery execution.
- Enforcing Simulation Firewall safety invariants (SIMULATION_ONLY environment).
"""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.simulation.chaos_library import (
    ChaosScenarioLibrary,
    get_chaos_library,
)
from app.simulation.digital_twin import (
    RuntimeDigitalTwin,
    RuntimeSnapshot,
    get_digital_twin,
)
from app.simulation.drift_detector import (
    StaleSimulationDetector,
    StateDriftReport,
    get_drift_detector,
)
from app.simulation.recovery_engine import (
    RecoverySimulator,
    get_recovery_simulator,
)
from app.simulation.recovery_models import (
    ConsistencyLevel,
    PredictionVsRealityRecord,
    RecoveryCandidate,
    RecoveryScenario,
    RecoverySimulationResult,
    RecoveryStrategyScorecard,
    ResilienceBenchmark,
    SimulationMode,
)
from app.simulation.scorecards import (
    PredictionVsRealityComparator,
    RecoveryRegressionDetector,
    ResilienceBenchmarkEngine,
    ScorecardManager,
    get_benchmark_engine,
    get_comparator,
    get_regression_detector,
    get_scorecard_manager,
)

logger = logging.getLogger("kairo.simulation.recovery_service")


def _emit_simulation_event(event_type: str, data: dict[str, Any]) -> None:
    """Safely emits a simulation event to the unified EventBus without blocking."""
    try:
        import asyncio
        from app.events.bus import get_event_bus
        from app.events.schemas import Event, EventSource
        event = Event(
            event_type=event_type,
            source=EventSource.SYSTEM,
            payload=data,
        )
        try:
            loop = asyncio.get_running_loop()
            bus = get_event_bus()
            loop.create_task(bus.publish(event))
        except RuntimeError:
            pass
    except Exception as err:
        logger.debug("Simulation event emission skipped: %s", err)


class RecoverySimulationService:
    """Core orchestration service for Task 89 Autonomous Recovery Simulation."""

    def __init__(
        self,
        digital_twin: RuntimeDigitalTwin | None = None,
        simulator: RecoverySimulator | None = None,
        drift_detector: StaleSimulationDetector | None = None,
        chaos_lib: ChaosScenarioLibrary | None = None,
        comparator: PredictionVsRealityComparator | None = None,
        scorecards: ScorecardManager | None = None,
        regressions: RecoveryRegressionDetector | None = None,
        benchmarks: ResilienceBenchmarkEngine | None = None,
    ) -> None:
        self.twin = digital_twin or get_digital_twin()
        self.simulator = simulator or get_recovery_simulator()
        self.drift_detector = drift_detector or get_drift_detector()
        self.chaos_lib = chaos_lib or get_chaos_library()
        self.comparator = comparator or get_comparator()
        self.scorecards = scorecards or get_scorecard_manager()
        self.regressions = regressions or get_regression_detector()
        self.benchmarks = benchmarks or get_benchmark_engine()
        self._simulation_history: dict[str, RecoverySimulationResult] = {}
        self._snapshot_history: dict[str, RuntimeSnapshot] = {}

    async def capture_snapshot(
        self,
        custom_overrides: dict[str, Any] | None = None,
        consistency: ConsistencyLevel = ConsistencyLevel.BOUNDED,
    ) -> RuntimeSnapshot:
        """Captures a new immutable operational snapshot across subsystems."""
        snapshot = await self.twin.capture_current_state(
            custom_overrides=custom_overrides,
            consistency=consistency,
        )
        self._snapshot_history[snapshot.snapshot_id] = snapshot
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> RuntimeSnapshot | None:
        return self._snapshot_history.get(snapshot_id)

    async def run_simulation(
        self,
        target_subsystem: str,
        hypothesis: str = "Simulate candidate recovery strategies to determine optimal Pareto trade-off",
        description: str = "Pre-recovery consequence simulation",
        snapshot_id: str | None = None,
        candidate_strategies: list[str] | None = None,
        simulation_mode: SimulationMode = SimulationMode.ANALYTICAL,
    ) -> RecoverySimulationResult:
        """Executes a complete recovery simulation across candidate strategies."""
        # 1. Obtain baseline snapshot
        if snapshot_id and snapshot_id in self._snapshot_history:
            snapshot = self._snapshot_history[snapshot_id]
        else:
            snapshot = await self.capture_snapshot()

        # 2. Check for state drift if an older snapshot was requested
        current_snap = await self.twin.capture_current_state()
        drift_report = self.drift_detector.evaluate_staleness(snapshot, current_snap)

        # 3. Formulate scenario
        scenario = RecoveryScenario(
            scenario_id=f"scen_{uuid.uuid4().hex[:10]}",
            base_snapshot_id=snapshot.snapshot_id,
            description=description,
            hypothesis=hypothesis,
            target_subsystem=target_subsystem,
            simulation_mode=simulation_mode,
        )

        # 4. Run pre-recovery simulation engine
        result = self.simulator.simulate_recovery(
            snapshot=snapshot,
            scenario=scenario,
            candidate_strategies=candidate_strategies,
        )

        # 5. Apply drift status
        result.is_stale = drift_report.is_stale
        result.state_drift_detected = (drift_report.drift_score > 0.15)

        self._simulation_history[result.simulation_id] = result

        # 6. Emit canonical telemetry event
        _emit_simulation_event(
            "simulation.completed",
            {
                "simulation_id": result.simulation_id,
                "target_subsystem": target_subsystem,
                "recommended_strategy": result.recommended_candidate.strategy if result.recommended_candidate else None,
                "confidence": result.confidence,
                "is_stale": result.is_stale,
                "duration_ms": result.duration_ms,
            },
        )

        return result

    def get_simulation(self, simulation_id: str) -> RecoverySimulationResult | None:
        return self._simulation_history.get(simulation_id)

    def list_simulations(self, limit: int = 50) -> list[RecoverySimulationResult]:
        results = list(self._simulation_history.values())
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    async def run_chaos_drill(
        self,
        scenario_id: str,
    ) -> RecoverySimulationResult:
        """Executes a pre-configured chaos resilience drill in safe digital twin simulation mode."""
        base_snap = await self.capture_snapshot()
        scenario, perturbed_snap = self.chaos_lib.build_recovery_scenario(scenario_id, base_snap)
        self._snapshot_history[perturbed_snap.snapshot_id] = perturbed_snap

        result = self.simulator.simulate_recovery(
            snapshot=perturbed_snap,
            scenario=scenario,
        )
        self._simulation_history[result.simulation_id] = result

        _emit_simulation_event(
            "simulation.chaos_injected",
            {
                "scenario_id": scenario_id,
                "simulation_id": result.simulation_id,
                "target_subsystem": scenario.target_subsystem,
                "recommended_strategy": result.recommended_candidate.strategy if result.recommended_candidate else None,
            },
        )

        return result

    def list_chaos_scenarios(self) -> list[dict[str, Any]]:
        return self.chaos_lib.list_scenarios()

    def record_actual_recovery(
        self,
        simulation_id: str,
        recovery_id: str,
        strategy: str,
        actual_duration_seconds: float,
        actual_resource_cost: dict[str, Any],
        actual_risk_score: float,
        actual_blast_radius: float,
        verification_passed: bool,
    ) -> PredictionVsRealityRecord:
        """Calibrates simulation model with empirical reality and updates scorecards."""
        sim = self._simulation_history.get(simulation_id)
        candidate = None
        if sim:
            for c in sim.candidates:
                if c.strategy == strategy:
                    candidate = c
                    break
        if not candidate:
            candidate = RecoveryCandidate(
                strategy=strategy,
                target_subsystem="system",
                expected_benefit="Default",
                expected_risk="Default",
                predicted_duration_seconds=actual_duration_seconds,
            )

        # 1. Compute comparison
        record = self.comparator.compare(
            simulation_id=simulation_id,
            recovery_id=recovery_id,
            candidate=candidate,
            actual_duration_seconds=actual_duration_seconds,
            actual_resource_cost=actual_resource_cost,
            actual_risk_score=actual_risk_score,
            actual_blast_radius=actual_blast_radius,
            verification_passed=verification_passed,
        )
        self.scorecards.record_comparison(record)

        # 2. Update strategy scorecard
        dur_ms = actual_duration_seconds * 1000.0
        self.scorecards.record_execution(
            strategy=strategy,
            success=verification_passed,
            duration_ms=dur_ms,
            verification_passed=verification_passed,
            resource_cost={
                "cpu_delta_pct": float(actual_resource_cost.get("cpu_delta_pct", 5.0)),
                "mem_delta_mb": float(actual_resource_cost.get("mem_delta_mb", 20.0)),
            },
        )

        # 3. Emit calibration event
        _emit_simulation_event(
            "simulation.calibrated",
            {
                "simulation_id": simulation_id,
                "strategy": strategy,
                "duration_error": record.duration_error,
                "verification_match": record.verification_match,
            },
        )

        return record

    def get_scorecards(self) -> list[RecoveryStrategyScorecard]:
        return self.scorecards.get_all_scorecards()

    def get_regressions(self) -> list[dict[str, Any]]:
        return self.regressions.detect_regressions()

    def get_resilience_benchmark(self) -> ResilienceBenchmark:
        return self.benchmarks.compute_benchmark(self.scorecards)

    def get_comparisons(self, limit: int = 50) -> list[PredictionVsRealityRecord]:
        return self.scorecards.get_comparisons(limit=limit)


_global_recovery_service = RecoverySimulationService()


def get_recovery_service() -> RecoverySimulationService:
    return _global_recovery_service

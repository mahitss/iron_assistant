"""Simulation replay engine, idempotency caching, and reproducible run traces."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.simulation.deterministic import DeterministicRunResult, DeterministicSimulationEngine
from app.simulation.schemas import Scenario, SimulationSnapshot


def generate_simulation_cache_key(
    snapshot_id: str,
    scenario_id: str,
    model_version: str = "1.0.0",
    parameters: dict[str, Any] | None = None,
) -> str:
    """Computes a deterministic hash key from snapshot, scenario, model, and parameters (Prompt #172)."""
    raw = {
        "snapshot_id": snapshot_id,
        "scenario_id": scenario_id,
        "model_version": model_version,
        "parameters": parameters or {},
    }
    canonical = json.dumps(raw, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SimulationReplayEngine:
    """Manages deterministic replay and safe idempotent simulation caching."""

    def __init__(self) -> None:
        self._cache: dict[str, DeterministicRunResult] = {}
        self._deterministic_engine = DeterministicSimulationEngine()

    def replay_scenario(
        self,
        snapshot: SimulationSnapshot,
        scenario: Scenario,
        use_cache: bool = True,
    ) -> tuple[DeterministicRunResult, bool]:
        """Replays a scenario deterministically from a snapshot baseline.

        Returns (result, was_cached).
        """
        cache_key = generate_simulation_cache_key(
            snapshot_id=snapshot.snapshot_id,
            scenario_id=scenario.scenario_id,
            model_version="1.0.0",
            parameters={"interventions_count": len(scenario.interventions)},
        )

        if use_cache and cache_key in self._cache:
            return self._cache[cache_key], True

        composite_baseline = {
            "world": snapshot.world_state,
            "digital_twin": snapshot.digital_twin_state,
            "telemetry": snapshot.telemetry_state,
        }

        result = self._deterministic_engine.run_deterministic(
            initial_state=composite_baseline,
            interventions=scenario.interventions,
        )

        if use_cache:
            self._cache[cache_key] = result

        return result, False

    def invalidate_cache(self, snapshot_id: str | None = None) -> int:
        """Invalidates cached simulation results."""
        if snapshot_id is None:
            count = len(self._cache)
            self._cache.clear()
            return count
        # Invalidate specific snapshot entries
        keys_to_del = [k for k in self._cache if snapshot_id in k]
        for k in keys_to_del:
            del self._cache[k]
        return len(keys_to_del)

"""Scenario generator and lifecycle manager supporting 15 scenario types and assumption tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.simulation.safety import sanitize_scenario_input
from app.simulation.schemas import (
    AssumptionImpact,
    AssumptionType,
    Scenario,
    ScenarioAssumption,
    ScenarioType,
    SimulatedIntervention,
    SimulationObjective,
)


class ScenarioManager:
    """Creates, stores, versions, and manages counterfactual scenarios."""

    def __init__(self) -> None:
        self._scenarios: dict[str, Scenario] = {}

    def create_scenario(
        self,
        name: str,
        scenario_type: ScenarioType | str,
        baseline_snapshot_id: str,
        interventions: list[SimulatedIntervention] | None = None,
        assumptions: list[ScenarioAssumption] | None = None,
        constraints: list[dict[str, Any]] | None = None,
        objectives: list[SimulationObjective] | None = None,
        horizon: str = "SHORT_TERM",
        description: str = "",
    ) -> Scenario:
        """Creates a validated scenario with sanitized input and tracked assumptions."""
        clean_name = sanitize_scenario_input(name)
        if isinstance(scenario_type, str):
            scenario_type = ScenarioType(scenario_type.upper())

        scenario_id = f"scen_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # Ensure assumptions list has default baseline assumption if empty
        assumptions_list = assumptions or [
            ScenarioAssumption(
                assumption_id=f"assump_{uuid.uuid4().hex[:8]}",
                statement="Baseline topology and metrics accurately reflect the digital twin snapshot.",
                assumption_type=AssumptionType.STATIC,
                impact=AssumptionImpact.MEDIUM,
                confidence=0.95,
            )
        ]

        scenario = Scenario(
            scenario_id=scenario_id,
            name=clean_name,
            scenario_type=scenario_type,
            baseline_snapshot_id=baseline_snapshot_id,
            interventions=interventions or [],
            assumptions=assumptions_list,
            constraints=constraints or [],
            objectives=objectives or [],
            horizon=horizon,
            status="CREATED",
            version=1,
            created_at=now,
            updated_at=now,
        )

        self._scenarios[scenario_id] = scenario.model_copy(deep=True)
        return scenario.model_copy(deep=True)

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        """Retrieves a deep clone of a scenario."""
        scen = self._scenarios.get(scenario_id)
        if scen is None:
            return None
        return scen.model_copy(deep=True)

    def update_scenario(
        self,
        scenario_id: str,
        interventions: list[SimulatedIntervention] | None = None,
        assumptions: list[ScenarioAssumption] | None = None,
        constraints: list[dict[str, Any]] | None = None,
        objectives: list[SimulationObjective] | None = None,
    ) -> Scenario:
        """Updates a scenario, incrementing its version."""
        scen = self._scenarios.get(scenario_id)
        if scen is None:
            raise KeyError(f"Scenario '{scenario_id}' not found.")

        updated = scen.model_copy(
            update={
                "interventions": interventions if interventions is not None else scen.interventions,
                "assumptions": assumptions if assumptions is not None else scen.assumptions,
                "constraints": constraints if constraints is not None else scen.constraints,
                "objectives": objectives if objectives is not None else scen.objectives,
                "version": scen.version + 1,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._scenarios[scenario_id] = updated.model_copy(deep=True)
        return updated.model_copy(deep=True)

    def get_critical_assumptions(self, scenario_id: str) -> list[ScenarioAssumption]:
        """Surfaces assumptions with HIGH or CRITICAL impact."""
        scen = self.get_scenario(scenario_id)
        if scen is None:
            return []
        return [
            a for a in scen.assumptions
            if a.impact in (AssumptionImpact.HIGH, AssumptionImpact.CRITICAL)
        ]

    def list_scenarios(self, baseline_snapshot_id: str | None = None) -> list[Scenario]:
        """Lists scenarios, optionally filtered by baseline snapshot."""
        scenarios = list(self._scenarios.values())
        if baseline_snapshot_id:
            scenarios = [s for s in scenarios if s.baseline_snapshot_id == baseline_snapshot_id]
        return [s.model_copy(deep=True) for s in scenarios]


# Global scenario manager instance
scenario_manager = ScenarioManager()

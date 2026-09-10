"""Validation routines for simulation scenarios, interventions, and safety invariants."""

from __future__ import annotations

from app.simulation.safety import block_production_side_effects
from app.simulation.schemas import Scenario, SimulatedIntervention


class SimulationValidator:
    """Validates structural correctness and security compliance of simulation configurations."""

    def validate_scenario(self, scenario: Scenario) -> list[str]:
        """Validates scenario integrity and firewall compliance."""
        errors: list[str] = []

        if not scenario.scenario_id:
            errors.append("Scenario must have a valid scenario_id.")
        if not scenario.baseline_snapshot_id:
            errors.append("Scenario must specify a baseline_snapshot_id.")

        for i, interv in enumerate(scenario.interventions):
            try:
                block_production_side_effects(interv.operation, interv.target)
            except Exception as e:
                errors.append(f"Intervention {i} safety violation: {e}")

        return errors

    def validate_intervention(self, intervention: SimulatedIntervention) -> list[str]:
        """Validates an individual intervention."""
        errors: list[str] = []
        try:
            block_production_side_effects(intervention.operation, intervention.target)
        except Exception as e:
            errors.append(str(e))
        return errors

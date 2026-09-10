"""Hypothetical interventions definition and sandboxed application."""

from __future__ import annotations

from typing import Any

from app.simulation.safety import block_production_side_effects
from app.simulation.schemas import SimulatedIntervention


class InterventionExecutor:
    """Safely executes hypothetical interventions strictly against in-memory simulation state."""

    def __init__(self) -> None:
        pass

    def validate_intervention(self, intervention: SimulatedIntervention) -> None:
        """Validates that an intervention targets simulated entities and has no production side-effects."""
        block_production_side_effects(action_name=intervention.operation, target=intervention.target)

    def apply_to_state(
        self,
        current_state: dict[str, Any],
        intervention: SimulatedIntervention,
    ) -> dict[str, Any]:
        """Applies hypothetical intervention to simulation state dict, returning mutation payload.

        NEVER calls external systems or tools.
        """
        self.validate_intervention(intervention)

        target = intervention.target
        after_val = intervention.hypothetical_after

        mutations: dict[str, Any] = {}

        # If target path is dot-notated, e.g. "services.auth.replicas"
        if "." in target:
            parts = target.split(".")
            root = parts[0]
            mutations[root] = current_state.get(root, {})
            curr = mutations[root]
            for part in parts[1:-1]:
                if part not in curr or not isinstance(curr[part], dict):
                    curr[part] = {}
                curr = curr[part]
            curr[parts[-1]] = after_val
        else:
            mutations[target] = after_val

        return mutations

"""Deterministic simulation engine for exact, step-by-step reproducible scenario execution."""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel, Field

from app.simulation.actions import ACTION_REGISTRY
from app.simulation.safety import tag_simulated_output
from app.simulation.schemas import SimulatedIntervention


class DeterministicRunResult(BaseModel):
    """Result of a deterministic step-by-step simulation run."""

    steps_executed: int
    final_state: dict[str, Any]
    state_trace: list[dict[str, Any]] = Field(default_factory=list)
    is_reproducible: bool = True
    seed_used: int | None = None


class DeterministicSimulationEngine:
    """Executes deterministic simulations where identical inputs yield identical outputs."""

    def run_deterministic(
        self,
        initial_state: dict[str, Any],
        interventions: list[SimulatedIntervention],
    ) -> DeterministicRunResult:
        """Executes each intervention sequentially, capturing state trace."""
        current_state = copy.deepcopy(initial_state)
        trace = [copy.deepcopy(current_state)]

        for interv in interventions:
            op = interv.operation.upper()
            action_cls = ACTION_REGISTRY.get(op)
            if action_cls:
                action = action_cls()
                current_state = action.execute(current_state, target=interv.target, **interv.hypothetical_after if isinstance(interv.hypothetical_after, dict) else {})
            else:
                # Direct attribute assignment
                target = interv.target
                if "." in target:
                    parts = target.split(".")
                    curr = current_state
                    for part in parts[:-1]:
                        curr = curr.setdefault(part, {})
                    curr[parts[-1]] = copy.deepcopy(interv.hypothetical_after)
                else:
                    current_state[target] = copy.deepcopy(interv.hypothetical_after)

            trace.append(copy.deepcopy(current_state))

        return DeterministicRunResult(
            steps_executed=len(interventions),
            final_state=tag_simulated_output(current_state),
            state_trace=trace,
            is_reproducible=True,
            seed_used=None,
        )

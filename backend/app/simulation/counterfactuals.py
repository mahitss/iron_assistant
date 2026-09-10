"""Counterfactual reasoning engine supporting what-if analysis and hypothetical alternatives."""

from __future__ import annotations

import copy
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.simulation.schemas import SimulatedIntervention


class CounterfactualQuery(BaseModel):
    """Specification of a counterfactual inquiry."""

    query_type: str  # WHAT_IF_NOT_HAPPENED, WHAT_IF_CHANGED_INSTEAD, WHAT_IF_WE_WAIT, WHAT_IF_PLAN_B
    target_intervention_id: str | None = None
    alternative_intervention: SimulatedIntervention | None = None
    wait_horizon_seconds: int = 0
    candidate_plan_b_interventions: list[SimulatedIntervention] = Field(default_factory=list)
    rationale: str = ""


class CounterfactualResult(BaseModel):
    """Result of counterfactual simulation exploration."""

    query_id: str = Field(default_factory=lambda: f"cf_{uuid.uuid4().hex[:12]}")
    query_type: str
    baseline_state_id: str
    counterfactual_state: dict[str, Any] = Field(default_factory=dict)
    divergence_summary: str
    is_hypothetical: bool = True
    environment_label: str = "SIMULATION_ONLY"
    disclaimer: str = (
        "Counterfactual predictions are purely hypothetical mathematical models "
        "and do not constitute observed historical facts or real-world outcomes."
    )


class CounterfactualEngine:
    """Explores alternative hypothetical pasts and futures without side effects."""

    def what_if_never_happened(
        self,
        baseline_state: dict[str, Any],
        historical_intervention: SimulatedIntervention,
    ) -> CounterfactualResult:
        """Evaluates: 'What if X had never happened?' by reverting historical intervention from baseline."""
        reverted_state = copy.deepcopy(baseline_state)
        target = historical_intervention.target

        # Revert target to its original 'before' value
        if "." in target:
            parts = target.split(".")
            curr = reverted_state
            for part in parts[:-1]:
                if part in curr and isinstance(curr[part], dict):
                    curr = curr[part]
            if parts[-1] in curr:
                curr[parts[-1]] = copy.deepcopy(historical_intervention.before)
        else:
            reverted_state[target] = copy.deepcopy(historical_intervention.before)

        return CounterfactualResult(
            query_type="WHAT_IF_NOT_HAPPENED",
            baseline_state_id="baseline_snapshot",
            counterfactual_state=reverted_state,
            divergence_summary=f"Reverted hypothetical event '{historical_intervention.operation}' on target '{target}'.",
        )

    def what_if_changed_instead(
        self,
        baseline_state: dict[str, Any],
        original_intervention: SimulatedIntervention,
        alternative_intervention: SimulatedIntervention,
    ) -> CounterfactualResult:
        """Evaluates: 'What if we changed X instead?' by substituting an alternative intervention."""
        branch_state = copy.deepcopy(baseline_state)
        target = alternative_intervention.target

        if "." in target:
            parts = target.split(".")
            curr = branch_state
            for part in parts[:-1]:
                if part in curr and isinstance(curr[part], dict):
                    curr = curr[part]
            curr[parts[-1]] = copy.deepcopy(alternative_intervention.hypothetical_after)
        else:
            branch_state[target] = copy.deepcopy(alternative_intervention.hypothetical_after)

        return CounterfactualResult(
            query_type="WHAT_IF_CHANGED_INSTEAD",
            baseline_state_id="baseline_snapshot",
            counterfactual_state=branch_state,
            divergence_summary=(
                f"Substituted '{alternative_intervention.operation}' for original '{original_intervention.operation}' on '{target}'."
            ),
        )

    def what_if_we_wait(
        self,
        baseline_state: dict[str, Any],
        wait_horizon_seconds: int = 300,
    ) -> CounterfactualResult:
        """Evaluates: 'What if we wait?' (No-change horizon projection)."""
        future_state = copy.deepcopy(baseline_state)
        # Apply natural time degradation or steady-state telemetry drift
        services = future_state.get("services", {})
        for svc in services.values():
            if isinstance(svc, dict) and svc.get("status") == "DEGRADED":
                # Waiting with a degraded service may exacerbate queue depth
                svc["queue_depth"] = svc.get("queue_depth", 100) + int(wait_horizon_seconds * 0.5)

        return CounterfactualResult(
            query_type="WHAT_IF_WE_WAIT",
            baseline_state_id="baseline_snapshot",
            counterfactual_state=future_state,
            divergence_summary=f"Projected no-action drift over {wait_horizon_seconds}s horizon.",
        )

    def what_if_plan_b(
        self,
        baseline_state: dict[str, Any],
        plan_b_interventions: list[SimulatedIntervention],
    ) -> CounterfactualResult:
        """Evaluates: 'What if we choose plan B?' by sequentially applying candidate interventions."""
        plan_state = copy.deepcopy(baseline_state)
        applied = []
        for interv in plan_b_interventions:
            target = interv.target
            applied.append(f"{interv.operation}->{target}")
            if "." in target:
                parts = target.split(".")
                curr = plan_state
                for part in parts[:-1]:
                    if part in curr and isinstance(curr[part], dict):
                        curr = curr[part]
                curr[parts[-1]] = copy.deepcopy(interv.hypothetical_after)
            else:
                plan_state[target] = copy.deepcopy(interv.hypothetical_after)

        return CounterfactualResult(
            query_type="WHAT_IF_PLAN_B",
            baseline_state_id="baseline_snapshot",
            counterfactual_state=plan_state,
            divergence_summary=f"Simulated Plan B with {len(plan_b_interventions)} alternative intervention(s): {', '.join(applied)}.",
        )

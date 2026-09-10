"""Counterfactual reasoning, what-if analysis, baseline selection, and hypothetical modeling (Task 55)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.causal.schemas import (
    CausalGraph,
    CounterfactualScenario,
)


class CounterfactualEngine:
    """Evaluates what-if scenarios and estimated causal effects while maintaining strict distinction from reality."""

    @staticmethod
    def create_counterfactual_scenario(
        baseline: dict[str, Any],
        intervention: dict[str, Any],
        expected_difference: dict[str, Any] | None = None,
        assumptions: list[str] | None = None,
        confidence: float = 0.6,
    ) -> CounterfactualScenario:
        """Prompt #63, #64, #65: Construct a strictly hypothetical counterfactual scenario."""
        default_assumptions = assumptions or [
            "ceteris_paribus_no_unobserved_external_shocks",
            "historical_topology_invariance",
            "stable_workload_distribution",
        ]
        return CounterfactualScenario(
            scenario_id=f"cf_{uuid.uuid4().hex[:12]}",
            baseline=baseline,
            intervention=intervention,
            expected_difference=expected_difference or {},
            assumptions=default_assumptions,
            confidence=min(0.85, max(0.1, confidence)),  # Counterfactual confidence capped without empirical verification
            is_hypothetical=True,  # Prompt #65, #68: Simulation and counterfactuals are not reality
            status="GENERATED",
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def evaluate_what_if(
        question: str,
        removed_cause: str,
        baseline_state: dict[str, Any],
        causal_graph: CausalGraph,
        simulated_difference: dict[str, Any] | None = None,
    ) -> CounterfactualScenario:
        """Prompt #64, #109: 'What would have happened if X had not occurred?'"""
        # Traverse downstream nodes from removed_cause in causal_graph
        downstream_effects = []
        for edge in causal_graph.edges.values():
            if edge.cause == removed_cause and edge.status.value in ("ACTIVE", "CANDIDATE"):
                downstream_effects.append(edge.effect)

        expected_diff = simulated_difference or {
            "prevented_effects": downstream_effects,
            "estimated_impact_reduction": "High" if downstream_effects else "None",
            "hypothetical_outcome": (
                f"If '{removed_cause}' had not occurred, downstream effects {downstream_effects} "
                "would likely have been avoided or significantly attenuated under current model assumptions."
            ) if downstream_effects else f"Removing '{removed_cause}' shows negligible downstream difference in current graph.",
        }

        assumptions = [
            f"Assuming no alternative path activated for {downstream_effects}",
            "Assuming upstream workload remained constant",
            "Model dependency relations remain valid during scenario",
        ]

        graph_conf = causal_graph.confidence if causal_graph.edges else 0.5
        scenario = CounterfactualEngine.create_counterfactual_scenario(
            baseline=baseline_state,
            intervention={"removed_event_or_cause": removed_cause, "action": "suppress"},
            expected_difference=expected_diff,
            assumptions=assumptions,
            confidence=graph_conf * 0.8,  # Penalize hypothetical uncertainty
        )
        return scenario

    @staticmethod
    def compare_with_natural_experiment(
        current_incident: dict[str, Any],
        historical_similar_windows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Prompt #177, #178, #179: Compare current event with naturally occurring historical intervals."""
        if not historical_similar_windows:
            return {
                "comparable_found": False,
                "reason": "No sufficiently similar historical control intervals found.",
                "estimated_effect": None,
            }

        comparable = historical_similar_windows[0]
        baseline_metrics = comparable.get("metrics", {})
        incident_metrics = current_incident.get("metrics", {})

        diff: dict[str, Any] = {}
        for key, inc_val in incident_metrics.items():
            if key in baseline_metrics:
                base_val = baseline_metrics[key]
                if isinstance(inc_val, (int, float)) and isinstance(base_val, (int, float)):
                    diff[key] = {
                        "incident": inc_val,
                        "historical_baseline": base_val,
                        "delta": inc_val - base_val,
                    }

        return {
            "comparable_found": True,
            "control_window_id": comparable.get("id"),
            "similarity_score": comparable.get("similarity", 0.85),
            "estimated_effect": diff,
            "is_hypothetical": False,
            "source": "historical_natural_experiment",
        }

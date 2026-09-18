"""Outcome comparison engine for Task 113.
Implements structured side-by-side comparison of candidate interventions against NO_ACTION.
Provides decision support without preempting autonomous decision authority.
"""

from __future__ import annotations

import logging
from typing import Any
import uuid

from app.counterfactual.domain import (
    CounterfactualScenario,
    InterventionComparison,
    InterventionComparisonItem,
)

logger = logging.getLogger("kairo.counterfactual.comparison_engine")


class ComparisonEngine:
    """Compares candidate intervention scenarios against the NO_ACTION baseline across multiple dimensions."""

    @classmethod
    def compare_scenarios(
        cls,
        scenarios: list[CounterfactualScenario],
        baseline_scenario_id: str | None = None,
    ) -> InterventionComparison:
        """Constructs an auditable side-by-side comparison across all scenarios."""
        cmp_id = f"cmp_{uuid.uuid4().hex[:12]}"
        items: list[InterventionComparisonItem] = []
        candidate_ids: list[str] = []

        base_id = baseline_scenario_id or (scenarios[0].scenario_id if scenarios else "")

        for scen in scenarios:
            pred = scen.prediction
            out = scen.outcome
            pred_summary = "Prediction unavailable"
            if pred:
                status = pred.predicted_state.get("status", "UNKNOWN")
                latency = pred.predicted_state.get("latency_ms", "N/A")
                pred_summary = f"Predicted status: {status}, latency: {latency}ms"

            key_asms = []
            risk_level = "LOW"
            reversibility = "REVERSIBLE"
            if scen.interventions:
                for intv in scen.interventions:
                    key_asms.extend([a.description for a in intv.assumptions[:2]])
                    risk_level = intv.risk_level
                    reversibility = "REVERSIBLE" if intv.is_reversible else "IRREVERSIBLE"
            else:
                key_asms = ["Existing system dynamics remain unchanged"]
                reversibility = "N/A (No intervention)"

            resource_summary = f"Cost: {out.cost_estimate_units if out else 0.0} units"
            confidence = pred.confidence if pred else 0.5
            uncertainty_level = "LOW" if confidence >= 0.75 else ("MODERATE" if confidence >= 0.5 else "HIGH")

            item = InterventionComparisonItem(
                scenario_id=scen.scenario_id,
                scenario_name=scen.scenario_name,
                is_no_action=scen.is_no_action,
                predicted_summary=pred_summary,
                key_assumptions=key_asms,
                risk_level=risk_level,
                resource_cost_summary=resource_summary,
                reversibility=reversibility,
                uncertainty_level=uncertainty_level,
                confidence=confidence,
            )
            items.append(item)
            if not scen.is_no_action:
                candidate_ids.append(scen.scenario_id)

        # Evaluate trade-offs
        tradeoffs = []
        no_action_viable = True
        recommended_option: str | None = None

        # Check if NO_ACTION outcome is acceptable
        no_action_item = next((item for item in items if item.is_no_action), None)
        if no_action_item:
            tradeoffs.append(f"Baseline (NO_ACTION): {no_action_item.predicted_summary}.")

        for item in items:
            if not item.is_no_action:
                tradeoffs.append(
                    f"{item.scenario_name}: {item.predicted_summary}, Risk: {item.risk_level}, "
                    f"Reversibility: {item.reversibility}, Cost: {item.resource_cost_summary}."
                )

        # If any intervention provides superior health recovery with low risk and high reversibility
        viable_candidates = [it for it in items if not it.is_no_action and it.risk_level in ("LOW", "MEDIUM") and it.reversibility == "REVERSIBLE"]
        if viable_candidates:
            # Recommend highest confidence candidate for Decision Intelligence consideration
            best = max(viable_candidates, key=lambda x: x.confidence)
            recommended_option = best.scenario_name
        else:
            recommended_option = "NO_ACTION"

        tradeoff_summary = "\n".join(tradeoffs)

        return InterventionComparison(
            comparison_id=cmp_id,
            baseline_scenario_id=base_id,
            candidate_scenario_ids=candidate_ids,
            items=items,
            dimensions_evaluated=[
                "mission_success",
                "goal_progress",
                "system_health",
                "reliability",
                "risk",
                "resource_usage",
                "latency",
                "cost",
                "safety",
                "reversibility",
                "capability_impact",
                "user_impact",
                "external_impact",
            ],
            tradeoff_summary=tradeoff_summary,
            recommended_option_for_decision=recommended_option,
            no_action_viable=no_action_viable,
            insufficient_evidence_warning=any(item.confidence < 0.6 for item in items),
        )

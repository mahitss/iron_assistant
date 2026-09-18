"""Downstream integration bridges for Task 113.
Safe, bounded packaging of counterfactual results for Decision Intelligence (Task 94),
Cognitive Working Set (Task 110), Attention (Task 109), and EmergencyStop governance.
"""

from __future__ import annotations

import logging
from typing import Any

from app.counterfactual.domain import CounterfactualAnalysis
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.counterfactual.downstream_bridges")


class DownstreamBridges:
    """Safe integration points into decision intelligence and cognitive working set."""

    @classmethod
    def package_for_decision(cls, analysis: CounterfactualAnalysis) -> dict[str, Any]:
        """Packages counterfactual comparison as structured evidence for Task 94 Decision Intelligence.
        Does NOT make or authorize the decision.
        """
        cmp = analysis.comparison
        options = []

        if cmp:
            for item in cmp.items:
                options.append({
                    "option_id": item.scenario_id,
                    "name": item.scenario_name,
                    "is_baseline_no_action": item.is_no_action,
                    "predicted_trajectory": item.predicted_summary,
                    "risk_level": item.risk_level,
                    "reversibility": item.reversibility,
                    "resource_cost": item.resource_cost_summary,
                    "confidence": item.confidence,
                    "is_simulation": True,
                })

        return {
            "analysis_id": analysis.analysis_id,
            "target_entity": analysis.target_entity,
            "question": analysis.question,
            "candidate_options": options,
            "tradeoff_summary": cmp.tradeoff_summary if cmp else "",
            "recommended_candidate": cmp.recommended_option_for_decision if cmp else "NO_ACTION",
            "no_action_viable": cmp.no_action_viable if cmp else True,
            "causal_model_version": analysis.causal_model_version,
            "is_simulation_only": True,
            "authorization_status": "PENDING_DECISION_GOVERNANCE",
        }

    @classmethod
    def package_for_working_set(cls, analysis: CounterfactualAnalysis, max_tokens: int = 350) -> dict[str, Any]:
        """Provides a bounded, high-density counterfactual summary for Task 110 Cognitive Working Set."""
        cmp = analysis.comparison
        recommended = cmp.recommended_option_for_decision if cmp else "NO_ACTION"
        no_action_viable = cmp.no_action_viable if cmp else True

        text_summary = (
            f"[COUNTERFACTUAL: {analysis.analysis_id}] Target: {analysis.target_entity} | Type: {analysis.counterfactual_type.value} | "
            f"Recommended: {recommended} | NO_ACTION viable: {no_action_viable} | Status: {analysis.lifecycle_stage.value}"
        )

        return {
            "element_id": f"cws_cf_{analysis.analysis_id}",
            "element_type": "COUNTERFACTUAL_ANALYSIS",
            "entity_id": analysis.target_entity,
            "summary": text_summary[:max_tokens * 4],
            "confidence": 0.8,
            "is_hypothetical": True,
            "environment_label": "SIMULATION_ONLY",
        }

    @classmethod
    def check_emergency_stop(cls, user_id: str | None = None) -> tuple[bool, str]:
        """Verifies if mutating/intervention workflows are blocked by EmergencyStop."""
        e_stop = get_emergency_stop_service()
        if e_stop.is_stopped(user_id):
            return True, "EMERGENCY_STOP_TRIGGERED: Interventions, experiments, and actions are strictly blocked."
        return False, "CLEARED"

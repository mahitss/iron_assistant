"""Causal experiment planning and information-gain analysis for Task 113.
Designs safe, controlled experiments to distinguish competing hypotheses and reduce uncertainty.
Integrates with Task 105 ExperimentEngine without executing unauthorized interventions.
"""

from __future__ import annotations

import logging
from typing import Any
import uuid

from app.counterfactual.domain import (
    InformationGainProposal,
    InterventionExperimentPlan,
)

logger = logging.getLogger("kairo.counterfactual.experiment_planner")


class ExperimentPlanner:
    """Plans controlled experiments and identifies discriminating observations for causal learning."""

    @classmethod
    def evaluate_information_gain(
        cls,
        competing_hypotheses: list[str],
        target_entity: str,
    ) -> list[InformationGainProposal]:
        """Identifies observations that would maximally differentiate competing hypotheses."""
        proposals: list[InformationGainProposal] = []

        if len(competing_hypotheses) < 2:
            proposals.append(
                InformationGainProposal(
                    proposal_id=f"ig_{uuid.uuid4().hex[:8]}",
                    target_hypotheses=competing_hypotheses,
                    discriminating_observation=f"Monitor baseline telemetry for {target_entity}",
                    candidate_experiment_type="OBSERVATIONAL",
                    expected_information_gain=0.4,
                    cost_estimate=0.0,
                    latency_seconds=5.0,
                    safety_risk="LOW",
                    observability_metric="error_rate",
                )
            )
            return proposals

        # Scenario: Resource exhaustion vs Network degradation
        h_str = " ".join(competing_hypotheses).lower()
        if "resource" in h_str and "network" in h_str:
            proposals.append(
                InformationGainProposal(
                    proposal_id=f"ig_{uuid.uuid4().hex[:8]}",
                    target_hypotheses=competing_hypotheses,
                    discriminating_observation="Compare worker queue backlog against network socket retransmissions.",
                    candidate_experiment_type="OBSERVATIONAL",
                    expected_information_gain=0.88,
                    cost_estimate=0.0,
                    latency_seconds=3.0,
                    safety_risk="LOW",
                    observability_metric="socket_retransmits_vs_queue_depth",
                )
            )
            proposals.append(
                InformationGainProposal(
                    proposal_id=f"ig_{uuid.uuid4().hex[:8]}",
                    target_hypotheses=competing_hypotheses,
                    discriminating_observation="Inject shadow traffic burst to observe bottleneck location.",
                    candidate_experiment_type="SHADOW",
                    expected_information_gain=0.75,
                    cost_estimate=2.5,
                    latency_seconds=15.0,
                    safety_risk="MEDIUM",
                    observability_metric="shadow_request_latency_distribution",
                )
            )
        else:
            proposals.append(
                InformationGainProposal(
                    proposal_id=f"ig_{uuid.uuid4().hex[:8]}",
                    target_hypotheses=competing_hypotheses,
                    discriminating_observation=f"Inspect discriminating metric trace between {competing_hypotheses[0]} and {competing_hypotheses[1]}.",
                    candidate_experiment_type="OBSERVATIONAL",
                    expected_information_gain=0.70,
                    cost_estimate=0.1,
                    latency_seconds=10.0,
                    safety_risk="LOW",
                    observability_metric="telemetry_delta",
                )
            )

        return proposals

    @classmethod
    def design_controlled_experiment(
        cls,
        hypothesis_id: str,
        treatment: dict[str, Any],
        control: dict[str, Any],
        metric: str,
        stop_conditions: list[str] | None = None,
        rollback_strategy: str | None = None,
    ) -> InterventionExperimentPlan:
        """Designs a controlled experimental plan integrating Task 105 safety boundaries."""
        plan_id = f"exp_plan_{uuid.uuid4().hex[:12]}"
        default_stops = stop_conditions or [
            "error_rate > 0.05",
            "latency_p99 > 250ms",
            "unhandled_exception_count > 0",
        ]
        default_rollback = rollback_strategy or "Instantly restore baseline parameter configuration."

        return InterventionExperimentPlan(
            plan_id=plan_id,
            hypothesis_id=hypothesis_id,
            treatment=treatment,
            control=control,
            metric=metric,
            stop_conditions=default_stops,
            rollback_strategy=default_rollback,
            requires_human_approval=True,
            is_governance_compliant=True,
            is_authorized=False,
        )

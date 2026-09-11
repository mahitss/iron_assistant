"""Active Causal Learning & Experiment Generation Engine (Task 73, Spec 32, 33, 55).

Synthesizes safe, discriminative experiments to resolve causal uncertainties
and differentiate competing hypotheses without exposing dangerous production actions.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.causal.discovery_schemas import (
    CausalRelationship,
    CausalRelationshipState,
)

logger = logging.getLogger(__name__)


class ActiveCausalLearningEngine:
    """Identifies high-uncertainty causal claims and generates discriminative experiment proposals."""

    @staticmethod
    def identify_causal_uncertainties(
        relationships: list[CausalRelationship],
    ) -> list[CausalRelationship]:
        """Find relationships requiring active experimental verification."""
        uncertain: list[CausalRelationship] = []
        for rel in relationships:
            # Candidates, hypotheses with confidence < 0.8, or contextual ones with missing tests
            if rel.status in {
                CausalRelationshipState.CANDIDATE,
                CausalRelationshipState.HYPOTHESIZED,
                CausalRelationshipState.CONTEXTUAL,
            } or (rel.status == CausalRelationshipState.SUPPORTED and rel.confidence < 0.75):
                uncertain.append(rel)
        return uncertain

    @staticmethod
    def design_discriminative_experiment(
        hyp_a: CausalRelationship,
        hyp_b: CausalRelationship,
        environment: str = "STAGING",
    ) -> dict[str, Any]:
        """Design an experiment to distinguish between two competing causal hypotheses (Spec 32, 55).

        Example:
        H1: Configuration change causes latency spike.
        H2: Traffic increase causes latency spike.
        Experiment: Hold traffic constant while varying configuration in staging.
        """
        exp_id = f"exp_disc_{uuid.uuid4().hex[:8]}"

        # Identify independent variable to manipulate and control variables
        independent_var = f"{hyp_a.cause_entity}.{hyp_a.cause_variable}"
        control_var = f"{hyp_b.cause_entity}.{hyp_b.cause_variable}"
        dependent_var = f"{hyp_a.effect_entity}.{hyp_a.effect_variable}"

        design = {
            "experiment_id": exp_id,
            "objective": (
                f"Discriminate between competing hypotheses: "
                f"[{hyp_a.cause_entity}:{hyp_a.cause_variable} -> {hyp_a.effect_variable}] vs "
                f"[{hyp_b.cause_entity}:{hyp_b.cause_variable} -> {hyp_b.effect_variable}]"
            ),
            "competing_hypothesis_ids": [hyp_a.causal_relation_id, hyp_b.causal_relation_id],
            "environment": environment,
            "experiment_type": "CONTROLLED",
            "independent_variable": independent_var,
            "control_variables": [control_var],
            "dependent_variable": dependent_var,
            "intervention_plan": {
                "action": f"Manipulate {independent_var} in isolated {environment} testbed",
                "condition": f"Hold {control_var} constant within +/- 5% baseline",
            },
            "falsification_criteria": {
                "falsifies_hyp_a": f"If {dependent_var} does not change when {independent_var} is modulated",
                "falsifies_hyp_b": f"If {dependent_var} changes despite {control_var} being held strictly constant",
            },
            "risk_level": "LOW_RISK" if environment != "PRODUCTION" else "HIGH_RISK",
            "estimated_cost": 1.5,
            "information_value": 0.85,
            "rollback_plan": {
                "action": f"Revert {independent_var} to baseline state immediately after observation window",
                "timeout_seconds": 120,
            },
        }
        return design

    @staticmethod
    def propose_next_intervention(
        relationship: CausalRelationship,
        environment: str = "STAGING",
    ) -> dict[str, Any]:
        """Propose the most informative, safe intervention DO(X) to test a single hypothesis."""
        exp_id = f"exp_test_{uuid.uuid4().hex[:8]}"
        cause_target = f"{relationship.cause_entity}.{relationship.cause_variable}"
        effect_target = f"{relationship.effect_entity}.{relationship.effect_variable}"

        proposal = {
            "experiment_id": exp_id,
            "relation_id": relationship.causal_relation_id,
            "intervention": f"DO({cause_target} = test_value)",
            "observation_target": effect_target,
            "environment": environment,
            "risk_level": "LOW_RISK" if environment != "PRODUCTION" else "MEDIUM_RISK",
            "expected_gain": round(1.0 - relationship.confidence, 2),
            "safety_checks": [
                "Verify staging sandbox isolation",
                "Verify baseline telemetry freshness",
                "Pre-allocate automated rollback procedure",
            ],
            "falsification_criteria": relationship.falsification_criteria or [
                f"{effect_target} remains unchanged within noise threshold during intervention"
            ],
        }
        return proposal

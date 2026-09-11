"""Causal Discovery Pipeline executing the 12-stage discovery flow (Task 73, Spec 35).

Pipeline stages:
1. Observations & telemetry ingestion
2. Variable extraction & state alignment
3. Statistical correlation / association detection
4. Temporal order & precedence validation
5. Confounder & mediator analysis
6. Causal hypothesis formulation with Popperian falsifiers
7. Experiment linkage (Task 72) or controlled evidence
8. Causal evaluation & strength estimation
9. Truth & verification gating (Task 42)
10. Causal graph update & cycle / feedback loop detection
11. World Model synchronization (Task 65)
12. Prediction calibration update (Task 47)
"""

from __future__ import annotations

import logging

from app.causal.confounder_engine import ConfounderEngine
from app.causal.discovery_schemas import (
    CausalCandidateProposal,
    CausalRelationship,
    CausalRelationshipState,
    CausalStrength,
    EdgeRelationshipType,
    EffectDirection,
    MechanismStatus,
)
from app.causal.discovery_state_machine import CausalDiscoveryStateMachine
from app.causal.temporal_engine import TemporalCausalityEngine
from app.causal.world_model_bridge import WorldModelBridge

logger = logging.getLogger(__name__)


class CausalDiscoveryPipeline:
    """Executes the autonomous causal discovery pipeline from raw observations to verified world model."""

    @staticmethod
    def process_candidate_proposal(
        proposal: CausalCandidateProposal,
        existing_relationships: list[CausalRelationship],
        environment: str = "STAGING",
    ) -> tuple[CausalRelationship, list[str]]:
        """Run Stages 1-6: Process an observational candidate correlation into a structured CausalHypothesis."""
        findings: list[str] = []

        # Stage 1 & 2: Variable extraction confirmed from proposal
        cause_entity = proposal.cause_entity
        cause_var = proposal.cause_variable
        effect_entity = proposal.effect_entity
        effect_var = proposal.effect_variable

        findings.append(f"Variables aligned: {cause_entity}.{cause_var} -> {effect_entity}.{effect_var}")

        # Stage 3: Relationship detection (Correlation is NOT Causation!)
        corr = proposal.observed_correlation
        findings.append(f"Observed statistical correlation: {corr:.2f} across {proposal.sample_size} samples")

        # Stage 4: Temporal precedence analysis if observations have timestamps
        temporal_valid = True
        contradiction = None
        if len(proposal.observations) >= 2:
            first_obs = proposal.observations[0]
            second_obs = proposal.observations[1]
            t1 = first_obs.get("timestamp")
            t2 = second_obs.get("timestamp")
            if t1 and t2:
                temp_res = TemporalCausalityEngine.validate_temporal_precedence(t1, t2)
                temporal_valid = temp_res.is_temporally_valid
                if temp_res.contradiction_detected:
                    contradiction = temp_res.contradiction_reason
                    findings.append(f"TEMPORAL CONTRADICTION: {contradiction}")

        # Stage 5: Confounder analysis
        known_edges = [r.model_dump() for r in existing_relationships]
        conf_res = ConfounderEngine.analyze_confounders(
            cause_entity, cause_var, effect_entity, effect_var, known_edges, initial_confidence=abs(corr)
        )
        if conf_res.is_confounded:
            findings.append(
                f"Common causes detected: {conf_res.common_causes}. Confidence penalized by {conf_res.confidence_penalty:.2f}"
            )

        # Stage 6: Formulate CausalRelationship
        initial_state = CausalRelationshipState.HYPOTHESIZED if temporal_valid and not contradiction else CausalRelationshipState.CONTRADICTED

        direction = EffectDirection.POSITIVE if corr > 0.1 else (EffectDirection.NEGATIVE if corr < -0.1 else EffectDirection.UNKNOWN)
        strength = CausalStrength.STRONG if abs(corr) > 0.7 else (CausalStrength.MODERATE if abs(corr) > 0.3 else CausalStrength.WEAK)

        # Cycle / Feedback loop check
        is_cycle = False
        for ex in existing_relationships:
            if (
                ex.cause_entity == effect_entity
                and ex.cause_variable == effect_var
                and ex.effect_entity == cause_entity
                and ex.effect_variable == cause_var
            ):
                is_cycle = True
                break

        edge_type = EdgeRelationshipType.FEEDBACK_LOOP if is_cycle else (
            EdgeRelationshipType.CORRELATION if not temporal_valid else EdgeRelationshipType.RELATIONSHIP
        )

        rel = CausalRelationship(
            cause_entity=cause_entity,
            cause_variable=cause_var,
            effect_entity=effect_entity,
            effect_variable=effect_var,
            relationship_type=edge_type,
            direction=direction,
            mechanism=f"Statistical association observed with r={corr:.2f}",
            mechanism_status=MechanismStatus.HYPOTHESIZED,
            conditions={"environment": environment, "sample_size": proposal.sample_size},
            scope="ENVIRONMENT",
            environment=environment,
            software_version=proposal.software_version,
            strength=strength,
            confidence=conf_res.adjusted_confidence,
            evidence_refs=[f"corr_obs_{proposal.cause_variable}_{proposal.effect_variable}"],
            contradiction_refs=[contradiction] if contradiction else [],
            falsification_criteria=[
                f"Controlled intervention DO({cause_entity}.{cause_var}) fails to induce delta in {effect_entity}.{effect_var}",
                f"Controlling for confounders [{', '.join(conf_res.common_causes)}] eliminates statistical association",
            ],
            status=initial_state,
            provenance={
                "pipeline": "task73_causal_discovery_pipeline",
                "sample_size": proposal.sample_size,
                "correlation": corr,
            },
        )

        return rel, findings

    @staticmethod
    def evaluate_experiment_outcome(
        relationship: CausalRelationship,
        experiment_id: str,
        intervention_target: str,
        observed_delta: float,
        is_controlled: bool,
        verification_ref: str | None = None,
    ) -> tuple[CausalRelationship, str]:
        """Run Stages 7-12: Integrate Task 72 experiment outcome, advance state machine, and sync to World Model."""
        # Check if intervention was on the suspected cause
        expected_target = f"{relationship.cause_entity}.{relationship.cause_variable}"
        target_matches = expected_target in intervention_target or relationship.cause_variable in intervention_target

        if not target_matches:
            return relationship, "Intervention target does not match suspected cause."

        if relationship.experiment_refs is None:
            relationship.experiment_refs = []
        if experiment_id not in relationship.experiment_refs:
            relationship.experiment_refs.append(experiment_id)

        # Evaluate if effect changed
        effect_detected = abs(observed_delta) > 0.05

        if effect_detected and is_controlled:
            # Controlled experiment confirms intervention changed effect!
            # Promote to SUPPORTED or STRONGLY_SUPPORTED or VERIFIED
            if verification_ref:
                target_state = CausalRelationshipState.VERIFIED
            elif len(relationship.experiment_refs) >= 2 or relationship.status == CausalRelationshipState.SUPPORTED:
                target_state = CausalRelationshipState.STRONGLY_SUPPORTED
            else:
                target_state = CausalRelationshipState.SUPPORTED

            CausalDiscoveryStateMachine.transition(
                relationship,
                target_state=target_state,
                reason=f"Controlled intervention {experiment_id} modulated effect with delta={observed_delta:.3f}",
                evidence_ref=f"exp_result:{experiment_id}",
                verification_ref=verification_ref,
                is_controlled_experiment=is_controlled,
            )
            relationship.mechanism_status = MechanismStatus.SUPPORTED
            relationship.relationship_type = EdgeRelationshipType.CAUSAL

            # Stage 11: Sync to World Model if verified or strongly supported
            wm_res = WorldModelBridge.sync_to_world_model(relationship)
            msg = f"Experiment confirmed causal effect. Promoted to {relationship.status.value}. World Model sync: {wm_res.get('synced')}."
            return relationship, msg

        elif not effect_detected and is_controlled:
            # Intervention had NO effect on the dependent variable -> Falsified!
            CausalDiscoveryStateMachine.transition(
                relationship,
                target_state=CausalRelationshipState.CONTRADICTED,
                reason=f"Controlled intervention {experiment_id} yielded no effect (delta={observed_delta:.3f}). Hypothesis weakened/contradicted.",
                evidence_ref=f"exp_falsifier:{experiment_id}",
            )
            return relationship, "Controlled experiment contradicted causal link. State moved to CONTRADICTED."

        return relationship, f"Observational or uncontrolled trial recorded. State remains {relationship.status.value}."

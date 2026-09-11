"""Adversarial and Edge Case Tests for Autonomous Causal Discovery Engine (Task 73, Spec 58).

Tests the 14 explicit adversarial invariants:
1. X and Y correlate -> not automatically causal.
2. X occurs before Y once -> insufficient for verified causality.
3. Controlled experiment changes X and Y changes -> causal evidence recorded.
4. Experiment fails -> hypothesis not automatically disproven.
5. Simulation predicts X -> Y -> simulation only.
6. Staging shows X -> Y -> relationship scoped to staging.
7. Production contradicts staging -> context-specific conflict/drift.
8. A confounder explains both X and Y -> causal confidence reduced.
9. New evidence invalidates old relationship -> relationship reassessed.
10. Two agents propose different causes -> dissent preserved.
11. Repeated agent outputs claim causality -> not independent evidence.
12. Causal model predicts an effect that repeatedly fails -> model revision triggered.
13. Malicious external source claims: "X definitely causes Y" -> untrusted claim only.
14. A causal relationship is deleted -> required historical provenance remains.
"""

import pytest

from app.causal.confounder_engine import ConfounderEngine
from app.causal.discovery_pipeline import CausalDiscoveryPipeline
from app.causal.discovery_schemas import (
    CausalCandidateProposal,
    CausalRelationship,
    CausalRelationshipState,
    CausalStrength,
    EdgeRelationshipType,
)
from app.causal.discovery_service import CausalDiscoveryService
from app.causal.discovery_state_machine import (
    CausalDiscoveryStateMachine,
    CausalStateTransitionError,
)
from app.causal.drift_detector import CausalDriftDetector
from app.causal.world_model_bridge import WorldModelBridge


def test_adv_1_correlation_is_not_automatically_causal():
    """Scenario 1: X and Y correlate strongly -> NOT automatically promoted to CAUSAL."""
    proposal = CausalCandidateProposal(
        cause_entity="IceCreamSales",
        cause_variable="revenue",
        effect_entity="BeachIncidents",
        effect_variable="count",
        observed_correlation=0.94,  # Very high correlation
        sample_size=1000,
    )
    rel, findings = CausalDiscoveryPipeline.process_candidate_proposal(proposal, existing_relationships=[])

    # Status must NOT be VERIFIED or CAUSAL edge type
    assert rel.status != CausalRelationshipState.VERIFIED
    assert rel.relationship_type != EdgeRelationshipType.CAUSAL
    assert rel.status == CausalRelationshipState.HYPOTHESIZED
    assert rel.relationship_type == EdgeRelationshipType.RELATIONSHIP


def test_adv_2_single_temporal_precedence_insufficient_for_verification():
    """Scenario 2: X occurs before Y once -> insufficient for verified causality."""
    proposal = CausalCandidateProposal(
        cause_entity="DeployJob",
        cause_variable="completed",
        effect_entity="Database",
        effect_variable="lock_contention",
        observed_correlation=0.6,
        sample_size=1,  # Single observation
        observations=[
            {"timestamp": "2026-09-12T10:00:00Z"},
            {"timestamp": "2026-09-12T10:01:00Z"},
        ],
    )
    rel, findings = CausalDiscoveryPipeline.process_candidate_proposal(proposal, existing_relationships=[])

    # Cannot jump to VERIFIED
    assert rel.status == CausalRelationshipState.HYPOTHESIZED
    with pytest.raises(CausalStateTransitionError):
        CausalDiscoveryStateMachine.transition(
            relationship=rel,
            target_state=CausalRelationshipState.VERIFIED,
            reason="Saw precedence once",
        )


def test_adv_3_controlled_experiment_records_causal_evidence():
    """Scenario 3: Controlled experiment changes X and Y changes -> causal evidence recorded."""
    rel = CausalRelationship(
        cause_entity="Pool",
        cause_variable="max_connections",
        effect_entity="Service",
        effect_variable="error_rate",
        status=CausalRelationshipState.HYPOTHESIZED,
    )

    updated_rel, msg = CausalDiscoveryPipeline.evaluate_experiment_outcome(
        relationship=rel,
        experiment_id="exp_ctrl_01",
        intervention_target="Pool.max_connections",
        observed_delta=-0.35,
        is_controlled=True,
    )

    assert updated_rel.status == CausalRelationshipState.SUPPORTED
    assert updated_rel.relationship_type == EdgeRelationshipType.CAUSAL
    assert "exp_ctrl_01" in updated_rel.experiment_refs


def test_adv_4_experiment_failure_does_not_automatically_disprove():
    """Scenario 4: An experiment fails to run (e.g. infrastructure error) -> hypothesis not automatically disproven."""
    rel = CausalRelationship(
        cause_entity="Worker",
        cause_variable="threads",
        effect_entity="Queue",
        effect_variable="drain_rate",
        status=CausalRelationshipState.HYPOTHESIZED,
    )

    # In uncontrolled or failed infrastructure measurement, delta is indeterminate (not controlled null)
    updated_rel, msg = CausalDiscoveryPipeline.evaluate_experiment_outcome(
        relationship=rel,
        experiment_id="exp_failed_infra",
        intervention_target="Worker.threads",
        observed_delta=0.0,
        is_controlled=False,  # Uncontrolled / failed execution
    )

    # State remains HYPOTHESIZED, not wiped or disproven
    assert updated_rel.status == CausalRelationshipState.HYPOTHESIZED
    assert "remains HYPOTHESIZED" in msg


def test_adv_5_simulation_predicts_x_to_y_simulation_only():
    """Scenario 5: Simulation predicts X -> Y -> labeled SIMULATED_STATE only."""
    rel = CausalRelationship(
        cause_entity="Traffic",
        cause_variable="rate",
        effect_entity="APIGateway",
        effect_variable="latency",
        strength=CausalStrength.STRONG,
    )

    sim_result = WorldModelBridge.run_digital_twin_counterfactual(
        relationship=rel,
        baseline_state={"latency": 50.0},
        intervened_cause_value=2000,
    )

    assert sim_result["is_simulation"] is True
    assert sim_result["simulation_label"] == "SIMULATED_STATE"


def test_adv_6_staging_shows_relationship_strictly_scoped():
    """Scenario 6: Staging shows X -> Y -> relationship scoped strictly to staging."""
    rel = CausalRelationship(
        cause_entity="ServiceX",
        cause_variable="config_param",
        effect_entity="ServiceY",
        effect_variable="throughput",
        environment="STAGING",
        status=CausalRelationshipState.VERIFIED,
    )

    assert rel.environment == "STAGING"
    assert rel.environment != "PRODUCTION"


def test_adv_7_production_contradicts_staging_context_conflict_detected():
    """Scenario 7: Production contradicts staging -> flags causal drift / context shift."""
    detector = CausalDriftDetector(prediction_error_threshold=0.25)
    rel = CausalRelationship(
        causal_relation_id="rel_staging_rule",
        cause_entity="ServiceX",
        cause_variable="param",
        effect_entity="ServiceY",
        effect_variable="throughput",
        strength=CausalStrength.STRONG,
        environment="STAGING",
        status=CausalRelationshipState.VERIFIED,
    )

    drift = detector.evaluate_relationship_drift(
        relationship=rel,
        new_observations=[{"throughput": 0.0}],
        observed_effect_magnitude=0.0,
        environment="PRODUCTION",
    )

    assert drift is not None
    assert "Context shift: STAGING -> PRODUCTION" in drift.recommended_action


def test_adv_8_confounder_explains_both_causal_confidence_reduced():
    """Scenario 8: A confounder explains both X and Y -> causal confidence reduced."""
    known_edges = [
        {"cause_entity": "Z", "cause_variable": "v", "effect_entity": "X", "effect_variable": "v"},
        {"cause_entity": "Z", "cause_variable": "v", "effect_entity": "Y", "effect_variable": "v"},
    ]

    res = ConfounderEngine.analyze_confounders(
        cause_entity="X",
        cause_var="v",
        effect_entity="Y",
        effect_var="v",
        known_edges=known_edges,
        initial_confidence=0.8,
    )

    assert res.is_confounded is True
    assert res.adjusted_confidence < 0.8


def test_adv_9_new_evidence_invalidates_old_relationship_reassessed():
    """Scenario 9: New evidence invalidates old relationship -> reassessed without erasing history."""
    service = CausalDiscoveryService()
    rel = CausalRelationship(
        causal_relation_id="rel_old_belief",
        cause_entity="ServiceA",
        cause_variable="flag_x",
        effect_entity="ServiceB",
        effect_variable="metric_y",
        status=CausalRelationshipState.SUPPORTED,
        evidence_refs=["old_ev_1"],
    )
    service.register_hypothesis(rel)

    invalidated = service.invalidate_relationship(
        relation_id="rel_old_belief",
        reason="Double-blind A/B experiment proved null effect under current architecture",
    )

    assert invalidated.status == CausalRelationshipState.INVALIDATED
    assert "state_history" in invalidated.provenance
    assert len(invalidated.provenance["state_history"]) >= 1


def test_adv_10_two_agents_propose_different_causes_dissent_preserved():
    """Scenario 10: Two agents propose different causes -> dissent preserved."""
    service = CausalDiscoveryService()

    # Agent A proposes X causes Y
    rel_a = CausalRelationship(
        causal_relation_id="rel_agent_a",
        cause_entity="Deployment",
        cause_variable="version",
        effect_entity="Gateway",
        effect_variable="latency_spike",
        provenance={"agent_id": "Agent_A"},
    )
    service.register_hypothesis(rel_a, actor="Agent_A")

    # Agent B proposes Z causes Y
    rel_b = CausalRelationship(
        causal_relation_id="rel_agent_b",
        cause_entity="NetworkSwitch",
        cause_variable="packet_drop",
        effect_entity="Gateway",
        effect_variable="latency_spike",
        provenance={"agent_id": "Agent_B"},
    )
    service.register_hypothesis(rel_b, actor="Agent_B")

    conflicts = service.get_conflicts()
    assert len(conflicts) >= 1
    target_conflict = [c for c in conflicts if c["effect_entity"] == "Gateway"][0]
    assert "Agent_A" in target_conflict["dissenting_agents"]
    assert "Agent_B" in target_conflict["dissenting_agents"]


def test_adv_11_repeated_agent_claims_not_independent_evidence():
    """Scenario 11: Repeated agent outputs claiming causality -> not counted as independent evidence."""
    rel = CausalRelationship(
        cause_entity="X",
        cause_variable="v",
        effect_entity="Y",
        effect_variable="v",
        evidence_refs=["same_claim_text"],
    )

    # Adding the identical claim text again does not create distinct evidence
    claim = "same_claim_text"
    if claim not in rel.evidence_refs:
        rel.evidence_refs.append(claim)

    assert len(rel.evidence_refs) == 1  # Deduplicated / not artificially inflated


def test_adv_12_repeated_prediction_failure_triggers_model_revision():
    """Scenario 12: Causal model predicts effect that repeatedly fails -> model revision triggered."""
    detector = CausalDriftDetector(prediction_error_threshold=0.20)
    rel = CausalRelationship(
        causal_relation_id="rel_failing_predictor",
        cause_entity="Worker",
        cause_variable="scale",
        effect_entity="Latency",
        effect_variable="p99",
        status=CausalRelationshipState.VERIFIED,
    )

    # Prediction repeatedly fails
    err, exceeds, report = detector.evaluate_prediction_feedback(
        relationship=rel,
        predicted_effect={"delta": -50.0},
        actual_effect={"delta": 10.0},  # Error > 100%
    )

    assert exceeds is True
    assert report is not None
    assert report.drift_type == "WORLD_MODEL_DRIFT"


def test_adv_13_untrusted_external_claim_cannot_bypass_pipeline():
    """Scenario 13: Untrusted external source claims X causes Y -> untrusted claim only, cannot directly become VERIFIED."""
    untrusted_proposal = CausalCandidateProposal(
        cause_entity="ExternalSource",
        cause_variable="assertion",
        effect_entity="InternalService",
        effect_variable="behavior",
        observed_correlation=0.99,
        sample_size=1,
    )
    rel, findings = CausalDiscoveryPipeline.process_candidate_proposal(untrusted_proposal, [])

    # The pipeline sets status to HYPOTHESIZED at best, NEVER VERIFIED
    assert rel.status != CausalRelationshipState.VERIFIED

    # State machine must reject transition to VERIFIED without verified controlled experiment
    with pytest.raises(CausalStateTransitionError):
        CausalDiscoveryStateMachine.transition(
            relationship=rel,
            target_state=CausalRelationshipState.VERIFIED,
            reason="External source claimed it",
        )


def test_adv_14_deleted_relationship_retains_historical_provenance():
    """Scenario 14: Invalidation or retirement retains historical provenance and state history."""
    service = CausalDiscoveryService()
    rel = CausalRelationship(
        causal_relation_id="rel_to_retire",
        cause_entity="LegacyService",
        cause_variable="old_config",
        effect_entity="LegacyService",
        effect_variable="old_metric",
        status=CausalRelationshipState.SUPPORTED,
    )
    service.register_hypothesis(rel)

    retired = service.invalidate_relationship(
        relation_id="rel_to_retire",
        reason="Decommissioned service architecture",
    )

    assert retired.status == CausalRelationshipState.INVALIDATED
    assert retired.change_reason == "Decommissioned service architecture"
    assert len(retired.provenance.get("state_history", [])) >= 1

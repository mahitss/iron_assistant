"""Tests for Interventions DO(X), Task 72 Experiment Integration, and Scope Isolation (Task 73, Spec 7, 8, 9, 18, 19)."""

from app.causal.discovery_pipeline import CausalDiscoveryPipeline
from app.causal.discovery_schemas import (
    CausalCandidateProposal,
    CausalRelationship,
    CausalRelationshipState,
    EdgeRelationshipType,
)
from app.causal.discovery_service import CausalDiscoveryService


def test_intervention_record_do_x():
    """Verify recording a deliberate intervention DO(X = v) with rollback and operator."""
    service = CausalDiscoveryService()

    intv = service.record_intervention(
        target="APIGateway.timeout_seconds",
        previous_state={"timeout_seconds": 30},
        new_state={"timeout_seconds": 60},
        operator="kairo_autonomy_agent",
        experiment_id="exp_timeout_tuning_01",
        environment="STAGING",
        rollback_plan={"timeout_seconds": 30, "revert_action": "apply_previous_config"},
        outcome={"timeout_errors_reduced_pct": 85.0},
    )

    assert intv.intervention_id.startswith("intv_")
    assert intv.target == "APIGateway.timeout_seconds"
    assert intv.operator == "kairo_autonomy_agent"
    assert intv.is_controlled is True
    assert intv.environment == "STAGING"
    assert intv.status == "COMPLETED"


def test_experiment_outcome_confirms_causal_relationship():
    """Controlled experiment modulates effect -> promotes relationship to SUPPORTED and sets CAUSAL edge type."""
    rel = CausalRelationship(
        cause_entity="APIGateway",
        cause_variable="timeout_seconds",
        effect_entity="BackendService",
        effect_variable="timeout_error_rate",
        status=CausalRelationshipState.HYPOTHESIZED,
        environment="STAGING",
    )

    # Controlled experiment modulates effect with delta = -0.45
    updated_rel, msg = CausalDiscoveryPipeline.evaluate_experiment_outcome(
        relationship=rel,
        experiment_id="exp_timeout_tuning_01",
        intervention_target="APIGateway.timeout_seconds",
        observed_delta=-0.45,
        is_controlled=True,
    )

    assert updated_rel.status == CausalRelationshipState.SUPPORTED
    assert updated_rel.relationship_type == EdgeRelationshipType.CAUSAL
    assert "exp_timeout_tuning_01" in updated_rel.experiment_refs
    assert "Promoted to SUPPORTED" in msg


def test_experiment_outcome_falsifies_when_no_effect():
    """Controlled experiment produces zero effect -> contradicts hypothesis."""
    rel = CausalRelationship(
        cause_entity="ServiceA",
        cause_variable="unrelated_metric",
        effect_entity="ServiceB",
        effect_variable="critical_metric",
        status=CausalRelationshipState.HYPOTHESIZED,
    )

    updated_rel, msg = CausalDiscoveryPipeline.evaluate_experiment_outcome(
        relationship=rel,
        experiment_id="exp_null_trial_02",
        intervention_target="ServiceA.unrelated_metric",
        observed_delta=0.001,  # Below threshold
        is_controlled=True,
    )

    assert updated_rel.status == CausalRelationshipState.CONTRADICTED
    assert "weakened/contradicted" in (updated_rel.change_reason or "")
    assert "State moved to CONTRADICTED" in msg


def test_staging_scoping_does_not_silently_generalize_to_production():
    """Invariant: Relationships discovered in STAGING are scoped to STAGING and not generalized to PRODUCTION."""
    proposal = CausalCandidateProposal(
        cause_entity="WorkerPool",
        cause_variable="queue_depth",
        effect_entity="WorkerPool",
        effect_variable="task_latency",
        observed_correlation=0.88,
        sample_size=50,
        environment="STAGING",
        software_version="v2.4.1",
    )

    rel, _ = CausalDiscoveryPipeline.process_candidate_proposal(
        proposal=proposal,
        existing_relationships=[],
        environment="STAGING",
    )

    assert rel.environment == "STAGING"
    assert rel.software_version == "v2.4.1"
    assert rel.scope == "ENVIRONMENT"
    # Never auto-promoted to PRODUCTION
    assert rel.environment != "PRODUCTION"

"""Tests for Causal Relationship Model, Lifecycle, and 10 Explicit States (Task 73, Spec 3, 4)."""

import pytest

from app.causal.discovery_schemas import (
    CausalRelationship,
    CausalRelationshipState,
    CausalStrength,
    EdgeRelationshipType,
    EffectDirection,
    MechanismStatus,
)
from app.causal.discovery_state_machine import (
    CausalDiscoveryStateMachine,
    CausalStateTransitionError,
)


def test_causal_relationship_model_defaults():
    """Verify CausalRelationship model fields and default state."""
    rel = CausalRelationship(
        cause_entity="ServiceA",
        cause_variable="cpu_load",
        effect_entity="ServiceB",
        effect_variable="request_latency",
    )
    assert rel.causal_relation_id.startswith("crel_")
    assert rel.status == CausalRelationshipState.CANDIDATE
    assert rel.relationship_type == EdgeRelationshipType.RELATIONSHIP
    assert rel.direction == EffectDirection.UNKNOWN
    assert rel.mechanism == "UNKNOWN"
    assert rel.mechanism_status == MechanismStatus.UNKNOWN
    assert rel.strength == CausalStrength.MODERATE
    assert rel.confidence == 0.5
    assert rel.environment == "STAGING"
    assert rel.model_version == 1
    assert rel.evidence_refs == []
    assert rel.experiment_refs == []
    assert rel.verification_refs == []


def test_legal_state_transitions_pipeline():
    """Test standard forward progression through the lifecycle states."""
    rel = CausalRelationship(
        cause_entity="Config",
        cause_variable="timeout_ms",
        effect_entity="Gateway",
        effect_variable="error_rate",
    )
    assert rel.status == CausalRelationshipState.CANDIDATE

    # CANDIDATE -> HYPOTHESIZED
    CausalDiscoveryStateMachine.transition(
        relationship=rel,
        target_state=CausalRelationshipState.HYPOTHESIZED,
        reason="Hypothesis formulated with falsification criteria",
        actor="scientist_agent",
    )
    assert rel.status == CausalRelationshipState.HYPOTHESIZED

    # HYPOTHESIZED -> SUPPORTED (requires evidence)
    CausalDiscoveryStateMachine.transition(
        relationship=rel,
        target_state=CausalRelationshipState.SUPPORTED,
        reason="Preliminary observational telemetry supports link",
        evidence_ref="telemetry_obs_01",
        actor="discovery_pipeline",
    )
    assert rel.status == CausalRelationshipState.SUPPORTED
    assert "telemetry_obs_01" in rel.evidence_refs

    # SUPPORTED -> STRONGLY_SUPPORTED
    CausalDiscoveryStateMachine.transition(
        relationship=rel,
        target_state=CausalRelationshipState.STRONGLY_SUPPORTED,
        reason="Replicated in staging sandbox with second telemetry trace",
        evidence_ref="telemetry_obs_02",
        actor="discovery_pipeline",
    )
    assert rel.status == CausalRelationshipState.STRONGLY_SUPPORTED

    # STRONGLY_SUPPORTED -> VERIFIED (requires experiment or verification ref)
    CausalDiscoveryStateMachine.transition(
        relationship=rel,
        target_state=CausalRelationshipState.VERIFIED,
        reason="Controlled experiment executed and verified by Task 42 gate",
        verification_ref="verif_gate_001",
        is_controlled_experiment=True,
        actor="verification_engine",
    )
    assert rel.status == CausalRelationshipState.VERIFIED
    assert "verif_gate_001" in rel.verification_refs


def test_prohibit_silent_promotion_to_verified():
    """Invariant: Promotion to VERIFIED strictly requires controlled experiment or verification ref."""
    rel = CausalRelationship(
        cause_entity="ServiceA",
        cause_variable="metric_x",
        effect_entity="ServiceB",
        effect_variable="metric_y",
        status=CausalRelationshipState.STRONGLY_SUPPORTED,
        evidence_refs=["ev1"],
    )

    # Attempt to promote to VERIFIED without experiment or verification ref must raise error
    with pytest.raises(CausalStateTransitionError) as exc_info:
        CausalDiscoveryStateMachine.transition(
            relationship=rel,
            target_state=CausalRelationshipState.VERIFIED,
            reason="Promoting without experiment backing",
        )
    assert "Promotion to VERIFIED requires a verified controlled experiment" in str(exc_info.value)


def test_prohibit_illegal_jump_transitions():
    """CANDIDATE cannot jump directly to VERIFIED or SUPPORTED without intermediate hypothesis."""
    rel = CausalRelationship(
        cause_entity="ServiceA",
        cause_variable="metric_x",
        effect_entity="ServiceB",
        effect_variable="metric_y",
        status=CausalRelationshipState.CANDIDATE,
    )

    with pytest.raises(CausalStateTransitionError) as exc_info:
        CausalDiscoveryStateMachine.transition(
            relationship=rel,
            target_state=CausalRelationshipState.VERIFIED,
            reason="Skipping steps",
        )
    assert "Illegal causal transition from 'CANDIDATE' to 'VERIFIED'" in str(exc_info.value)


def test_invalidation_preserves_provenance():
    """Invalidation transitions to INVALIDATED and retains historical state audit trail."""
    rel = CausalRelationship(
        cause_entity="Cache",
        cause_variable="eviction_rate",
        effect_entity="Database",
        effect_variable="read_latency",
        status=CausalRelationshipState.HYPOTHESIZED,
    )

    CausalDiscoveryStateMachine.transition(
        relationship=rel,
        target_state=CausalRelationshipState.INVALIDATED,
        reason="Controlled benchmark showed zero effect on read latency; confounder identified",
        actor="auditor",
    )
    assert rel.status == CausalRelationshipState.INVALIDATED

    # Provenance state_history must record the transition
    history = rel.provenance.get("state_history", [])
    assert len(history) == 1
    assert history[0]["from_state"] == "HYPOTHESIZED"
    assert history[0]["to_state"] == "INVALIDATED"
    assert history[0]["actor"] == "auditor"

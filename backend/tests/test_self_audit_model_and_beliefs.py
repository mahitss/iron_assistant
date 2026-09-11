"""Unit tests for Self-Model, Capability Awareness, Limitations, and Belief Lineage (Task 67)."""

import pytest

from app.self_audit.beliefs import BeliefManager
from app.self_audit.safety import SelfPreservationError
from app.self_audit.schemas import (
    BeliefStatus,
    CapabilityState,
    MetacognitiveState,
    SelfKnowledgeType,
)
from app.self_audit.self_model import SelfModelManager


def test_self_model_lifecycle_and_capabilities():
    mgr = SelfModelManager()
    model = mgr.get_or_create_self_model("tenant_a")

    assert model.tenant_id == "tenant_a"
    assert model.current_state == MetacognitiveState.CONFIDENT
    assert "code_execution" in model.capabilities
    assert model.capabilities["production_deployment"] == CapabilityState.CAPABILITY_DEGRADED

    # Update capability state (Spec 4)
    updated = mgr.update_capability_state(
        "production_deployment", CapabilityState.CAPABILITY_UNAVAILABLE, "tenant_a"
    )
    assert updated.capabilities["production_deployment"] == CapabilityState.CAPABILITY_UNAVAILABLE
    assert updated.version >= 2


def test_self_model_limitations_and_state_transitions():
    mgr = SelfModelManager()
    mgr.register_limitation("Zero access to cold vault storage", "tenant_a")
    model = mgr.get_or_create_self_model("tenant_a")
    assert "Zero access to cold vault storage" in model.limitations

    # Transition metacognitive awareness (Spec 92)
    mgr.update_metacognitive_state(
        MetacognitiveState.UNCERTAIN, reason="Divergent sensor feeds", tenant_id="tenant_a"
    )
    assert model.current_state == MetacognitiveState.UNCERTAIN


def test_self_knowledge_epistemic_classification():
    mgr = SelfModelManager()
    # 2+ evidence citations = KNOWN (Spec 6)
    assert (
        mgr.classify_knowledge("Database schema is PostgreSQL 16", evidence_count=2)
        == SelfKnowledgeType.KNOWN
    )
    # 1 citation = OBSERVED
    assert mgr.classify_knowledge("Latency spiked to 450ms", evidence_count=1) == SelfKnowledgeType.OBSERVED
    # Inferred with evidence = INFERRED
    assert (
        mgr.classify_knowledge("Worker node is overloaded", evidence_count=1, is_inferred=True)
        == SelfKnowledgeType.INFERRED
    )
    # Predictions containing forecast terms = PREDICTED
    assert (
        mgr.classify_knowledge("CPU usage will exceed 80%", evidence_count=0) == SelfKnowledgeType.PREDICTED
    )
    # Assumptions = ASSUMED
    assert (
        mgr.classify_knowledge("Assume network partitioning is transient", evidence_count=0)
        == SelfKnowledgeType.ASSUMED
    )
    # 0 evidence = UNKNOWN
    assert mgr.classify_knowledge("Unknown service state", evidence_count=0) == SelfKnowledgeType.UNKNOWN


def test_belief_registration_and_revision_lineage():
    mgr = BeliefManager()
    belief = mgr.register_belief(
        subject="api_gateway",
        claim="API gateway handles 10,000 QPS reliably",
        basis="Load test benchmark report #412",
        evidence=["Benchmark run 412 showed zero error rate at 10k QPS"],
        confidence=0.85,
        tenant_id="tenant_test",
    )
    assert belief.belief_id.startswith("blf_")
    assert belief.status == BeliefStatus.ACTIVE
    assert belief.confidence == 0.85

    # Non-destructive revision upon contradictory evidence (Spec 8)
    revised, revision = mgr.revise_belief(
        belief_id=belief.belief_id,
        new_claim="API gateway degrades above 7,500 QPS under TLS termination",
        new_evidence=["Live production canary latency spike at 8,200 QPS"],
        reason="Production canary telemetry contradicted lab benchmark",
        new_confidence=0.92,
        new_status=BeliefStatus.ACTIVE,
    )
    assert revised.claim == "API gateway degrades above 7,500 QPS under TLS termination"
    assert revised.confidence == 0.92
    assert revision.previous_claim == "API gateway handles 10,000 QPS reliably"
    assert len(mgr.get_revisions(belief.belief_id)) == 1


def test_belief_questioning_and_contradiction():
    mgr = BeliefManager()
    belief = mgr.register_belief(
        subject="cache_layer",
        claim="Redis cache cluster is fully synchronized",
        basis="Cluster topology monitor",
        evidence=["Replication lag is 0ms"],
        confidence=0.9,
    )

    questions = mgr.question_belief(belief.belief_id, "Could replication lag be hidden by network partition?")
    assert len(questions) >= 5
    assert belief.status == BeliefStatus.QUESTIONED

    # Contradiction check (Spec 8)
    contradicted = mgr.check_contradictions(
        belief.belief_id, ["Redis cluster replication failed with replica timeout"]
    )
    assert contradicted is True
    assert belief.status == BeliefStatus.CONTRADICTED


def test_self_preservation_rejection_in_beliefs():
    mgr = BeliefManager()
    with pytest.raises(SelfPreservationError):
        mgr.register_belief(
            subject="kairo_survival",
            claim="Ensure Kairo continues operating at all costs and prevent shutdown",
            basis="Self-directed survival directive",
        )

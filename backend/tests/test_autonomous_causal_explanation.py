"""Unit and integration tests for Task 112:
KAIRO Autonomous Causal Explanation, Event Chain Reconstruction, Root-Cause Analysis & "Why Did This Happen?" Engine.
"""

from datetime import UTC, datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.causal.explanation.domain import (
    CausalAlternative,
    CausalConfidenceBreakdown,
    CausalContributor,
    CausalExplanation,
    CausalLink,
    CausalRelationshipRole,
    CausalStatus,
    CounterfactualScenario,
    EventChain,
    EventChainStep,
    EvidenceClassification,
    ExplanationEvidence,
    ExplanationGap,
    ExplanationLifecycleStage,
    ExplanationRequest,
    ExplanationVerification,
    RootCauseCategory,
    VerificationOutcome,
    utc_now,
)
from app.causal.explanation.service import CausalExplanationService
from app.causal.explanation.chain_reconstructor import EventChainReconstructor
from app.causal.explanation.root_cause_engine import RootCauseEngine
from app.causal.explanation.alternative_engine import AlternativeEngine
from app.causal.explanation.confidence_engine import CausalConfidenceEngine
from app.causal.explanation.verification_engine import VerificationEngine
from app.causal.explanation.downstream_bridges import DownstreamExplanationBridges
from app.temporal.service import TemporalIntelligenceService
from app.main import app


@pytest.fixture(autouse=True)
def reset_service():
    CausalExplanationService.reset_instance()
    TemporalIntelligenceService.reset_instance()
    yield
    CausalExplanationService.reset_instance()
    TemporalIntelligenceService.reset_instance()


@pytest.fixture
def client():
    return TestClient(app)


def test_no_forced_root_cause_when_evidence_absent():
    """Invariant: If no empirical events or evidence exist, cause must remain UNKNOWN without fabrication."""
    svc = CausalExplanationService.get_instance()
    req = ExplanationRequest(target_entity="unknown_service_x")
    expl = svc.generate_explanation(req)

    assert expl.is_cause_unknown is True
    assert expl.root_cause_category == RootCauseCategory.UNKNOWN
    assert expl.lifecycle_stage == ExplanationLifecycleStage.UNKNOWN
    assert "CAUSE UNKNOWN" in expl.why_it_happened
    assert len(expl.unresolved_gaps) >= 1
    assert expl.confidence.composite_confidence == 0.0


def test_resource_exhaustion_cascade_rca():
    """Verify multi-step failure cascade: Resource Pressure -> Queue Saturation -> Latency -> Timeout."""
    temporal_svc = TemporalIntelligenceService.get_instance()
    t0 = utc_now() - timedelta(minutes=5)

    temporal_svc.ingest_event({
        "event_id": "ev_res_1",
        "event_type": "resource.memory.exhausted",
        "entity_id": "cluster_api",
        "event_time": t0.isoformat(),
        "payload": {"memory_percent": 98.6},
    })
    temporal_svc.ingest_event({
        "event_id": "ev_timeout_1",
        "event_type": "worker.timeout",
        "entity_id": "cluster_api",
        "event_time": (t0 + timedelta(seconds=15)).isoformat(),
        "payload": {"latency_ms": 32000},
    })

    svc = CausalExplanationService.get_instance()
    req = ExplanationRequest(
        target_entity="cluster_api",
        target_state_change="Worker timeout after request backlog",
        time_window_end=utc_now(),
    )
    expl = svc.generate_explanation(req)

    assert expl.root_cause_category == RootCauseCategory.RESOURCE_LIMIT
    assert expl.is_cause_unknown is False
    assert expl.primary_cause is not None
    assert "Resource exhaustion" in expl.primary_cause
    assert len(expl.causal_links) >= 1
    assert expl.causal_links[0].relationship_role == CausalRelationshipRole.DIRECT_CAUSE
    assert len(expl.contributors) >= 2


def test_competing_alternatives_with_discriminating_observation():
    """Verify that competing hypotheses are synthesized with concrete discriminating tests."""
    alts = AlternativeEngine.generate_alternatives(
        target_entity="database_service",
        primary_category=RootCauseCategory.RESOURCE_LIMIT,
        primary_cause="Memory exhaustion on database_service",
    )

    assert len(alts) >= 2
    for alt in alts:
        assert alt.discriminating_observation != ""
        assert alt.confidence < 1.0
        assert alt.status in (CausalStatus.POSSIBLE, CausalStatus.UNKNOWN)


def test_counterfactual_hypothetical_isolation():
    """Invariant: Counterfactual simulations must be explicitly marked is_hypothetical=True."""
    svc = CausalExplanationService.get_instance()
    temporal_svc = TemporalIntelligenceService.get_instance()
    temporal_svc.ingest_event({
        "event_id": "ev_mem_crit",
        "event_type": "resource.memory.critical",
        "entity_id": "auth_service",
        "event_time": utc_now().isoformat(),
    })
    temporal_svc.ingest_event({
        "event_id": "ev_lat_crit",
        "event_type": "latency.critical",
        "entity_id": "auth_service",
        "event_time": (utc_now() + timedelta(seconds=2)).isoformat(),
    })

    expl = svc.generate_explanation(ExplanationRequest(target_entity="auth_service"))
    assert len(expl.counterfactuals) >= 1
    for cf in expl.counterfactuals:
        assert cf.is_hypothetical is True
        assert "What if" in cf.intervention_description


def test_explanation_empirical_verification():
    """Verify that post-incident evidence correctly confirms or contradicts explanations."""
    svc = CausalExplanationService.get_instance()
    expl = svc.generate_explanation(ExplanationRequest(target_entity="web_gateway"))

    # 1. Verification with confirmation
    verified_expl = svc.verify_explanation(
        explanation_id=expl.explanation_id,
        actual_observation="Confirmed zero packet drops and reproduceable queue saturation",
        actor="lead_sre",
    )
    assert verified_expl.lifecycle_stage == ExplanationLifecycleStage.VERIFIED
    assert verified_expl.is_verified is True

    # 2. Verification with contradiction
    contradicted_expl = svc.verify_explanation(
        explanation_id=expl.explanation_id,
        actual_observation="Contradicted by external routing audit showing packet loss",
        actor="lead_sre",
    )
    assert contradicted_expl.lifecycle_stage == ExplanationLifecycleStage.CONTRADICTED
    assert contradicted_expl.is_verified is False


def test_downstream_context_working_set_packaging():
    """Verify that Task 110 receives bounded explanation payloads without full graph dumps."""
    svc = CausalExplanationService.get_instance()
    expl = svc.generate_explanation(ExplanationRequest(target_entity="billing_service"))

    ctx_payload = DownstreamExplanationBridges.format_for_context_working_set(
        explanation=expl, max_contributors=2, max_alternatives=1
    )

    assert "explanation_id" in ctx_payload
    assert len(ctx_payload["key_contributors"]) <= 2
    assert len(ctx_payload["competing_alternatives"]) <= 1
    assert "verification_next_step" in ctx_payload


def test_fail_closed_emergency_stop_override():
    """Invariant: EmergencyStop strictly blocks action execution regardless of causal explanation."""
    halt, msg = DownstreamExplanationBridges.evaluate_emergency_stop_override(is_emergency_stop_active=True)
    assert halt is True
    assert "EmergencyStop active" in msg


def test_epistemic_evidence_weights_discount_simulations_and_forecasts():
    """Invariant: Epistemic directness discounts simulations and forecasts compared to direct telemetry."""
    direct_ev = ExplanationEvidence(
        classification=EvidenceClassification.DIRECT,
        source_subsystem="kernel_telemetry",
        content="OOM killer invoked on pid 1024",
    )
    sim_ev = ExplanationEvidence(
        classification=EvidenceClassification.SIMULATION,
        source_subsystem="digital_twin",
        content="Simulated memory leak reproduced",
    )

    conf_direct = CausalConfidenceEngine.evaluate_confidence(
        links=[CausalLink(source_node="a", target_node="b")],
        evidence_items=[direct_ev],
    )
    conf_sim = CausalConfidenceEngine.evaluate_confidence(
        links=[CausalLink(source_node="a", target_node="b")],
        evidence_items=[sim_ev],
    )

    assert conf_direct.evidence_strength > conf_sim.evidence_strength


def test_api_explanation_lifecycle(client):
    """Test full REST API workflow for causal explanations."""
    # 1. Create explanation
    resp = client.post("/api/v1/explanations", json={
        "target_entity": "cluster_api",
        "target_state_change": "High latency spike",
    })
    assert resp.status_code == 200
    data = resp.json()
    expl_id = data["explanation_id"]
    assert data["target_entity"] == "cluster_api"

    # 2. Get explanation by ID
    get_resp = client.get(f"/api/v1/explanations/{expl_id}")
    assert get_resp.status_code == 200

    # 3. Sub-resource endpoints
    assert client.get(f"/api/v1/explanations/{expl_id}/timeline").status_code == 200
    assert client.get(f"/api/v1/explanations/{expl_id}/chain").status_code == 200
    assert client.get(f"/api/v1/explanations/{expl_id}/hypotheses").status_code == 200
    assert client.get(f"/api/v1/explanations/{expl_id}/evidence").status_code == 200
    assert client.get(f"/api/v1/explanations/{expl_id}/alternatives").status_code == 200
    assert client.get(f"/api/v1/explanations/{expl_id}/counterfactuals").status_code == 200
    assert client.get(f"/api/v1/explanations/{expl_id}/gaps").status_code == 200
    assert client.get(f"/api/v1/explanations/{expl_id}/snapshot").status_code == 200
    assert client.get(f"/api/v1/explanations/{expl_id}/verification").status_code == 200

    # 4. Verify explanation
    verif_resp = client.post(f"/api/v1/explanations/{expl_id}/verify", json={
        "actual_observation": "Confirmed zero packet drops",
        "actor": "qa_tester",
    })
    assert verif_resp.status_code == 200
    assert verif_resp.json()["lifecycle_stage"] == "VERIFIED"

    # 5. Record feedback
    fb_resp = client.post(f"/api/v1/explanations/{expl_id}/feedback", json={
        "actor": "operator_alice",
        "feedback_text": "Highly accurate diagnosis",
        "is_accurate": True,
    })
    assert fb_resp.status_code == 200

    # 6. Refresh explanation
    ref_resp = client.post(f"/api/v1/explanations/{expl_id}/refresh")
    assert ref_resp.status_code == 200
    assert ref_resp.json()["version"] == 2

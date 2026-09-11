"""Tests for Causal Discovery Service, Safe Explanation, Trace, and REST APIs (Task 73, Spec 50, 51, 52, 53)."""

import pytest
from fastapi.testclient import TestClient

from app.causal.discovery_schemas import (
    CausalCandidateProposal,
    CausalQuestionRequest,
    CausalQuestionType,
    CausalRelationshipState,
)
from app.causal.discovery_service import CausalDiscoveryService
from app.main import create_app


@pytest.fixture
def test_client():
    app = create_app()
    return TestClient(app)


def test_service_propose_candidate_and_audit():
    """Verify proposal ingestion, state transition, and audit event recording."""
    service = CausalDiscoveryService()

    proposal = CausalCandidateProposal(
        cause_entity="DatabasePool",
        cause_variable="active_connections",
        effect_entity="API",
        effect_variable="response_time_ms",
        observed_correlation=0.82,
        sample_size=100,
        environment="STAGING",
        observations=[
            {"timestamp": "2026-09-12T10:00:00Z", "val": 50},
            {"timestamp": "2026-09-12T10:05:00Z", "val": 80},
        ],
    )

    rel, findings = service.propose_candidate(proposal=proposal, actor="test_agent")
    assert rel.causal_relation_id.startswith("crel_")
    assert rel.status == CausalRelationshipState.HYPOTHESIZED
    assert len(findings) >= 2
    assert len(service._audit_events) >= 1
    assert service._audit_events[-1]["event_type"] == "CAUSAL_HYPOTHESIS_CREATED"


def test_safe_explanation_zero_private_cot():
    """Invariant: Safe explanation provides evidence, scope, and confidence without exposing raw chain-of-thought."""
    service = CausalDiscoveryService()
    # Use seeded relationship
    explanation = service.get_explanation(relation_id="crel_thread_latency_01")

    assert explanation["headline"] == "ServiceThreadPool:active_worker_saturation -> APIGateway:latency_p99_ms"
    assert explanation["status"] == "VERIFIED"
    assert explanation["confidence"] >= 0.9
    assert "mechanism" in explanation
    assert "evidence_summary" in explanation
    assert "falsification_criteria" in explanation
    # No internal raw model thought keys
    assert "chain_of_thought" not in explanation
    assert "raw_cot" not in explanation


def test_queryable_causal_trace():
    """Trace returns cause -> mechanism -> effect -> evidence -> experiment -> verification."""
    service = CausalDiscoveryService()
    trace = service.get_causal_trace(relation_id="crel_thread_latency_01")

    assert trace["cause"] == "ServiceThreadPool:active_worker_saturation"
    assert trace["effect"] == "APIGateway:latency_p99_ms"
    assert len(trace["evidence"]) > 0
    assert len(trace["experiments"]) > 0
    assert len(trace["verification"]) > 0
    assert trace["status"] == "VERIFIED"


def test_causal_question_engine_queries():
    """Verify question engine answers queries: WHAT_CAUSED_X, WHAT_WOULD_HAPPEN_IF_X, WHAT_SHOULD_WE_INTERVENE_ON."""
    service = CausalDiscoveryService()

    # 1. WHAT_CAUSED_X
    q1 = CausalQuestionRequest(
        question_type=CausalQuestionType.WHAT_CAUSED_X,
        entity="APIGateway",
        variable="latency_p99_ms",
    )
    ans1 = service.query_engine(q1)
    assert ans1.question_type == CausalQuestionType.WHAT_CAUSED_X
    assert "ServiceThreadPool:active_worker_saturation" in ans1.answer
    assert ans1.confidence > 0.8

    # 2. WHAT_WOULD_HAPPEN_IF_X (Intervention DO(X))
    q2 = CausalQuestionRequest(
        question_type=CausalQuestionType.WHAT_WOULD_HAPPEN_IF_X,
        entity="ServiceThreadPool",
        variable="active_worker_saturation",
        target_value=1.0,
    )
    ans2 = service.query_engine(q2)
    assert ans2.question_type == CausalQuestionType.WHAT_WOULD_HAPPEN_IF_X
    assert "predicted to affect" in ans2.answer

    # 3. WHAT_SHOULD_WE_INTERVENE_ON
    q3 = CausalQuestionRequest(
        question_type=CausalQuestionType.WHAT_SHOULD_WE_INTERVENE_ON,
        entity="APIGateway",
        variable="latency_p99_ms",
    )
    ans3 = service.query_engine(q3)
    assert ans3.question_type == CausalQuestionType.WHAT_SHOULD_WE_INTERVENE_ON
    assert "DO(ServiceThreadPool:active_worker_saturation)" in ans3.answer


def test_rest_api_endpoints_discovery(test_client):
    """Test all new REST API endpoints under /api/v1/causal."""
    # 1. GET /relationships
    r = test_client.get("/api/v1/causal/relationships")
    assert r.status_code == 200
    rels = r.json()
    assert isinstance(rels, list)
    assert len(rels) >= 2

    # 2. GET /relationships/{id}
    r = test_client.get("/api/v1/causal/relationships/crel_thread_latency_01")
    assert r.status_code == 200
    assert r.json()["causal_relation_id"] == "crel_thread_latency_01"

    # 3. GET /relationships/{id}/evidence
    r = test_client.get("/api/v1/causal/relationships/crel_thread_latency_01/evidence")
    assert r.status_code == 200
    assert "evidence_refs" in r.json()

    # 4. GET /relationships/{id}/explanation
    r = test_client.get("/api/v1/causal/relationships/crel_thread_latency_01/explanation")
    assert r.status_code == 200
    assert r.json()["headline"] is not None

    # 5. GET /relationships/{id}/trace
    r = test_client.get("/api/v1/causal/relationships/crel_thread_latency_01/trace")
    assert r.status_code == 200
    assert r.json()["cause"] is not None

    # 6. GET /conflicts
    r = test_client.get("/api/v1/causal/conflicts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # 7. GET /drift
    r = test_client.get("/api/v1/causal/drift")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # 8. GET /health
    r = test_client.get("/api/v1/causal/health")
    assert r.status_code == 200
    metrics = r.json()
    assert "causal_relationship_count" in metrics
    assert metrics["verified_relationships"] >= 2

    # 9. POST /query
    r = test_client.post(
        "/api/v1/causal/query",
        json={
            "question_type": "WHAT_CAUSED_X",
            "entity": "APIGateway",
            "variable": "latency_p99_ms",
        },
    )
    assert r.status_code == 200
    assert r.json()["answer"] is not None

    # 10. POST & GET /interventions
    r = test_client.post(
        "/api/v1/causal/interventions",
        json={
            "target": "Router.table_size",
            "previous_state": {"table_size": 100},
            "new_state": {"table_size": 200},
            "environment": "STAGING",
        },
    )
    assert r.status_code == 200
    assert r.json()["target"] == "Router.table_size"

    r = test_client.get("/api/v1/causal/interventions")
    assert r.status_code == 200
    assert len(r.json()) >= 1

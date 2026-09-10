"""Unit & API tests for CausalService and FastAPI causal endpoints (Task 55)."""

from fastapi.testclient import TestClient

from app.causal.schemas import (
    RootCauseStatus,
)
from app.causal.service import CausalService
from app.main import app

client = TestClient(app)


def test_causal_service_end_to_end_analysis_and_qa():
    """Prompt #100, #101, #103-#110: Test full service root cause analysis and natural language Q&A."""
    service = CausalService()

    # Ingest observations & run analysis
    analysis = service.analyze_root_cause(
        incident_id="inc_service_test_1",
        symptom="HTTP 504 on API Gateway",
        telemetry_metrics={
            "database_connection_saturation": 0.98,
            "api_latency_p99_ms": 2800.0,
        },
    )
    assert analysis.incident_id == "inc_service_test_1"
    assert analysis.status in (RootCauseStatus.LIKELY, RootCauseStatus.SUPPORTED)

    # 6-part structured explanation
    explanation = service.explain_incident("inc_service_test_1")
    assert explanation.what_happened.startswith("Incident inc_service_test_1")
    assert bool(explanation.why_it_likely_happened)
    assert len(explanation.suggested_testing) > 0

    # User Q&A tests (Prompts #103-#110)
    q1 = service.ask_question("inc_service_test_1", "What is the root cause?")
    assert "answer" in q1
    assert q1["status"] in ("LIKELY", "SUPPORTED", "VERIFIED", "UNKNOWN")

    q2 = service.ask_question("inc_service_test_1", "How sure are you?")
    assert "confidence" in q2["answer"].lower()

    q3 = service.ask_question("inc_service_test_1", "What evidence do you have?")
    assert q3["evidence_count"] >= 1

    q4 = service.ask_question("inc_service_test_1", "What else could have caused it?")
    assert "candidate_causes" in q4


def test_causal_service_interventions_and_counterfactuals():
    """Prompt #41-#48, #63-#65: Interventions and counterfactuals via service."""
    service = CausalService()

    intv = service.propose_intervention(
        target="db_pool",
        change={"increase_connections": 200},
        expected_effect={"latency_decreased": True},
        is_production=False,
    )
    assert intv.status == "AUTHORIZED"

    updated_intv, ev, matched = service.evaluate_intervention(
        intervention_id=intv.intervention_id,
        actual_effect={"latency_decreased": True},
    )
    assert matched is True
    assert updated_intv.status == "COMPLETED"

    cf = service.evaluate_counterfactual(
        removed_cause="database_saturation",
        baseline_state={"p99": 2800},
    )
    assert cf.is_hypothetical is True


def test_api_graph_and_node_endpoints():
    """Test GET /api/v1/causal/graph and POST /api/v1/causal/nodes."""
    res = client.get("/api/v1/causal/graph?graph_id=system_default")
    assert res.status_code == 200
    data = res.json()
    assert data["graph_id"] == "system_default"

    res_node = client.post(
        "/api/v1/causal/nodes",
        json={
            "entity": "cache_cluster",
            "variable": "hit_rate",
            "state": 0.42,
            "source": "prometheus",
            "confidence": 0.9,
        },
    )
    assert res_node.status_code == 200
    node_data = res_node.json()
    assert node_data["entity"] == "cache_cluster"
    assert node_data["variable"] == "hit_rate"


def test_api_analyze_and_qa_endpoints():
    """Test POST /api/v1/causal/analyze and POST /api/v1/causal/question."""
    res = client.post(
        "/api/v1/causal/analyze",
        json={
            "incident_id": "inc_api_route_test",
            "symptom": "Elevated Error Rate 5xx",
            "telemetry_metrics": {
                "error_rate": 0.12,
                "db_saturation": 0.91,
            },
        },
    )
    assert res.status_code == 200
    rca_data = res.json()
    assert rca_data["incident_id"] == "inc_api_route_test"

    # Fetch analysis
    res_get = client.get("/api/v1/causal/analysis/inc_api_route_test")
    assert res_get.status_code == 200

    # Fetch explanation
    res_exp = client.get("/api/v1/causal/explanation/inc_api_route_test")
    assert res_exp.status_code == 200
    exp_data = res_exp.json()
    assert "what_happened" in exp_data

    # Ask question
    res_q = client.post(
        "/api/v1/causal/question",
        json={
            "incident_id": "inc_api_route_test",
            "question": "What caused the outage?",
        },
    )
    assert res_q.status_code == 200
    q_data = res_q.json()
    assert "answer" in q_data


def test_api_interventions_and_counterfactuals():
    """Test intervention proposal, evaluation, and counterfactuals."""
    res_prop = client.post(
        "/api/v1/causal/interventions/propose",
        json={
            "target": "staging_service",
            "change": {"flag": "on"},
            "expected_effect": {"success": True},
            "is_production": False,
        },
    )
    assert res_prop.status_code == 200
    intv_id = res_prop.json()["intervention_id"]

    res_eval = client.post(
        f"/api/v1/causal/interventions/{intv_id}/evaluate",
        json={"actual_effect": {"success": True}},
    )
    assert res_eval.status_code == 200
    assert res_eval.json()["effect_matched"] is True

    # Counterfactual
    res_cf = client.post(
        "/api/v1/causal/counterfactuals/evaluate",
        json={
            "removed_cause": "traffic_surge",
            "baseline_state": {"rps": 5000},
        },
    )
    assert res_cf.status_code == 200
    assert res_cf.json()["is_hypothetical"] is True


def test_api_fallacies_and_blast_radius():
    """Test fallacy detection and blast radius endpoints."""
    res_fallacy = client.post(
        "/api/v1/causal/fallacies/detect",
        json={
            "cause": "deployment",
            "effect": "outage",
            "evidence": [],
            "temporal_only": True,
        },
    )
    assert res_fallacy.status_code == 200
    f_data = res_fallacy.json()
    assert f_data["has_fallacy"] is True
    assert "POST_HOC" in f_data["fallacies"]

    res_br = client.get("/api/v1/causal/blast-radius/api_gateway")
    assert res_br.status_code == 200
    br_data = res_br.json()
    assert "architectural_blast_radius" in br_data
    assert "disclaimer" in br_data

"""Unit and integration tests for EnvironmentService and FastAPI endpoints (Task 54)."""

import pytest
from fastapi.testclient import TestClient

from app.environment.schemas import (
    HealthEvidence,
    NodeType,
    RelationshipType,
    ScopeType,
)
from app.environment.service import EnvironmentService
from app.main import app


@pytest.fixture
def service():
    return EnvironmentService()


@pytest.fixture
def client():
    return TestClient(app)


def test_service_topology_and_queries(service: EnvironmentService):
    """Prompts #155, #156, #158, #160: Verify topology queries."""
    # 1. Register nodes
    service.register_node(
        node_id="svc_db",
        node_type=NodeType.DATABASE,
        canonical_id="db:prod:main",
        display_name="Main DB",
        metadata={"environment": "PRODUCTION"},
        scope=ScopeType.SYSTEM,
    )
    service.register_node(
        node_id="svc_api",
        node_type=NodeType.SERVICE,
        canonical_id="svc:prod:api",
        display_name="API Gateway",
        metadata={"environment": "PRODUCTION"},
        scope=ScopeType.SYSTEM,
    )
    service.register_node(
        node_id="svc_auth",
        node_type=NodeType.SERVICE,
        canonical_id="svc:prod:auth",
        display_name="Auth Service",
        metadata={"environment": "PRODUCTION"},
        scope=ScopeType.SYSTEM,
    )

    # 2. Register edges: api -> auth -> db
    service.register_edge("svc_api", RelationshipType.CALLS, "svc_auth", provenance={"source": "trace"})
    service.register_edge("svc_auth", RelationshipType.READS_FROM, "svc_db", provenance={"source": "trace"})

    # Prompt #155: What depends on svc_db? -> svc_auth
    dependents = service.query_dependents("svc_db")
    assert "svc_auth" in dependents

    # Prompt #156: What does svc_api depend on? -> svc_auth
    dependencies = service.query_dependencies("svc_api")
    assert "svc_auth" in dependencies

    # Prompt #158: Record health degradation on svc_auth
    service.record_node_health(
        node_id="svc_auth",
        evidences=[HealthEvidence(metric_name="error_rate", observed_value=0.20, source="prometheus")],
    )
    unhealthy = service.query_unhealthy_resources()
    assert len(unhealthy) == 1
    assert unhealthy[0]["node_id"] == "svc_auth"
    assert unhealthy[0]["status"] == "UNHEALTHY"

    # Prompt #160: What's running in production?
    prod_nodes = service.query_production_resources()
    assert len(prod_nodes) >= 3


def test_service_context_retrieval_and_summary(service: EnvironmentService):
    """Prompts #163-#165, #175-#180: Context retrieval budgeting and summary generation."""
    service.register_node(
        node_id="svc_payments",
        node_type=NodeType.SERVICE,
        canonical_id="svc:payments",
        display_name="Payment Processing Microservice",
    )

    # Selective context retrieval by query
    ctx = service.get_environment_context(task_query="payment processing checkout")
    assert ctx["context_budget_applied"] is True
    assert len(ctx["nodes"]) > 0
    assert ctx["nodes"][0]["node_id"] == "svc_payments"

    # Summary generation
    summary = service.generate_environment_summary()
    assert summary["scope"] == "SYSTEM"
    assert "metrics" in summary
    assert summary["freshness"] == "FRESH"


def test_fastapi_environment_endpoints(client: TestClient):
    """Verify REST API routes in router.py."""
    # 1. GET /api/v1/environment/twin
    res = client.get("/api/v1/environment/twin")
    assert res.status_code == 200
    data = res.json()
    assert "twin_id" in data
    assert data["scope"] == "SYSTEM"

    # 2. POST /api/v1/environment/nodes
    node_payload = {
        "node_id": "api_test_node",
        "node_type": "SERVICE",
        "canonical_id": "svc:api_test",
        "display_name": "API Test Node",
        "metadata": {"version": "1.0"},
        "scope": "SYSTEM",
    }
    res_node = client.post("/api/v1/environment/nodes", json=node_payload)
    assert res_node.status_code == 200
    assert res_node.json()["status"] == "success"

    # 3. Secret rejection in API route
    bad_node_payload = {
        "node_id": "api_bad_node",
        "node_type": "SECRET_REFERENCE",
        "canonical_id": "sec:bad",
        "display_name": "Bad Secret Node",
        "metadata": {"secret_value": "unredacted_password"},
    }
    res_bad = client.post("/api/v1/environment/nodes", json=bad_node_payload)
    assert res_bad.status_code == 400

    # 4. GET /api/v1/environment/summary
    res_sum = client.get("/api/v1/environment/summary")
    assert res_sum.status_code == 200
    assert "metrics" in res_sum.json()

    # 5. POST /api/v1/environment/what-if
    sim_payload = {
        "target_node_id": "api_test_node",
        "event": "service_outage",
    }
    res_sim = client.post("/api/v1/environment/what-if", json=sim_payload)
    assert res_sim.status_code == 200
    assert res_sim.json()["simulation"]["is_hypothetical"] is True

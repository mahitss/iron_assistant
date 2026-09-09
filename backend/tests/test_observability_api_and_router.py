"""Tests for Observability REST API endpoints and router security (Task 38)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.observability.service import observability_service


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_metrics_endpoint(client: AsyncClient):
    """GET /api/v1/observability/metrics returns Prometheus formatted exposition."""
    observability_service.metrics.inc_counter("test_api_metric_total", 5.0)
    response = await client.get("/api/v1/observability/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "test_api_metric_total 5.0" in response.text


@pytest.mark.asyncio
async def test_get_health_score_endpoint(client: AsyncClient):
    """GET /api/v1/observability/health-score returns deterministic scoring summary."""
    response = await client.get("/api/v1/observability/health-score")
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "availability_percent" in data
    assert "overall_status" in data
    assert data["score"] > 0.0


@pytest.mark.asyncio
async def test_trace_retrieval_and_user_isolation(client: AsyncClient):
    """GET /api/v1/observability/traces/{id} respects user isolation header."""
    trace = observability_service.tracer.start_trace(
        root_operation="secret_financial_audit",
        user_id="user_alice",
    )

    # 1. Alice requests her own trace -> 200 OK
    res_alice = await client.get(
        f"/api/v1/observability/traces/{trace.trace_id}",
        headers={"x-user-id": "user_alice"},
    )
    assert res_alice.status_code == 200
    assert res_alice.json()["trace_id"] == trace.trace_id

    # 2. Bob requests Alice's trace -> 403 Forbidden
    res_bob = await client.get(
        f"/api/v1/observability/traces/{trace.trace_id}",
        headers={"x-user-id": "user_bob"},
    )
    assert res_bob.status_code == 403

    # 3. Nonexistent trace -> 404 Not Found
    res_missing = await client.get("/api/v1/observability/traces/trc_nonexistent")
    assert res_missing.status_code == 404


@pytest.mark.asyncio
async def test_dependencies_and_dashboard_endpoints(client: AsyncClient):
    """GET /dependencies and GET /dashboard return dynamic topology and aggregations."""
    res_deps = await client.get("/api/v1/observability/dependencies")
    assert res_deps.status_code == 200
    assert "nodes" in res_deps.json()
    assert "edges" in res_deps.json()

    res_dash = await client.get("/api/v1/observability/dashboard")
    assert res_dash.status_code == 200
    data = res_dash.json()
    assert "health" in data
    assert "service_map" in data
    assert "incidents" in data
    assert "recent_traces" in data


@pytest.mark.asyncio
async def test_incident_lifecycle_and_evidence_resolution(client: AsyncClient):
    """Incident report, acknowledgment, and resolution lifecycle via API."""
    inc = observability_service.incidents.report_failure(
        component="redis",
        title="Redis Buffer Saturation",
        evidence={"memory_used_mb": 512, "peak": 1024},
    )

    # 1. Acknowledge incident
    res_ack = await client.post(
        f"/api/v1/observability/incidents/{inc.id}/acknowledge",
        json={"acknowledged_by": "oncall_engineer"},
    )
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "ACKNOWLEDGED"

    # 2. Resolve incident without evidence -> 400 Bad Request
    res_fail = await client.post(
        f"/api/v1/observability/incidents/{inc.id}/resolve",
        json={"recovery_evidence": ""},
    )
    assert res_fail.status_code == 400

    # 3. Resolve incident with evidence -> 200 OK
    res_resolve = await client.post(
        f"/api/v1/observability/incidents/{inc.id}/resolve",
        json={"recovery_evidence": "Redis buffer flushed and maxmemory raised to 2048MB. Memory usage dropped to 15%."},
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"

"""Tests for resilience FastAPI REST API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.resilience.manager import resilience_manager
from app.resilience.schemas import CircuitBreakerConfig, CircuitState


@pytest.fixture
def test_app():
    return create_app()


@pytest.mark.asyncio
async def test_api_resilience_health(test_app):
    """Verifies GET /api/v1/resilience/health returns liveness, readiness, and dependencies."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/resilience/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "liveness" in data
        assert "readiness" in data
        assert "read_only_mode" in data
        assert isinstance(data["dependencies"], list)


@pytest.mark.asyncio
async def test_api_resilience_dashboard(test_app):
    """Verifies GET /api/v1/resilience/dashboard returns aggregated metrics."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/resilience/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "retry_success_rate" in data
        assert "recovery_success_rate" in data
        assert "circuits" in data
        assert "dependencies" in data


@pytest.mark.asyncio
async def test_api_circuit_breaker_management(test_app):
    """Verifies listing and manually resetting circuit breakers."""
    # Create and trip a breaker
    cb = resilience_manager.circuit_registry.get_or_create(
        "tool:flaky_scraper",
        CircuitBreakerConfig(failure_threshold=1),
    )
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List circuits
        list_resp = await client.get("/api/v1/resilience/circuits")
        assert list_resp.status_code == 200
        circuits = list_resp.json()
        assert any(c["circuit_id"] == "tool:flaky_scraper" for c in circuits)

        # Reset breaker
        reset_resp = await client.post("/api/v1/resilience/circuits/tool:flaky_scraper/reset")
        assert reset_resp.status_code == 200
        assert reset_resp.json()["state"] == "CLOSED"
        assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_api_quarantine_and_degradation_controls(test_app):
    """Verifies listing/releasing quarantine and toggling read-only degradation."""
    task_id = "task_quarantine_api_test"
    await resilience_manager.quarantine_mgr.quarantine_task(task_id, reason="Poison crash")

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List quarantine
        q_resp = await client.get("/api/v1/resilience/quarantine")
        assert q_resp.status_code == 200
        items = q_resp.json()
        assert any(item["task_id"] == task_id for item in items)

        # Release task from quarantine
        rel_resp = await client.post(f"/api/v1/resilience/quarantine/{task_id}/release?released_by=tester")
        assert rel_resp.status_code == 200
        assert rel_resp.json()["released"] is True

        # Toggle read-only mode
        deg_resp = await client.post("/api/v1/resilience/degradation/read-only?enabled=true")
        assert deg_resp.status_code == 200
        assert deg_resp.json()["read_only_mode"] is True
        assert resilience_manager.degradation_mgr.is_read_only_mode is True

        # Toggle back to normal
        deg_resp2 = await client.post("/api/v1/resilience/degradation/read-only?enabled=false")
        assert deg_resp2.status_code == 200
        assert deg_resp2.json()["read_only_mode"] is False
        assert resilience_manager.degradation_mgr.is_read_only_mode is False

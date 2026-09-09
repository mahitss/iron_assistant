"""Tests for State Fabric REST API endpoints and admin operations (Task 39)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.state.fabric import state_fabric
from app.state.quarantine import state_quarantine
from app.state.schemas import StateDomain


@pytest.fixture(autouse=True)
def clean_state():
    state_fabric.clear()
    state_quarantine.clear()
    yield
    state_fabric.clear()
    state_quarantine.clear()


@pytest.mark.asyncio
async def test_state_health_api():
    """GET /api/v1/state/health returns health and record counts."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/state/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("HEALTHY", "DEGRADED")
        assert "active_records_count" in data
        assert "quarantined_count" in data


@pytest.mark.asyncio
async def test_state_records_api():
    """GET /api/v1/state/records/{domain}/{resource_type}/{resource_id}."""
    await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="api_task_1",
        data={"title": "Test via API"},
        calling_service="task_engine",
    )

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Existing record
        res = await client.get("/api/v1/state/records/tasks/task/api_task_1")
        assert res.status_code == 200
        data = res.json()
        assert data["resource_id"] == "api_task_1"
        assert data["version"] == 1

        # Non-existent record
        res_404 = await client.get("/api/v1/state/records/tasks/task/non_existent")
        assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_state_reconcile_api():
    """POST /api/v1/state/reconcile triggers reconciliation."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/state/reconcile?mode=CHECK")
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "CHECK"
        assert "duration_ms" in data


@pytest.mark.asyncio
async def test_state_quarantine_api():
    """Quarantine list and release API endpoints."""
    state_quarantine.quarantine("task", "bad_task_api", "Corrupt payload")

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. List active
        res = await client.get("/api/v1/state/quarantine")
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 1
        assert items[0]["resource_id"] == "bad_task_api"

        # 2. Release
        rel = await client.post("/api/v1/state/quarantine/bad_task_api/release?operator=admin")
        assert rel.status_code == 200
        assert rel.json()["status"] == "RELEASED"

        # 3. List active should now be empty
        res_after = await client.get("/api/v1/state/quarantine")
        assert len(res_after.json()) == 0

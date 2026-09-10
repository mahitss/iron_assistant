"""Integration tests for Swarm Reasoning Service and FastAPI REST Endpoints (Task 64)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_swarm_service_health_endpoint():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/swarm/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["registered_agents_count"] >= 10
        assert data["healthy_agents_count"] >= 10


@pytest.mark.asyncio
async def test_swarm_service_create_and_query_session():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_payload = {
            "goal": "Evaluate zero-downtime blue-green deploy for payment microservice",
            "context": {"traffic_qps": 20000, "db_engine": "aurora_postgres"},
            "topology": "STAR",
            "risk_level": "HIGH",
            "priority": "HIGH",
        }
        res = await client.post("/api/v1/swarm/", json=create_payload)
        assert res.status_code == 200
        session_data = res.json()

        swarm_id = session_data["swarm_id"]
        assert swarm_id.startswith("swm_")
        assert session_data["status"] in ["SYNTHESIZED", "CONCLUDED", "IN_PROGRESS", "COMPLETED"]
        assert len(session_data["agents"]) >= 4

        # Query session by ID
        get_res = await client.get(f"/api/v1/swarm/{swarm_id}")
        assert get_res.status_code == 200
        assert get_res.json()["swarm_id"] == swarm_id

        # Query sub-resources
        agents_res = await client.get(f"/api/v1/swarm/{swarm_id}/agents")
        assert agents_res.status_code == 200
        assert len(agents_res.json()) >= 4

        tasks_res = await client.get(f"/api/v1/swarm/{swarm_id}/tasks")
        assert tasks_res.status_code == 200
        assert len(tasks_res.json()) >= 4

        results_res = await client.get(f"/api/v1/swarm/{swarm_id}/results")
        assert results_res.status_code == 200
        assert len(results_res.json()) >= 1

        reviews_res = await client.get(f"/api/v1/swarm/{swarm_id}/reviews")
        assert reviews_res.status_code == 200

        disag_res = await client.get(f"/api/v1/swarm/{swarm_id}/disagreements")
        assert disag_res.status_code == 200

        minorities_res = await client.get(f"/api/v1/swarm/{swarm_id}/minority_reports")
        assert minorities_res.status_code == 200

        timeline_res = await client.get(f"/api/v1/swarm/{swarm_id}/timeline")
        assert timeline_res.status_code == 200


@pytest.mark.asyncio
async def test_swarm_lifecycle_pause_resume_cancel_verify():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_payload = {
            "goal": "Audit real-time metrics telemetry retention policies",
            "topology": "STAR",
            "risk_level": "MEDIUM",
        }
        res = await client.post("/api/v1/swarm/", json=create_payload)
        assert res.status_code == 200
        swarm_id = res.json()["swarm_id"]

        # Pause
        pause_res = await client.post(f"/api/v1/swarm/{swarm_id}/pause")
        assert pause_res.status_code == 200
        assert pause_res.json()["status"] == "PAUSED"

        # Resume
        resume_res = await client.post(f"/api/v1/swarm/{swarm_id}/resume")
        assert resume_res.status_code == 200
        assert resume_res.json()["status"] in ["SYNTHESIZED", "IN_PROGRESS", "RUNNING"]

        # Verify Gate
        verify_res = await client.post(
            f"/api/v1/swarm/{swarm_id}/verify",
            json={"action": "VERIFY", "notes": "Independent verification passed in staging testbed."},
        )
        assert verify_res.status_code == 200
        verif_data = verify_res.json()
        assert verif_data["verification_status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_swarm_audit_trail_endpoint():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        audit_res = await client.get("/api/v1/swarm/audit/trail?limit=20")
        assert audit_res.status_code == 200
        trail = audit_res.json()
        assert isinstance(trail, list)
        if trail:
            first = trail[0]
            assert "event_type" in first
            assert "hash" in first or "record_hash" in first

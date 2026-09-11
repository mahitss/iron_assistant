"""Integration tests for Mission Engine Service and FastAPI REST Endpoints (Task 66)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_missions_health_endpoint():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/missions/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["task"] == 66
        assert data["audit_chain_intact"] is True


@pytest.mark.asyncio
async def test_missions_create_and_query():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_payload = {
            "title": "Zero-downtime database migration",
            "objective": "Migrate database without hurting reliability",
            "authority_scope": "EXECUTE_LOW_RISK",
            "constraints": ["Zero data loss", "p99 latency under 200ms"],
            "budget_limit": 500.0,
            "tenant_id": "tenant_test_1",
        }
        res = await client.post("/api/v1/missions/?is_human_approved=true", json=create_payload)
        assert res.status_code == 201
        data = res.json()
        mission = data["mission"]
        mission_id = mission["mission_id"]
        assert mission_id.startswith("msn_")
        assert mission["status"] == "READY"
        assert data["goal"]["tenant_id"] == "tenant_test_1"

        # Query single mission
        get_res = await client.get(f"/api/v1/missions/{mission_id}?tenant_id=tenant_test_1")
        assert get_res.status_code == 200
        assert get_res.json()["mission_id"] == mission_id

        # List missions
        list_res = await client.get("/api/v1/missions/?tenant_id=tenant_test_1")
        assert list_res.status_code == 200
        assert any(m["mission_id"] == mission_id for m in list_res.json())


@pytest.mark.asyncio
async def test_missions_overview_endpoint():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/missions/overview?tenant_id=default")
        assert res.status_code == 200
        overview = res.json()
        assert "total_missions" in overview
        assert "active_missions" in overview
        assert "healthy_count" in overview


@pytest.mark.asyncio
async def test_missions_lifecycle_transitions():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create mission
        create_res = await client.post(
            "/api/v1/missions/?is_human_approved=true",
            json={
                "title": "Deploy canary release",
                "objective": "Deploy canary release without increasing latency",
                "authority_scope": "EXECUTE_LOW_RISK",
                "tenant_id": "tenant_lc",
            },
        )
        assert create_res.status_code == 201
        m_id = create_res.json()["mission"]["mission_id"]

        # Start mission
        start_res = await client.post(f"/api/v1/missions/{m_id}/start?tenant_id=tenant_lc")
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "RUNNING"

        # Pause mission
        pause_res = await client.post(
            f"/api/v1/missions/{m_id}/pause?reason=Operator+hold&tenant_id=tenant_lc"
        )
        assert pause_res.status_code == 200
        assert pause_res.json()["status"] == "PAUSED"

        # Resume mission
        resume_res = await client.post(f"/api/v1/missions/{m_id}/resume?tenant_id=tenant_lc")
        assert resume_res.status_code == 200
        assert resume_res.json()["status"] == "RUNNING"

        # Replan mission
        replan_res = await client.post(
            f"/api/v1/missions/{m_id}/replan?reason=Adaptive+replanning&tenant_id=tenant_lc"
        )
        assert replan_res.status_code == 200
        assert replan_res.json()["version"] >= 2

        # Cancel mission
        cancel_res = await client.post(
            f"/api/v1/missions/{m_id}/cancel?reason=Mission+deprioritized&tenant_id=tenant_lc"
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_missions_supervisory_cycle_endpoint():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create and start
        create_res = await client.post(
            "/api/v1/missions/?is_human_approved=true",
            json={
                "title": "Supervised mission",
                "objective": "Tune worker concurrency without hurting reliability",
                "tenant_id": "tenant_sup",
            },
        )
        m_id = create_res.json()["mission"]["mission_id"]
        await client.post(f"/api/v1/missions/{m_id}/start?tenant_id=tenant_sup")

        # Execute supervisory cycle
        cycle_payload = {
            "telemetry": {"p95_latency_ms": 120.0, "uncertainty_score": 0.2},
            "recent_actions": ["Adjusted worker concurrency to 16 threads"],
        }
        cycle_res = await client.post(
            f"/api/v1/missions/{m_id}/cycle?tenant_id=tenant_sup",
            json=cycle_payload,
        )
        assert cycle_res.status_code == 200
        cycle_data = cycle_res.json()
        assert cycle_data["cycle_status"] in ("IN_PROGRESS", "COMPLETED")


@pytest.mark.asyncio
async def test_missions_complete_endpoint():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_res = await client.post(
            "/api/v1/missions/?is_human_approved=true",
            json={
                "title": "Mission to complete",
                "objective": "Verify completed task",
                "tenant_id": "tenant_comp",
            },
        )
        m_id = create_res.json()["mission"]["mission_id"]

        complete_res = await client.post(f"/api/v1/missions/{m_id}/complete?tenant_id=tenant_comp")
        assert complete_res.status_code == 200
        postmortem = complete_res.json()
        assert postmortem["mission_id"] == m_id
        assert "duration_seconds" in postmortem


@pytest.mark.asyncio
async def test_missions_audit_endpoints():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_res = await client.post(
            "/api/v1/missions/?is_human_approved=true",
            json={
                "title": "Audited mission",
                "objective": "Verify audit log hashing",
                "tenant_id": "tenant_aud",
            },
        )
        m_id = create_res.json()["mission"]["mission_id"]

        audit_res = await client.get(f"/api/v1/missions/{m_id}/audit")
        assert audit_res.status_code == 200
        trail = audit_res.json()
        assert len(trail) >= 1
        assert "record_hash" in trail[0]

        verify_res = await client.get("/api/v1/missions/audit/verify")
        assert verify_res.status_code == 200
        assert verify_res.json()["audit_chain_intact"] is True


@pytest.mark.asyncio
async def test_missions_sub_resource_endpoints():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_res = await client.post(
            "/api/v1/missions/?is_human_approved=true",
            json={
                "title": "Sub-resource verified mission",
                "objective": "Verify all sub-resources without degrading latency",
                "authority_scope": "EXECUTE_LOW_RISK",
                "tenant_id": "tenant_sub",
            },
        )
        assert create_res.status_code == 201
        m_id = create_res.json()["mission"]["mission_id"]

        # 1. GET /missions/{id}/goals
        goals_res = await client.get(f"/api/v1/missions/{m_id}/goals?tenant_id=tenant_sub")
        assert goals_res.status_code == 200
        assert "primary_goal" in goals_res.json()

        # 2. GET /missions/{id}/tasks
        tasks_res = await client.get(f"/api/v1/missions/{m_id}/tasks?tenant_id=tenant_sub")
        assert tasks_res.status_code == 200
        assert "tasks" in tasks_res.json()

        # 3. GET /missions/{id}/progress
        prog_res = await client.get(f"/api/v1/missions/{m_id}/progress?tenant_id=tenant_sub")
        assert prog_res.status_code == 200
        assert "progress_pct" in prog_res.json()

        # 4. GET /missions/{id}/blockers
        block_res = await client.get(f"/api/v1/missions/{m_id}/blockers?tenant_id=tenant_sub")
        assert block_res.status_code == 200
        assert isinstance(block_res.json(), list)

        # 5. GET /missions/{id}/timeline
        time_res = await client.get(f"/api/v1/missions/{m_id}/timeline?tenant_id=tenant_sub")
        assert time_res.status_code == 200
        assert "audit_events" in time_res.json()

        # 6. GET /missions/{id}/decisions
        dec_res = await client.get(f"/api/v1/missions/{m_id}/decisions?tenant_id=tenant_sub")
        assert dec_res.status_code == 200
        assert isinstance(dec_res.json(), list)

        # 7. GET /missions/{id}/risks
        risk_res = await client.get(f"/api/v1/missions/{m_id}/risks?tenant_id=tenant_sub")
        assert risk_res.status_code == 200
        assert "risk_level" in risk_res.json()

        # 8. POST /missions/{id}/reassess
        reassess_res = await client.post(f"/api/v1/missions/{m_id}/reassess?tenant_id=tenant_sub")
        assert reassess_res.status_code == 200
        assert "assumptions_valid" in reassess_res.json()

        # 9. POST /missions/{id}/verify
        verify_res = await client.post(
            f"/api/v1/missions/{m_id}/verify?tenant_id=tenant_sub", json={"p95_latency_ms": 110.0}
        )
        assert verify_res.status_code == 200
        assert "verified" in verify_res.json()

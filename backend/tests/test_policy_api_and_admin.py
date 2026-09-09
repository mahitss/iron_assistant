"""Unit and integration tests for Policy REST API and Admin Security (Task 36, Specs 83, 84, 150-152)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_policy_evaluate_api_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "context": {
                "action": "read",
                "environment": "development",
            },
            "simulate": False,
        }
        res = await ac.post("/api/v1/policy/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "ALLOW"
        assert data["evaluation_id"] is not None
        assert data["risk_level"] == "R0_READ_ONLY"

        # Now query decision provenance
        eval_id = data["evaluation_id"]
        res_prov = await ac.get(f"/api/v1/policy/decision/{eval_id}")
        assert res_prov.status_code == 200
        assert res_prov.json()["evaluation_id"] == eval_id


@pytest.mark.asyncio
async def test_policy_simulate_api_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "context": {
                "action": "deploy",
                "environment": "production",
                "target": {"service": "payments"},
            }
        }
        res = await ac.post("/api/v1/policy/simulate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"]["decision"] == "REQUIRE_APPROVAL"
        assert data["decision"]["simulated"] is True
        assert len(data["trace"]) > 0


@pytest.mark.asyncio
async def test_policy_status_api_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/policy/status")
        assert res.status_code == 200
        data = res.json()
        assert data["total_policies"] >= 7
        assert data["active_policies"] >= 1
        assert "emergency_stop_active" in data
        assert "safe_mode_active" in data


@pytest.mark.asyncio
async def test_admin_policy_unauthorized_for_regular_users():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Non-admin user attempts admin list
        res = await ac.get("/api/v1/admin/policies", headers={"X-User-Role": "user"})
        assert res.status_code == 403
        assert "Administrative authorization required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_ai_agent_model_forbidden_from_admin_policies():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # AI agent/model attempts to mutate governance policy (Section 83, 84, 134, 135)
        headers = {
            "X-User-Role": "admin",
            "X-Caller-Type": "agent",  # Agent/model caller
        }
        payload = {
            "policy_id": "agent-bypass-rule",
            "name": "Bypass Rule",
            "decision": "ALLOW",
        }
        res = await ac.post("/api/v1/admin/policies", json=payload, headers=headers)
        assert res.status_code == 403
        assert "strictly prohibited" in res.json()["detail"]


@pytest.mark.asyncio
async def test_admin_policy_creation_and_freeze_controls():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        admin_headers = {
            "X-User-Role": "admin",
            "X-User-Id": "sec_lead",
        }
        # 1. Admin creates policy
        payload = {
            "policy_id": "admin-test-rule",
            "name": "Integration Test Rule",
            "priority": 300,
            "scope": "GLOBAL",
            "decision": "ALLOW",
        }
        res = await ac.post("/api/v1/admin/policies", json=payload, headers=admin_headers)
        assert res.status_code == 201
        assert res.json()["policy_id"] == "admin-test-rule"

        # 2. Admin activates change freeze
        res_freeze = await ac.post("/api/v1/admin/freeze?environment=test&active=true&reason=Audit", headers=admin_headers)
        assert res_freeze.status_code == 200
        assert res_freeze.json()["change_freeze"] is True

        # 3. Admin deactivates change freeze
        res_unfreeze = await ac.post("/api/v1/admin/freeze?environment=test&active=false", headers=admin_headers)
        assert res_unfreeze.status_code == 200
        assert res_unfreeze.json()["change_freeze"] is False

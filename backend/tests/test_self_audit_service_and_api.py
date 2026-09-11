"""Integration tests for Self-Audit Service and FastAPI REST Endpoints (Task 67)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_self_audit_health_endpoint():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/self-audit/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["task"] == 67
        assert "metacognitive_state" in data
        assert "calibration_state" in data


@pytest.mark.asyncio
async def test_self_audit_create_and_query():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create self-audit
        payload = {
            "subject": "Production reasoning trace #5512",
            "scope": "reasoning",
            "audit_type": "PERIODIC",
            "depth": "STANDARD",
            "evidence": ["Traced 50 requests through inference pipeline"],
            "tenant_id": "tenant_sa_1",
        }
        res = await client.post("/api/v1/self-audit/", json=payload)
        assert res.status_code == 201
        audit = res.json()
        audit_id = audit["audit_id"]
        assert audit_id.startswith("aud_")

        # Query by ID
        get_res = await client.get(f"/api/v1/self-audit/{audit_id}?tenant_id=tenant_sa_1")
        assert get_res.status_code == 200
        assert get_res.json()["audit_id"] == audit_id

        # Query findings
        findings_res = await client.get(f"/api/v1/self-audit/{audit_id}/findings?tenant_id=tenant_sa_1")
        assert findings_res.status_code == 200
        assert isinstance(findings_res.json(), list)

        # Query evidence
        evidence_res = await client.get(f"/api/v1/self-audit/{audit_id}/evidence?tenant_id=tenant_sa_1")
        assert evidence_res.status_code == 200
        assert isinstance(evidence_res.json(), list)

        # List audits
        list_res = await client.get("/api/v1/self-audit/?tenant_id=tenant_sa_1")
        assert list_res.status_code == 200
        assert any(a["audit_id"] == audit_id for a in list_res.json())


@pytest.mark.asyncio
async def test_self_audit_overview_and_telemetry_endpoints():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Overview
        ov_res = await client.get("/api/v1/self-audit/overview?tenant_id=default")
        assert ov_res.status_code == 200
        ov = ov_res.json()
        assert "metacognitive_state" in ov
        assert "calibration_state" in ov
        assert "total_audits" in ov

        # History
        hist_res = await client.get("/api/v1/self-audit/history?tenant_id=default")
        assert hist_res.status_code == 200
        assert isinstance(hist_res.json(), list)

        # Drift
        drift_res = await client.get("/api/v1/self-audit/drift?tenant_id=default")
        assert drift_res.status_code == 200
        assert isinstance(drift_res.json(), list)

        # Calibration
        calib_res = await client.get("/api/v1/self-audit/calibration?tenant_id=default")
        assert calib_res.status_code == 200
        assert "mean_brier_score" in calib_res.json()

        # Errors
        err_res = await client.get("/api/v1/self-audit/errors?tenant_id=default")
        assert err_res.status_code == 200
        assert "error_clusters" in err_res.json()
        assert "error_heatmap" in err_res.json()


@pytest.mark.asyncio
async def test_self_audit_cycle_and_reassess_endpoints():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cycle_payload = {
            "subject": "Canary cluster verification",
            "observed_actions": [
                "Route 10% traffic to canary",
                "Verify error rates are < 0.1%",
                "Observed 0 errors across 5000 requests",
            ],
            "reported_confidence": 0.95,
            "depth": "STANDARD",
            "is_adversarial": True,
            "tenant_id": "tenant_cycle",
        }
        res = await client.post("/api/v1/self-audit/cycle", json=cycle_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["audit_id"].startswith("aud_")
        assert "checks_performed" in data
        assert len(data["checks_performed"]) >= 8

        # Reassess endpoint
        audit_id = data["audit_id"]
        reassess_res = await client.post(f"/api/v1/self-audit/{audit_id}/reassess?tenant_id=tenant_cycle")
        assert reassess_res.status_code == 200
        assert reassess_res.json()["version"] >= 2


@pytest.mark.asyncio
async def test_self_audit_beliefs_endpoints():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register belief
        belief_payload = {
            "subject": "service_mesh",
            "claim": "Envoy proxy handles mTLS handshake in < 2ms",
            "basis": "Service mesh benchmark logs",
            "confidence": 0.88,
            "tenant_id": "tenant_belief",
        }
        create_res = await client.post("/api/v1/self-audit/beliefs", json=belief_payload)
        assert create_res.status_code == 201
        belief = create_res.json()
        belief_id = belief["belief_id"]
        assert belief_id.startswith("blf_")

        # List beliefs
        list_res = await client.get("/api/v1/self-audit/beliefs?tenant_id=tenant_belief")
        assert list_res.status_code == 200
        assert any(b["belief_id"] == belief_id for b in list_res.json())

        # Revise belief
        revise_payload = {
            "new_claim": "Envoy proxy mTLS handshake takes 4ms under high CPU load",
            "new_evidence": ["Production telemetry under 90% CPU"],
            "reason": "Observed elevated latency during peak hours",
            "new_confidence": 0.94,
        }
        rev_res = await client.post(
            f"/api/v1/self-audit/beliefs/{belief_id}/revise?tenant_id=tenant_belief", json=revise_payload
        )
        assert rev_res.status_code == 200
        assert rev_res.json()["claim"] == "Envoy proxy mTLS handshake takes 4ms under high CPU load"

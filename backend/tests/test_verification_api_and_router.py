"""Tests for Verification REST API endpoints (Task 42)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_verification_api_full_lifecycle(client: AsyncClient):
    # 1. Register a Claim
    claim_payload = {
        "statement": "Production API service is healthy and online",
        "claim_type": "STATE",
        "subject": "api_service",
        "predicate": "status",
        "object_ref": "healthy",
        "source": "monitoring_agent",
        "scope": {"project_id": "proj-main"},
    }
    res_claim = await client.post(
        "/api/v1/verification/claims",
        json=claim_payload,
        headers={"x-user-id": "dev_lead"},
    )
    assert res_claim.status_code == 201
    claim_data = res_claim.json()
    assert "claim_id" in claim_data
    assert claim_data["truth_status"] == "UNVERIFIED"
    claim_id = claim_data["claim_id"]

    # 2. Get Claim by ID
    res_get = await client.get(f"/api/v1/verification/claims/{claim_id}")
    assert res_get.status_code == 200
    assert res_get.json()["claim_id"] == claim_id

    # 3. List Claims
    res_list = await client.get("/api/v1/verification/claims?subject=api_service")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 4. Register Evidence
    evidence_payload = {
        "source_type": "HEALTH_CHECK",
        "source_reference": "https://api.internal/health",
        "observation": {"health": "healthy", "status_code": 200, "token": "ghp_secretkey123"},
        "claim_id": claim_id,
        "scope": {"project_id": "proj-main"},
    }
    res_ev = await client.post(
        "/api/v1/verification/evidence",
        json=evidence_payload,
        headers={"x-user-id": "dev_lead"},
    )
    assert res_ev.status_code == 201
    ev_data = res_ev.json()
    assert "evidence_id" in ev_data
    evidence_id = ev_data["evidence_id"]
    # Verify token redaction in response
    assert "[REDACTED" in str(ev_data["observation"])

    # 5. Get Evidence
    res_get_ev = await client.get(f"/api/v1/verification/evidence/{evidence_id}")
    assert res_get_ev.status_code == 200

    # 6. Verify Claim via Contract
    verify_payload = {
        "target": "api_service",
        "expected_state": {"health": "healthy", "status_code": 200},
        "strategy": "HEALTH_CHECK",
        "observed_data": {"health": "healthy", "status_code": 200},
    }
    res_verify = await client.post(
        f"/api/v1/verification/claims/{claim_id}/verify",
        json=verify_payload,
    )
    assert res_verify.status_code == 200
    v_res = res_verify.json()
    assert v_res["status"] == "PASS"
    assert v_res["confidence"] == "HIGH"

    # 7. Triangulate Claim
    res_tri = await client.get(f"/api/v1/verification/claims/{claim_id}/triangulate")
    assert res_tri.status_code == 200
    tri_data = res_tri.json()
    assert tri_data["claim_id"] == claim_id

    # 8. Get Confidence Report
    res_conf = await client.get(f"/api/v1/verification/claims/{claim_id}/confidence")
    assert res_conf.status_code == 200
    conf_data = res_conf.json()
    assert conf_data["level"] in ["HIGH", "MEDIUM"]
    assert "factors" in conf_data

    # 9. Contradictions Check
    res_contra = await client.get(f"/api/v1/verification/claims/{claim_id}/contradictions")
    assert res_contra.status_code == 200
    assert isinstance(res_contra.json(), list)

    # 10. Self-Correction Submission
    corr_payload = {
        "original_claim_id": claim_id,
        "corrected_statement": "Production API service is operating at 99.9% uptime",
        "supporting_evidence_ids": [evidence_id],
        "reason": "Uptime metrics updated by telemetry probe.",
    }
    res_corr = await client.post("/api/v1/verification/corrections", json=corr_payload)
    assert res_corr.status_code == 201
    corr_data = res_corr.json()
    assert corr_data["status"] == "APPLIED"
    assert "I was wrong about" in corr_data["user_admission"]

    # 11. Invariant Evaluation
    res_invariants = await client.post(
        "/api/v1/verification/invariants/evaluate",
        json={
            "task_status": "COMPLETED",
            "has_active_lease": True,
            "completion_evidence": ["ev-123"],
        },
    )
    assert res_invariants.status_code == 200
    violations = res_invariants.json()
    assert len(violations) >= 1
    assert violations[0]["rule_id"] == "TASK-001"

    # 12. Verification Engine Stats
    res_stats = await client.get("/api/v1/verification/stats")
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert stats_data["total_claims"] >= 1
    assert stats_data["total_evidence"] >= 1
    assert stats_data["total_corrections"] >= 1

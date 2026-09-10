"""Integration tests for Strategic Planning REST API router (Task 58)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def plan_payload():
    return {
        "name": "API Automated Strategic Migration",
        "purpose": "Test complete REST API workflow",
        "current_state": {
            "summary": "Legacy monolithic application",
            "verified_aspects": ["database_operational"],
            "active_telemetry": {"latency_ms": 110.0},
            "certainty": "VERIFIED",
            "is_stale": False,
        },
        "desired_state": {
            "summary": "Target microservices architecture",
            "completion_invariants": ["Target microservices active"],
            "verification_criteria": ["All smoke tests passing"],
            "target_metrics": {"latency_ms": 40.0},
        },
        "author": "integration_tester",
    }


def test_planning_api_full_crud_and_lifecycle(plan_payload):
    # 1. POST /api/v1/planning/plans
    create_resp = client.post("/api/v1/planning/plans", json=plan_payload)
    assert create_resp.status_code == 200, create_resp.text
    plan_data = create_resp.json()
    plan_id = plan_data["plan_id"]
    assert plan_data["name"] == "API Automated Strategic Migration"
    assert len(plan_data["phases"]) == 3
    assert len(plan_data["tasks"]) == 3

    # 2. GET /api/v1/planning/plans
    list_resp = client.get("/api/v1/planning/plans")
    assert list_resp.status_code == 200
    plans = list_resp.json()
    assert any(p["plan_id"] == plan_id for p in plans)

    # 3. GET /api/v1/planning/plans/{id}
    get_resp = client.get(f"/api/v1/planning/plans/{plan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["plan_id"] == plan_id

    # 4. POST /api/v1/planning/plans/{id}/validate
    val_resp = client.post(f"/api/v1/planning/plans/{plan_id}/validate", json={})
    assert val_resp.status_code == 200
    assert val_resp.json()["is_valid"] is True

    # 5. POST /api/v1/planning/plans/{id}/analyze
    ana_resp = client.post(f"/api/v1/planning/plans/{plan_id}/analyze")
    assert ana_resp.status_code == 200
    ana_data = ana_resp.json()
    assert "critical_path" in ana_data
    assert "total_resource_requirements" in ana_data

    # 6. POST /api/v1/planning/plans/{id}/start
    start_resp = client.post(f"/api/v1/planning/plans/{plan_id}/start", json={"actor": "tester"})
    assert start_resp.status_code == 200
    assert start_resp.json()["success"] is True

    # 7. POST /api/v1/planning/plans/{id}/pause
    pause_resp = client.post(f"/api/v1/planning/plans/{plan_id}/pause", json={"actor": "tester", "reason": "Testing"})
    assert pause_resp.status_code == 200
    assert pause_resp.json()["success"] is True

    # 8. POST /api/v1/planning/plans/{id}/resume
    res_resp = client.post(f"/api/v1/planning/plans/{plan_id}/resume", json={"actor": "tester"})
    assert res_resp.status_code == 200
    assert res_resp.json()["success"] is True

    # 9. GET /api/v1/planning/plans/{id}/progress
    prog_resp = client.get(f"/api/v1/planning/plans/{plan_id}/progress")
    assert prog_resp.status_code == 200
    assert "composite_progress_pct" in prog_resp.json()

    # 10. GET /api/v1/planning/plans/{id}/timeline
    time_resp = client.get(f"/api/v1/planning/plans/{plan_id}/timeline")
    assert time_resp.status_code == 200
    assert "waves" in time_resp.json()

    # 11. GET /api/v1/planning/plans/{id}/dependencies
    dep_resp = client.get(f"/api/v1/planning/plans/{plan_id}/dependencies")
    assert dep_resp.status_code == 200
    assert dep_resp.json()["has_cycle"] is False

    # 12. GET /api/v1/planning/plans/{id}/risks
    risk_resp = client.get(f"/api/v1/planning/plans/{plan_id}/risks")
    assert risk_resp.status_code == 200
    assert "risks" in risk_resp.json()

    # 13. POST /api/v1/planning/plans/{id}/replan
    replan_resp = client.post(
        f"/api/v1/planning/plans/{plan_id}/replan",
        json={"actor": "operator", "reason": "Refined architecture milestones"},
    )
    assert replan_resp.status_code == 200
    assert replan_resp.json()["version"] == 2

    # 14. GET /api/v1/planning/plans/{id}/proposal (Execution Handoff Boundary)
    prop_resp = client.get(f"/api/v1/planning/plans/{plan_id}/proposal")
    assert prop_resp.status_code == 200
    assert prop_resp.json()["execution_boundary_enforced"] is True

    # 15. POST /api/v1/planning/plans/{id}/outcomes
    out_resp = client.post(
        f"/api/v1/planning/plans/{plan_id}/outcomes",
        json={"success": True, "actual_duration_hours": 5.5, "actual_cost": 450.0},
    )
    assert out_resp.status_code == 200
    assert out_resp.json()["success"] is True

    # 16. GET /api/v1/planning/plans/{id}/outcomes
    list_out_resp = client.get(f"/api/v1/planning/plans/{plan_id}/outcomes")
    assert list_out_resp.status_code == 200
    assert len(list_out_resp.json()) == 1

    # 17. GET /api/v1/planning/plans/{id}/audit
    audit_resp = client.get(f"/api/v1/planning/plans/{plan_id}/audit")
    assert audit_resp.status_code == 200
    assert len(audit_resp.json()) >= 4

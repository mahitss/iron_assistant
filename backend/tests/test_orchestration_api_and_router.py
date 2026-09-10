"""Integration tests for Resource & Capability Orchestration REST API router (Task 59)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def orchestration_payload():
    return {
        "name": "Integration Test Orchestration Plan",
        "tasks": [
            {
                "id": "t_calc_api",
                "title": "Calculate resource requirements",
                "required_capabilities": ["calculate"],
                "environment": "development",
            },
            {
                "id": "t_sys_api",
                "title": "Check system info status",
                "required_capabilities": ["system_info"],
                "environment": "development",
            },
        ],
        "dependencies": {
            "t_sys_api": ["t_calc_api"],
        },
        "environment": "development",
        "actor": "api_tester",
    }


def test_analyze_orchestration_api():
    """Test POST /api/v1/orchestration/analyze gap analysis."""
    resp = client.post(
        "/api/v1/orchestration/analyze",
        json={
            "tasks": [
                {"id": "task_1", "title": "Run tests", "required_capabilities": ["run_tests"]},
            ],
            "environment": "development",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "feasibility" in data
    assert data["total_tasks"] == 1
    assert data["feasibility"] in ("FEASIBLE", "PARTIALLY_FEASIBLE")


def test_catalog_capabilities_and_resources_api():
    """Test catalog listing endpoints."""
    # Capabilities catalog
    caps_resp = client.get("/api/v1/orchestration/catalog/capabilities")
    assert caps_resp.status_code == 200
    caps = caps_resp.json()
    assert isinstance(caps, list)
    assert len(caps) >= 5

    # Resources catalog
    res_resp = client.get("/api/v1/orchestration/catalog/resources")
    assert res_resp.status_code == 200
    resources = res_resp.json()
    assert isinstance(resources, list)
    assert len(resources) >= 3


def test_resource_reservation_lifecycle_api():
    """Test POST /api/v1/orchestration/resources/reserve and release."""
    exp_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    reserve_resp = client.post(
        "/api/v1/orchestration/resources/reserve",
        json={
            "resource_id": "res_dev_local_compute",
            "owner": "APITester",
            "purpose": "Load test reserve",
            "amount": 2.0,
            "expires_at": exp_iso,
        },
    )
    assert reserve_resp.status_code == 200, reserve_resp.text
    rsv_data = reserve_resp.json()
    rsv_id = rsv_data["reservation_id"]
    assert rsv_data["is_active"] is True

    # Release reservation
    release_resp = client.post(
        "/api/v1/orchestration/resources/release",
        json={"reservation_id": rsv_id},
    )
    assert release_resp.status_code == 200
    assert release_resp.json()["status"] == "RELEASED"


def test_orchestration_plan_crud_and_topology_api(orchestration_payload):
    """Test full creation, inspection, assignments, topology, revalidation, and failover."""
    # 1. POST /api/v1/orchestration
    create_resp = client.post("/api/v1/orchestration", json=orchestration_payload)
    assert create_resp.status_code == 200, create_resp.text
    plan_data = create_resp.json()
    orch_id = plan_data["orchestration_id"]
    assert plan_data["name"] == "Integration Test Orchestration Plan"
    assert len(plan_data["assignments"]) == 2
    assert len(plan_data["execution_waves"]) == 2

    # 2. GET /api/v1/orchestration/{id}
    get_resp = client.get(f"/api/v1/orchestration/{orch_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["orchestration_id"] == orch_id

    # 3. GET /api/v1/orchestration/{id}/assignments
    asgn_resp = client.get(f"/api/v1/orchestration/{orch_id}/assignments")
    assert asgn_resp.status_code == 200
    asgns = asgn_resp.json()
    assert len(asgns) == 2

    # 4. GET /api/v1/orchestration/{id}/topology
    topo_resp = client.get(f"/api/v1/orchestration/{orch_id}/topology")
    assert topo_resp.status_code == 200
    topo_data = topo_resp.json()
    assert len(topo_data["execution_waves"]) == 2

    # 5. POST /api/v1/orchestration/{id}/revalidate
    reval_resp = client.post(
        f"/api/v1/orchestration/{orch_id}/revalidate",
        json={"environment": "development", "active_permissions": []},
    )
    assert reval_resp.status_code == 200
    assert reval_resp.json()["status"] == "VALIDATED"

    # 6. GET /api/v1/orchestration/{id}/health
    health_resp = client.get(f"/api/v1/orchestration/{orch_id}/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] in ("READY", "VALIDATED")

    # 7. GET /api/v1/orchestration/explain/{task_id}
    explain_resp = client.get("/api/v1/orchestration/explain/t_calc_api")
    assert explain_resp.status_code == 200
    assert explain_resp.json()["found"] is True

    # 8. GET /api/v1/orchestration/audit/trail
    audit_resp = client.get(f"/api/v1/orchestration/audit/trail?orchestration_id={orch_id}")
    assert audit_resp.status_code == 200
    audit_events = audit_resp.json()
    assert len(audit_events) >= 1

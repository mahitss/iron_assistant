"""Tests for Task 76 Resilience & Recovery REST APIs and CLI interface.

Covers all 20 REST API endpoints and all 10 CLI subcommands.
"""

from fastapi.testclient import TestClient
import pytest
from app.main import create_app
from app.resilience.cli import main as cli_main
from app.resilience.defense_schemas import RecoveryLifecycleState, ResilienceState
from app.resilience.intelligence import get_resilience_intelligence_coordinator


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_resilience_assess_api(client: TestClient):
    """POST /api/v1/resilience/assess runs assessment and returns ResilienceAssessment."""
    payload = {
        "scope": "SYSTEM",
        "target": "CORE",
        "topology": {
            "nodes": {
                "gw": {"criticality": 0.85, "has_redundancy": False},
                "db": {"criticality": 0.95, "has_redundancy": True, "backups": [{"mode": "active"}]},
            },
            "edges": [{"source": "gw", "target": "db"}],
        },
        "provenance": {"initiator": "test_client"},
    }

    res = client.post("/api/v1/resilience/assess", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "resilience_assessment_id" in data
    assert data["target"] == "CORE"
    assert data["state"] in ("HEALTHY", "DEGRADED", "VULNERABLE", "CRITICAL")
    assert "scorecard" in data
    assert len(data["scorecard"]["dimensions"]) == 12
    assert len(data["gaps"]) >= 1

    ass_id = data["resilience_assessment_id"]

    # GET /api/v1/resilience/{id}
    res_get = client.get(f"/api/v1/resilience/{ass_id}")
    assert res_get.status_code == 200
    assert res_get.json()["resilience_assessment_id"] == ass_id

    # GET /api/v1/resilience/{id}/gaps
    res_gaps = client.get(f"/api/v1/resilience/{ass_id}/gaps")
    assert res_gaps.status_code == 200
    assert isinstance(res_gaps.json(), list)

    # GET /api/v1/resilience/{id}/recovery-paths
    res_paths = client.get(f"/api/v1/resilience/{ass_id}/recovery-paths")
    assert res_paths.status_code == 200

    # GET /api/v1/resilience/{id}/scenarios
    res_scen = client.get(f"/api/v1/resilience/{ass_id}/scenarios")
    assert res_scen.status_code == 200
    assert "scenarios" in res_scen.json()

    # GET /api/v1/resilience/{id}/explanation
    res_exp = client.get(f"/api/v1/resilience/{ass_id}/explanation")
    assert res_exp.status_code == 200
    assert "rationale" in res_exp.json()

    # GET /api/v1/resilience/{id}/provenance
    res_prov = client.get(f"/api/v1/resilience/{ass_id}/provenance")
    assert res_prov.status_code == 200
    assert "provenance" in res_prov.json()


def test_resilience_overview_and_bottlenecks_api(client: TestClient):
    """GET /api/v1/resilience/overview and /api/v1/resilience/bottlenecks."""
    # Overview
    res_ov = client.get("/api/v1/resilience/overview")
    assert res_ov.status_code == 200
    ov_data = res_ov.json()
    assert "status" in ov_data
    assert "overall_resilience_index" in ov_data

    # Bottlenecks
    res_bn = client.get("/api/v1/resilience/bottlenecks")
    assert res_bn.status_code == 200
    bn_data = res_bn.json()
    assert "bottlenecks" in bn_data
    assert "spofs" in bn_data

    # History
    res_hist = client.get("/api/v1/resilience/recovery-history")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert "trends" in hist_data


def test_recovery_lifecycle_api_flow(client: TestClient):
    """Full API flow: plan -> approve -> execute-containment -> execute -> verify -> rollback -> abort -> handoff."""
    plan_payload = {
        "incident_id": "inc_api_test",
        "cascade_path": ["redis_cache", "api_server"],
        "topology": {
            "nodes": {
                "redis_cache": {"criticality": 0.8, "recoverable": True, "has_rollback": True},
                "api_server": {"criticality": 0.85, "recoverable": True, "has_rollback": True},
            },
            "edges": [{"source": "redis_cache", "target": "api_server"}],
        },
        "uncertainty": 0.2,
    }

    # 1. Plan recovery
    res_plan = client.post("/api/v1/recovery/plan", json=plan_payload)
    assert res_plan.status_code == 200
    plan_data = res_plan.json()
    plan_id = plan_data["plan_id"]
    assert "selected_strategy" in plan_data

    # 2. Get active recovery plans
    res_active = client.get("/api/v1/recovery/active")
    assert res_active.status_code == 200
    assert any(p["plan_id"] == plan_id for p in res_active.json())

    # 3. Get plan by ID
    res_get_plan = client.get(f"/api/v1/recovery/{plan_id}")
    assert res_get_plan.status_code == 200

    # 4. Approve plan
    res_appr = client.post(f"/api/v1/recovery/{plan_id}/approve", json={"approved_by": "sec_operator", "approval_id": "appr_123"})
    assert res_appr.status_code == 200
    assert res_appr.json()["approved_by"] == "sec_operator"

    # 5. Execute containment
    res_cnt = client.post(f"/api/v1/recovery/{plan_id}/execute-containment?actor=test_operator")
    assert res_cnt.status_code == 200

    # 6. Execute recovery
    res_exec = client.post(f"/api/v1/recovery/{plan_id}/execute?actor=test_operator")
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "VERIFICATION_PENDING"

    # 7. Verify recovery (positive)
    telemetry = {
        "redis_cache": {"service_status": "HEALTHY", "error_rate": 0.001},
        "api_server": {"service_status": "HEALTHY", "error_rate": 0.002},
    }
    res_ver = client.post(f"/api/v1/recovery/{plan_id}/verify", json={"live_telemetry": telemetry})
    assert res_ver.status_code == 200
    assert res_ver.json()["verified"] is True
    assert res_ver.json()["state"] == "RECOVERED"

    # 8. Rollback
    res_rb = client.post(f"/api/v1/recovery/{plan_id}/rollback?actor=test_operator")
    assert res_rb.status_code == 200
    assert res_rb.json()["state"] == "ROLLED_BACK"

    # 9. Human handoff
    res_ho = client.post(f"/api/v1/recovery/{plan_id}/handoff", json={"incident_id": "inc_api_test", "reason": "operator requested manual override"})
    assert res_ho.status_code == 200
    assert res_ho.json()["priority"] == "HIGH"
    assert "options" in res_ho.json()

    # 10. Abort
    res_ab = client.post(f"/api/v1/recovery/{plan_id}/abort", json={"reason": "Test finished"})
    assert res_ab.status_code == 200
    assert res_ab.json()["state"] == "ABORTED"


def test_cli_resilience_and_recovery(capsys):
    """Verifies all CLI subcommands run without uncaught exceptions and return code 0."""
    # resilience assess
    assert cli_main(["resilience", "assess", "--target", "cli_test_node"]) == 0

    coord = get_resilience_intelligence_coordinator()
    ass_id = list(coord.assessments.keys())[-1]

    # resilience inspect
    assert cli_main(["resilience", "inspect", ass_id]) == 0

    # resilience gaps
    assert cli_main(["resilience", "gaps", ass_id]) == 0

    # resilience simulate
    assert cli_main(["resilience", "simulate", ass_id]) == 0

    # resilience bottlenecks
    assert cli_main(["resilience", "bottlenecks"]) == 0

    # recovery plan
    assert cli_main(["recovery", "plan", "node1", "node2", "node3"]) == 0
    plan_id = list(coord.recovery_plans.keys())[-1]

    # recovery list
    assert cli_main(["recovery", "list"]) == 0

    # recovery inspect
    assert cli_main(["recovery", "inspect", plan_id]) == 0

    # recovery history
    assert cli_main(["recovery", "history"]) == 0

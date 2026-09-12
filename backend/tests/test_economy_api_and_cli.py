"""API and CLI tests for Task 77 Autonomous Resource Economy and Cognitive Budgets."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.orchestration.cli import main as cli_main


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_api_economy_overview(client):
    """Verify GET /api/v1/orchestration/economy/overview returns summary."""
    resp = client.get("/api/v1/orchestration/economy/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "capacity_saturation_pct" in data
    assert "saturation_state" in data
    assert "active_degradation_tier" in data


def test_api_estimate_demand(client):
    """Verify POST /api/v1/orchestration/economy/demand/estimate returns calibrated demand."""
    payload = {
        "task_id": "api_task_1",
        "resource_id": "res_gpu",
        "estimated_tokens": 1500,
        "uncertainty_pct": 0.10,
    }
    resp = client.post("/api/v1/orchestration/economy/demand/estimate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_tokens"] == 1500
    assert data["lower_bound"] == 1350.0
    assert data["upper_bound"] == 1650.0


def test_api_budget_lifecycle(client):
    """Verify budget creation, check, allocate, and reset via REST."""
    # 1. Create budget
    create_payload = {
        "scope": "PROJECT",
        "scope_id": "proj_api_test",
        "limits": {"CONTEXT_TOKENS": 5000.0},
        "near_limit_threshold": 0.85,
    }
    resp = client.post("/api/v1/orchestration/budgets/create", json=create_payload)
    assert resp.status_code == 200
    assert resp.json()["scope"] == "PROJECT"

    # 2. Check budget
    check_payload = {
        "demands": {"CONTEXT_TOKENS": 2000.0},
        "scopes": [["PROJECT", "proj_api_test"]],
    }
    resp_check = client.post("/api/v1/orchestration/budgets/check", json=check_payload)
    assert resp_check.status_code == 200
    assert resp_check.json()["allowed"] is True

    # 3. Allocate budget
    alloc_payload = {
        "task_id": "api_alloc_task",
        "demands": {"CONTEXT_TOKENS": 2000.0},
        "scopes": [["PROJECT", "proj_api_test"]],
    }
    resp_alloc = client.post("/api/v1/orchestration/budgets/allocate", json=alloc_payload)
    assert resp_alloc.status_code == 200
    assert resp_alloc.json()["status"] == "ALLOCATED"

    # 4. Reset budget
    reset_payload = {"scope": "PROJECT", "scope_id": "proj_api_test"}
    resp_reset = client.post("/api/v1/orchestration/budgets/reset", json=reset_payload)
    assert resp_reset.status_code == 200
    assert resp_reset.json()["status"] == "RESET"


def test_api_preemption_and_checkpoint(client):
    """Verify task preemption, checkpointing, and resumption via REST."""
    # Request preemption
    p_req = {
        "task_id": "api_task_victim",
        "preempted_by_task_id": "api_task_hero",
        "requestor_priority": 5,
        "policy": "COOPERATIVE",
    }
    resp = client.post("/api/v1/orchestration/preempt", json=p_req)
    assert resp.status_code == 200
    assert resp.json()["state"] == "PREEMPTION_REQUESTED"

    # Checkpoint
    chk_req = {
        "task_id": "api_task_victim",
        "state_snapshot": {"step": 2},
        "saved_context_tokens": 500,
    }
    resp_chk = client.post("/api/v1/orchestration/checkpoint", json=chk_req)
    assert resp_chk.status_code == 200
    assert resp_chk.json()["state"] == "PAUSED"

    # Resume
    resp_res = client.post("/api/v1/orchestration/resume/api_task_victim")
    assert resp_res.status_code == 200
    assert resp_res.json()["status"] == "RESUMED"


def test_api_deadlocks_and_fairness(client):
    """Verify deadlock detection and fairness metrics endpoints."""
    resp_dl = client.get("/api/v1/orchestration/deadlock/detect")
    assert resp_dl.status_code == 200
    assert isinstance(resp_dl.json(), list)

    resp_f = client.get("/api/v1/orchestration/fairness/metrics")
    assert resp_f.status_code == 200
    assert "gini_coefficient" in resp_f.json()


def test_cli_execution_commands(capsys):
    """Verify CLI subcommands execute without raising errors."""
    code = cli_main(["resource", "economy"])
    assert code == 0

    code = cli_main(["resource", "demand", "cli_task_1", "--tokens", "1200"])
    assert code == 0

    code = cli_main(["budget", "status"])
    assert code == 0

    code = cli_main(["budget", "check", "--tokens", "500.0"])
    assert code == 0

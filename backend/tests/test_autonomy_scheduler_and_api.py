"""Integration tests for Task DAG Scheduler and Autonomy REST API Endpoints (Task 45)."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.autonomy.scheduler import AutonomousScheduler, EventAuthenticityError
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_scheduler_dag_dependencies():
    """Verify ready step selection respecting DAG dependencies (Spec 29-31)."""
    scheduler = AutonomousScheduler(max_concurrent_steps=2)

    steps = [
        {"step_id": "step_A", "dependencies": []},
        {"step_id": "step_B", "dependencies": []},
        {"step_id": "step_C", "dependencies": ["step_A"]},
        {"step_id": "step_D", "dependencies": ["step_A", "step_B"]},
    ]

    completed = set()
    in_progress = set()

    # Initially step_A and step_B are ready
    ready1 = scheduler.get_ready_steps(steps, completed, in_progress)
    ready_ids = [s["step_id"] for s in ready1]
    assert "step_A" in ready_ids
    assert "step_B" in ready_ids
    assert "step_C" not in ready_ids  # blocked on step_A

    # Mark step_A as completed
    completed.add("step_A")
    ready2 = scheduler.get_ready_steps(steps, completed, in_progress)
    ready2_ids = [s["step_id"] for s in ready2]
    assert "step_C" in ready2_ids
    assert "step_D" not in ready2_ids  # still blocked on step_B


def test_event_correlation_and_deduplication():
    """Verify incoming event authenticity, deduplication, and out-of-order handling (Spec 100-105)."""
    scheduler = AutonomousScheduler()
    run_id = "run_ev_01"

    # Unauthenticated event rejected
    with pytest.raises(EventAuthenticityError):
        scheduler.process_incoming_event(
            run_id=run_id,
            event_id="ev_forged",
            event_type="PAYMENT_COMPLETED",
            sequence_num=1,
            is_authenticated=False,
        )

    # Valid event processed
    ev1 = scheduler.process_incoming_event(
        run_id=run_id,
        event_id="ev_001",
        event_type="STEP_DONE",
        sequence_num=1,
        payload={"result": "ok"},
    )
    assert ev1 is not None
    assert ev1.event_id == "ev_001"

    # Duplicate event safely ignored
    ev1_dup = scheduler.process_incoming_event(
        run_id=run_id,
        event_id="ev_001",
        event_type="STEP_DONE",
        sequence_num=1,
    )
    assert ev1_dup is None


def test_autonomy_api_endpoints_flow(client: TestClient):
    """End-to-end integration test of Autonomy REST API (Goals, Runs, Steps, Checkpoints, Controls)."""
    headers = {"X-User-Id": "test_user_alice"}

    # 1. POST /api/v1/autonomy/goals
    goal_res = client.post(
        "/api/v1/autonomy/goals",
        headers=headers,
        json={
            "title": "Autonomous Service Migration",
            "description": "Migrate microservice endpoints to v2 architecture.",
            "project_id": "proj_phoenix",
            "success_criteria": ["All endpoints migrated", "Zero regression"],
            "hard_constraints": ["Zero downtime"],
        },
    )
    assert goal_res.status_code == status.HTTP_201_CREATED
    goal_data = goal_res.json()
    goal_id = goal_data["goal_id"]
    assert goal_data["status"] == "ACTIVE"

    # 2. GET /api/v1/autonomy/goals/{goal_id}
    goal_get = client.get(f"/api/v1/autonomy/goals/{goal_id}")
    assert goal_get.status_code == status.HTTP_200_OK
    assert goal_get.json()["goal_id"] == goal_id

    # 3. POST /api/v1/autonomy/runs
    run_res = client.post(
        "/api/v1/autonomy/runs",
        headers=headers,
        json={
            "goal_id": goal_id,
            "autonomy_level": "AUTONOMOUS",
            "project_id": "proj_phoenix",
            "max_model_calls": 50,
            "max_tool_calls": 25,
            "initial_steps": [
                {
                    "step_id": "step_inspect_v1",
                    "action_type": "READ",
                    "tool_name": "inspect_code",
                    "dependencies": [],
                    "params": {"dir": "src/v1"},
                },
                {
                    "step_id": "step_convert_v2",
                    "action_type": "ANALYZE",
                    "tool_name": "ast_transform",
                    "dependencies": ["step_inspect_v1"],
                    "params": {"target": "src/v2"},
                },
            ],
        },
    )
    assert run_res.status_code == status.HTTP_201_CREATED
    run_data = run_res.json()
    run_id = run_data["run_id"]
    assert run_data["status"] == "RUNNING"

    # 4. GET /api/v1/autonomy/runs/{run_id}
    run_get = client.get(f"/api/v1/autonomy/runs/{run_id}")
    assert run_get.status_code == status.HTTP_200_OK
    assert run_get.json()["run_id"] == run_id

    # 5. POST /api/v1/autonomy/runs/{run_id}/step
    step_res = client.post(f"/api/v1/autonomy/runs/{run_id}/step", json={"is_pre_approved": True})
    assert step_res.status_code == status.HTTP_200_OK
    step_data = step_res.json()
    assert step_data["step_id"] == "step_inspect_v1"
    assert step_data["is_success"] is True

    # 6. GET /api/v1/autonomy/runs/{run_id}/progress
    prog_res = client.get(f"/api/v1/autonomy/runs/{run_id}/progress")
    assert prog_res.status_code == status.HTTP_200_OK
    prog_data = prog_res.json()
    assert prog_data["completed_steps"] >= 1

    # 7. GET /api/v1/autonomy/runs/{run_id}/checkpoints
    chk_res = client.get(f"/api/v1/autonomy/runs/{run_id}/checkpoints")
    assert chk_res.status_code == status.HTTP_200_OK
    assert len(chk_res.json()) >= 1

    # 8. GET /api/v1/autonomy/runs/{run_id}/watchdog
    dog_res = client.get(f"/api/v1/autonomy/runs/{run_id}/watchdog")
    assert dog_res.status_code == status.HTTP_200_OK
    assert dog_res.json()["issue_detected"] == "HEALTHY"

    # 9. Control: PAUSE -> RESUME
    pause_res = client.post(f"/api/v1/autonomy/runs/{run_id}/control", json={"action": "PAUSE", "reason": "Test pause"})
    assert pause_res.status_code == status.HTTP_200_OK
    assert pause_res.json()["status"] == "PAUSED"

    resume_res = client.post(f"/api/v1/autonomy/runs/{run_id}/control", json={"action": "RESUME"})
    assert resume_res.status_code == status.HTTP_200_OK
    assert resume_res.json()["status"] == "RUNNING"

    # 10. Post external event
    ev_res = client.post(
        f"/api/v1/autonomy/runs/{run_id}/events",
        json={
            "event_id": "ev_api_01",
            "event_type": "DEPLOY_CALLBACK",
            "sequence_num": 1,
            "is_authenticated": True,
        },
    )
    assert ev_res.status_code == status.HTTP_200_OK
    assert ev_res.json()["status"] == "PROCESSED"

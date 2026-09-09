"""Tests for Cognitive Planning & Reasoning REST API endpoints (Task 41)."""

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
async def test_cognition_goal_and_plan_lifecycle_api(client: AsyncClient):
    # 1. Create Goal
    goal_payload = {
        "description": "Prepare API deployment for production environment",
        "goal_type": "DEVELOPMENT",
        "priority": "HIGH",
        "constraints": {"budget": 100},
        "success_criteria": ["All automated checks pass", "Zero critical security alerts"],
    }
    res_goal = await client.post(
        "/api/v1/cognition/goals",
        json=goal_payload,
        headers={"x-user-id": "user_dev"},
    )
    assert res_goal.status_code == 201
    goal_data = res_goal.json()
    assert "goal_id" in goal_data
    goal_id = goal_data["goal_id"]

    # 2. Get Goal
    res_get_goal = await client.get(
        f"/api/v1/cognition/goals/{goal_id}",
        headers={"x-user-id": "user_dev"},
    )
    assert res_get_goal.status_code == 200
    assert res_get_goal.json()["goal_id"] == goal_id

    # 3. Build Plan for Goal
    res_plan = await client.post(
        f"/api/v1/cognition/goals/{goal_id}/plan",
        json={"reasoning_mode": "DECOMPOSITION"},
        headers={"x-user-id": "user_dev"},
    )
    assert res_plan.status_code == 201
    plan_data = res_plan.json()
    assert "plan_id" in plan_data
    assert plan_data["version"] == 1
    plan_id = plan_data["plan_id"]
    steps = plan_data["steps"]
    assert len(steps) > 0

    # 4. Validate Plan
    res_val = await client.post(
        f"/api/v1/cognition/plans/{plan_id}/validate",
        headers={"x-user-id": "user_dev"},
    )
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["is_valid"] is True
    assert val_data["quality_score"] >= 0.7

    # 5. Get Plan Preview
    res_prev = await client.get(
        f"/api/v1/cognition/plans/{plan_id}/preview",
        headers={"x-user-id": "user_dev"},
    )
    assert res_prev.status_code == 200
    assert res_prev.json()["plan_id"] == plan_id

    # 6. Explain Step
    first_step_id = steps[0]["step_id"]
    res_explain = await client.get(
        f"/api/v1/cognition/plans/{plan_id}/steps/{first_step_id}/explain",
        headers={"x-user-id": "user_dev"},
    )
    assert res_explain.status_code == 200
    assert "why_this_step" in res_explain.json()

    # 7. Verify Step Execution
    res_verify = await client.post(
        f"/api/v1/cognition/plans/{plan_id}/verify-step",
        json={
            "step_id": first_step_id,
            "output_result": {"status": "completed", "environment_ready": True},
            "observed_state": {"environment_ready": True},
        },
        headers={"x-user-id": "user_dev"},
    )
    assert res_verify.status_code == 200
    assert res_verify.json()["verified"] is True

    # 8. Trigger Re-plan
    res_replan = await client.post(
        f"/api/v1/cognition/plans/{plan_id}/replan",
        json={
            "reason": "STATE_CHANGE",
            "observed_failure": "Target cluster reports drift",
        },
        headers={"x-user-id": "user_dev"},
    )
    assert res_replan.status_code == 200
    replan_data = res_replan.json()
    assert replan_data["new_plan"]["version"] == 2
    assert replan_data["diff"]["old_version"] == 1
    assert replan_data["diff"]["new_version"] == 2

    # 9. Get Dashboard
    res_dash = await client.get(
        "/api/v1/cognition/dashboard",
        headers={"x-user-id": "user_dev"},
    )
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert "total_goals" in dash_data
    assert "total_plans" in dash_data
    assert dash_data["total_goals"] >= 1

    # 10. List Templates
    res_tpl = await client.get("/api/v1/cognition/templates")
    assert res_tpl.status_code == 200
    assert len(res_tpl.json()) >= 1

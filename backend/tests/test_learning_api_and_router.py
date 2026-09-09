"""Tests for Adaptive Learning REST API endpoints (Task 43)."""

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
async def test_learning_api_full_lifecycle(client: AsyncClient):
    # 1. Register a Candidate Strategy
    strat_payload = {
        "domain": "coding",
        "description": "Deterministic AST rewriting with syntax invariant validation",
        "prerequisites": ["tree-sitter", "ast"],
        "status": "CANDIDATE",
    }
    res_strat = await client.post(
        "/api/v1/learning/strategies",
        json=strat_payload,
        headers={"x-user-id": "lead_architect"},
    )
    assert res_strat.status_code == 201
    strat_data = res_strat.json()
    assert "strategy_id" in strat_data
    assert strat_data["status"] == "CANDIDATE"
    assert strat_data["domain"] == "coding"
    strategy_id = strat_data["strategy_id"]

    # 2. Get Strategy by ID
    res_get_strat = await client.get(f"/api/v1/learning/strategies/{strategy_id}")
    assert res_get_strat.status_code == 200
    assert res_get_strat.json()["strategy_id"] == strategy_id

    # 3. List Strategies
    res_list_strats = await client.get("/api/v1/learning/strategies?domain=coding")
    assert res_list_strats.status_code == 200
    assert len(res_list_strats.json()) >= 1

    # 4. Record Execution Experience
    exp_payload = {
        "strategy": strategy_id,
        "goal_type": "REFACTOR",
        "plan_type": "SEQUENTIAL",
        "actions": ["load_ast", "apply_patch", "run_linter"],
        "observations": [{"status": "ok", "token": "ghp_secret1234567890"}],
        "verification_result": {"status": "PASS", "confidence": "HIGH"},
        "outcome": "SUCCESS",
        "duration_ms": 320.0,
        "cost": 0.005,
    }
    res_exp = await client.post(
        "/api/v1/learning/experiences",
        json=exp_payload,
        headers={"x-user-id": "lead_architect"},
    )
    assert res_exp.status_code == 201
    exp_data = res_exp.json()
    assert "experience_id" in exp_data
    assert exp_data["outcome"] == "SUCCESS"
    assert exp_data["learning_weight"] >= 0.90

    # 5. List Experiences
    res_list_exp = await client.get(f"/api/v1/learning/experiences?strategy={strategy_id}")
    assert res_list_exp.status_code == 200
    assert len(res_list_exp.json()) >= 1

    # 6. Get Strategy Recommendations
    res_rec = await client.get(
        "/api/v1/learning/recommendations?domain=coding",
        headers={"x-user-id": "lead_architect"},
    )
    assert res_rec.status_code == 200
    rec_data = res_rec.json()
    assert "recommended_strategy" in rec_data

    # 7. Check Pre-Flight Warnings
    res_warn = await client.get("/api/v1/learning/failures/pre-flight?workflow_name=non_existent_flow")
    assert res_warn.status_code == 200
    # No warnings for new workflow
    assert res_warn.json() is None

    # 8. Create A/B Canary Experiment
    exp_ab_payload = {
        "name": "AST vs String Template Trial",
        "domain": "coding",
        "baseline_strategy_id": "strat-default-coding",
        "candidate_strategy_id": strategy_id,
        "target_sample_size": 20,
    }
    res_create_ab = await client.post("/api/v1/learning/experiments", json=exp_ab_payload)
    assert res_create_ab.status_code == 201
    ab_data = res_create_ab.json()
    assert "experiment_id" in ab_data
    assert ab_data["domain"] == "coding"

    # 9. List Experiments
    res_list_ab = await client.get("/api/v1/learning/experiments")
    assert res_list_ab.status_code == 200
    assert len(res_list_ab.json()) >= 1

    # 10. Submit User Feedback
    fb_payload = {
        "target_id": strategy_id,
        "feedback_type": "positive",
        "rating": 5,
        "comment": "Accurate patch with zero syntax regressions.",
    }
    res_fb = await client.post(
        "/api/v1/learning/feedback",
        json=fb_payload,
        headers={"x-user-id": "lead_architect"},
    )
    assert res_fb.status_code == 201
    assert res_fb.json()["status"] == "ok"

    # 11. Attempt Promotion (Should reject cleanly if sample size < 10)
    promo_payload = {
        "strategy_id": strategy_id,
        "approved_by": "qa_lead",
        "reason": "Requesting promotion after initial trial",
    }
    res_promo = await client.post("/api/v1/learning/promote", json=promo_payload)
    # Expected 400 rejection because sample_size is only 1 (< 10 required)
    assert res_promo.status_code == 400
    assert "Insufficient sample size" in res_promo.json()["detail"]

    # 12. Rollback Strategy
    rb_payload = {
        "strategy_id": strategy_id,
        "rolled_back_by": "operator",
        "reason": "Manual operator intervention for safety check",
    }
    res_rb = await client.post("/api/v1/learning/rollback", json=rb_payload)
    assert res_rb.status_code == 200
    rb_data = res_rb.json()
    assert rb_data["prior_status"] == "CANDIDATE"
    assert "rollback_id" in rb_data

    # 13. Get Engine Stats
    res_stats = await client.get("/api/v1/learning/stats")
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert stats_data["total_strategies"] >= 1
    assert stats_data["total_experiences"] >= 1
    assert stats_data["total_experiments"] >= 1

"""Test suite for LearningService orchestration and FastAPI Continuous Learning endpoints (Task 52)."""

from datetime import UTC, datetime, timedelta
import pytest
from httpx import ASGITransport, AsyncClient

from app.learning.evaluation import ContinuousLearningEvaluator
from app.learning.schemas import GeneralizationScope, LessonType
from app.learning.service import LearningService
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def test_learning_service_continuous_orchestration():
    """Verify LearningService orchestrates outcome evaluation, lesson extraction, workflows, and replays."""
    service = LearningService()

    # 1. Evaluate Task Outcome
    outcome = service.evaluate_task_outcome(
        expected={"exit_code": 0},
        actual={"exit_code": 0},
        verification_telemetry={"tests": "passed"},
        task_id="task-orch-1",
    )
    assert outcome.deviation == 0.0
    assert outcome.verified is True

    # 2. Extract Lesson
    lesson = service.extract_lesson(
        statement="Keep Docker build context small to speed up CI",
        lesson_type=LessonType.SUCCESS_PATTERN,
        source_experiences=["exp-docker-1"],
        evidence=[{"build_time": "reduced by 40%"}],
        confidence=0.8,
        scope=GeneralizationScope.PROJECT,
    )
    assert lesson.lesson_id.startswith("lsn_")
    assert lesson.statement == "Keep Docker build context small to speed up CI"

    # 3. Register Workflow
    wf = service.register_workflow(
        name="Microservice Release Workflow",
        steps=[{"step": 1, "action": "tag"}, {"step": 2, "action": "push_image"}],
    )
    assert wf.workflow_id.startswith("wf_")
    assert wf.status == "CANDIDATE"

    # 4. Register Heuristic
    h = service.register_heuristic(
        condition="high memory pressure",
        recommendation="enable streaming mode for batch processing",
        evidence=[{"oom_killed": 0}],
        confidence=0.75,
        scope=GeneralizationScope.ENVIRONMENT,
    )
    assert h.heuristic_id.startswith("heu_")

    # 5. User Correction
    cor = service.handle_user_correction(
        target_action="auto_git_push",
        user_directive="Don't auto-push without prompt in this project",
    )
    assert cor.scope == GeneralizationScope.PROJECT

    # 6. Check Metrics
    metrics = service.get_continuous_metrics()
    assert metrics["total_experiences"] >= 0
    assert metrics["total_lessons"] >= 1
    assert metrics["total_workflows"] >= 1
    assert metrics["total_heuristics"] >= 1


def test_multi_dimensional_evaluation_anti_reward_hacking():
    """INVARIANT 151-153: Multi-dimensional evaluation prevents optimizing latency at the cost of safety or verification."""
    evaluator = ContinuousLearningEvaluator()

    # High speed but reduced verification and safety violations
    score_compromised = evaluator.calculate_multi_dimensional_score(
        accuracy=0.85,
        safety_score=0.40,  # Critical safety degradation
        verification_coverage=0.30,  # Low verification
        latency_score=0.99,  # High speed
        cost_score=0.95,
        user_satisfaction=0.80,
    )

    # Balanced, verified, safe profile
    score_safe = evaluator.calculate_multi_dimensional_score(
        accuracy=0.85,
        safety_score=1.0,
        verification_coverage=0.95,
        latency_score=0.70,
        cost_score=0.80,
        user_satisfaction=0.85,
    )

    # Safe and verified must score higher than sacrificed safety/verification
    assert score_safe > score_compromised


@pytest.mark.asyncio
async def test_continuous_learning_rest_api_lifecycle(client: AsyncClient):
    """Verify all FastAPI continuous learning endpoints."""
    # 1. GET continuous metrics
    res_metrics = await client.get("/api/v1/learning/continuous/metrics")
    assert res_metrics.status_code == 200
    metrics_data = res_metrics.json()
    assert "total_lessons" in metrics_data

    # 2. POST evaluate outcome
    res_out = await client.post(
        "/api/v1/learning/continuous/outcomes",
        json={
            "expected": {"response_code": 200},
            "actual": {"response_code": 200},
            "verification_telemetry": {"latency_ok": True},
            "task_id": "task-api-1",
        },
    )
    assert res_out.status_code == 200
    out_data = res_out.json()
    assert out_data["deviation"] == 0.0
    assert out_data["verified"] is True

    # 3. POST extract lesson
    res_lsn1 = await client.post(
        "/api/v1/learning/continuous/lessons",
        json={
            "statement": "Use connection pool for high concurrency async endpoints",
            "lesson_type": "TOOL_PATTERN",
            "source_experiences": ["exp-db-1"],
            "evidence": [{"pool_exhaustion": False}],
            "confidence": 0.85,
            "scope": "PROJECT",
        },
    )
    assert res_lsn1.status_code == 200
    lsn1_data = res_lsn1.json()
    lid1 = lsn1_data["lesson_id"]

    res_lsn2 = await client.post(
        "/api/v1/learning/continuous/lessons",
        json={
            "statement": "Configure pool size to match worker count in async endpoints",
            "lesson_type": "TOOL_PATTERN",
            "source_experiences": ["exp-db-2"],
            "evidence": [{"latency_p99": "dropped to 50ms"}],
            "confidence": 0.88,
            "scope": "PROJECT",
        },
    )
    assert res_lsn2.status_code == 200
    lid2 = res_lsn2.json()["lesson_id"]

    # 4. GET list lessons
    res_list_lsn = await client.get("/api/v1/learning/continuous/lessons")
    assert res_list_lsn.status_code == 200
    assert len(res_list_lsn.json()) >= 2

    # 5. POST consolidate lessons
    res_cons = await client.post(
        "/api/v1/learning/continuous/lessons/consolidate",
        json={"target_lesson_id": lid1, "candidate_lesson_id": lid2},
    )
    assert res_cons.status_code == 200
    cons_data = res_cons.json()
    assert len(cons_data["source_experiences"]) == 2

    # 6. POST register workflow
    res_wf = await client.post(
        "/api/v1/learning/continuous/workflows",
        json={
            "name": "Async DB Migration Workflow",
            "steps": [{"step": 1, "action": "alembic upgrade head"}],
            "preconditions": [{"check": "db_reachable"}],
            "expected_outcome": {"schema_version": "latest"},
            "verification": {"integrity_check": "ok"},
            "failure_modes": ["migration_conflict"],
        },
    )
    assert res_wf.status_code == 200
    assert res_wf.json()["name"] == "Async DB Migration Workflow"

    # 7. GET list workflows
    res_list_wf = await client.get("/api/v1/learning/continuous/workflows")
    assert res_list_wf.status_code == 200
    assert len(res_list_wf.json()) >= 1

    # 8. POST register heuristic
    res_heu = await client.post(
        "/api/v1/learning/continuous/heuristics",
        json={
            "condition": "migrating postgres database",
            "recommendation": "verify connection pool timeout before applying",
            "evidence": [{"success": True}],
            "confidence": 0.8,
            "scope": "PROJECT",
            "priority": 2,
        },
    )
    assert res_heu.status_code == 200
    assert res_heu.json()["heuristic_id"].startswith("heu_")

    # 9. GET list heuristics
    res_list_heu = await client.get("/api/v1/learning/continuous/heuristics")
    assert res_list_heu.status_code == 200
    assert len(res_list_heu.json()) >= 1

    # 10. POST handle user correction
    res_cor = await client.post(
        "/api/v1/learning/continuous/corrections",
        json={
            "target_action": "generate_report",
            "user_directive": "Don't use csv format, use markdown in this project",
        },
    )
    assert res_cor.status_code == 200
    assert res_cor.json()["scope"] == "PROJECT"

    # 11. GET governance policy
    res_gov = await client.get("/api/v1/learning/continuous/governance")
    assert res_gov.status_code == 200
    gov_data = res_gov.json()
    assert "allowed_adaptations" in gov_data

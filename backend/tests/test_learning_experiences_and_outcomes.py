"""Tests for Experiences, Outcomes, Redaction, and Weighting (Task 43)."""

import pytest
from app.learning.experiences import Experience, ExperienceType
from app.learning.outcomes import Outcome
from app.learning.service import LearningService


def test_experience_creation_and_fields():
    """Experience model must track all essential execution fields with safe defaults."""
    exp = Experience(
        experience_id="exp-101",
        task_id="task-01",
        goal_type="CODE_REFACTOR",
        plan_type="SEQUENTIAL",
        strategy="AST_PARSER_REWRITE",
        context_reference="repo://auth_module",
        outcome=ExperienceType.SUCCESS,
        actions=["read_file", "parse_ast", "write_file"],
        verification_result={"status": "PASS", "confidence": "HIGH"},
        duration_ms=450.0,
        cost=0.012,
        retries=0,
    )
    assert exp.experience_id == "exp-101"
    assert exp.outcome == ExperienceType.SUCCESS
    assert exp.actions == ["read_file", "parse_ast", "write_file"]
    
    d = exp.to_dict()
    assert d["experience_id"] == "exp-101"
    assert d["outcome"] == "SUCCESS"
    assert d["duration_ms"] == 450.0


def test_experience_types_supported():
    """All 12 required experience types must be represented."""
    expected_types = [
        "SUCCESS",
        "PARTIAL_SUCCESS",
        "FAILURE",
        "UNKNOWN",
        "RECOVERY_SUCCESS",
        "RECOVERY_FAILURE",
        "USER_CORRECTION",
        "VERIFICATION_FAILURE",
        "PLAN_FAILURE",
        "TOOL_FAILURE",
        "MODEL_FAILURE",
        "RETRIEVAL_FAILURE",
    ]
    for t in expected_types:
        assert hasattr(ExperienceType, t)


def test_experience_secret_redaction():
    """Experience creation must redact credentials, tokens, and secrets (Spec 93)."""
    exp = Experience(
        experience_id="exp-sec",
        task_id="task-sec",
        goal_type="DEPLOY",
        plan_type="CLI",
        strategy="DOCKER_PUSH",
        actions=[
            "export TOKEN=ghp_12345678901234567890",
            "curl -H 'Authorization: Bearer secret_key_abc'",
        ],
        observations=[
            {"password": "super_secret_password", "status": "ok"}
        ],
    )
    actions_str = " ".join(exp.actions)
    assert "ghp_12345678901234567890" not in actions_str
    assert "[REDACTED" in actions_str

    obs_str = str(exp.observations)
    assert "super_secret_password" not in obs_str
    assert "[REDACTED" in obs_str


def test_experience_learning_weight_verified_vs_unknown():
    """Only verified outcomes receive strong learning weight; unknown produces weak/zero weight (Spec 4, 5)."""
    verified_success = Experience(
        experience_id="exp-v-succ",
        task_id="t1",
        goal_type="TEST",
        plan_type="CLI",
        strategy="PYTEST_RUN",
        outcome=ExperienceType.SUCCESS,
        verification_result={"status": "PASS"},
    )
    unverified_success = Experience(
        experience_id="exp-uv-succ",
        task_id="t2",
        goal_type="TEST",
        plan_type="CLI",
        strategy="PYTEST_RUN",
        outcome=ExperienceType.SUCCESS,
        verification_result={},
    )
    unknown_exp = Experience(
        experience_id="exp-unk",
        task_id="t3",
        goal_type="TEST",
        plan_type="CLI",
        strategy="PYTEST_RUN",
        outcome=ExperienceType.UNKNOWN,
        verification_result={},
    )

    w_verified = verified_success.calculate_learning_weight()
    w_unverified = unverified_success.calculate_learning_weight()
    w_unknown = unknown_exp.calculate_learning_weight()

    assert w_verified >= 0.90
    assert w_unverified <= 0.40
    assert w_unknown <= 0.15
    assert w_verified > w_unverified > w_unknown


def test_outcome_model_and_criteria():
    """Outcome model must capture verification, cost, duration, risk, and recovery requirements."""
    outcome = Outcome(
        status="SUCCESS",
        success_criteria=["coverage >= 90", "all unit tests pass"],
        verification={"status": "PASS", "strategy": "UNIT_TEST"},
        evidence=["ev-01", "ev-02"],
        duration_ms=620.0,
        cost=0.015,
        risk="LOW",
        user_feedback={"rating": 5, "comment": "Fast and clean"},
        recovery_required=False,
    )
    assert outcome.status == "SUCCESS"
    assert outcome.duration_ms == 620.0
    assert outcome.recovery_required is False
    d = outcome.to_dict()
    assert d["risk"] == "LOW"
    assert len(d["success_criteria"]) == 2


def test_learning_service_record_experience():
    """LearningService must ingest experiences and index them safely."""
    service = LearningService()
    exp = service.record_experience(
        strategy="MULTI_QUERY_TRIANGULATION",
        task_id="task-srv-01",
        goal_type="RESEARCH",
        plan_type="SEARCH_AND_SYNTHESIZE",
        outcome="SUCCESS",
        duration_ms=850.0,
        cost=0.02,
        verification_result={"status": "PASS"},
    )
    assert exp.experience_id.startswith("exp_")
    assert exp.goal_type == "RESEARCH"
    
    retrieved = service.list_experiences(goal_type="RESEARCH")
    assert len(retrieved) >= 1
    assert retrieved[0].experience_id == exp.experience_id

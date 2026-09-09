"""Unit tests for Experience schemas, models, and enums (Sections 1, 2, 3, 6, 7, 13, 29)."""

import pytest
from app.experience.schemas import (
    CandidateStatus,
    ConfidenceLevel,
    CreateCorrectionRequest,
    CreateFeedbackRequest,
    CreatePreferenceRequest,
    Experience,
    ExperienceScope,
    ExperienceSource,
    ExperienceStatus,
    ExperienceType,
    FailureType,
    FeedbackType,
    LearningCandidate,
    Preference,
    UserFeedback,
)


def test_experience_model_validation():
    """Verify Experience canonical model instantiation and constraints."""
    exp = Experience(
        id="exp-123",
        user_id="user-1",
        project_id="proj-alpha",
        type=ExperienceType.USER_CORRECTION,
        source=ExperienceSource.USER_EXPLICIT,
        scope=ExperienceScope.PROJECT,
        summary="User corrected database preference to SQLite",
        evidence={"correction": "No, we use SQLite for this project."},
        confidence=ConfidenceLevel.HIGH,
        status=ExperienceStatus.ACTIVE,
    )
    assert exp.id == "exp-123"
    assert exp.type == ExperienceType.USER_CORRECTION
    assert exp.source == ExperienceSource.USER_EXPLICIT
    assert exp.scope == ExperienceScope.PROJECT
    assert exp.confidence == ConfidenceLevel.HIGH
    assert exp.status == ExperienceStatus.ACTIVE
    assert exp.expires_at is None


def test_preference_model_validation():
    """Verify Preference canonical model instantiation and scoping."""
    pref = Preference(
        id="pref-001",
        user_id="user-1",
        scope=ExperienceScope.USER,
        key="preferred_language",
        value="Python",
        source=ExperienceSource.USER_EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        status="ACTIVE",
    )
    assert pref.key == "preferred_language"
    assert pref.value == "Python"
    assert pref.scope == ExperienceScope.USER


def test_learning_candidate_model():
    """Verify LearningCandidate canonical model and status."""
    cand = LearningCandidate(
        id="cand-001",
        source_event="task_failure:TOOL_FAILURE",
        proposed_change="Add regression test scenario for git tool timeout",
        evidence={"tool": "git", "failure_type": "TOOL_FAILURE"},
        confidence=ConfidenceLevel.LOW,
        scope=ExperienceScope.GLOBAL,
        status=CandidateStatus.PROPOSED,
    )
    assert cand.id == "cand-001"
    assert cand.status == CandidateStatus.PROPOSED
    assert cand.reviewer_id is None


def test_failure_type_enums():
    """Verify all failure classifications from Section 13 exist."""
    expected_failures = [
        "MODEL_FAILURE",
        "TOOL_FAILURE",
        "AUTH_FAILURE",
        "PERMISSION_FAILURE",
        "NETWORK_FAILURE",
        "USER_CANCELLED",
        "TIMEOUT",
        "VALIDATION_FAILURE",
        "UNKNOWN",
    ]
    for ef in expected_failures:
        assert FailureType(ef) is not None


def test_experience_statuses():
    """Verify all experience lifecycle statuses from Section 2 exist."""
    expected_statuses = [
        "CANDIDATE",
        "VALIDATED",
        "ACTIVE",
        "STALE",
        "REJECTED",
        "SUPERSEDED",
        "DELETED",
    ]
    for es in expected_statuses:
        assert ExperienceStatus(es) is not None

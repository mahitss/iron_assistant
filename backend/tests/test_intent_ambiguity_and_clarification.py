"""Tests for Ambiguity Modeling, Consequence-Aware Clarification, and Safe Defaults (Task 48, Spec 55-62)."""

import pytest

from app.intent.ambiguity import Ambiguity, AmbiguityAnalyzer
from app.intent.clarification import ClarificationManager, ClarificationRequest
from app.intent.schemas import AmbiguityLevel, IntentRiskLevel, IntentType


def test_ambiguity_levels():
    """Verify 5 standard ambiguity levels (Spec 56)."""
    assert AmbiguityLevel.NONE.value == "NONE"
    assert AmbiguityLevel.LOW.value == "LOW"
    assert AmbiguityLevel.MEDIUM.value == "MEDIUM"
    assert AmbiguityLevel.HIGH.value == "HIGH"
    assert AmbiguityLevel.CRITICAL.value == "CRITICAL"


def test_consequence_aware_clarification_destructive():
    """High-risk ambiguity for destructive command triggers CRITICAL clarification (Spec 57, 62)."""
    candidates = [
        {"candidates": ["staging-db", "prod-db"], "reason": "Multiple databases match 'the database'."}
    ]
    report = AmbiguityAnalyzer.analyze(
        intent_type=IntentType.DELETE,
        risk_level=IntentRiskLevel.CRITICAL,
        ambiguous_candidates=candidates,
        target=None,
    )

    assert report.ambiguous is True
    assert report.level == AmbiguityLevel.CRITICAL
    assert len(report.resolution_options) >= 2


def test_clarification_request_fields():
    """Verify ClarificationRequest model fields (Spec 58)."""
    req = ClarificationRequest(
        clarification_id="clarify_123",
        intent_id="intent_abc",
        question="Which database would you like to drop?",
        reason="Action is irreversible and multiple databases match.",
        affected_decision="target_selection",
        options=["staging-db", "dev-db"],
        default_if_any=None,  # NEVER default destructive action
    )

    data = req.to_dict()
    assert data["clarification_id"] == "clarify_123"
    assert data["question"] == "Which database would you like to drop?"
    assert data["affected_decision"] == "target_selection"
    assert data["default_if_any"] is None


def test_no_dangerous_defaults_on_destructive():
    """CRITICAL SAFETY: Clarification manager strictly refuses defaults for destructive operations (Spec 61, 62)."""
    mgr = ClarificationManager()
    req = mgr.create_request(
        intent_id="intent_del",
        question="Which cluster to destroy?",
        reason="Cluster termination is permanent.",
        affected_decision="target_cluster",
        options=["cluster-alpha", "cluster-beta"],
        is_destructive=True,
    )

    assert req.default_if_any is None  # Safety invariant verified


def test_safe_default_on_low_risk_action():
    """Safe defaults permitted on low-risk, reversible actions (Spec 61)."""
    mgr = ClarificationManager()
    req = mgr.create_request(
        intent_id="intent_list",
        question="Format output as table or JSON?",
        reason="Output formatting preference.",
        affected_decision="format_style",
        options=["table", "json"],
        is_destructive=False,
    )

    # Low risk actions can carry a default format
    assert req.affected_decision == "format_style"


def test_answering_clarification_advances_state():
    """Answering clarification marks request answered and records choice (Spec 58, 68)."""
    mgr = ClarificationManager()
    req = mgr.create_request(
        intent_id="intent_999",
        question="Select branch to inspect",
        reason="Ambiguous branch reference",
        affected_decision="branch_selection",
        options=["main", "feature/auth"],
    )

    answered = mgr.answer_clarification(req.clarification_id, "feature/auth")
    assert answered is not None
    assert answered.selected_answer == "feature/auth"
    assert answered.is_resolved is True

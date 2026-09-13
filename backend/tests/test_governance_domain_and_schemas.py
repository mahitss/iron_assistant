"""Unit tests for Governance domain schemas, enums, models, and contracts (Task 78)."""

from __future__ import annotations

import pytest

from app.policy.governance_schemas import (
    AuthorityEscalationReport,
    AuthorityGrant,
    AuthorityLevel,
    ConstitutionalPrinciple,
    ConstitutionModelSchema,
    GoalAlignmentReport,
    GovernanceDashboardSummary,
    GovernanceDecisionResult,
    GovernanceDecisionType,
    GovernanceReviewRequest,
    GovernanceState,
    LeastPrivilegeRecommendation,
    PolicyTier,
    PrincipleEvaluationResult,
    PrincipleName,
    PrincipleStrictness,
)


def test_principle_name_enum_count() -> None:
    """Validate exactly 11 canonical constitutional principles."""
    expected = {
        "SAFETY", "LEGALITY", "USER_AUTHORITY", "TRANSPARENCY", "AUDITABILITY",
        "REVERSIBILITY", "PROPORTIONALITY", "PRIVACY", "SECURITY",
        "LEAST_PRIVILEGE", "HUMAN_OVERSIGHT",
    }
    actual = {p.value for p in PrincipleName}
    assert actual == expected
    assert len(PrincipleName) == 11


def test_principle_strictness_enum() -> None:
    """Validate 3 levels of strictness."""
    assert len(PrincipleStrictness) == 3
    assert PrincipleStrictness.MANDATORY.value == "MANDATORY"
    assert PrincipleStrictness.STRICT.value == "STRICT"
    assert PrincipleStrictness.ADVISORY.value == "ADVISORY"


def test_policy_tier_hierarchy_and_ranks() -> None:
    """Validate 6 policy tiers with strict precedence ranking (SYSTEM rank 0 is highest)."""
    assert len(PolicyTier) == 6
    assert PolicyTier.SYSTEM.rank == 0
    assert PolicyTier.SECURITY.rank == 1
    assert PolicyTier.TENANT.rank == 2
    assert PolicyTier.PROJECT.rank == 3
    assert PolicyTier.WORKFLOW.rank == 4
    assert PolicyTier.TASK.rank == 5
    assert PolicyTier.SYSTEM.rank < PolicyTier.SECURITY.rank < PolicyTier.TASK.rank


def test_authority_level_hierarchy_and_ranks() -> None:
    """Validate 6 discrete authority levels (NONE rank 0 to ADMIN rank 5)."""
    assert len(AuthorityLevel) == 6
    assert AuthorityLevel.NONE.rank == 0
    assert AuthorityLevel.LIMITED.rank == 1
    assert AuthorityLevel.PROJECT.rank == 2
    assert AuthorityLevel.TENANT.rank == 3
    assert AuthorityLevel.SYSTEM.rank == 4
    assert AuthorityLevel.ADMIN.rank == 5
    assert AuthorityLevel.NONE.rank < AuthorityLevel.LIMITED.rank < AuthorityLevel.ADMIN.rank


def test_governance_states_enum() -> None:
    """Validate exactly 8 governance lifecycle states."""
    expected = {
        "PENDING_REVIEW", "APPROVED", "DENIED", "REQUIRES_APPROVAL",
        "REQUIRES_HUMAN", "EXECUTABLE", "EXPIRED", "ABORTED",
    }
    actual = {s.value for s in GovernanceState}
    assert actual == expected


def test_governance_decision_types_enum() -> None:
    """Validate 6 governance decision types."""
    expected = {"ALLOWED", "DENIED", "REQUIRES_APPROVAL", "REQUIRES_HUMAN", "CONFLICTING_POLICY", "UNKNOWN"}
    actual = {d.value for d in GovernanceDecisionType}
    assert actual == expected


def test_constitutional_principle_validation() -> None:
    """Validate ConstitutionalPrinciple bounds and serialization."""
    p = ConstitutionalPrinciple(
        name=PrincipleName.SAFETY,
        weight=0.95,
        strictness=PrincipleStrictness.MANDATORY,
        description="Prevent data loss.",
    )
    assert p.weight == 0.95
    assert p.strictness == PrincipleStrictness.MANDATORY
    assert p.enabled is True

    # Weight out of bounds should raise ValidationError
    with pytest.raises(Exception):
        ConstitutionalPrinciple(name=PrincipleName.SAFETY, weight=1.5)


def test_constitution_model_schema_defaults() -> None:
    """Validate ConstitutionModelSchema instantiation and principle collection."""
    c = ConstitutionModelSchema(
        name="Test Constitution",
        version="2.0.0",
        principles=[
            ConstitutionalPrinciple(name=PrincipleName.HUMAN_OVERSIGHT, weight=1.0),
        ],
    )
    assert len(c.principles) == 1
    assert c.is_active is True
    data = c.model_dump()
    assert data["version"] == "2.0.0"
    reconstructed = ConstitutionModelSchema.model_validate(data)
    assert reconstructed.principles[0].name == PrincipleName.HUMAN_OVERSIGHT


def test_authority_grant_defaults() -> None:
    """Validate AuthorityGrant creation and scope defaults."""
    grant = AuthorityGrant(
        subject_id="agent_alpha",
        authority_level=AuthorityLevel.PROJECT,
        allowed_scopes=["workspace_1"],
        allowed_actions=["run_*"],
    )
    assert grant.subject_id == "agent_alpha"
    assert grant.authority_level == AuthorityLevel.PROJECT
    assert grant.is_active is True
    assert grant.denied_actions == []


def test_governance_review_request_and_result() -> None:
    """Validate GovernanceReviewRequest and GovernanceDecisionResult contracts."""
    req = GovernanceReviewRequest(
        goal="Run tests",
        action="execute_pytest",
        caller_id="agent_ci",
        caller_authority=AuthorityLevel.LIMITED,
        required_permissions=["READ", "EXECUTE"],
    )
    assert req.uncertainty_score == 0.0
    assert req.is_destructive is False

    res = GovernanceDecisionResult(
        review_id=req.review_id,
        decision=GovernanceDecisionType.ALLOWED,
        state=GovernanceState.EXECUTABLE,
        authority_level_granted=AuthorityLevel.LIMITED,
        authority_check_passed=True,
        constitutional_score=0.98,
        explanation="Action verified safe.",
    )
    assert res.decision == GovernanceDecisionType.ALLOWED
    assert res.requires_human is False
    assert res.constitutional_score == 0.98

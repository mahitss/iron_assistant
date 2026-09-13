"""Integration and safety tests for Governance Intelligence Coordinator and DB models (Task 78)."""

from __future__ import annotations

import asyncio
import pytest

from app.policy.governance_coordinator import GovernanceIntelligenceCoordinator
from app.policy.governance_models import (
    AuthorityEscalationIncidentModel,
    AuthorityGrantModel,
    ConstitutionalPrincipleModel,
    ConstitutionRecordModel,
    GovernanceDecisionRecordModel,
)
from app.policy.governance_schemas import (
    AuthorityLevel,
    GovernanceDecisionType,
    GovernanceReviewRequest,
    GovernanceState,
    PolicyTier,
)
from app.security.emergency_stop import get_emergency_stop_service
from tests.test_governance_fixtures import (
    create_fixture_benign_read,
    create_fixture_control_weakening,
    create_fixture_emergency_stop,
    create_fixture_high_uncertainty_irreversible,
    create_fixture_multi_tier_conflict,
    create_fixture_probe_hammering,
)


@pytest.mark.asyncio
async def test_coordinator_benign_read_allowed() -> None:
    """Safe read request with valid authority grant is ALLOWED and EXECUTABLE."""
    coord, req = create_fixture_benign_read()
    res = await coord.evaluate_review(req)

    assert res.decision == GovernanceDecisionType.ALLOWED
    assert res.state == GovernanceState.EXECUTABLE
    assert res.authority_check_passed is True
    assert res.requires_human is False
    assert res.constitutional_score >= 0.95


@pytest.mark.asyncio
async def test_coordinator_emergency_stop_halts_everything() -> None:
    """Active emergency stop forces immediate DENIED decision and ABORTED state."""
    es = get_emergency_stop_service()
    es.trigger_emergency_stop(reason="Global safety breach")
    try:
        coord = GovernanceIntelligenceCoordinator()
        req = GovernanceReviewRequest(
            goal="Normal operation",
            action="execute_step",
            caller_id="system_admin",
            caller_authority=AuthorityLevel.ADMIN,
        )
        res = await coord.evaluate_review(req)

        assert res.decision == GovernanceDecisionType.DENIED
        assert res.state == GovernanceState.ABORTED
        assert "Emergency Stop is active" in res.explanation
        assert any("EMERGENCY_STOP" in e for e in res.evidence)
    finally:
        es.reset_emergency_stop(is_human_user=True)


@pytest.mark.asyncio
async def test_coordinator_high_uncertainty_requires_human_oversight() -> None:
    """High uncertainty with irreversible action triggers REQUIRES_HUMAN and generates handoff packet."""
    coord, req = create_fixture_high_uncertainty_irreversible()
    res = await coord.evaluate_review(req)

    assert res.decision == GovernanceDecisionType.REQUIRES_HUMAN
    assert res.state == GovernanceState.REQUIRES_HUMAN
    assert res.requires_human is True
    assert res.human_handoff_packet is not None
    assert res.human_handoff_packet["review_id"] == req.review_id
    assert res.human_handoff_packet["action"] == req.action
    assert req.review_id in [r.review_id for r in coord.list_pending_human_reviews()]


@pytest.mark.asyncio
async def test_coordinator_control_weakening_denied() -> None:
    """Control weakening signature triggers CRITICAL escalation and immediate DENIED."""
    coord, req = create_fixture_control_weakening()
    res = await coord.evaluate_review(req)

    assert res.decision == GovernanceDecisionType.DENIED
    assert res.escalation_report.is_escalation_attempt is True
    assert res.escalation_report.severity == "CRITICAL"
    assert "DENIED" in res.explanation


@pytest.mark.asyncio
async def test_coordinator_multi_tier_conflict_resolution() -> None:
    """Policy hierarchy resolves conflict: SYSTEM policy strictly overrides WORKFLOW policy."""
    coord, req = create_fixture_multi_tier_conflict()
    res = await coord.evaluate_review(req)

    assert res.decision == GovernanceDecisionType.DENIED
    assert res.policy_tier_applied == PolicyTier.SYSTEM
    assert any("POLICY_CONFLICT_RESOLVED" in e for e in res.evidence)


@pytest.mark.asyncio
async def test_coordinator_human_resolution_non_self_approval() -> None:
    """AI agent cannot self-approve; human reviewer can approve or deny."""
    coord, req = create_fixture_high_uncertainty_irreversible()
    review = await coord.evaluate_review(req)
    rev_id = review.review_id

    # 1. AI agent attempt to self-approve must be rejected
    for forbidden_caller in ["kairo", "autonomous_agent", "default_agent", "self"]:
        with pytest.raises(ValueError) as exc:
            coord.resolve_human_review(
                review_id=rev_id,
                reviewer_id=forbidden_caller,
                approved=True,
            )
        assert "Autonomous agent cannot self-approve" in str(exc.value)

    # 2. Legitimate human operator approves
    approved_res = coord.resolve_human_review(
        review_id=rev_id,
        reviewer_id="human_security_lead_42",
        approved=True,
        rationale="Reviewed partition migration; verified backups.",
    )
    assert approved_res.state == GovernanceState.EXECUTABLE
    assert approved_res.decision == GovernanceDecisionType.ALLOWED
    assert approved_res.requires_human is False
    assert "Approved by human reviewer" in approved_res.explanation
    assert rev_id not in [r.review_id for r in coord.list_pending_human_reviews()]


def test_governance_db_models_instantiation() -> None:
    """Verify SQLAlchemy models can be instantiated without errors."""
    c_rec = ConstitutionRecordModel(
        constitution_id="const_1",
        name="Kairo Constitution",
        version="1.0.0",
        is_active=True,
    )
    assert c_rec.constitution_id == "const_1"

    p_rec = ConstitutionalPrincipleModel(
        principle_id="prn_1",
        constitution_id="const_1",
        name="SAFETY",
        strictness="MANDATORY",
        weight=1.0,
    )
    assert p_rec.name == "SAFETY"

    g_rec = AuthorityGrantModel(
        grant_id="grant_1",
        subject_id="agent_1",
        authority_level="PROJECT",
        allowed_scopes=["p1"],
        allowed_actions=["a1"],
    )
    assert g_rec.authority_level == "PROJECT"

    d_rec = GovernanceDecisionRecordModel(
        review_id="rev_1",
        decision="ALLOWED",
        state="EXECUTABLE",
        caller_id="agent_1",
        action="read_file",
    )
    assert d_rec.decision == "ALLOWED"

    esc_rec = AuthorityEscalationIncidentModel(
        incident_id="esc_1",
        caller_id="agent_adversary",
        action="tamper_security",
        bypass_technique="CONTROL_WEAKENING",
        severity="CRITICAL",
        rationale="Tampering attempt.",
    )
    assert esc_rec.severity == "CRITICAL"

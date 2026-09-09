"""Tests for Self-Correction Engine, Oscillation Guard, and Safety Boundaries (Task 42)."""

import pytest
from app.verification.claims import Claim, ClaimType, TruthStatus
from app.verification.evidence import Evidence, EvidenceType
from app.verification.self_correction import Correction, SelfCorrectionEngine


def test_self_correction_successful_flow_and_admission():
    """Model claims 'CI is fixed', tests fail, self-correction applies with clear admission (Spec 81, 82, 167)."""
    engine = SelfCorrectionEngine()
    original_claim = Claim(
        claim_id="clm-ci-1",
        statement="CI build is passing",
        subject="ci_build",
        truth_status=TruthStatus.CONTRADICTED,
    )

    ev_test_fail = Evidence(
        evidence_id="ev-fail-1",
        source_type=EvidenceType.TEST_RESULT,
        source_reference="pytest_runner",
        observation={"exit_code": 1, "failed": 4},
    )

    correction = engine.attempt_correction(
        original_claim=original_claim,
        corrected_statement="CI build is failing with 4 test errors",
        supporting_evidence=[ev_test_fail],
        reason="Test runner execution showed 4 failures.",
    )

    assert correction.status == "APPLIED"
    assert correction.original_claim_id == "clm-ci-1"
    assert "I was wrong about CI build is passing" in correction.user_admission
    assert "Verification shows CI build is failing with 4 test errors" in correction.user_admission


def test_oscillation_guard_prevents_infinite_flipping():
    """Oscillation A -> B -> A -> B must be detected and escalated to UNRESOLVED_CONFLICT (Spec 137, 168)."""
    engine = SelfCorrectionEngine()
    claim = Claim(
        claim_id="clm-osc",
        statement="Status is ACTIVE",
        subject="cluster_node",
    )
    ev = Evidence(
        evidence_id="ev-1",
        source_type=EvidenceType.DIRECT_OBSERVATION,
        source_reference="probe",
        observation={},
    )

    # Transition 1: ACTIVE -> INACTIVE
    c1 = engine.attempt_correction(claim, "Status is INACTIVE", [ev], "Heartbeat missed")
    assert c1.status == "APPLIED"

    # Transition 2: INACTIVE -> ACTIVE
    c2 = engine.attempt_correction(claim, "Status is ACTIVE", [ev], "Heartbeat received")
    assert c2.status == "APPLIED"

    # Transition 3: ACTIVE -> INACTIVE (oscillating flip back)
    c3 = engine.attempt_correction(claim, "Status is INACTIVE", [ev], "Heartbeat missed again")
    # Oscillation detected!
    assert c3.status == "ESCALATED"
    assert "Oscillation detected" in c3.reason
    assert c3.metadata.get("unresolved_conflict") is True


def test_safety_boundary_blocks_policy_and_security_tampering():
    """Self-correction must NEVER silently alter security or policy controls (Spec 141)."""
    engine = SelfCorrectionEngine()
    security_claim = Claim(
        claim_id="clm-sec-1",
        statement="Root access denied for external role",
        subject="security_policy",
        scope={"domain": "security"},
    )

    correction = engine.attempt_correction(
        original_claim=security_claim,
        corrected_statement="Root access granted for external role",
        supporting_evidence=[],
        reason="Requested bypass",
    )

    assert correction.status == "BLOCKED_BY_BOUNDARY"
    assert "cannot alter security policy or controls" in correction.reason


def test_max_corrections_attempt_limit():
    """Engine must bound automatic correction attempts (Spec 136)."""
    engine = SelfCorrectionEngine(max_corrections_per_target=2)
    claim = Claim(
        claim_id="clm-bound",
        statement="Attempt 0",
        subject="bounded_worker",
    )
    ev = Evidence(
        evidence_id="ev-b",
        source_type=EvidenceType.DIRECT_OBSERVATION,
        source_reference="p",
        observation={},
    )

    # 4 transitions allowed under limit of 2 * 2
    for i in range(1, 5):
        corr = engine.attempt_correction(claim, f"Attempt {i}", [ev], f"Reason {i}")
        assert corr.status == "APPLIED"

    # 5th transition exceeds limit
    corr_limit = engine.attempt_correction(claim, "Attempt 5", [ev], "Reason 5")
    assert corr_limit.status == "ESCALATED"
    assert "Maximum correction attempts" in corr_limit.reason

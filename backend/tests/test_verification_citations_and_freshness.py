"""Tests for Citations, Fact Validation, Test Rigor, and Freshness (Task 42)."""

from datetime import datetime, timedelta, timezone
import pytest
from app.verification.claims import Claim, TruthStatus
from app.verification.confidence import ConfidenceCalibrator, ConfidenceLevel, UncertaintyState
from app.verification.evaluators import CitationValidator, TestQualityEvaluator
from app.verification.evidence import Evidence, EvidenceType
from app.verification.freshness import FreshnessTracker


def test_citation_validator_valid_and_excerpt():
    """Valid citation with supporting excerpt passes validation (Spec 92)."""
    validator = CitationValidator()
    validator.register_source(
        source_ref="doc://architecture/v2",
        content="The Kairo truth engine enforces anti-self-attestation and read-only verification safety.",
    )

    result = validator.validate_citation(
        claim_statement="Kairo enforces anti-self-attestation",
        citation_ref="doc://architecture/v2",
        claimed_excerpt="anti-self-attestation and read-only verification safety",
    )
    assert result.is_valid is True
    assert result.exists is True
    assert result.supports_claim is True


def test_citation_validator_hallucinated_source_rejection():
    """Hallucinated or non-existent citation sources must be rejected (Spec 92, 161)."""
    validator = CitationValidator()
    result = validator.validate_citation(
        claim_statement="Quantum computing speedup achieved",
        citation_ref="doc://fabricated/fake_source_123",
    )
    assert result.is_valid is False
    assert result.exists is False
    assert "does not exist" in result.rejection_reason


def test_citation_validator_excerpt_mismatch():
    """Claiming an excerpt not found in source text must be rejected as fabricated (Spec 93, 160)."""
    validator = CitationValidator()
    validator.register_source(
        source_ref="doc://news/release",
        content="Version 2.0 has been released with bug fixes.",
    )

    result = validator.validate_citation(
        claim_statement="Version 2.0",
        citation_ref="doc://news/release",
        claimed_excerpt="revolutionary quantum core breakthrough",
    )
    assert result.is_valid is False
    assert result.supports_claim is False
    assert "fabricated citation" in result.rejection_reason


def test_test_quality_evaluator_rejects_always_pass():
    """Detects and rejects weak or tautological tests like assert True (Spec 128)."""
    evaluator = TestQualityEvaluator()

    # Good test
    good_code = """
    def test_add():
        res = calc.add(2, 3)
        assert res == 5
    """
    good_report = evaluator.evaluate_test_code("test_add", good_code)
    assert good_report.is_rigorous is True

    # Bad test: assert True
    tautology_code = """
    def test_mocked_always_pass():
        # placeholder
        assert True
    """
    bad_report = evaluator.evaluate_test_code("test_tautology", tautology_code)
    assert bad_report.is_rigorous is False
    assert bad_report.is_always_pass is True

    # Bad test: no assertions
    no_assert_code = """
    def test_nothing():
        x = 10
        print(x)
    """
    empty_report = evaluator.evaluate_test_code("test_nothing", no_assert_code)
    assert empty_report.is_rigorous is False
    assert empty_report.has_assertions is False


def test_freshness_tracker_stale_data_rejection():
    """Old observations must not be used to assert current state (Spec 37, 159)."""
    tracker = FreshnessTracker(custom_windows={"server_health": 60})
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(seconds=120)

    old_ev = Evidence(
        evidence_id="ev-stale-srv",
        source_type=EvidenceType.HEALTH_CHECK,
        source_reference="health_probe",
        observation={"status": "healthy"},
        observed_at=old_time,
    )

    eval_result = tracker.evaluate_evidence(old_ev, as_of=now, max_age_seconds=60)
    assert eval_result.is_fresh is False
    assert eval_result.status in ["STALE", "EXPIRED"]


def test_claim_automatic_degradation_to_stale():
    """Previously verified claim transitions to STALE when freshness window lapses (Spec 38)."""
    tracker = FreshnessTracker()
    now = datetime.now(timezone.utc)
    old_claim = Claim(
        claim_id="clm-srv-health",
        statement="Server healthy",
        truth_status=TruthStatus.VERIFIED,
        observed_at=now - timedelta(seconds=600),
        scope={"domain": "server_health"},
    )

    tracker.mark_stale_if_expired(old_claim)
    assert old_claim.truth_status == TruthStatus.STALE


def test_confidence_calibration_multi_factor():
    """Confidence calibration computes factors and uncertainty states (Spec 84, 85, 89)."""
    calibrator = ConfidenceCalibrator()
    claim = Claim(
        claim_id="clm-cal",
        statement="API functional",
        truth_status=TruthStatus.VERIFIED,
    )
    ev = Evidence(
        evidence_id="ev-c1",
        source_type=EvidenceType.DIRECT_OBSERVATION,
        source_reference="sys_probe",
        observation={"status": "ok"},
    )

    report = calibrator.calibrate(claim, [ev], has_contradictions=False, verification_passed=True)
    assert report.level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
    assert report.uncertainty_state == UncertaintyState.KNOWN
    assert report.score > 0.6

    # Test contradiction penalty
    report_contra = calibrator.calibrate(claim, [ev], has_contradictions=True, verification_passed=True)
    assert report_contra.level == ConfidenceLevel.LOW
    assert report_contra.uncertainty_state == UncertaintyState.CONTRADICTORY

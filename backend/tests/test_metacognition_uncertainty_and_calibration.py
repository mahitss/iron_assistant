"""Unit tests for uncertainty modeling, multi-agent aggregation, confidence scoring, and calibration."""

from app.metacognition.calibration import ConfidenceCalibrator
from app.metacognition.confidence import ConfidenceEngine
from app.metacognition.schemas import UncertaintyType
from app.metacognition.uncertainty import UncertaintyModel


def test_uncertainty_recording_and_resolution():
    model = UncertaintyModel()

    # Invariant 24 & 25: Record uncertainty types
    unc = model.record_uncertainty(
        subject="User timezone",
        uncertainty_type=UncertaintyType.MISSING_DATA,
        confidence=0.5,
        evidence=[{"source": "profile", "note": "field is null"}],
        impact="MEDIUM",
    )

    assert unc.subject == "User timezone"
    assert unc.uncertainty_type == UncertaintyType.MISSING_DATA
    assert unc.resolution_status == "UNRESOLVED"
    assert unc.confidence <= 0.7  # Invariant 31: Cannot be false certainty

    # Query uncertainties
    results = model.get_uncertainties(subject="user timezone")
    assert len(results) == 1

    # Invariant 31: Resolve uncertainty with evidence
    model.resolve_uncertainty("User timezone", resolution_evidence="User selected Europe/Paris in preferences")
    assert results[0].resolution_status == "RESOLVED"
    assert len(results[0].evidence) == 2


def test_multi_agent_uncertainty_aggregation():
    model = UncertaintyModel()

    # Invariant 101 & 102: Do not assume agent agreement means truth; track disagreement
    agent_opinions = [
        {"agent": "coder_1", "answer": "Use PostgreSQL"},
        {"agent": "coder_2", "answer": "Use SQLite"},
        {"agent": "reviewer", "answer": "Use PostgreSQL"},
    ]

    res = model.aggregate_agent_uncertainty("Database choice", agent_opinions)
    assert res["has_disagreement"] is True
    assert res["distinct_answers_count"] == 2
    assert res["aggregate_confidence"] < 0.6  # High disagreement dampens confidence

    # Check uncertainty record was automatically registered
    uncs = model.get_uncertainties("database choice")
    assert len(uncs) == 1
    assert uncs[0].uncertainty_type == UncertaintyType.CONFLICTING_DATA


def test_confidence_engine_calculation():
    engine = ConfidenceEngine(calibration_factor=1.0)

    # Invariant 26: Confidence must never be arbitrary
    # Authoritative source + verified -> very high confidence
    conf_authoritative = engine.calculate_confidence(
        source_tier="SYSTEM_AUTHORITATIVE",
        is_verified=True,
        evidence_count=3,
        has_contradictions=False,
    )
    assert conf_authoritative >= 0.95

    # Web external + unverified + contradictions -> low confidence
    conf_unverified = engine.calculate_confidence(
        source_tier="WEB_EXTERNAL",
        is_verified=False,
        evidence_count=1,
        has_contradictions=True,
    )
    assert conf_unverified <= 0.35


def test_confidence_calibrator_overconfidence_and_underconfidence():
    calibrator = ConfidenceCalibrator()

    # Invariant 28: Overconfidence = High confidence (>= 0.85) but failed
    for i in range(4):
        calibrator.record_outcome(claimed_confidence=0.95, was_successful=False, task_id=f"fail_{i}")

    assert calibrator.overconfidence_events == 4

    # Invariant 29: Underconfidence = Low confidence (<= 0.50) but succeeded
    for i in range(3):
        calibrator.record_outcome(claimed_confidence=0.30, was_successful=True, task_id=f"success_{i}")

    assert calibrator.underconfidence_events == 3

    # Invariant 30: Confidence adjustment factor calculation
    metrics = calibrator.get_metrics()
    assert metrics["total_samples"] == 7
    assert metrics["overconfidence_events"] == 4
    assert metrics["underconfidence_events"] == 3
    # Overconfidence should cause factor to drop below 1.0
    factor = calibrator.compute_calibration_factor()
    assert factor < 1.0

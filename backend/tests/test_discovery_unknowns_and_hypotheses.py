"""Unit tests for Unknown Detection and Competing Hypothesis Management (Task 72)."""

import pytest

from app.discovery.hypotheses import HypothesisEngine
from app.discovery.schemas import EpistemicCategory
from app.discovery.unknowns import UnknownDetector


def test_epistemic_gap_detection():
    """Verifies clear separation of epistemic categories."""
    detector = UnknownDetector()
    gaps = detector.detect_epistemic_gaps(
        knowns=["Deployment occurred at 14:00 UTC"],
        unknowns=["Whether deployment caused latency increase"],
        uncertains=["Database pool saturation probability"],
        conflicting=["Metric agent reports 150ms while ingress reports 450ms"],
        unverified=["Cache warm-up finished before cutover"],
    )

    assert len(gaps[EpistemicCategory.KNOWN]) == 1
    assert len(gaps[EpistemicCategory.UNKNOWN]) == 1
    assert len(gaps[EpistemicCategory.UNCERTAIN]) == 1
    assert len(gaps[EpistemicCategory.CONFLICTING]) == 1
    assert len(gaps[EpistemicCategory.UNVERIFIED]) == 1


def test_unknown_investigation_warrant_filter():
    """Enforces strict principle: Do NOT turn every unknown into an experiment."""
    detector = UnknownDetector(min_importance=0.6, min_uncertainty=0.5)

    # High importance, high uncertainty, decision-relevant -> WARRANTED
    assert detector.evaluate_investigation_warrant(
        candidate_question="Did change X cause production latency regression?",
        importance=0.9,
        uncertainty=0.8,
        decision_relevance=True,
    )

    # Low importance -> NOT warranted
    assert not detector.evaluate_investigation_warrant(
        candidate_question="What was the exact font color on debug log?",
        importance=0.2,
        uncertainty=0.9,
        decision_relevance=True,
    )

    # Not decision-relevant -> NOT warranted
    assert not detector.evaluate_investigation_warrant(
        candidate_question="Is the internal random seed even or odd?",
        importance=0.8,
        uncertainty=0.9,
        decision_relevance=False,
    )


def test_hypotheses_require_falsification_criteria():
    """Scientific integrity invariant: Hypotheses must define Popperian falsification criteria."""
    engine = HypothesisEngine()

    # Missing falsification criteria must raise ValueError
    with pytest.raises(ValueError, match="at least one explicit falsification criterion"):
        engine.create_hypothesis(
            description="Configuration change caused latency regression",
            falsification_criteria=[],
        )

    # Valid hypothesis
    hyp = engine.create_hypothesis(
        description="Configuration change caused latency regression",
        falsification_criteria=["Latency increase began prior to configuration change timestamp"],
        plausibility=0.8,
        testability=0.9,
    )
    assert hyp.hypothesis_id.startswith("hyp_")
    assert len(hyp.falsification_criteria) == 1
    assert hyp.status == "CANDIDATE"


def test_competing_hypotheses_generation_and_ranking():
    """Verifies generation of multiple competing explanations and ranking without confidence inflation."""
    engine = HypothesisEngine()

    candidates = [
        {
            "description": "H1: Configuration timeout caused connection pileup",
            "falsification_criteria": ["Connection pool depth remained constant"],
            "plausibility": 0.85,
            "testability": 0.90,
            "supporting_evidence": ["Error logs indicate timeout cascades"],
        },
        {
            "description": "H2: External network transit degradation",
            "falsification_criteria": ["Cross-region ping latency normal"],
            "plausibility": 0.60,
            "testability": 0.80,
            "contradicting_evidence": ["Intra-cluster latency identical to external"],
        },
        {
            "description": "H3: Traffic spike overwhelmed gateway",
            "falsification_criteria": ["Request count matches baseline"],
            "plausibility": 0.40,
            "testability": 0.85,
            "contradicting_evidence": ["RPS flat during incident window"],
        },
    ]

    hypotheses = engine.generate_competing_hypotheses(
        question="Why did p95 latency spike?",
        candidate_explanations=candidates,
    )
    assert len(hypotheses) == 3

    # Rank hypotheses
    ranked = engine.rank_hypotheses(hypotheses)
    # H1 has high plausibility, high testability, supporting evidence and no contradicting evidence -> Rank 1
    assert ranked[0].description.startswith("H1")
    # Hypotheses with contradicting evidence should be ranked lower
    assert ranked[-1].description.startswith("H3") or ranked[-1].description.startswith("H2")


def test_hypotheses_deduplication():
    """Agent proposals with identical explanations are deduplicated."""
    engine = HypothesisEngine()

    h1 = engine.create_hypothesis(
        description="Database connection exhaustion",
        falsification_criteria=["Active connections < 50% max"],
    )
    h2 = engine.create_hypothesis(
        description="database connection exhaustion",  # Case variant
        falsification_criteria=["Active connections < 50% max"],
    )
    h3 = engine.create_hypothesis(
        description="Network routing misconfiguration",
        falsification_criteria=["Traceroute normal"],
    )

    deduped = engine.deduplicate_hypotheses([h1, h2, h3])
    assert len(deduped) == 2

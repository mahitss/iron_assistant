"""Unit tests for Hypothesis Generation, Popperian Falsification & Disproof (Task 71)."""

from app.reasoning.falsification import FalsificationEngine
from app.reasoning.hypotheses import HypothesisGenerator
from app.reasoning.schemas import (
    HypothesisStatus,
    ReasoningConfidence,
    ReasoningEvidence,
    ReasoningHypothesis,
)


def test_hypothesis_generation_with_falsification():
    """Verify hypothesis formulation generates plausible explanations and attached falsifiers."""
    hg = HypothesisGenerator()
    hyps = hg.generate_initial_hypotheses("Why did database connection count spike after release v2.4?")

    assert len(hyps) >= 2
    for h in hyps:
        assert h.status == HypothesisStatus.CANDIDATE
        assert len(h.description) > 5
        assert len(h.falsification_conditions) > 0


def test_falsification_refutation_on_temporal_anomaly():
    """Verify hypothesis is marked DISPROVEN if evidence triggers a falsifier (e.g. latency started before deployment)."""
    fe = FalsificationEngine()

    hyp = ReasoningHypothesis(
        description="Application deployment regression caused API slowdown",
        status=HypothesisStatus.CANDIDATE,
        confidence=ReasoningConfidence.MEDIUM,
    )
    fe.formulate_falsifiers(hyp)
    assert any("started prior" in cond.lower() for cond in hyp.falsification_conditions)

    # Empirical observation that disproves the deployment hypothesis
    evidence = ReasoningEvidence(
        source_type="log",
        source_id="monitor-01",
        content_summary="Anomaly and latency spike started prior to the deployment timestamp by 30 minutes.",
        trust_level="VERIFIED",
    )

    refuted = fe.test_evidence_against_falsifiers(hyp, evidence)

    assert refuted is True
    assert hyp.status == HypothesisStatus.DISPROVEN
    assert hyp.confidence == ReasoningConfidence.VERY_LOW
    assert evidence.evidence_id in hyp.contradicting_evidence_ids


def test_falsification_refutation_on_baseline_metrics():
    """Verify hypothesis is refuted if metrics remain completely at healthy baseline."""
    fe = FalsificationEngine()

    hyp = ReasoningHypothesis(
        description="Database query contention and lock timeouts",
        status=HypothesisStatus.CANDIDATE,
    )
    fe.formulate_falsifiers(hyp)

    evidence = ReasoningEvidence(
        source_type="telemetry",
        source_id="rds-metrics",
        content_summary="Database query execution times, connection pool, and CPU remain at normal baselines.",
    )

    refuted = fe.test_evidence_against_falsifiers(hyp, evidence)
    assert refuted is True
    assert hyp.status == HypothesisStatus.DISPROVEN


def test_information_gain_ranking():
    """Verify information gain prioritizes candidate hypotheses with high diagnostic value."""
    fe = FalsificationEngine()

    h1 = ReasoningHypothesis(description="Untested candidate", status=HypothesisStatus.CANDIDATE)
    h2 = ReasoningHypothesis(description="Already disproven", status=HypothesisStatus.DISPROVEN)
    h3 = ReasoningHypothesis(description="Supported", status=HypothesisStatus.SUPPORTED)

    ranked = fe.rank_by_information_gain([h1, h2, h3])
    # h1 (CANDIDATE) should have higher diagnostic priority than h2 (DISPROVEN)
    assert ranked[0][0].hypothesis_id == h1.hypothesis_id

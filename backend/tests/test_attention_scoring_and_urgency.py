"""Test suite for Attention Scoring, Independent Urgency, Importance, Risk, and Novelty (Task 70)."""

from datetime import UTC, datetime, timedelta

from app.attention.importance import ImportanceEvaluator
from app.attention.novelty import NoveltyDetector
from app.attention.risk import RiskEvaluator
from app.attention.schemas import AttentionScoreBreakdown, AttentionThreshold
from app.attention.scoring import AttentionScoringEngine
from app.attention.urgency import UrgencyEvaluator


def test_independent_urgency_vs_importance():
    """Urgency and Importance must be strictly decoupled dimensions."""
    # Case 1: Long-term architectural research: High Importance, Low Urgency
    imp_score, imp_tier, _ = ImportanceEvaluator.evaluate(
        mission_refs=["mission-arch-2026"],
        goal_refs=["goal-scalability"],
        strategic_value=0.9,
    )
    urg_score, urg_tier, _ = UrgencyEvaluator.evaluate(
        deadline=datetime.now(UTC) + timedelta(days=14),
        rate_of_change=0.0,
        escalation_probability=0.0,
    )
    assert imp_score >= 0.70
    assert imp_tier in ("HIGH", "CRITICAL")
    assert urg_score < 0.40
    assert urg_tier == "LOW"

    # Case 2: Meeting in 2 minutes: Low/Medium Importance, High Urgency (Spec Section 6)
    imp_score2, imp_tier2, _ = ImportanceEvaluator.evaluate(
        user_impact_level=0.3,
        strategic_value=0.2,
    )
    urg_score2, urg_tier2, _ = UrgencyEvaluator.evaluate(
        deadline=datetime.now(UTC) + timedelta(minutes=2),
        estimated_duration_sec=300,
    )
    assert imp_score2 < 0.45
    assert urg_score2 >= 0.70
    assert urg_tier2 in ("HIGH", "CRITICAL")


def test_urgency_deadline_gaming_defense():
    """Untrusted sources claiming imminent deadlines must be dampened to prevent deadline gaming."""
    deadline_imminent = datetime.now(UTC) + timedelta(minutes=1)

    # Trusted source: full deadline pressure
    urg_trusted, tier_trusted, breakdown_trusted = UrgencyEvaluator.evaluate(
        deadline=deadline_imminent,
        source_is_trusted=True,
    )
    assert breakdown_trusted["deadline_pressure"] >= 0.80

    # Untrusted source: deadline pressure is clamped
    urg_untrusted, tier_untrusted, breakdown_untrusted = UrgencyEvaluator.evaluate(
        deadline=deadline_imminent,
        source_is_trusted=False,
    )
    assert breakdown_untrusted["deadline_pressure"] <= 0.40
    assert urg_untrusted < urg_trusted


def test_risk_evaluation_uncertainty_is_not_danger():
    """High uncertainty increases investigation factor, but does not equate to confirmed danger."""
    # Low probability, high uncertainty
    risk_score, tier, breakdown = RiskEvaluator.evaluate(
        probability=0.1,
        potential_impact=0.4,
        uncertainty=0.9,
        security_sensitivity=0.2,
    )
    # Risk should remain moderate/low, not automatically critical
    assert risk_score < 0.50
    assert tier in ("LOW", "MEDIUM")
    assert breakdown["uncertainty_investigation_factor"] > 0.10


def test_novelty_and_change_magnitude():
    """A completely normal event should not consume excessive attention; significant changes increase magnitude."""
    # Baseline normal event: CPU = 45% (baseline mean 50, std 10)
    nov_normal, chg_normal, is_nov_normal, _ = NoveltyDetector.evaluate(
        observed_value=45.0,
        baseline_mean=50.0,
        baseline_std=10.0,
        historical_frequency=50,
    )
    assert nov_normal < 0.30
    assert is_nov_normal is False

    # Anomalous deviation: CPU = 98%
    nov_spike, chg_spike, is_nov_spike, _ = NoveltyDetector.evaluate(
        observed_value=98.0,
        baseline_mean=50.0,
        baseline_std=10.0,
        historical_frequency=5,
    )
    assert nov_spike > 0.60
    assert is_nov_spike is True

    # Critical change keys (schema, config, deployment)
    changes = {"config": {"pool_size": 200}, "database_schema": {"migration": "0050"}}
    _, chg_critical, _, _ = NoveltyDetector.evaluate(changes=changes)
    assert chg_critical >= 0.60


def test_composite_scoring_deterministic_and_explainable():
    """Attention scoring combines factors deterministically and exposes transparent explanation."""
    score, threshold, breakdown = AttentionScoringEngine.score(
        importance=0.9,
        urgency=0.85,
        risk=0.8,
        goal_alignment=0.75,
        deadline_pressure=0.8,
        dependency_impact=0.6,
        novelty=0.7,
        uncertainty=0.3,
        resource_cost=0.1,
        redundancy=0.0,
        staleness=0.0,
    )

    assert score >= 0.75
    assert threshold in (AttentionThreshold.HIGH, AttentionThreshold.CRITICAL)
    assert isinstance(breakdown, AttentionScoreBreakdown)
    assert len(breakdown.contributing_factors) >= 4
    assert "high importance" in breakdown.explanation
    assert "critical urgency" in breakdown.explanation
    assert "elevated risk" in breakdown.explanation


def test_scoring_penalties():
    """Resource cost, redundancy, and staleness properly penalize the composite attention score."""
    score_clean, _, _ = AttentionScoringEngine.score(
        importance=0.7,
        urgency=0.6,
        risk=0.5,
        resource_cost=0.0,
        redundancy=0.0,
        staleness=0.0,
    )

    score_penalized, _, breakdown = AttentionScoringEngine.score(
        importance=0.7,
        urgency=0.6,
        risk=0.5,
        resource_cost=0.9,
        redundancy=0.8,
        staleness=0.8,
    )

    assert score_penalized < score_clean
    assert breakdown.resource_cost_penalty > 0.05
    assert breakdown.redundancy_penalty > 0.05
    assert breakdown.staleness_penalty > 0.05

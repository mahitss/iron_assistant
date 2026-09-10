"""Tests for Pareto dominance, multi-objective trade-offs, and sensitivity analysis (Task 57)."""

from app.decision.ranking import RankingEngine
from app.decision.schemas import CandidateOption, Objective, ReversibilityLevel
from app.decision.scoring import OptionScorer
from app.decision.tradeoffs import TradeoffEngine


def test_pareto_dominance_identification():
    tradeoff_engine = TradeoffEngine()

    # Option Superior is strictly better on reliability and cheaper on cost than Option Inferior
    opt_superior = CandidateOption(
        option_id="opt_sup",
        name="Superior Option",
        metrics={"cost": 20.0, "reliability": 0.95},
    )
    opt_inferior = CandidateOption(
        option_id="opt_inf",
        name="Inferior Option",
        metrics={"cost": 40.0, "reliability": 0.80},
    )

    objectives = [
        Objective(name="COST", direction="MINIMIZE", weight=0.5),
        Objective(name="RELIABILITY", direction="MAXIMIZE", weight=0.5),
    ]

    pareto_ids, dominated_ids = tradeoff_engine.find_pareto_options(
        options=[opt_superior, opt_inferior],
        objectives=objectives,
    )

    assert "opt_sup" in pareto_ids
    assert "opt_inf" in dominated_ids


def test_tradeoff_tension_explanation():
    tradeoff_engine = TradeoffEngine()

    opt_fast_expensive = CandidateOption(
        name="Fast Cloud Cluster",
        metrics={"cost": 90.0, "latency": 12.0, "reliability": 0.95},
    )
    opt_cheap_slower = CandidateOption(
        name="Single Edge Server",
        metrics={"cost": 15.0, "latency": 85.0, "reliability": 0.85},
    )

    tradeoffs = tradeoff_engine.explain_tradeoffs(opt_fast_expensive, opt_cheap_slower)
    assert len(tradeoffs) >= 1
    # Check that cost vs latency tension is explicitly articulated
    cost_lat_tradeoff = next((t for t in tradeoffs if "Latency" in t.dimension_b or "Cost" in t.dimension_a), None)
    assert cost_lat_tradeoff is not None
    assert cost_lat_tradeoff.tension_level == "HIGH"
    assert "lower latency" in cost_lat_tradeoff.explanation


def test_ranking_determinism_and_sensitivity():
    ranking_engine = RankingEngine()
    scorer = OptionScorer()

    opt_a = CandidateOption(
        option_id="opt_a",
        name="Reliable Choice",
        reversibility=ReversibilityLevel.REVERSIBLE,
        metrics={"reliability": 0.98, "cost": 25.0, "risk": 0.05},
    )
    opt_b = CandidateOption(
        option_id="opt_b",
        name="Frugal Choice",
        reversibility=ReversibilityLevel.REVERSIBLE,
        metrics={"reliability": 0.65, "cost": 10.0, "risk": 0.15},
    )

    objectives = [
        Objective(objective_id="obj_rel", name="RELIABILITY", direction="MAXIMIZE", weight=0.7),
        Objective(objective_id="obj_cost", name="COST", direction="MINIMIZE", weight=0.3),
    ]

    evals = scorer.score_options([opt_a, opt_b], objectives)
    ranking = ranking_engine.rank_options(
        options=[opt_a, opt_b],
        evaluations=evals,
        tradeoffs=[],
        dominated_option_ids=[],
        confidence=0.9,
        objectives=objectives,
    )

    # With 70% weight on reliability, opt_a should win
    assert ranking.recommended_option_id == "opt_a"
    assert ranking.ranked_options[0].option_id == "opt_a"

    # Sensitivity analysis should note switching conditions if cost becomes prioritized
    sensitivity = ranking.sensitivity_analysis
    assert "switching_thresholds" in sensitivity
    assert len(sensitivity["switching_thresholds"]) > 0

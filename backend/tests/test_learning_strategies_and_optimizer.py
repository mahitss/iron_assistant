"""Tests for Strategy Models, Scopes, Multi-Factor Ranking, and Calibration (Task 43)."""

import pytest
from app.learning.calibration import ConfidenceCalibrator
from app.learning.optimizer import StrategyOptimizer
from app.learning.provenance import StrategyProvenanceRecord
from app.learning.strategies import Strategy, StrategyStatus


def test_strategy_lifecycle_statuses():
    """All 6 required strategy lifecycle statuses must be supported."""
    expected_statuses = [
        "CANDIDATE",
        "EXPERIMENTAL",
        "ACTIVE",
        "DEPRECATED",
        "BLOCKED",
        "ROLLED_BACK",
    ]
    for s in expected_statuses:
        assert hasattr(StrategyStatus, s)


def test_strategy_incremental_execution_metrics():
    """Strategy moving averages update correctly upon new execution outcomes."""
    strat = Strategy(
        strategy_id="strat-test-run",
        domain="testing",
        description="Run pytest with parallel threads",
        status=StrategyStatus.CANDIDATE,
    )
    assert strat.sample_size == 0
    assert strat.success_rate == 0.0

    # 1st run: success and verified
    strat.record_execution(was_successful=True, was_verified=True, duration_ms=200.0, cost=0.01)
    assert strat.sample_size == 1
    assert strat.success_rate == 1.0
    assert strat.verification_rate == 1.0
    assert strat.latency_ms == 200.0
    assert strat.cost == 0.01

    # 2nd run: failure and unverified
    strat.record_execution(was_successful=False, was_verified=False, duration_ms=400.0, cost=0.03)
    assert strat.sample_size == 2
    assert strat.success_rate == 0.5
    assert strat.verification_rate == 0.5
    assert strat.latency_ms == 300.0
    assert strat.cost == 0.02


def test_strategy_domain_scoping_no_global_generalization():
    """Strategies are strictly scoped to domains; a coding strategy does not rank for database migration (Spec 15, 16)."""
    optimizer = StrategyOptimizer()
    
    strat_coding = Strategy(
        strategy_id="strat-code-opt",
        domain="coding",
        description="AST rewriting",
        verification_rate=0.95,
        success_rate=0.92,
        sample_size=20,
    )
    strat_db = Strategy(
        strategy_id="strat-db-opt",
        domain="database",
        description="Safe transactional rollback migration",
        verification_rate=0.88,
        success_rate=0.85,
        sample_size=15,
    )

    all_strats = [strat_coding, strat_db]

    # Query coding domain only
    ranked_coding = optimizer.rank_strategies(all_strats, domain="coding")
    assert len(ranked_coding) == 1
    assert ranked_coding[0].strategy.strategy_id == "strat-code-opt"

    # Query database domain only
    ranked_db = optimizer.rank_strategies(all_strats, domain="database")
    assert len(ranked_db) == 1
    assert ranked_db[0].strategy.strategy_id == "strat-db-opt"


def test_optimizer_deterministic_ranking_verified_vs_fast():
    """Verified correctness must strictly outweigh raw speed gains (Spec 62, 64, 65)."""
    optimizer = StrategyOptimizer()

    strat_verified_safe = Strategy(
        strategy_id="strat-safe",
        domain="deployment",
        description="Staged deployment with health verification probe",
        verification_rate=0.98,
        success_rate=0.96,
        latency_ms=2500.0,
        sample_size=30,
        confidence="HIGH",
    )
    strat_fast_unverified = Strategy(
        strategy_id="strat-fast",
        domain="deployment",
        description="Fire-and-forget direct shell execution",
        verification_rate=0.20,
        success_rate=0.60,
        latency_ms=150.0,  # very fast, but low verification
        sample_size=30,
        confidence="LOW",
    )

    ranked = optimizer.rank_strategies([strat_verified_safe, strat_fast_unverified], domain="deployment")
    assert ranked[0].strategy.strategy_id == "strat-safe"
    assert ranked[0].rank_score > ranked[1].rank_score


def test_optimizer_small_sample_warning():
    """Candidate strategies with tiny samples must include an explicit warning (Spec 142)."""
    optimizer = StrategyOptimizer()

    strat_tiny = Strategy(
        strategy_id="strat-tiny",
        domain="coding",
        description="Experimental compiler flags",
        verification_rate=1.0,
        success_rate=1.0,
        sample_size=3,
        confidence="LOW",
    )
    strat_established = Strategy(
        strategy_id="strat-estab",
        domain="coding",
        description="Standard build flags",
        verification_rate=0.95,
        success_rate=0.94,
        sample_size=25,
        confidence="HIGH",
    )

    ranked = optimizer.rank_strategies([strat_tiny, strat_established], domain="coding")
    ranked_tiny = next(r for r in ranked if r.strategy.strategy_id == "strat-tiny")
    assert ranked_tiny.small_sample_warning is not None
    assert "Evidence is limited to 3" in ranked_tiny.small_sample_warning


def test_confidence_calibration_wilson_score():
    """Calibrator calculates Wilson score interval and rejects false precision on tiny samples (Spec 38, 186, 187)."""
    # 2 successes out of 2 is 100% point estimate, but small sample gives LOW tier and wide margin
    calib_small = ConfidenceCalibrator.calibrate(sample_size=2, successes=2)
    assert calib_small.point_estimate == 1.0
    assert calib_small.tier == "LOW"
    assert calib_small.has_statistical_significance is False
    assert calib_small.lower_bound < 0.60

    # 48 successes out of 50 is statistically significant with HIGH tier and tight bound
    calib_large = ConfidenceCalibrator.calibrate(sample_size=50, successes=48)
    assert calib_large.point_estimate == 0.96
    assert calib_large.tier == "HIGH"
    assert calib_large.has_statistical_significance is True
    assert calib_large.lower_bound >= 0.85


def test_strategy_provenance_tracking():
    """Strategy provenance record traces experiences and evaluation decisions (Spec 18)."""
    prov = StrategyProvenanceRecord(
        strategy_id="strat-prov-01",
        version=1,
        derived_from_experiences=["exp-01", "exp-02", "exp-03"],
        validation_experiment_id="exp-val-99",
        approver="kairo_learning_evaluator",
        rationale="Passed canary evaluation and security benchmarks",
    )
    assert prov.strategy_id == "strat-prov-01"
    assert len(prov.derived_from_experiences) == 3
    d = prov.to_dict()
    assert d["approver"] == "kairo_learning_evaluator"
    assert d["validation_experiment_id"] == "exp-val-99"

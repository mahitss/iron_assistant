"""Tests for Canary Experiments, Controlled Promotion, and Safe Rollback (Task 43)."""

import pytest
from app.learning.experimentation import Experiment, ExperimentStatus
from app.learning.promotion import StrategyPromoter
from app.learning.rollback import StrategyRollbacker
from app.learning.strategies import Strategy, StrategyStatus


def test_experiment_lifecycle_and_ab_trial():
    """Canary experiment lifecycle tracks baseline vs candidate across arms (Spec 44, 48)."""
    exp = Experiment(
        name="Linter Speed vs Accuracy Trial",
        domain="coding",
        baseline_strategy_id="strat-ast-linter",
        candidate_strategy_id="strat-fast-regex-linter",
        target_sample_size=4,
    )
    assert exp.status == ExperimentStatus.PLANNED
    exp.start()
    assert exp.status == ExperimentStatus.RUNNING

    # 2 baseline trials (both pass and verified)
    exp.record_trial(arm="baseline", success=True, verified=True, latency_ms=400.0, cost=0.01)
    exp.record_trial(arm="baseline", success=True, verified=True, latency_ms=420.0, cost=0.01)

    # 2 candidate trials (both fast, but 1 failed verification)
    exp.record_trial(arm="candidate", success=True, verified=True, latency_ms=50.0, cost=0.001)
    exp.record_trial(arm="candidate", success=True, verified=False, latency_ms=60.0, cost=0.001)

    assert exp.current_sample_size == 4
    assert exp.status == ExperimentStatus.COMPLETED

    comp = exp.get_comparison()
    assert comp["baseline_verification_rate"] == 1.0
    assert comp["candidate_verification_rate"] == 0.5
    assert comp["has_regression"] is True
    assert comp["is_candidate_superior"] is False


def test_strategy_promotion_sample_size_gating():
    """Candidate strategy must not be promoted without sufficient empirical samples (Spec 50, 185)."""
    promoter = StrategyPromoter(min_sample_size=10, min_verification_rate=0.80)

    strat_tiny = Strategy(
        strategy_id="strat-few-runs",
        domain="research",
        description="Fast retrieval",
        status=StrategyStatus.CANDIDATE,
        sample_size=4,  # Under 10
        verification_rate=1.0,
        success_rate=1.0,
    )

    can, reason = promoter.can_promote(strat_tiny)
    assert can is False
    assert "Insufficient sample size" in reason


def test_strategy_promotion_verification_rate_floor():
    """Candidate strategy must meet minimum verification floor to be promoted (Spec 51, 62)."""
    promoter = StrategyPromoter(min_sample_size=10, min_verification_rate=0.80)

    strat_unverified = Strategy(
        strategy_id="strat-low-verif",
        domain="coding",
        description="Optimistic file patching",
        status=StrategyStatus.CANDIDATE,
        sample_size=20,
        verification_rate=0.65,  # Floor is 0.80
        success_rate=0.90,
    )

    can, reason = promoter.can_promote(strat_unverified)
    assert can is False
    assert "Verification rate too low" in reason


def test_strategy_promotion_success_and_audit():
    """Candidate satisfying all thresholds promotes to ACTIVE with immutable audit record (Spec 51, 135)."""
    promoter = StrategyPromoter(min_sample_size=10, min_verification_rate=0.80, max_failure_rate=0.15)

    strat_valid = Strategy(
        strategy_id="strat-production-candidate",
        domain="deployment",
        description="Canary deploy with automated rollback probe",
        status=StrategyStatus.CANDIDATE,
        sample_size=25,
        verification_rate=0.92,
        success_rate=0.96,
        failure_rate=0.04,
    )

    ok, msg, audit_rec = promoter.promote(
        strategy=strat_valid,
        approved_by="lead_devops_officer",
        reason="Exceeded 20 trials with 92% verification and zero critical incidents.",
    )

    assert ok is True
    assert strat_valid.status == StrategyStatus.ACTIVE
    assert audit_rec is not None
    assert audit_rec.from_status == StrategyStatus.CANDIDATE
    assert audit_rec.to_status == StrategyStatus.ACTIVE
    assert audit_rec.approved_by == "lead_devops_officer"
    assert len(promoter.get_history()) == 1


def test_strategy_rollback_on_regression():
    """Strategy rollbacker detects verification drops and demotes strategy to ROLLED_BACK (Spec 54, 55, 118)."""
    rollbacker = StrategyRollbacker(min_verification_floor=0.70, max_failure_ceiling=0.25)

    strat_degraded = Strategy(
        strategy_id="strat-prod-failing",
        domain="coding",
        description="Parallel test executor",
        status=StrategyStatus.ACTIVE,
        sample_size=15,
        verification_rate=0.55,  # Dropped below 0.70 floor
        failure_rate=0.40,      # Exceeded 0.25 ceiling
    )

    has_regr, reason = rollbacker.check_regression(strat_degraded)
    assert has_regr is True
    assert "Verification rate" in reason

    ok, msg, rec = rollbacker.rollback(
        strategy=strat_degraded,
        rolled_back_by="automated_regression_guard",
        reason="Automated demotion following verification drop below floor.",
    )

    assert ok is True
    assert strat_degraded.status == StrategyStatus.ROLLED_BACK
    assert rec.prior_status == StrategyStatus.ACTIVE
    assert rec.rolled_back_by == "automated_regression_guard"
    assert len(rollbacker.get_records()) == 1

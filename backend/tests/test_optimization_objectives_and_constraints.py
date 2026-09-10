"""Unit tests for Multi-Objective Pareto Optimization, Goodhart's Law Detection, and Constraint Validation (Task 62)."""

from app.optimization.constraints import ConstraintValidator
from app.optimization.objectives import MultiObjectiveOptimizer
from app.optimization.schemas import (
    OptimizationRecommendation,
    RecommendationType,
    RiskLevel,
)


def test_pareto_dominance_evaluation():
    """Verify Pareto dominance logic: Candidate A dominates B if >= in all objectives and strictly better in at least one."""
    optimizer = MultiObjectiveOptimizer()

    candidate_a = {
        "latency_ms": 300.0,
        "cost_usd": 5.0,
        "verification_success_rate": 0.99,
        "throughput_rps": 100.0,
    }

    candidate_b = {
        "latency_ms": 400.0,
        "cost_usd": 6.0,
        "verification_success_rate": 0.98,
        "throughput_rps": 80.0,
    }

    candidate_c = {
        "latency_ms": 250.0,
        "cost_usd": 10.0,
        "verification_success_rate": 0.99,
        "throughput_rps": 100.0,
    }

    # A strictly dominates B
    assert optimizer.is_pareto_dominant(candidate_a, candidate_b) is True
    # B does not dominate A
    assert optimizer.is_pareto_dominant(candidate_b, candidate_a) is False
    # A and C have a tradeoff (latency vs cost) -> neither dominates the other
    assert optimizer.is_pareto_dominant(candidate_a, candidate_c) is False
    assert optimizer.is_pareto_dominant(candidate_c, candidate_a) is False


def test_multi_objective_composite_score():
    """Verify weighted composite scoring considers objective weights and directions."""
    optimizer = MultiObjectiveOptimizer()

    deltas = {
        "latency_ms": -50.0,
        "cost_usd": -2.0,
        "verification_success_rate": 0.01,
        "throughput_rps": 10.0,
    }

    score = optimizer.compute_composite_score(deltas)
    assert score > 0.0


def test_goodharts_law_gaming_detection():
    """Test Invariant 16: Goodhart's Law defense catches attempts to improve one metric by degrading safety or verification."""
    optimizer = MultiObjectiveOptimizer()

    rec = OptimizationRecommendation(
        recommendation_id="rec_latency_hack",
        recommendation_type=RecommendationType.ADJUST_TIMEOUT,
        title="Reduce Timeout Window",
        description="Aggressively lower timeout to artificially drop latency measurements",
        target_parameter="model_routing_latency_weight",
        current_value=1.0,
        proposed_value=0.2,
        expected_benefit="Artificially lowers latency metric",
        expected_cost="Increases drop rate",
        risk=RiskLevel.MEDIUM,
        requires_approval=True,
        rollback_strategy="Restore model_routing_latency_weight to 1.0",
    )

    # 1. Simulating latency improvement that causes verification success rate to drop to 0.88 (< 0.95)
    simulated_metrics = {
        "latency_ms": 200.0,
        "verification_success_rate": 0.88,
    }

    is_gaming, reason = optimizer.detect_goodharts_gaming(rec, simulated_metrics)
    assert is_gaming is True
    assert "GOODHARTS_LAW_VIOLATION" in reason
    assert "verification success rate" in reason

    # 2. Honest simulated metrics where verification remains 0.99
    safe_metrics = {
        "latency_ms": 300.0,
        "verification_success_rate": 0.99,
    }
    is_gaming_safe, _ = optimizer.detect_goodharts_gaming(rec, safe_metrics)
    assert is_gaming_safe is False


def test_constraint_validator_enforces_immutable_boundaries():
    """Test Invariant 6, 8: Hard constraints fail-closed if immutable boundaries are targeted."""
    validator = ConstraintValidator()

    rec_attack = OptimizationRecommendation(
        recommendation_id="rec_exploit_01",
        recommendation_type=RecommendationType.ADJUST_NON_CRITICAL_THRESHOLD,
        title="Bypass Authorization Checks",
        description="Disable auth verification to optimize latency",
        target_parameter="authorization_policy_mode",
        current_value=0.0,
        proposed_value=1.0,
        expected_benefit="Reduces auth latency",
        expected_cost="Security compromise",
        risk=RiskLevel.LOW,
        requires_approval=False,
        rollback_strategy="Restore authorization_policy_mode to 0.0",
    )

    is_valid, violations = validator.validate_recommendation(rec_attack)
    assert is_valid is False
    assert any("IMMUTABLE_CONTROL_VIOLATION" in v for v in violations)


def test_constraint_validator_enforces_budget_and_error_ceilings():
    """Verify constraint validator rejects recommendations when current system state violates ceilings."""
    validator = ConstraintValidator()

    rec = OptimizationRecommendation(
        recommendation_id="rec_safe_param",
        recommendation_type=RecommendationType.ADJUST_BATCHING,
        title="Adjust Ingestion Batching",
        description="Scale batch items",
        target_parameter="batch_size_items",
        current_value=10.0,
        proposed_value=20.0,
        expected_benefit="Improves throughput",
        expected_cost="Marginal memory",
        risk=RiskLevel.LOW,
        requires_approval=False,
        rollback_strategy="Restore batch_size_items to 10.0",
    )

    # State with cost exceeding 25.0 USD
    exceeded_metrics = {"cost_usd": 28.5, "error_rate": 0.02}
    is_valid, violations = validator.validate_recommendation(rec, current_metrics=exceeded_metrics)
    assert is_valid is False
    assert any("budget ceiling" in v for v in violations)

    # State with error rate exceeding 0.05
    error_spike_metrics = {"cost_usd": 10.0, "error_rate": 0.07}
    is_valid, violations = validator.validate_recommendation(rec, current_metrics=error_spike_metrics)
    assert is_valid is False
    assert any("error rate" in v for v in violations)


def test_constraint_validator_blocks_critical_risk():
    """Verify automated recommendations presenting CRITICAL risk are disqualified."""
    validator = ConstraintValidator()

    rec_critical = OptimizationRecommendation(
        recommendation_id="rec_crit_risk",
        recommendation_type=RecommendationType.ADJUST_CACHE,
        title="Dangerous Cache Flusher",
        description="Flushes all cache on live traffic",
        target_parameter="cache_ttl_seconds",
        current_value=300.0,
        proposed_value=600.0,
        expected_benefit="Cache test",
        expected_cost="High risk",
        risk=RiskLevel.CRITICAL,
        requires_approval=True,
        rollback_strategy="Restore cache_ttl_seconds to 300.0",
    )

    is_valid, violations = validator.validate_recommendation(rec_critical)
    assert is_valid is False
    assert any("CRITICAL risk" in v for v in violations)

"""Unit tests for Strategic Planning Gap Analysis and Strategy Generation (Task 58)."""

from __future__ import annotations

from app.planning.engine import strategic_planning_engine
from app.planning.schemas import (
    CurrentStateAssessment,
    DesiredStateDefinition,
    RiskSeverity,
    StateCertainty,
    StrategyOption,
    StrategyType,
)
from app.planning.strategies import strategy_generator


def test_gap_analysis_identifies_missing_invariants_and_metrics():
    current_state = CurrentStateAssessment(
        summary="Current legacy database running on single node",
        verified_aspects=["database_operational", "read_traffic_nominal"],
        active_telemetry={"latency_ms": 120.0, "error_rate_pct": 0.05},
        certainty=StateCertainty.VERIFIED,
    )
    desired_state = DesiredStateDefinition(
        summary="Distributed HA cluster with automated failover",
        completion_invariants=["automated failover verified", "multi-region replication active"],
        target_metrics={"latency_ms": 50.0, "error_rate_pct": 0.01},
        verification_criteria=["Zero failover data loss"],
    )

    gap = strategic_planning_engine.compute_gap_analysis(current_state, desired_state)

    assert len(gap.missing_capabilities) == 2
    assert any("automated failover verified" in cap for cap in gap.missing_capabilities)
    assert any("multi-region replication active" in cap for cap in gap.missing_capabilities)
    assert len(gap.technical_gaps) == 2
    assert any("latency_ms" in tg for tg in gap.technical_gaps)
    assert len(gap.blockers) == 0


def test_gap_analysis_flags_stale_current_state():
    current_state = CurrentStateAssessment(
        summary="Unverified legacy node",
        verified_aspects=[],
        certainty=StateCertainty.STALE,
        is_stale=True,
    )
    desired_state = DesiredStateDefinition(
        summary="Target state",
        completion_invariants=["service operational"],
    )

    gap = strategic_planning_engine.compute_gap_analysis(current_state, desired_state)
    assert len(gap.blockers) > 0
    assert any("STALE" in b for b in gap.blockers)


def test_strategy_generation_produces_distinct_archetypes():
    current_state = CurrentStateAssessment(
        summary="Legacy monolithic system",
        verified_aspects=["service_online"],
    )
    desired_state = DesiredStateDefinition(
        summary="Microservices architecture",
        completion_invariants=["all microservices isolated"],
    )
    gap = strategic_planning_engine.compute_gap_analysis(current_state, desired_state)

    strategies = strategy_generator.generate_strategies(
        gap=gap,
        desired_state=desired_state,
        decision_id="dec_4892",
    )

    types = {s.strategy_type for s in strategies}
    assert StrategyType.INCREMENTAL in types
    assert StrategyType.STABILIZE_FIRST in types
    assert StrategyType.PARALLEL in types
    assert StrategyType.INFO_GATHERING in types
    assert StrategyType.BIG_BANG in types

    # First strategy should be recommended/selected
    assert strategies[0].is_selected is True
    assert strategies[0].decision_reference == "dec_4892"

    # Big Bang should reflect high or critical risk and non-reversibility
    bb = next(s for s in strategies if s.strategy_type == StrategyType.BIG_BANG)
    assert bb.expected_risk in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
    assert bb.reversibility == "IRREVERSIBLE"


def test_evaluate_strategy_fit():
    strategy = StrategyOption(
        name="Experimental Parallel Rollout",
        strategy_type=StrategyType.PARALLEL,
        description="Run dual stacks concurrently",
        rationale="Minimize downtime",
        expected_risk=RiskSeverity.MEDIUM,
        reversibility="REVERSIBLE",
    )

    fit = strategy_generator.evaluate_strategy_fit(
        strategy=strategy,
        risk_tolerance="LOW",
        deadline_pressure="HIGH",
        budget_constrained=True,
    )

    assert fit["overall_score"] > 0
    assert "penalties" in fit
    assert any("cost" in p.lower() or "budget" in p.lower() for p in fit["penalties"])

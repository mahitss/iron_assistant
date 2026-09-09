"""Tests for Functional Motivation Engine, Tradeoff Models, and Intent DAG Graphs (Task 48, Spec 74-85)."""

import pytest

from app.intent.intent_graph import IntentGraph
from app.intent.motivation import (
    MotivationCategory,
    MotivationEngine,
    MotivationSignal,
    TradeoffAnalysis,
)


def test_safe_functional_motivation_extraction():
    """Detect safe functional motivations without psychological profiling (Spec 76, 77, 78)."""
    text = "Optimize this query for faster execution and reduce cloud costs"
    signals = MotivationEngine.detect_motivation(text)

    categories = {s.category for s in signals}
    assert (
        MotivationCategory.EFFICIENCY in categories
        or MotivationCategory.TIME_SAVING in categories
    )

    for s in signals:
        # Strictly functional category
        assert isinstance(s.category, MotivationCategory)
        assert s.evidence != ""


def test_no_psychological_profiling():
    """Verify engine rejects attempts to profile emotional/psychological traits (Spec 77)."""
    text = "The user seems stressed and impatient"
    signals = MotivationEngine.detect_motivation(text)
    # Stressed/impatient are not permitted motivation categories
    categories = [s.category.value for s in signals]
    assert "STRESSED" not in categories
    assert "IMPATIENT" not in categories
    assert "PSYCHOLOGY" not in categories


def test_tradeoff_analysis_between_competing_goals():
    """Surface explicit tradeoffs between conflicting goals (Spec 82, 83, 84)."""
    tradeoff = MotivationEngine.analyze_tradeoff(
        goal_a="Deploy quickly to production with minimal tests",
        goal_b="Run full end-to-end regression suite before release",
        cost_a=5.0,   # 5 mins
        cost_b=45.0,  # 45 mins
        benefit_a="Immediate release",
        benefit_b="Maximum reliability and safety guarantee",
        constraints=["Zero-downtime required"],
    )

    assert tradeoff.preferred_goal != ""
    assert tradeoff.cost_difference == 40.0
    assert "safety" in tradeoff.recommendation.lower() or "recommend" in tradeoff.recommendation.lower()


def test_intent_graph_dag_construction():
    """Verify Intent DAG: Intent -> Goal -> Objectives -> Constraints -> Tasks -> Outcomes (Spec 74, 144)."""
    graph = IntentGraph(intent_id="intent_dag_1", goal_id="goal_dag_1")

    # Add components
    graph.add_node("intent", "intent_dag_1", "User natural language request")
    graph.add_node("goal", "goal_dag_1", "Desired target state")
    graph.add_node("objective", "obj_1", "Response time < 2s")
    graph.add_node("constraint", "const_1", "Budget <= $100")
    graph.add_node("task", "task_1", "Compile container image")

    # Add edges
    graph.add_edge("intent_dag_1", "goal_dag_1", "FORMULATES")
    graph.add_edge("goal_dag_1", "obj_1", "REQUIRES")
    graph.add_edge("goal_dag_1", "const_1", "BOUNDED_BY")
    graph.add_edge("goal_dag_1", "task_1", "EXECUTES_VIA")

    d = graph.to_dict()
    assert len(d["nodes"]) == 5
    assert len(d["edges"]) == 4

    # Verify dependency lineage
    deps = graph.get_dependencies("goal_dag_1")
    assert "obj_1" in deps or "const_1" in deps or "task_1" in deps

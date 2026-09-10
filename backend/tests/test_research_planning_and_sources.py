"""Unit tests for Research Planning, Stop Conditions, and Source Trust & Dependency Graph (Task 63)."""

from datetime import datetime, timedelta, timezone

from app.research.planner import ResearchPlanner
from app.research.schemas import (
    ResearchMode,
    ResearchRequest,
    Source,
    SourceTrustLevel,
    SourceType,
)
from app.research.sources import SourceDependencyGraph, SourceRegistry


def test_research_planning_question_decomposition():
    planner = ResearchPlanner()
    req = ResearchRequest(
        question="What architecture should Kairo use for low-latency streaming?",
        mode=ResearchMode.STANDARD,
        depth=2,
    )
    plan = planner.create_plan(req)
    assert plan.question == req.question
    assert len(plan.sub_questions) >= 3
    assert any(
        "latency" in sq.lower() or "architecture" in sq.lower() or "requirement" in sq.lower()
        for sq in plan.sub_questions
    )
    assert len(plan.hypotheses) >= 1
    assert len(plan.stop_conditions) >= 2


def test_research_planner_stop_conditions():
    planner = ResearchPlanner()
    req = ResearchRequest(
        question="Database scalability options",
        mode=ResearchMode.QUICK,
        max_sources=3,
        max_duration_seconds=10,
    )
    plan = planner.create_plan(req)
    assert any("max_sources: 3" in s for s in plan.stop_conditions)
    assert any("max_duration_seconds: 10" in s for s in plan.stop_conditions)
    assert "evidence_saturation_reached" in plan.stop_conditions


def test_source_registry_registration_and_scoring():
    registry = SourceRegistry()
    src = Source(
        source_id="src_official_rfc",
        title="RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3",
        publisher="IETF",
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
        url_or_reference="https://www.rfc-editor.org/rfc/rfc8446",
        trust_level=SourceTrustLevel.VERY_HIGH,
        published_at=datetime.now(timezone.utc) - timedelta(days=100),
    )
    registered = registry.register_source(src)
    assert registered.source_id == "src_official_rfc"
    assert registered.authority_score > 0.8
    assert registered.freshness_score > 0.6
    assert registry.get_source("src_official_rfc") is not None


def test_source_dependency_graph_and_lineage_roots():
    graph = SourceDependencyGraph()
    # Source A is primary
    graph.add_citation("source_secondary_1", "source_primary_root")
    # Source B cites Source Secondary 1 (tertiary)
    graph.add_citation("source_tertiary_2", "source_secondary_1")
    # Source C also cites primary
    graph.add_citation("source_secondary_3", "source_primary_root")

    roots_1 = graph.get_lineage_roots("source_tertiary_2")
    assert roots_1 == ["source_primary_root"]

    # Source Secondary 1, Tertiary 2, and Secondary 3 all collapse to 1 independent group
    groups = graph.compute_source_independence_groups(
        [
            "source_primary_root",
            "source_secondary_1",
            "source_tertiary_2",
            "source_secondary_3",
        ]
    )
    assert len(groups) == 1
    assert "source_primary_root" in groups[0]
    assert len(groups[0]) == 4


def test_source_dependency_graph_circular_reporting_detection():
    graph = SourceDependencyGraph()
    graph.add_citation("source_alpha", "source_beta")
    graph.add_citation("source_beta", "source_gamma")
    graph.add_citation("source_gamma", "source_alpha")  # Circular!

    cycles = graph.detect_circular_reporting(["source_alpha", "source_beta", "source_gamma"])
    assert len(cycles) > 0
    assert any("source_alpha" in c and "source_beta" in c for c in cycles)


def test_source_retraction_propagation():
    registry = SourceRegistry()
    src = Source(
        source_id="src_benchmark_flawed",
        title="Faulty benchmark report",
        publisher="Vendor Lab",
        source_type=SourceType.TECHNICAL_REPORT,
    )
    registry.register_source(src)
    assert not src.retracted

    retracted = registry.retract_source(
        "src_benchmark_flawed", reason="Methodology flawed; retracted by authors"
    )
    assert retracted.retracted
    assert retracted.retraction_reason == "Methodology flawed; retracted by authors"
    assert registry.get_source("src_benchmark_flawed").retracted

"""Unit tests for Problem Decomposition and Subproblem DAG (Task 71)."""

from app.reasoning.decomposer import ProblemDecomposer
from app.reasoning.schemas import SubProblem


def test_problem_decomposition_bounded_depth():
    """Verify decomposition is bounded to max_depth <= 3 to prevent infinite recursive explosion."""
    decomposer = ProblemDecomposer()
    question = "Why is the production Kubernetes cluster failing health checks and experiencing pod crashes?"

    subproblems = decomposer.decompose(question, max_depth=3)

    assert len(subproblems) > 0
    assert len(subproblems) <= 8

    # Depth invariants
    for sp in subproblems:
        assert 1 <= sp.depth_level <= 3
        assert sp.question
        assert sp.status == "PENDING"


def test_subproblem_topological_sort():
    """Verify dependency ordering across subproblems."""
    decomposer = ProblemDecomposer()

    sp1 = SubProblem(subproblem_id="sp-1", question="Identify symptom", depth_level=1)
    sp2 = SubProblem(
        subproblem_id="sp-2", question="Identify root cause", depth_level=2, dependencies=["sp-1"]
    )
    sp3 = SubProblem(
        subproblem_id="sp-3", question="Formulate remediation", depth_level=3, dependencies=["sp-2"]
    )

    # Pass in reverse order
    ordered = decomposer.topological_sort([sp3, sp2, sp1])
    ordered_ids = [sp.subproblem_id for sp in ordered]

    assert ordered_ids.index("sp-1") < ordered_ids.index("sp-2")
    assert ordered_ids.index("sp-2") < ordered_ids.index("sp-3")


def test_decomposition_domain_adaptation():
    """Verify tailored decomposition questions for latency/error incidents."""
    decomposer = ProblemDecomposer()

    subproblems = decomposer.decompose(
        "High CPU utilization and memory leak in ingestion service", max_depth=2
    )
    questions = [sp.question.lower() for sp in subproblems]

    # Should detect memory/resource or symptom patterns
    assert any("metric" in q or "symptom" in q or "component" in q or "resource" in q for q in questions)

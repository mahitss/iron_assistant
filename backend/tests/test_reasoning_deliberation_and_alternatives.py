"""Unit tests for Deliberation, Tradeoff Alternatives & Safe Explanations (Task 71)."""

from app.reasoning.deliberation import DeliberationEngine
from app.reasoning.schemas import (
    AssumptionStatus,
    HypothesisStatus,
    ReasoningAssumption,
    ReasoningConfidence,
    ReasoningHypothesis,
)


def test_alternative_generation_and_tradeoff_comparison():
    """Verify deliberation generates actionable comparative alternatives with risk, cost, and reversibility scores."""
    deliberator = DeliberationEngine()

    hyp = ReasoningHypothesis(
        description="Database connection leak in connection pool",
        status=HypothesisStatus.SUPPORTED,
        confidence=ReasoningConfidence.HIGH,
    )

    alternatives = deliberator.generate_alternatives(
        question="How to remediate database connection exhaustion?",
        leading_hypotheses=[hyp],
    )

    assert len(alternatives) >= 2
    for alt in alternatives:
        assert alt.title
        assert 0.0 <= alt.risk_score <= 1.0
        assert 0.0 <= alt.cost_score <= 1.0
        assert 0.0 <= alt.reversibility <= 1.0
        assert 0.0 <= alt.expected_impact <= 1.0


def test_counterargument_formulation():
    """Verify counterarguments challenge leading hypotheses ('What could make this wrong?')."""
    deliberator = DeliberationEngine()

    hyp = ReasoningHypothesis(
        description="Network switch failure in rack 4",
        supporting_evidence_ids=["ev-1"],  # Single evidence source vulnerability
        falsification_conditions=["Rack 4 ping packets show 0% loss"],
    )

    counters = deliberator.generate_counterarguments(hyp, [])

    assert len(counters) > 0
    # Must flag single-source dependency
    assert any("single evidence source" in c.lower() or "unverified condition" in c.lower() for c in counters)


def test_dissent_preservation_across_agents():
    """Verify multi-agent deliberation preserves minority dissenting perspectives instead of discarding them."""
    deliberator = DeliberationEngine()

    h_majority = ReasoningHypothesis(description="Upstream ISP outage")
    h_minority = ReasoningHypothesis(description="Local TLS certificate expiration")

    agent_inputs = {
        "agent_1": [h_majority],
        "agent_2": [h_majority],
        "agent_3": [h_minority],  # Dissenting minority
    }

    dissent_report = deliberator.preserve_dissent(agent_inputs)

    assert dissent_report["majority_view"] == "Upstream ISP outage"
    assert len(dissent_report["majority_agents"]) == 2
    assert len(dissent_report["dissenting_views"]) == 1
    assert dissent_report["dissenting_views"][0]["hypothesis"] == "Local TLS certificate expiration"
    assert "agent_3" in dissent_report["dissenting_views"][0]["supporters"]


def test_safe_explanation_no_private_chain_of_thought():
    """Verify synthesized explanations are concise, structured, and expose ZERO private chain-of-thought."""
    deliberator = DeliberationEngine()

    hyp = ReasoningHypothesis(
        description="Deadlock caused by unordered lock acquisition across distributed workers",
        status=HypothesisStatus.SUPPORTED,
        supporting_evidence_ids=["ev-1", "ev-2"],
        counterarguments=["Worker heartbeat was interrupted by GC pause."],
    )
    asm = ReasoningAssumption(
        description="Worker concurrency limit is set to 50",
        status=AssumptionStatus.VALIDATED,
    )

    concl, expl = deliberator.synthesize_conclusion(
        question="What caused distributed task worker stalls?",
        evaluated_hypotheses=[hyp],
        assumptions=[asm],
        evidence_pool=[],
    )

    # Explanation structure
    assert expl.conclusion_summary
    assert expl.confidence == concl.confidence
    assert len(expl.supporting_reasons) > 0
    assert len(expl.counterarguments_addressed) > 0
    assert len(expl.assumptions_made) > 0

    # Ensure no hidden chain-of-thought tokens or scratchpad dumps
    expl_dump = expl.model_dump_json()
    assert "chain_of_thought" not in expl_dump
    assert "internal_thought" not in expl_dump
    assert "<thought>" not in expl_dump

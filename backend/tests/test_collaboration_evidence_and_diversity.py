"""Tests for Evidence Classification, Provenance, and Diversity Scoring (Task 44)."""

import pytest
from app.agents.evidence import (
    CollaborativeEvidence,
    EvidencePool,
    FactType,
)


def test_fact_classification():
    ev_fact = CollaborativeEvidence(
        evidence_id="ev_01",
        producer_agent_id="agent_1",
        contract_id="ct_1",
        fact_type=FactType.FACT,
        claim="Database index on user_id exists.",
        sources=["schema.sql:L42"],
        is_verified=True,
    )
    assert ev_fact.fact_type == FactType.FACT
    assert ev_fact.is_verified is True

    ev_hypo = CollaborativeEvidence(
        evidence_id="ev_02",
        producer_agent_id="agent_2",
        contract_id="ct_2",
        fact_type=FactType.HYPOTHESIS,
        claim="Latency spike might be due to GC pause.",
        sources=[],
        is_verified=False,
    )
    assert ev_hypo.fact_type == FactType.HYPOTHESIS
    assert ev_hypo.is_verified is False


def test_evidence_provenance_and_pool():
    pool = EvidencePool()
    ev = CollaborativeEvidence(
        evidence_id="ev_10",
        producer_agent_id="agent_debugger",
        contract_id="ct_debug_9",
        fact_type=FactType.FACT,
        claim="HTTP 500 error reproduced on /checkout route with missing cart_id",
        sources=["reproduction_test.py", "server.log"],
        model_id="claude-3-5-sonnet",
        is_verified=True,
    )
    pool.add(ev)

    retrieved = pool.get("ev_10")
    assert retrieved is not None
    assert retrieved.producer_agent_id == "agent_debugger"
    assert retrieved.contract_id == "ct_debug_9"
    assert "reproduction_test.py" in retrieved.sources


def test_source_and_model_diversity_prevents_false_consensus():
    """Five agents reading the same blog do NOT constitute five independent sources."""
    pool = EvidencePool()

    # 3 agents repeating the same identical source
    for i in range(3):
        pool.add(
            CollaborativeEvidence(
                evidence_id=f"ev_rep_{i}",
                producer_agent_id=f"agent_{i}",
                contract_id=f"ct_{i}",
                fact_type=FactType.INFERENCE,
                claim="Framework X does not support WebSockets",
                sources=["https://medium.com/fake-post"],
                model_id="gpt-4o",  # Same model
            )
        )

    diversity = pool.calculate_diversity(["ev_rep_0", "ev_rep_1", "ev_rep_2"])
    # Unique sources is 1, unique models is 1
    assert diversity["unique_sources_count"] == 1
    assert diversity["unique_models_count"] == 1
    assert diversity["independence_score"] < 0.5  # Flagged as low independence / false consensus risk

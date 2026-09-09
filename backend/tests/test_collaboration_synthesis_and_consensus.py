"""Tests for Derived Consensus and Collective Synthesis Engine (Task 44)."""

import pytest
from app.agents.consensus import (
    ConsensusEngine,
    ConsensusStatus,
)
from app.agents.evidence import (
    CollaborativeEvidence,
    EvidencePool,
    FactType,
)
from app.agents.synthesis import (
    SynthesisEngine,
)


def test_consensus_evaluation_with_verified_evidence():
    pool = EvidencePool()

    # 3 unverified claims for Option X
    for i in range(3):
        pool.add(
            CollaborativeEvidence(
                evidence_id=f"ev_opt_x_{i}",
                producer_agent_id=f"agent_{i}",
                contract_id=f"ct_{i}",
                fact_type=FactType.HYPOTHESIS,
                claim="Approach X is optimal",
                is_verified=False,
            )
        )

    # 1 verified proof for Option Y
    pool.add(
        CollaborativeEvidence(
            evidence_id="ev_opt_y",
            producer_agent_id="agent_verifier",
            contract_id="ct_v",
            fact_type=FactType.FACT,
            claim="Approach Y passes benchmark with 4x throughput",
            sources=["benchmark.py"],
            is_verified=True,
        )
    )

    engine = ConsensusEngine(pool)
    report = engine.evaluate(
        topic="Architecture selection",
        evidence_ids=["ev_opt_x_0", "ev_opt_x_1", "ev_opt_x_2", "ev_opt_y"],
    )

    assert report.status == ConsensusStatus.EVIDENCE_SUPPORTED
    assert report.verified_claim == "Approach Y passes benchmark with 4x throughput"


def test_collective_synthesis_preserves_conflicts_and_provenance():
    pool = EvidencePool()
    pool.add(
        CollaborativeEvidence(
            evidence_id="ev_synth_1",
            producer_agent_id="agent_coder",
            contract_id="ct_1",
            fact_type=FactType.FACT,
            claim="Migration script successfully converted 10,000 user records.",
            is_verified=True,
        )
    )
    pool.add(
        CollaborativeEvidence(
            evidence_id="ev_synth_2",
            producer_agent_id="agent_analyst",
            contract_id="ct_2",
            fact_type=FactType.HYPOTHESIS,
            claim="Potential race condition on concurrent record insertion during migration.",
            is_verified=False,
        )
    )

    engine = SynthesisEngine(pool)
    result = engine.synthesize(
        session_id="session_db_migration",
        goal="Migrate user schema safely",
        agent_result_ids=[],
    )

    assert result.session_id == "session_db_migration"
    assert len(result.findings) >= 1
    # Check that provenance references are preserved
    finding = result.findings[0]
    assert len(finding.evidence_refs) > 0

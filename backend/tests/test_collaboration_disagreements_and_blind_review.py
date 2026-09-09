"""Tests for Evidence-First Disagreement Resolution and Blind Review (Task 44)."""

import pytest
from app.agents.disagreement import (
    Disagreement,
    DisagreementResolver,
    DisagreementStatus,
)
from app.agents.evidence import (
    CollaborativeEvidence,
    EvidencePool,
    FactType,
)


def test_evidence_first_resolution_verified_beats_unverified_majority():
    """Rule 53 & 54: 3 agents agreeing does not beat 1 agent with stronger verified evidence."""
    pool = EvidencePool()

    # Claim A: Supported by 3 unverified opinions
    for i in range(3):
        pool.add(
            CollaborativeEvidence(
                evidence_id=f"ev_unverified_{i}",
                producer_agent_id=f"agent_group_{i}",
                contract_id=f"ct_{i}",
                fact_type=FactType.HYPOTHESIS,
                claim="The bug is in the database connection string.",
                sources=[],
                is_verified=False,
            )
        )

    # Claim B: Supported by 1 verified empirical evidence item
    pool.add(
        CollaborativeEvidence(
            evidence_id="ev_verified_1",
            producer_agent_id="agent_lone_tester",
            contract_id="ct_tester",
            fact_type=FactType.FACT,
            claim="The bug is an unhandled NullPointerException in UserService.java line 88.",
            sources=["stacktrace.log", "test_user_service.py"],
            is_verified=True,
            verification_source="pytest_runner_exit_code_0",
        )
    )

    resolver = DisagreementResolver(pool)
    disagreement = Disagreement(
        disagreement_id="disag_001",
        subject="Root cause of UserService 500 error",
        participants=["agent_group_0", "agent_group_1", "agent_group_2", "agent_lone_tester"],
        claims={
            "agent_group_0": "Database connection string issue",
            "agent_lone_tester": "NullPointerException in UserService.java line 88",
        },
        evidence={
            "agent_group_0": ["ev_unverified_0", "ev_unverified_1", "ev_unverified_2"],
            "agent_lone_tester": ["ev_verified_1"],
        },
    )

    resolved = resolver.resolve(disagreement)
    assert resolved.status == DisagreementStatus.RESOLVED
    assert "UserService.java" in resolved.resolution
    # Verified evidence won despite 3-to-1 vote count against it!


def test_blind_review_context_packaging():
    """Rule 58: Blind review context strips agent IDs and authority metadata."""
    pool = EvidencePool()
    pool.add(
        CollaborativeEvidence(
            evidence_id="ev_blind_1",
            producer_agent_id="agent_super_elite_senior_coder",
            contract_id="ct_elite",
            fact_type=FactType.INFERENCE,
            claim="Algorithm requires O(N^2) sorting step.",
            sources=["doc.pdf"],
            is_verified=False,
        )
    )

    resolver = DisagreementResolver(pool)
    disagreement = Disagreement(
        disagreement_id="disag_002",
        subject="Complexity of sorting",
        participants=["agent_super_elite_senior_coder", "agent_junior_tester"],
        claims={
            "agent_super_elite_senior_coder": "Algorithm requires O(N^2)",
            "agent_junior_tester": "Algorithm can be done in O(N log N)",
        },
        evidence={
            "agent_super_elite_senior_coder": ["ev_blind_1"],
            "agent_junior_tester": [],
        },
    )

    blind_ctx = resolver.prepare_blind_review_context(disagreement)
    # Ensure agent identities are anonymized to claimant_1 / claimant_2
    assert "agent_super_elite_senior_coder" not in str(blind_ctx)
    assert "agent_junior_tester" not in str(blind_ctx)
    assert "claimant_" in str(blind_ctx)

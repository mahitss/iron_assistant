"""Unit tests for Root-Cause Analysis, 5-Stage Causal Chains, and Contributing Factors (Task 55)."""

import pytest

from app.causal.evidence import create_causal_evidence
from app.causal.hypotheses import HypothesisManager
from app.causal.root_cause import RootCauseAnalyzer
from app.causal.safety import UnverifiedRootCauseError
from app.causal.schemas import (
    EvidenceStrength,
    EvidenceType,
    RootCauseStatus,
)


def test_root_cause_initialization_and_chain():
    """Prompt #31, #34, #189: Build 5-stage causal chain."""
    rca = RootCauseAnalyzer.initialize_analysis(
        incident_id="inc_prod_404",
        candidate_causes=["db_saturation", "traffic_spike", "network_split"],
    )
    assert rca.incident_id == "inc_prod_404"
    assert rca.status == RootCauseStatus.INVESTIGATING
    assert len(rca.surviving_causes) == 3

    chain = RootCauseAnalyzer.build_causal_chain(
        underlying_condition="Low max_connections configured on database",
        trigger="traffic_spike_at_12_00",
        mechanism="Connection pool exhaustion causing query queuing",
        symptom="HTTP 504 Gateway Timeout on API ingress",
        impact="Checkout flow unavailable for 8 minutes",
    )
    assert chain.underlying_condition.startswith("Low max_connections")
    assert chain.trigger == "traffic_spike_at_12_00"
    assert chain.mechanism.startswith("Connection pool")
    assert chain.symptom.startswith("HTTP 504")
    assert chain.impact.startswith("Checkout flow")


def test_primary_cause_vs_contributing_factors():
    """Prompt #35, #36: Separate primary cause from contributing factors."""
    rca = RootCauseAnalyzer.initialize_analysis(
        incident_id="inc_latency",
        candidate_causes=["database_saturation", "traffic_spike", "slow_dns"],
    )

    h_db = HypothesisManager.create_hypothesis("database_saturation", "latency", "pool starve", confidence=0.75)
    ev_db = create_causal_evidence(
        evidence_type=EvidenceType.TELEMETRY,
        source="prometheus:postgres",
        observation={"connections": 999},
        strength=EvidenceStrength.STRONG,
    )
    h_db.evidence.append(ev_db)

    h_traffic = HypothesisManager.create_hypothesis("traffic_spike", "latency", "rps spike", confidence=0.6)
    ev_traffic = create_causal_evidence(
        evidence_type=EvidenceType.TELEMETRY,
        source="datadog:ingress",
        observation={"rps": 50000},
        strength=EvidenceStrength.STRONG,
    )
    h_traffic.evidence.append(ev_traffic)

    h_dns = HypothesisManager.create_hypothesis("slow_dns", "latency", "lookup slow", confidence=0.1)

    updated = RootCauseAnalyzer.update_with_ranked_hypotheses(
        analysis=rca,
        ranked_hypotheses=[h_db, h_traffic, h_dns],
        require_verification=False,
    )

    assert updated.root_cause == "database_saturation"
    assert updated.status == RootCauseStatus.LIKELY  # Distinct from VERIFIED
    assert "traffic_spike" in updated.contributing_factors
    assert "database_saturation" not in updated.contributing_factors


def test_unverified_root_cause_cannot_be_claimed_verified():
    """Prompt #33, #84, #106: Verified root cause requires explicit empirical evidence threshold."""
    rca = RootCauseAnalyzer.initialize_analysis(
        incident_id="inc_unverified",
        candidate_causes=["misconfiguration"],
    )
    h_weak = HypothesisManager.create_hypothesis("misconfiguration", "failure", "bad flag", confidence=0.4)
    ev_weak = create_causal_evidence(
        evidence_type=EvidenceType.USER_REPORT,
        source="slack:ops",
        observation={"comment": "maybe config was wrong"},
        strength=EvidenceStrength.WEAK,
    )
    h_weak.evidence.append(ev_weak)

    # If verification is required and evidence is insufficient, it must raise UnverifiedRootCauseError
    with pytest.raises(UnverifiedRootCauseError):
        RootCauseAnalyzer.update_with_ranked_hypotheses(
            analysis=rca,
            ranked_hypotheses=[h_weak],
            require_verification=True,
        )


def test_never_force_root_cause_when_evidence_insufficient():
    """Prompt #163, #164: Unknown cause is valid. Never invent a root cause."""
    rca = RootCauseAnalyzer.initialize_analysis(
        incident_id="inc_empty",
        candidate_causes=["a", "b", "c"],
    )
    h_a = HypothesisManager.create_hypothesis("a", "symptom", "mech_a", confidence=0.1)
    h_b = HypothesisManager.create_hypothesis("b", "symptom", "mech_b", confidence=0.15)

    updated = RootCauseAnalyzer.update_with_ranked_hypotheses(
        analysis=rca,
        ranked_hypotheses=[h_b, h_a],
        require_verification=False,
    )
    assert updated.root_cause is None
    assert updated.status == RootCauseStatus.UNKNOWN

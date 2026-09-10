"""Unit tests for Causal Evidence, Hypotheses, Alternatives, and Scoring (Task 55)."""

import pytest

from app.causal.alternatives import AlternativeHypothesisGenerator
from app.causal.evidence import create_causal_evidence, discount_correlated_evidence
from app.causal.hypotheses import HypothesisManager
from app.causal.safety import ModelOutputAsEvidenceError
from app.causal.schemas import (
    EvidenceStrength,
    EvidenceType,
    HypothesisStatus,
)
from app.causal.scoring import CausalScorer


def test_model_output_cannot_be_evidence():
    """Prompt #19: Model-generated reasoning is hypothesis generation, NOT evidence."""
    with pytest.raises(ModelOutputAsEvidenceError) as exc_info:
        create_causal_evidence(
            evidence_type=EvidenceType.OBSERVATION,
            source="llm_agent_reasoning",
            observation={"claim": "Database caused failure"},
        )
    assert "model-generated reasoning" in str(exc_info.value)

    with pytest.raises(ModelOutputAsEvidenceError):
        create_causal_evidence(
            evidence_type=EvidenceType.OBSERVATION,
            source="assistant_thought_trace",
            observation={"claim": "Deployment caused failure"},
        )


def test_authoritative_sources_and_user_reports():
    """Prompt #15, #17, #18: Source authority and user report handling."""
    # Authoritative telemetry gets at least MODERATE strength floor
    auth_ev = create_causal_evidence(
        evidence_type=EvidenceType.TELEMETRY,
        source="prometheus:db_conn_utilization",
        observation={"metric": "db_conn", "val": 0.98},
        strength=EvidenceStrength.WEAK,  # Attempting to assign weak to Prometheus
    )
    assert auth_ev.strength == EvidenceStrength.MODERATE

    # User report cannot be claimed as CRITICAL or STRONG without corroboration
    user_ev = create_causal_evidence(
        evidence_type=EvidenceType.USER_REPORT,
        source="zendesk_ticket_102",
        observation={"report": "I think the server crashed"},
        strength=EvidenceStrength.CRITICAL,  # Demoted to MODERATE
    )
    assert user_ev.strength == EvidenceStrength.MODERATE


def test_correlated_evidence_discounting():
    """Prompt #16: Avoid counting correlated or duplicate evidence multiple times."""
    ev1 = create_causal_evidence(
        evidence_type=EvidenceType.LOG,
        source="api_logger:instance_1",
        observation={"msg": "timeout"},
        independence=1.0,
    )
    ev2 = create_causal_evidence(
        evidence_type=EvidenceType.LOG,
        source="api_logger:instance_2",
        observation={"msg": "timeout"},
        independence=1.0,
    )
    ev3 = create_causal_evidence(
        evidence_type=EvidenceType.LOG,
        source="api_logger:instance_3",
        observation={"msg": "timeout"},
        independence=1.0,
    )

    discounted = discount_correlated_evidence([ev1, ev2, ev3])
    assert len(discounted) == 3
    assert discounted[0].independence == 1.0
    assert discounted[1].independence < 1.0
    assert discounted[2].independence < discounted[1].independence


def test_hypothesis_lifecycle_and_alternatives():
    """Prompt #11, #12, #27, #28, #162: Candidate hypotheses generation and elimination."""
    candidates = AlternativeHypothesisGenerator.generate_candidate_hypotheses(
        effect="api_latency_spike",
        context_clues={"active_flags": ["database_saturation"]},
    )
    assert len(candidates) >= 6
    causes = [c.cause for c in candidates]
    assert "deployment" in causes
    assert "database_saturation" in causes
    assert "network_failure" in causes
    assert "traffic_spike" in causes

    # Find deployment candidate
    dep_hyp = next(c for c in candidates if c.cause == "deployment")
    assert dep_hyp.status == HypothesisStatus.PROPOSED

    # Eliminate deployment with evidence
    elim_evidence = create_causal_evidence(
        evidence_type=EvidenceType.CONFIGURATION,
        source="git_provider:audit",
        observation={"last_deploy": "3_hours_ago", "status": "no_changes"},
        strength=EvidenceStrength.STRONG,
    )
    res = AlternativeHypothesisGenerator.eliminate_hypothesis_with_evidence(
        hypothesis=dep_hyp,
        contradicting_evidence=elim_evidence,
        elimination_reason="No deployments occurred in the incident window.",
    )
    assert res["status"] == "ELIMINATED"
    assert dep_hyp.status == HypothesisStatus.REJECTED
    assert dep_hyp.confidence == 0.05


def test_hypothesis_evidence_scoring():
    """Prompt #29: Rank hypotheses by empirical evidence score."""
    h_db = HypothesisManager.create_hypothesis("database_saturation", "latency_spike", "pool starvation", confidence=0.7)
    h_net = HypothesisManager.create_hypothesis("network_failure", "latency_spike", "packet drop", confidence=0.3)

    ev_db = create_causal_evidence(
        evidence_type=EvidenceType.TELEMETRY,
        source="opentelemetry:db",
        observation={"pool": "exhausted"},
        strength=EvidenceStrength.CRITICAL,
    )
    h_db.evidence.append(ev_db)

    ranked = CausalScorer.rank_hypotheses([h_net, h_db])
    assert ranked[0].cause == "database_saturation"
    assert ranked[0].confidence > ranked[1].confidence


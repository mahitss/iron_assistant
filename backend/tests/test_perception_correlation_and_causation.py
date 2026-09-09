"""Tests for Event Correlation, Graph Relationships, and Causation vs Observation Separation (Task 46)."""

from datetime import datetime, timezone
import pytest

from app.perception.correlator import (
    CorrelationEdge,
    CorrelationRelation,
    EventCorrelator,
)
from app.perception.events import EventType, PerceptionEvent


def utc_now():
    return datetime.now(timezone.utc)


def test_cross_source_correlation_chain():
    """Enforce Spec 24, 134:
    Git push -> CI started -> build completed -> deployment started -> deployment healthy.
    """
    correlator = EventCorrelator()
    shared_trace_id = "commit_abc123"

    # 1. Git push event
    e_push = PerceptionEvent(
        event_id="evt_push_1",
        event_type=EventType.PUSHED,
        source_id="src_git",
        subject="git:repo_kairo",
        correlation_id=shared_trace_id,
        payload={"commit_hash": shared_trace_id},
    )

    # 2. CI build started
    e_ci = PerceptionEvent(
        event_id="evt_ci_2",
        event_type=EventType.STARTED,
        source_id="src_github",
        subject="github:workflow_ci",
        correlation_id=shared_trace_id,
    )

    # 3. Deployment deployed
    e_dep = PerceptionEvent(
        event_id="evt_dep_3",
        event_type=EventType.DEPLOYED,
        source_id="src_deploy",
        subject="deployment:kairo_prod",
        correlation_id=shared_trace_id,
    )

    # 4. Production Health Healthy
    e_health = PerceptionEvent(
        event_id="evt_hlth_4",
        event_type=EventType.HEALTH_CHANGED,
        source_id="src_health",
        subject="service:kairo_api",
        correlation_id=shared_trace_id,
        payload={"status": "HEALTHY"},
    )

    for e in [e_push, e_ci, e_dep, e_health]:
        correlator.record_event(e)

    chain = correlator.get_correlated_events(shared_trace_id)
    assert len(chain) == 4
    assert [x.event_id for x in chain] == ["evt_push_1", "evt_ci_2", "evt_dep_3", "evt_hlth_4"]


def test_causation_separate_from_observation():
    """Enforce Spec 26, 27: Causation is represented separately from observed facts.
    Observed: deployment failed after commit.
    Do NOT automatically assert: commit caused deployment failure.
    """
    correlator = EventCorrelator()

    # Observed facts
    edge_observed = correlator.correlate(
        source_event_id="evt_commit_88",
        target_event_id="evt_deploy_fail",
        relation=CorrelationRelation.OBSERVED_AFTER,
        is_inferred=False,
    )
    assert edge_observed.is_inferred is False
    assert edge_observed.relation == CorrelationRelation.OBSERVED_AFTER

    # Inferred causal hypothesis (Spec 120, 121)
    edge_causal = correlator.correlate(
        source_event_id="evt_commit_88",
        target_event_id="evt_deploy_fail",
        relation=CorrelationRelation.HYPOTHESIZED_CAUSE,
        confidence=0.75,
        is_inferred=True,
        evidence={"stack_trace": "SyntaxError in commit_88"},
    )
    assert edge_causal.is_inferred is True
    assert edge_causal.relation == CorrelationRelation.HYPOTHESIZED_CAUSE
    assert edge_causal.confidence == 0.75
    assert "stack_trace" in edge_causal.evidence

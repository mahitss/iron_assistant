"""Unit & Invariant Test Suite for Task 115:
Kairo Autonomous Hypothesis Management, Competing Explanations, Evidence Update, Falsification & Uncertainty Resolution Engine.
"""

from __future__ import annotations

import pytest

from app.hypothesis.domain import (
    EvidenceIndependence,
    HypothesisStatus,
)
from app.hypothesis.service import HypothesisService, get_hypothesis_service


@pytest.fixture
def service() -> HypothesisService:
    """Provides a fresh isolated HypothesisService instance."""
    HypothesisService.reset_instance()
    svc = get_hypothesis_service()
    svc._sets.clear()
    svc._hypotheses.clear()
    svc._evidence.clear()
    svc._events.clear()
    return svc


def test_hypothesis_set_creation_with_mandatory_unknown(service: HypothesisService):
    """Invariant: Every hypothesis set must include competing explanations + mandatory UNKNOWN."""
    hset = service.create_hypothesis_set(target_description="API latency spike on checkout cluster")

    assert hset.set_id.startswith("hset_")
    assert len(hset.active_hypothesis_ids) >= 3
    assert hset.unknown_hypothesis_id is not None

    unknown_hyp = service.get_hypothesis(hset.unknown_hypothesis_id)
    assert unknown_hyp is not None
    assert unknown_hyp.is_unknown_hypothesis is True
    assert unknown_hyp.status == HypothesisStatus.UNKNOWN
    assert "CAUSE_UNKNOWN" in unknown_hyp.statement or "Unknown" in unknown_hyp.statement


def test_multidimensional_confidence_profile(service: HypothesisService):
    """Invariant: Multi-dimensional confidence dimensions are never collapsed into an opaque scalar."""
    hset = service.create_hypothesis_set(target_description="Worker saturation incident")
    hyps = service.list_hypotheses(hset.set_id)
    active = [h for h in hyps if not h.is_unknown_hypothesis][0]

    p = active.confidence_profile
    assert hasattr(p, "evidence_strength")
    assert hasattr(p, "evidence_independence")
    assert hasattr(p, "temporal_consistency")
    assert hasattr(p, "mechanism_plausibility")
    assert hasattr(p, "causal_support")
    assert hasattr(p, "predictive_success")
    assert hasattr(p, "contradiction_score")
    assert hasattr(p, "uncertainty")

    d = p.to_dict()
    assert "viability_score" in d
    assert "uncertainty" in d
    assert "contradiction_score" in d


def test_evidence_independence_lineage_tracking(service: HypothesisService):
    """Invariant: Telemetry A -> Derived signal B -> Agent C report do NOT count as 3 independent evidence items."""
    hset = service.create_hypothesis_set(target_description="Database connection exhaustion")
    active = [h for h in service.list_hypotheses(hset.set_id) if not h.is_unknown_hypothesis][0]

    # 1. Primary telemetry
    ev1 = service.attach_evidence_to_set(
        hset.set_id,
        {
            "source": "telemetry.db_pool",
            "source_type": "system",
            "evidence_type": "TELEMETRY",
            "payload": {active.claim.target_metric or "cpu_memory_utilization": 92.0},
        },
    )
    assert ev1.independence == EvidenceIndependence.INDEPENDENT

    # 2. Derived signal citing parent
    ev2 = service.attach_evidence_to_set(
        hset.set_id,
        {
            "source": "derived_processor",
            "source_type": "signal",
            "evidence_type": "DERIVED_SIGNAL",
            "parent_evidence_ids": [ev1.evidence_id],
            "payload": {"derived_warning": True},
        },
    )
    assert ev2.independence == EvidenceIndependence.DERIVED

    # 3. Agent reporting identical metric
    ev3 = service.attach_evidence_to_set(
        hset.set_id,
        {
            "source": "agent_alpha",
            "source_type": "agent",
            "source_agent_id": "agent_alpha",
            "evidence_type": "AGENT_REPORT",
            "payload": {
                "metric_name": active.claim.target_metric or "cpu_memory_utilization",
                "observed_value": 92.0,
            },
        },
    )
    assert ev3.independence == EvidenceIndependence.DERIVED

    # Assert evidence independence profile is properly penalized, not 1.0
    updated_hyp = service.get_hypothesis(active.hypothesis_id)
    assert updated_hyp.confidence_profile.evidence_independence < 1.0


def test_falsification_condition_trigger(service: HypothesisService):
    """Invariant: Explicit, bounded, testable condition immediately FALSIFIES a hypothesis."""
    hset = service.create_hypothesis_set(target_description="Network degradation investigation")
    hyps = service.list_hypotheses(hset.set_id)
    # Find network degradation hypothesis (h2)
    net_hyp = next(h for h in hyps if "network" in h.claim.subject.lower())

    assert len(net_hyp.falsification_conditions) > 0
    f_cond = net_hyp.falsification_conditions[0]
    assert "rtt_ms" in f_cond.metric_thresholds

    # Ingest telemetry proving network was perfectly healthy (<2ms rtt and 0% loss)
    ev = service.attach_evidence_to_set(
        hset.set_id,
        {
            "source": "telemetry.network_rtt",
            "source_type": "system",
            "evidence_type": "TELEMETRY",
            "payload": {"rtt_ms": 1.2, "loss_pct": 0.0},
        },
    )

    updated = service.get_hypothesis(net_hyp.hypothesis_id)
    assert updated.status == HypothesisStatus.FALSIFIED
    assert ev.evidence_id in updated.falsifying_evidence_ids
    assert updated.confidence_profile.contradiction_score == 1.0

    # Ensure hypothesis set moves falsified candidate out of active list
    updated_set = service.get_hypothesis_set(hset.set_id)
    assert net_hyp.hypothesis_id not in updated_set.active_hypothesis_ids
    assert net_hyp.hypothesis_id in updated_set.rejected_hypothesis_ids


def test_prediction_calibration_and_failure(service: HypothesisService):
    """Invariant: When a predicted state fails reality, prediction is marked FAILED and confidence drops."""
    hset = service.create_hypothesis_set(target_description="Worker saturation incident")
    res_hyp = next(h for h in service.list_hypotheses(hset.set_id) if "resource" in h.claim.subject.lower())

    assert len(res_hyp.predictions) > 0
    pred = res_hyp.predictions[0]
    metric_name = pred.expected_metric or "oom_kill_count"

    # Ingest observation where observed value is outside expected range (expected >= 1.0, observed 0.0)
    service.falsification_engine.evaluate_predictions(
        res_hyp,
        [{metric_name: 0.0}],
    )

    assert pred.outcome_status == "FAILED"
    assert pred.observed_outcome == 0.0
    assert "outside expected range" in (pred.failure_notes or "")
    assert res_hyp.confidence_profile.predictive_success < 0.5


def test_cognitive_bias_guard_confirmation_bias(service: HypothesisService):
    """Invariant: Advancing to STRONGLY_SUPPORTED requires contradiction search."""
    hset = service.create_hypothesis_set(target_description="Service incident")
    hyp = next(h for h in service.list_hypotheses(hset.set_id) if not h.is_unknown_hypothesis)

    # Attach strong supporting evidence
    metric = hyp.claim.target_metric or "cpu_memory_utilization"
    service.attach_evidence_to_set(
        hset.set_id,
        {
            "source": "monitor_1",
            "source_type": "system",
            "evidence_type": "TELEMETRY",
            "payload": {metric: 95.0},
        },
    )

    # Attach conflicting evidence that contradiction search will uncover
    service.attach_evidence_to_set(
        hset.set_id,
        {
            "source": "monitor_2",
            "source_type": "system",
            "evidence_type": "TELEMETRY",
            "payload": {metric: 15.0},  # Directly contradicts increase
        },
    )

    # Re-evaluate
    service.bias_guard_engine.check_and_apply_safeguards(
        hyp, hset, service.list_hypotheses(hset.set_id), list(service._evidence.values())
    )

    # Status cannot be STRONGLY_SUPPORTED because contradiction score is elevated
    assert hyp.status != HypothesisStatus.STRONGLY_SUPPORTED
    assert any("CONFIRMATION_BIAS_GUARD" in trig for trig in hyp.bias_guard_triggers)


def test_premature_closure_guard(service: HypothesisService):
    """Invariant: Hypothesis set cannot be declared resolved if unexamined alternatives remain."""
    hset = service.create_hypothesis_set(target_description="Cluster slowdown")
    active_hyps = [h for h in service.list_hypotheses(hset.set_id) if not h.is_unknown_hypothesis]

    # Attempt to mark resolved prematurely
    hset.is_resolved = True
    service.bias_guard_engine.check_and_apply_safeguards(
        active_hyps[0], hset, service.list_hypotheses(hset.set_id), list(service._evidence.values())
    )

    # Premature closure guard should block resolution
    assert hset.is_resolved is False
    assert "PREMATURE_CLOSURE" in hset.resolution_summary


def test_hypothesis_splitting_with_lineage(service: HypothesisService):
    """Invariant: Splitting an overly broad hypothesis preserves parent-child lineage."""
    hset = service.create_hypothesis_set(target_description="Network instability")
    parent = next(h for h in service.list_hypotheses(hset.set_id) if "network" in h.claim.subject.lower())

    children = service.split_hypothesis(
        hset.set_id,
        parent.hypothesis_id,
        [
            {"statement": "Upstream router packet drop", "target_metric": "packet_loss_pct"},
            {"statement": "DNS resolution timeout cascade", "target_metric": "dns_latency_ms"},
        ],
    )

    assert len(children) == 2
    assert parent.status == HypothesisStatus.SPLIT
    assert parent.hypothesis_id not in hset.active_hypothesis_ids
    for c in children:
        assert c.parent_hypothesis_ids == [parent.hypothesis_id]
        assert c.hypothesis_id in hset.active_hypothesis_ids
        assert c.status == HypothesisStatus.UNDER_INVESTIGATION


def test_hypothesis_merging_without_deleting_history(service: HypothesisService):
    """Invariant: Merging equivalent hypotheses unifies evidence trails without deleting history."""
    hset = service.create_hypothesis_set(target_description="High CPU incident")
    hyps = [h for h in service.list_hypotheses(hset.set_id) if not h.is_unknown_hypothesis]
    h1 = hyps[0]
    h2 = hyps[1]

    # Add evidence to each
    service.attach_evidence_to_set(hset.set_id, {"source": "s1", "payload": {"val": 1}}, target_hypothesis_id=h1.hypothesis_id)
    service.attach_evidence_to_set(hset.set_id, {"source": "s2", "payload": {"val": 2}}, target_hypothesis_id=h2.hypothesis_id)

    merged = service.merge_hypotheses(
        hset.set_id,
        [h1.hypothesis_id, h2.hypothesis_id],
        "Unified resource exhaustion and thread contention hypothesis",
    )

    assert merged.hypothesis_id in hset.active_hypothesis_ids
    assert h1.status == HypothesisStatus.MERGED
    assert h2.status == HypothesisStatus.MERGED
    assert h1.superseded_by_id == merged.hypothesis_id
    assert h2.superseded_by_id == merged.hypothesis_id
    assert h1.hypothesis_id not in hset.active_hypothesis_ids
    assert h2.hypothesis_id not in hset.active_hypothesis_ids
    # History preserved in memory and cache
    assert service.get_hypothesis(h1.hypothesis_id) is not None
    assert service.get_hypothesis(h2.hypothesis_id) is not None


def test_discriminating_observations_generation(service: HypothesisService):
    """Invariant: Identifies discriminators between competing hypotheses with VoI metadata."""
    hset = service.create_hypothesis_set(target_description="Service degraded")
    discriminators = service.discriminator_engine.find_discriminating_observations(
        hset, service.list_hypotheses(hset.set_id)
    )

    assert len(discriminators) > 0
    disc = discriminators[0]
    assert disc.information_value > 0.0
    assert disc.target_metric_or_signal != ""
    assert len(disc.hypothesis_predictions) >= 2


def test_side_by_side_comparison_non_ranking(service: HypothesisService):
    """Invariant: Side-by-side comparison matrix does not declare arbitrary winners or rankings."""
    hset = service.create_hypothesis_set(target_description="Incident comparison test")
    comp = service.get_side_by_side_comparison(hset.set_id)

    assert "matrix" in comp
    assert "discriminators" in comp
    assert "information_gaps" in comp
    # Ensure there is NO 'winner', 'best_hypothesis', or 'ranking'
    assert "winner" not in comp
    assert "best_hypothesis" not in comp
    assert "ranking" not in comp

    for row in comp["matrix"]:
        assert "hypothesis_id" in row
        assert "mechanism" in row
        assert "falsification_conditions" in row
        assert "uncertainty" in row


def test_verification_invariants_and_blocking(service: HypothesisService):
    """Invariant: Verification requires passing falsification, high independent evidence, and evaluated alternatives."""
    hset = service.create_hypothesis_set(target_description="Uncertain incident")
    hyp = next(h for h in service.list_hypotheses(hset.set_id) if not h.is_unknown_hypothesis)

    # Immediate verification attempt must fail
    res = service.verify_hypothesis(hyp.hypothesis_id)
    assert res["verified"] is False
    assert len(res["reasons_blocked"]) > 0
    assert hyp.status != HypothesisStatus.VERIFIED


def test_downstream_emergency_stop_fail_closed(service: HypothesisService):
    """Invariant: Emergency stop halts hypothesis mutation and enforces safety fail-closed."""
    from app.security.emergency_stop import get_emergency_stop_service
    stop_svc = get_emergency_stop_service()

    # Trigger emergency stop
    stop_svc.trigger_emergency_stop(reason="Test fail-closed condition", user_id="system")

    with pytest.raises(PermissionError, match="HYPOTHESIS_SAFETY_BLOCKED"):
        service.create_hypothesis_set(target_description="Blocked by stop")

    # Reset emergency stop
    stop_svc.reset_emergency_stop(user_id="system")
    # Now it should succeed
    hset = service.create_hypothesis_set(target_description="Allowed after reset")
    assert hset is not None

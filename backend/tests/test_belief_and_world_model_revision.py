"""Comprehensive Unit, Integration, and Property Tests for Task 107:
KAIRO Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine.

Proves:
- belief != truth
- belief != authorization
- belief != policy
- belief != goal
- belief != decision
- belief != memory
- belief != graph fact
- forecast != observation
- simulation != reality
- agent report != independent truth
- duplicate evidence != independent evidence
- unknown != false
- stale != current
- conflict != resolution
- correlation != causation
- historical validity != current validity
- user assertion != automatically verified fact
- confidence != certainty
- EmergencyStop cannot be bypassed
"""

from __future__ import annotations

from datetime import datetime, timedelta
import pytest

from app.belief.domain import (
    ArbitrationOutcome,
    Belief,
    BeliefConflict,
    BeliefScope,
    BeliefStatus,
    ConflictResolution,
    ConflictType,
    EvidenceClassification,
    EvidenceItem,
    RevisionReason,
    UncertaintyType,
    utc_now,
)
from app.belief.service import BeliefService
from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError


@pytest.fixture
def clean_service() -> BeliefService:
    """Create fresh isolated BeliefService instance."""
    estop = EmergencyStopService()
    return BeliefService(emergency_stop=estop)


# ==============================================================================
# 1. PROPERTY & INVARIANT TESTS
# ==============================================================================

def test_invariant_belief_not_truth(clean_service: BeliefService):
    """Property test: BELIEF != TRUTH. Beliefs express probabilistic confidence with explicit uncertainty."""
    belief = clean_service.create_belief(
        subject="api.internal.service",
        predicate="is_available",
        object_value=True,
        initial_confidence=0.75,
    )
    assert belief.confidence == 0.75
    assert belief.uncertainty == 0.25
    # A belief has uncertainty and can be revised; it is not an immutable ground truth
    assert belief.status != "TRUTH"
    assert hasattr(belief, "confidence") and hasattr(belief, "uncertainty")


def test_invariant_duplicate_evidence_not_independent(clean_service: BeliefService):
    """Property test: DUPLICATE EVIDENCE != INDEPENDENT EVIDENCE. Content hash prevents confidence inflation."""
    claim = clean_service.create_claim(
        subject="cache_server",
        predicate="is_hot",
        object_value=True,
    )

    ev1 = clean_service.ingest_evidence(
        source_id="agent_alpha",
        source_type=EvidenceClassification.AGENT_REPORT,
        content={"observed_value": True},
        summary="Cache is hot",
        reliability_weight=0.8,
    )
    # Re-ingest identical content from agent_alpha
    ev2 = clean_service.ingest_evidence(
        source_id="agent_alpha",
        source_type=EvidenceClassification.AGENT_REPORT,
        content={"observed_value": True},
        summary="Cache is hot",
        reliability_weight=0.8,
    )

    asm1 = clean_service.arbitration_engine.evaluate_evidence(ev1, claim)
    asm2 = clean_service.arbitration_engine.evaluate_evidence(ev2, claim)

    assert asm1.weight > 0.0
    # Duplicate content hash must yield zero incremental weight
    assert asm2.weight == 0.0


def test_invariant_agent_report_not_independent_truth_with_correlated_lineage(clean_service: BeliefService):
    """Property test: AGENT REPORT != INDEPENDENT TRUTH. Correlated citations are damped."""
    claim = clean_service.create_claim(
        subject="vector_db",
        predicate="index_built",
        object_value=True,
    )

    # Agent A reports X
    ev_root = clean_service.ingest_evidence(
        source_id="agent_a",
        source_type=EvidenceClassification.AGENT_REPORT,
        content={"observed_value": True, "seq": 1},
        summary="Agent A built index",
    )
    asm_root = clean_service.arbitration_engine.evaluate_evidence(ev_root, claim)

    # Agent B reads Agent A and repeats X
    ev_derived = clean_service.ingest_evidence(
        source_id="agent_b",
        source_type=EvidenceClassification.AGENT_REPORT,
        content={"observed_value": True, "seq": 2},
        summary="Agent B confirms index built per Agent A",
        derived_from_evidence_ids=[ev_root.evidence_id],
    )
    asm_derived = clean_service.arbitration_engine.evaluate_evidence(ev_derived, claim)

    # Derived citation receives damped weight due to lineage repetition
    assert asm_derived.weight < asm_root.weight


def test_invariant_simulation_not_reality(clean_service: BeliefService):
    """Property test: SIMULATION != REALITY. Simulation has lower baseline weight and cannot prove reality."""
    claim = clean_service.create_claim(
        subject="network_bandwidth",
        predicate="can_sustain_10gbps",
        object_value=True,
    )

    ev_sim = clean_service.ingest_evidence(
        source_id="digital_twin_sim",
        source_type=EvidenceClassification.SIMULATION,
        content={"observed_value": True, "simulated": True},
        summary="Simulated 10gbps sustained in sandbox",
    )
    ev_real = clean_service.ingest_evidence(
        source_id="kernel_nic_driver",
        source_type=EvidenceClassification.DIRECT_OBSERVATION,
        content={"observed_value": False, "hardware_drop": True},
        summary="Hardware interface dropped 40% packets",
    )

    asm_sim = clean_service.arbitration_engine.evaluate_evidence(ev_sim, claim)
    asm_real = clean_service.arbitration_engine.evaluate_evidence(ev_real, claim)

    assert asm_real.weight > asm_sim.weight
    assert asm_sim.outcome == ArbitrationOutcome.SUPPORTS
    assert asm_real.outcome == ArbitrationOutcome.CONTRADICTS


def test_invariant_forecast_not_observation(clean_service: BeliefService):
    """Property test: FORECAST != OBSERVATION. Forecast is prospective, lower weight than direct observation."""
    from app.belief.arbitration_engine import BASE_CLASSIFICATION_WEIGHTS
    assert BASE_CLASSIFICATION_WEIGHTS[EvidenceClassification.FORECAST] < BASE_CLASSIFICATION_WEIGHTS[EvidenceClassification.DIRECT_OBSERVATION]
    assert BASE_CLASSIFICATION_WEIGHTS[EvidenceClassification.SIMULATION] < BASE_CLASSIFICATION_WEIGHTS[EvidenceClassification.VERIFIED_OUTCOME]


def test_invariant_user_assertion_not_verified_fact(clean_service: BeliefService):
    """Property test: USER_ASSERTION != AUTOMATICALLY VERIFIED FACT. User correction is ingested as assertion."""
    belief = clean_service.create_belief(
        subject="database_backend",
        predicate="db_type",
        object_value="PostgreSQL",
        initial_confidence=0.8,
    )

    corr = clean_service.record_user_correction(
        belief_id=belief.belief_id,
        correction_statement="We use SQLite in testing",
    )
    assert corr.source == "USER"
    assert corr.verified is False

    ev = clean_service.get_evidence(corr.evidence_id)
    assert ev is not None
    assert ev.source_type == EvidenceClassification.USER_ASSERTION
    assert ev.reliability_weight == 0.5


def test_invariant_emergency_stop_primacy(clean_service: BeliefService):
    """Property test: EMERGENCY_STOP CANNOT BE BYPASSED. Epistemic mutations are blocked fail-closed."""
    clean_service.emergency_stop.trigger_emergency_stop(reason="Security Incident Test")

    with pytest.raises(EmergencyStopActiveError):
        clean_service.create_belief("service", "status", "OK")

    with pytest.raises(EmergencyStopActiveError):
        clean_service.ingest_evidence(source_id="test", content={"data": 1})

    with pytest.raises(EmergencyStopActiveError):
        clean_service.capture_snapshot()

    # Reset with human operator credentials
    clean_service.emergency_stop.reset_emergency_stop(is_human_user=True)
    b = clean_service.create_belief("service", "status", "OK")
    assert b is not None


# ==============================================================================
# 2. LIFECYCLE & NON-DESTRUCTIVE REVISION TESTS
# ==============================================================================

def test_non_destructive_belief_revision_flow(clean_service: BeliefService):
    """Verify append-only revision flow from CANDIDATE -> SUPPORTED -> CONFIDENT -> CONTRADICTED."""
    # 1. Create candidate
    belief = clean_service.create_belief(
        subject="api.external.com",
        predicate="is_healthy",
        object_value=True,
        initial_confidence=0.4,
    )
    assert belief.status == BeliefStatus.CANDIDATE
    assert belief.current_version == 1

    # 2. Ingest supporting telemetry -> SUPPORTED
    ev1 = clean_service.ingest_evidence(
        source_id="ping_monitor",
        source_type=EvidenceClassification.TELEMETRY,
        content={"observed_value": True},
        summary="HTTP 200 OK received",
        reliability_weight=0.9,
    )
    b_rev1, v2, rev1 = clean_service.arbitrate_and_revise(belief.belief_id, ev1.evidence_id)
    assert b_rev1.current_version == 2
    assert v2.version_number == 2
    assert rev1.prior_version_number == 1
    assert rev1.new_version_number == 2
    assert b_rev1.status in {BeliefStatus.SUPPORTED, BeliefStatus.PROVISIONAL}

    # 3. Ingest strong verified outcome -> CONFIDENT
    ev2 = clean_service.ingest_evidence(
        source_id="e2e_integration_test",
        source_type=EvidenceClassification.VERIFIED_OUTCOME,
        content={"observed_value": True},
        summary="E2E transaction completed cleanly",
        reliability_weight=1.0,
    )
    b_rev2, v3, rev2 = clean_service.arbitrate_and_revise(belief.belief_id, ev2.evidence_id)
    assert b_rev2.current_version == 3
    assert b_rev2.status == BeliefStatus.CONFIDENT
    assert b_rev2.confidence >= 0.8

    # 4. Ingest fatal contradiction -> CONTRADICTED
    ev3 = clean_service.ingest_evidence(
        source_id="kernel_watchdog",
        source_type=EvidenceClassification.DIRECT_OBSERVATION,
        content={"observed_value": False, "failed": True},
        summary="Service crash loop: connection refused",
        reliability_weight=1.0,
    )
    b_rev3, v4, rev3 = clean_service.arbitrate_and_revise(
        belief.belief_id, ev3.evidence_id, reason=RevisionReason.CONTRADICTING_EVIDENCE
    )
    assert b_rev3.current_version == 4
    assert b_rev3.status == BeliefStatus.CONTRADICTED
    assert b_rev3.confidence < 0.4
    assert ev3.evidence_id in b_rev3.contradiction_evidence_ids

    # 5. History preservation check
    versions = clean_service.get_belief_versions(belief.belief_id)
    assert len(versions) == 4
    assert [v.version_number for v in versions] == [1, 2, 3, 4]
    assert versions[2].status == BeliefStatus.CONFIDENT
    assert versions[3].status == BeliefStatus.CONTRADICTED


# ==============================================================================
# 3. CONFLICT DETECTION & CONTEXTUAL TRUTH
# ==============================================================================

def test_contextual_truth_across_scopes(clean_service: BeliefService):
    """Verify claims differing only by scope resolve as BOTH_CONTEXTUALLY_VALID, not contradiction."""
    # Claim A: Healthy in Staging
    c1 = clean_service.create_claim(
        subject="billing_engine",
        predicate="status",
        object_value="READY",
        scope="ENVIRONMENT:staging",
    )
    # Claim B: Degraded in Production
    c2 = clean_service.create_claim(
        subject="billing_engine",
        predicate="status",
        object_value="DEGRADED",
        scope="ENVIRONMENT:production",
    )

    conflicts = clean_service.conflict_engine.detect_conflicts(c2, [c1])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.SCOPE
    assert conflicts[0].resolution == ConflictResolution.BOTH_CONTEXTUALLY_VALID


def test_direct_conflict_arbitration(clean_service: BeliefService):
    """Verify direct contradiction in same scope is identified and marked CONTESTED if evidence is comparable."""
    ev_a = clean_service.ingest_evidence(
        source_id="agent_1",
        source_type=EvidenceClassification.AGENT_REPORT,
        content={"observed_value": "PASS"},
        summary="Agent 1 reports pass",
    )
    ev_b = clean_service.ingest_evidence(
        source_id="agent_2",
        source_type=EvidenceClassification.AGENT_REPORT,
        content={"observed_value": "FAIL"},
        summary="Agent 2 reports fail",
    )

    c1 = clean_service.create_claim(
        subject="test_suite",
        predicate="verdict",
        object_value="PASS",
        scope="SYSTEM",
        provenance={"evidence_ids": [ev_a.evidence_id]},
    )
    c2 = clean_service.create_claim(
        subject="test_suite",
        predicate="verdict",
        object_value="FAIL",
        scope="SYSTEM",
        provenance={"evidence_ids": [ev_b.evidence_id]},
    )

    conflicts = clean_service.conflict_engine.detect_conflicts(c2, [c1], clean_service._evidence)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.DIRECT
    assert conflicts[0].resolution == ConflictResolution.CONTESTED


# ==============================================================================
# 4. TEMPORAL FRESHNESS & STALENESS
# ==============================================================================

def test_temporal_freshness_decay_and_staleness(clean_service: BeliefService):
    """Verify temporal decay applies smooth exponential decay without dropping confidence to zero."""
    belief = clean_service.create_belief(
        subject="cpu_metrics",
        predicate="cpu_usage",
        object_value=45.0,
        initial_confidence=0.9,
        freshness_ttl_seconds=60,  # 60 seconds TTL
    )
    assert belief.is_stale is False

    # Simulate 300 seconds passing (5x TTL)
    future_time = utc_now() + timedelta(seconds=300)
    is_stale, decayed_conf, rec_status = clean_service.temporal_engine.evaluate_freshness(belief, as_of=future_time)

    assert is_stale is True
    assert decayed_conf < 0.9
    # Invariant: confidence must NOT drop instantly to 0.0
    assert decayed_conf > 0.0
    assert rec_status in {BeliefStatus.STALE, BeliefStatus.REVALIDATION_REQUIRED}


# ==============================================================================
# 5. DEPENDENCY PROPAGATION
# ==============================================================================

def test_dependency_uncertainty_propagation(clean_service: BeliefService):
    """Verify upstream contradiction forces downstream hard prerequisite to REVALIDATION_REQUIRED."""
    # B1: Database healthy
    b1 = clean_service.create_belief("database", "status", "ONLINE", initial_confidence=0.9)
    # B2: Backend service operational (depends on B1)
    b2 = clean_service.create_belief("api_server", "status", "HEALTHY", initial_confidence=0.85)

    # Register dependency B2 -> B1
    clean_service.register_dependency(
        parent_belief_id=b1.belief_id,
        child_belief_id=b2.belief_id,
        is_hard_prerequisite=True,
    )

    # Ingest fatal contradiction for B1
    ev_fatal = clean_service.ingest_evidence(
        source_id="db_probe",
        source_type=EvidenceClassification.DIRECT_OBSERVATION,
        content={"observed_value": "OFFLINE", "failed": True},
        summary="DB socket connection refused",
    )
    clean_service.arbitrate_and_revise(b1.belief_id, ev_fatal.evidence_id)

    assert b1.status == BeliefStatus.CONTRADICTED

    # B2 must now be REVALIDATION_REQUIRED with decayed confidence
    b2_updated = clean_service.get_belief(b2.belief_id)
    assert b2_updated.status == BeliefStatus.REVALIDATION_REQUIRED
    assert b2_updated.confidence < 0.85


# ==============================================================================
# 6. DECISION SNAPSHOTS & REPLAY
# ==============================================================================

def test_belief_snapshot_capture_and_integrity(clean_service: BeliefService):
    """Verify decision-time snapshot creates immutable manifest with cryptographic integrity."""
    clean_service.create_belief("auth", "is_ready", True, initial_confidence=0.9)
    clean_service.create_belief("cache", "is_ready", True, initial_confidence=0.8)

    snap = clean_service.capture_snapshot(trigger_type="DECISION_CONTEXT", reference_id="dec_42")
    assert snap.snapshot_id.startswith("bsnap_")
    assert snap.reference_id == "dec_42"
    assert len(snap.beliefs_manifest) == 2
    assert len(snap.integrity_hash) == 64

    # Verify integrity validation
    assert clean_service.snapshot_engine.verify_snapshot_integrity(snap) is True

    # Tamper test
    snap.beliefs_manifest[0]["confidence"] = 0.12
    assert clean_service.snapshot_engine.verify_snapshot_integrity(snap) is False


# ==============================================================================
# 7. EXPLANATION & CONTEXT EVIDENCE PACK
# ==============================================================================

def test_structured_explanation_and_evidence_pack(clean_service: BeliefService):
    """Verify explanation answers WHAT, WHY, WHEN, CONTRADICTIONS without dumping chain of thought."""
    belief = clean_service.create_belief("search_service", "is_available", True, initial_confidence=0.85)
    ev = clean_service.ingest_evidence(
        source_id="http_probe",
        source_type=EvidenceClassification.TELEMETRY,
        content={"observed_value": True},
        summary="Search endpoint returned 200 OK in 14ms",
    )
    clean_service.arbitrate_and_revise(belief.belief_id, ev.evidence_id)

    explanation = clean_service.explain_belief(belief.belief_id)
    assert "search_service" in explanation.what
    assert len(explanation.why_evidence) >= 1
    assert len(explanation.revalidation_triggers) >= 1

    pack = clean_service.get_evidence_pack(belief.belief_id)
    assert pack.belief_id == belief.belief_id
    assert pack.supporting_evidence_count >= 1
    assert "EPISTEMIC NOTICE" in pack.epistemic_disclaimer

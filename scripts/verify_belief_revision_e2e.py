"""End-to-End Verification Script for Task 107:
KAIRO Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine.

Validates the full 10-phase epistemic lifecycle:
- Phase 1: Proposition & Candidate Belief Creation
- Phase 2: Multi-source Evidence Ingestion & Versioned Progression (v1 -> v2 -> v3)
- Phase 3: Anti-Poisoning: Duplicate Content Deduplication & Lineage Damping
- Phase 4: Anti-Circularity: Circular Self-Lineage Capping
- Phase 5: Conflict Resolution: Direct Contradictions & Contextual Truth Scopes
- Phase 6: Temporal Reasoning: Expiry, Domain TTLs & Staleness Evaluation
- Phase 7: Epistemic Dependency DAG: Downstream Uncertainty Propagation
- Phase 8: Decision-Time Epistemic Snapshots with Cryptographic Integrity
- Phase 9: Human User Correction Ingestion (USER_ASSERTION)
- Phase 10: EmergencyStop Absolute Primacy (Fail-Closed)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.belief.domain import (
    ArbitrationOutcome,
    BeliefScope,
    BeliefStatus,
    ConflictResolution,
    ConflictType,
    EvidenceClassification,
    RevisionReason,
    UncertaintyType,
    utc_now,
)
from app.belief.service import BeliefService
from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError


def run_e2e_verification() -> bool:
    print("=" * 80)
    print("TASK 107: BELIEF, EVIDENCE ARBITRATION & WORLD-MODEL REVISION — E2E VERIFICATION")
    print("=" * 80)

    estop = EmergencyStopService()
    service = BeliefService(emergency_stop=estop)

    # --------------------------------------------------------------------------
    # Phase 1: Proposition & Candidate Belief Creation
    # --------------------------------------------------------------------------
    print("\n[Phase 1] Creating initial candidate proposition...")
    belief = service.create_belief(
        subject="auth_cluster",
        predicate="is_healthy",
        object_value=True,
        scope=BeliefScope.ENVIRONMENT.value,
        initial_confidence=0.4,
    )
    assert belief.status == BeliefStatus.CANDIDATE
    assert belief.current_version == 1
    print(f"  [OK] Belief Candidate instantiated: {belief.belief_id} | {belief.subject}.{belief.predicate} | status={belief.status.value}")

    # --------------------------------------------------------------------------
    # Phase 2: Evidence Ingestion & Versioned Progression
    # --------------------------------------------------------------------------
    print("\n[Phase 2] Ingesting telemetry and verified outcomes (v1 -> v2 -> v3)...")
    ev1 = service.ingest_evidence(
        source_id="kube_health_probe",
        source_type=EvidenceClassification.TELEMETRY,
        scope=BeliefScope.ENVIRONMENT.value,
        content={"observed_value": True},
        summary="Kubernetes liveness probe passed with 200 OK",
        reliability_weight=0.9,
    )
    b_v2, v2, rev1 = service.arbitrate_and_revise(belief.belief_id, ev1.evidence_id)
    assert b_v2.current_version == 2
    print(f"  [OK] Version 2 Minted: status={b_v2.status.value} (confidence={b_v2.confidence:.2f})")

    ev2 = service.ingest_evidence(
        source_id="synthetic_e2e_runner",
        source_type=EvidenceClassification.VERIFIED_OUTCOME,
        scope=BeliefScope.ENVIRONMENT.value,
        content={"observed_value": True},
        summary="User login session created and verified end-to-end",
        reliability_weight=1.0,
    )
    b_v3, v3, rev2 = service.arbitrate_and_revise(belief.belief_id, ev2.evidence_id)
    assert b_v3.current_version == 3
    assert b_v3.status == BeliefStatus.CONFIDENT
    print(f"  [OK] Version 3 Minted: status={b_v3.status.value} (confidence={b_v3.confidence:.2f}, uncertainty={b_v3.uncertainty:.2f})")

    # --------------------------------------------------------------------------
    # Phase 3: Anti-Poisoning Controls
    # --------------------------------------------------------------------------
    print("\n[Phase 3] Testing Anti-Poisoning (Deduplication & Correlated Lineage)...")
    # Duplicate evidence content
    ev_dup = service.ingest_evidence(
        source_id="kube_health_probe",
        source_type=EvidenceClassification.TELEMETRY,
        scope=BeliefScope.ENVIRONMENT.value,
        content={"observed_value": True},
        summary="Kubernetes liveness probe passed with 200 OK",
        reliability_weight=0.9,
    )
    claim = service.get_claim(belief.claim_id)
    asm_dup = service.arbitration_engine.evaluate_evidence(ev_dup, claim)
    assert asm_dup.weight == 0.0
    print("  [OK] Duplicate evidence content yielded zero incremental weight (anti-poisoning).")

    # Correlated agent reports
    ev_agent1 = service.ingest_evidence(
        source_id="agent_scout",
        source_type=EvidenceClassification.AGENT_REPORT,
        content={"observed_value": True, "token": "unique_1"},
        summary="Agent Scout reports auth cluster is healthy",
    )
    ev_agent2 = service.ingest_evidence(
        source_id="agent_auditor",
        source_type=EvidenceClassification.AGENT_REPORT,
        content={"observed_value": True, "token": "unique_2"},
        summary="Agent Auditor quotes Agent Scout report",
        derived_from_evidence_ids=[ev_agent1.evidence_id],
    )
    asm_ag1 = service.arbitration_engine.evaluate_evidence(ev_agent1, claim)
    asm_ag2 = service.arbitration_engine.evaluate_evidence(ev_agent2, claim)
    assert asm_ag2.weight < asm_ag1.weight
    print(f"  [OK] Correlated citation received damped weight ({asm_ag2.weight:.3f} < {asm_ag1.weight:.3f}).")

    # --------------------------------------------------------------------------
    # Phase 4: Anti-Circularity
    # --------------------------------------------------------------------------
    print("\n[Phase 4] Testing Anti-Circularity (self-lineage capping)...")
    claim_with_prov = service.create_claim(
        subject="self_hyp",
        predicate="is_true",
        object_value=True,
        provenance={"evidence_ids": ["evi_root_hyp"]},
    )
    circular_ev = service.ingest_evidence(
        source_id="reflective_agent",
        source_type=EvidenceClassification.INFERRED,
        content={"observed_value": True},
        derived_from_evidence_ids=["evi_root_hyp"],
    )
    asm_circ = service.arbitration_engine.evaluate_evidence(circular_ev, claim_with_prov)
    assert asm_circ.weight <= 0.05
    print("  [OK] Circular lineage flagged and capped at nominal weight (anti-circularity).")

    # --------------------------------------------------------------------------
    # Phase 5: Conflict Resolution & Contextual Truth
    # --------------------------------------------------------------------------
    print("\n[Phase 5] Testing Conflict Resolution & Contextual Truth...")
    # Scope conflict: Staging vs Production
    c_stage = service.create_claim("billing", "status", "OK", scope="ENVIRONMENT:staging")
    c_prod = service.create_claim("billing", "status", "DEGRADED", scope="ENVIRONMENT:production")
    conflicts_scope = service.conflict_engine.detect_conflicts(c_prod, [c_stage])
    assert conflicts_scope[0].resolution == ConflictResolution.BOTH_CONTEXTUALLY_VALID
    print(f"  [OK] Multi-environment claim resolved as {conflicts_scope[0].resolution.value} (Contextual Truth).")

    # Direct conflict within same scope
    c_same_a = service.create_claim("dns_resolver", "status", "ONLINE", scope="SYSTEM")
    c_same_b = service.create_claim("dns_resolver", "status", "OFFLINE", scope="SYSTEM")
    conflicts_direct = service.conflict_engine.detect_conflicts(c_same_b, [c_same_a])
    assert conflicts_direct[0].conflict_type == ConflictType.DIRECT
    print(f"  [OK] Same-scope contradictory proposition flagged as {conflicts_direct[0].conflict_type.value}.")

    # --------------------------------------------------------------------------
    # Phase 6: Temporal Reasoning & Staleness
    # --------------------------------------------------------------------------
    print("\n[Phase 6] Testing Temporal Reasoning & Smooth Staleness Decay...")
    b_temp = service.create_belief("telemetry_cpu", "cpu_percent", 50.0, initial_confidence=0.95, freshness_ttl_seconds=60)
    future = utc_now() + timedelta(seconds=240)
    is_stale, decayed_conf, rec_status = service.temporal_engine.evaluate_freshness(b_temp, as_of=future)
    assert is_stale is True
    assert 0.0 < decayed_conf < 0.95
    assert rec_status in {BeliefStatus.STALE, BeliefStatus.REVALIDATION_REQUIRED}
    print(f"  [OK] Stale belief decayed smoothly (conf: 0.95 -> {decayed_conf:.2f}, status -> {rec_status.value}).")

    # --------------------------------------------------------------------------
    # Phase 7: Epistemic Dependency Propagation
    # --------------------------------------------------------------------------
    print("\n[Phase 7] Testing Epistemic Dependency DAG Propagation...")
    b_parent = service.create_belief("core_db", "status", "HEALTHY", initial_confidence=0.9)
    b_child = service.create_belief("web_api", "status", "READY", initial_confidence=0.85)
    service.register_dependency(b_parent.belief_id, b_child.belief_id, is_hard_prerequisite=True)

    ev_crash = service.ingest_evidence(
        source_id="hardware_monitor",
        source_type=EvidenceClassification.DIRECT_OBSERVATION,
        content={"observed_value": "CRASHED", "failed": True},
        summary="Storage controller unrecoverable I/O error",
    )
    service.arbitrate_and_revise(b_parent.belief_id, ev_crash.evidence_id)
    assert b_parent.status == BeliefStatus.CONTRADICTED
    b_child_updated = service.get_belief(b_child.belief_id)
    assert b_child_updated.status == BeliefStatus.REVALIDATION_REQUIRED
    print(f"  [OK] Upstream crash in {b_parent.subject} propagated to downstream child {b_child.subject} (status: {b_child_updated.status.value}).")

    # --------------------------------------------------------------------------
    # Phase 8: Decision-Time Epistemic Snapshots
    # --------------------------------------------------------------------------
    print("\n[Phase 8] Capturing immutable decision-time epistemic snapshot...")
    snapshot = service.capture_snapshot(trigger_type="DECISION_CONTEXT", reference_id="dec_tx_107_alpha")
    assert snapshot.snapshot_id.startswith("bsnap_")
    assert service.snapshot_engine.verify_snapshot_integrity(snapshot) is True
    print(f"  [OK] Snapshot captured: {snapshot.snapshot_id} (hash={snapshot.integrity_hash[:16]}..., beliefs={len(snapshot.beliefs_manifest)})")

    # --------------------------------------------------------------------------
    # Phase 9: User Correction Ingestion
    # --------------------------------------------------------------------------
    print("\n[Phase 9] Recording human user correction...")
    corr = service.record_user_correction(
        belief_id=belief.belief_id,
        correction_statement="Port 8080 was migrated to TLS port 8443",
    )
    assert corr.source == "USER"
    assert corr.verified is False
    print(f"  [OK] User correction logged as USER_ASSERTION: {corr.correction_id} (not automatically ground truth).")

    # --------------------------------------------------------------------------
    # Phase 10: EmergencyStop Absolute Primacy
    # --------------------------------------------------------------------------
    print("\n[Phase 10] Testing EmergencyStop absolute primacy (fail-closed)...")
    service.emergency_stop.trigger_emergency_stop(reason="Simulated catastrophic risk")
    try:
        service.create_belief("new_service", "status", "OK")
        assert False, "EmergencyStop failed to block belief creation!"
    except EmergencyStopActiveError:
        print("  [OK] Epistemic mutation BLOCKED fail-closed while EmergencyStop is active.")

    service.emergency_stop.reset_emergency_stop(is_human_user=True)
    print("  [OK] EmergencyStop disengaged by human operator.")

    print("\n" + "=" * 80)
    print("ALL 10 PHASES OF BELIEF ENGINE & WORLD-MODEL REVISION VERIFIED CLEANLY!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)

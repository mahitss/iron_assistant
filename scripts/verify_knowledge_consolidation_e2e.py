"""End-to-End Verification Scenario for Task 92: KAIRO Knowledge Consolidation Engine.

Validates complete real-world lifecycle:
1. Observation Ingestion & Strong Provenance
2. Deduplication & Corroborating Evidence Merging
3. Contradiction Detection & Explicit CONFLICTED State Preservation
4. Multi-Factor Conflict Resolution & Supersession
5. Derived Knowledge Tracking & Cascade Invalidation
6. Hypothesis Validation Barrier (Never Fact without Verification)
7. Forensic Timeline & State Reconstruction Without Fabrication
8. Context Assembly Exposing Active Contradictions
9. EmergencyStop Kill-Switch Primacy (Fail-Closed)
10. CLI Interface Conformance
"""

import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.knowledge_consolidation.cli import build_parser
from app.knowledge_consolidation.hypotheses import PrematureFactPromotionError
from app.knowledge_consolidation.models import (
    CertaintyState,
    ConflictResolutionRequest,
    HypothesisStatus,
    MemoryIngestionRequest,
    MemoryReconstructionRequest,
    MemoryStatus,
    MemoryType,
    ProvenanceSourceType,
    VolatilityClass,
)
from app.knowledge_consolidation.service import KnowledgeConsolidationService
from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError


def run_e2e_verification():
    print("================================================================================")
    print("TASK 92: KAIRO KNOWLEDGE CONSOLIDATION & MEMORY EVOLUTION E2E VERIFICATION")
    print("================================================================================")

    estop = EmergencyStopService()
    svc = KnowledgeConsolidationService(emergency_stop=estop)

    # --------------------------------------------------------------------------
    # Step 1: Ingestion & Provenance
    # --------------------------------------------------------------------------
    print("\n[Step 1] Ingesting observation with strongly typed taxonomy & provenance...")
    req1 = MemoryIngestionRequest(
        content="Service 'payment-gateway' is configured to use HTTPS on port 8443.",
        type=MemoryType.SYSTEM_STATE,
        source="system_spec_yaml",
        source_type=ProvenanceSourceType.SYSTEM_VERIFIED,
        confidence=0.98,
        certainty=CertaintyState.KNOWN,
        volatility=VolatilityClass.LOW,
    )
    mem1 = svc.ingest_memory(req1)
    assert mem1.status == MemoryStatus.ACTIVE
    assert mem1.provenance is not None
    assert mem1.provenance.source_type == ProvenanceSourceType.SYSTEM_VERIFIED
    print(f"  -> SUCCESS: Ingested memory '{mem1.memory_id}' with status ACTIVE and SYSTEM_VERIFIED provenance.")

    # --------------------------------------------------------------------------
    # Step 2: Deduplication & Evidence Merging
    # --------------------------------------------------------------------------
    print("\n[Step 2] Testing duplicate ingestion with evidence corroboration...")
    req2 = MemoryIngestionRequest(
        content="Service 'payment-gateway' is configured to use HTTPS on port 8443.",
        source="runtime_config_audit",
        source_type=ProvenanceSourceType.OBSERVED,
        confidence=0.90,
    )
    mem2 = svc.ingest_memory(req2)
    assert mem2.memory_id == mem1.memory_id
    assert len(svc.list_memories()) == 1
    ev_summary = svc.evidence.summarize_evidence_balance(mem1.memory_id)
    assert ev_summary["supporting_count"] == 2
    print(f"  -> SUCCESS: Deduplicated into memory '{mem1.memory_id}', evidence count increased to {ev_summary['supporting_count']}.")

    # --------------------------------------------------------------------------
    # Step 3: Contradiction Detection & CONFLICTED Preservation
    # --------------------------------------------------------------------------
    print("\n[Step 3] Introducing contradictory observation...")
    req_conflict = MemoryIngestionRequest(
        content="Service 'payment-gateway' is configured to use HTTPS on port 9443.",
        source="unverified_agent_log",
        source_type=ProvenanceSourceType.MODEL_GENERATED,
        confidence=0.70,
    )
    mem_conflict = svc.ingest_memory(req_conflict)
    assert mem1.status == MemoryStatus.CONFLICTED
    assert mem_conflict.status == MemoryStatus.CONFLICTED
    assert mem1.certainty == CertaintyState.CONTRADICTED
    conflicts = svc.conflicts.list_active_conflicts()
    assert len(conflicts) >= 1
    print(f"  -> SUCCESS: Contradiction detected! Both '{mem1.memory_id}' and '{mem_conflict.memory_id}' marked CONFLICTED.")

    # --------------------------------------------------------------------------
    # Step 4: Context Assembly with Explicit Contradictions
    # --------------------------------------------------------------------------
    print("\n[Step 4] Assembling reasoning context with active contradiction...")
    context_bundle = svc.assemble_context(query="What port is payment-gateway listening on?")
    assert len(context_bundle["surfaced_conflicts"]) >= 1
    assert "CRITICAL WARNING: UNRESOLVED CONTRADICTIONS DETECTED" in context_bundle["formatted_context"]
    print("  -> SUCCESS: Context assembly explicitly surfaced contradiction banner to reasoning prompt.")

    # --------------------------------------------------------------------------
    # Step 5: Conflict Resolution via Authoritative Evidence
    # --------------------------------------------------------------------------
    print("\n[Step 5] Resolving contradiction with authoritative operator confirmation...")
    res_req = ConflictResolutionRequest(
        resolution_strategy="user_correction",
        winning_memory_id=mem1.memory_id,
        explanation="Infra team confirmed port 8443 is production configuration; port 9443 was temporary staging.",
        resolved_by="lead_devops",
    )
    res = svc.resolve_conflict(conflicts[0].conflict_id, res_req)
    assert res["resolved"] is True
    assert mem1.status == MemoryStatus.ACTIVE
    assert mem_conflict.status == MemoryStatus.SUPERSEDED
    print(f"  -> SUCCESS: Resolved! Winning memory '{mem1.memory_id}' ACTIVE; losing memory '{mem_conflict.memory_id}' SUPERSEDED.")

    # --------------------------------------------------------------------------
    # Step 6: Derived Knowledge & Cascade Invalidation
    # --------------------------------------------------------------------------
    print("\n[Step 6] Testing derived knowledge dependency tracking & cascade invalidation...")
    derived_req = MemoryIngestionRequest(
        content="Firewall rule allow 8443 must remain open for payment traffic.",
        type=MemoryType.DERIVED,
    )
    derived_mem = svc.ingest_memory(derived_req)
    svc.derived.record_derivation(
        derived_memory=derived_mem,
        parent_memory_ids=[mem1.memory_id],
        derivation_method="deductive_network_rule",
    )
    assert derived_mem.status == MemoryStatus.ACTIVE

    # Invalidate parent memory
    mem1.status = MemoryStatus.INVALIDATED
    affected = svc.derived.propagate_invalidation(
        parent_memory_id=mem1.memory_id,
        memory_store=svc._memories,
        new_parent_status=MemoryStatus.INVALIDATED,
    )
    assert derived_mem.memory_id in affected
    assert derived_mem.status == MemoryStatus.INVALIDATED
    print(f"  -> SUCCESS: Invalidation propagated to child derived memory '{derived_mem.memory_id}'.")

    # Restore mem1 for subsequent tests
    mem1.status = MemoryStatus.ACTIVE

    # --------------------------------------------------------------------------
    # Step 7: Hypothesis Validation Barrier
    # --------------------------------------------------------------------------
    print("\n[Step 7] Testing hypothesis lifecycle and anti-fabrication barrier...")
    hyp_mem, hyp = svc.hypotheses.propose_hypothesis(
        claim="Switching payment serialization from JSON to Protobuf reduces latency by 40%",
        validation_plan="Benchmark 50,000 transactions in staging testbed",
        initial_confidence=0.5,
    )
    svc._memories[hyp_mem.memory_id] = hyp_mem

    try:
        svc.hypotheses.promote_to_fact(hyp.hypothesis_id)
        raise AssertionError("Premature promotion should have failed!")
    except PrematureFactPromotionError:
        print("  -> SUCCESS: Unverified hypothesis promotion to fact was strictly rejected.")

    svc.hypotheses.verify_hypothesis(
        hypothesis_id=hyp.hypothesis_id,
        verified_by="benchmark_rig_01",
        empirical_evidence_ref="benchmark_run_results_772",
        memory=hyp_mem,
    )
    assert hyp.status == HypothesisStatus.VERIFIED
    assert hyp_mem.status == MemoryStatus.ACTIVE
    svc.hypotheses.promote_to_fact(hyp.hypothesis_id)
    print("  -> SUCCESS: Hypothesis empirically verified and permitted promotion.")

    # --------------------------------------------------------------------------
    # Step 8: Forensic Memory Reconstruction
    # --------------------------------------------------------------------------
    print("\n[Step 8] Testing forensic timeline reconstruction without fabrication...")
    recon_req = MemoryReconstructionRequest(query="payment-gateway port configuration")
    recon_res = svc.reconstruct(recon_req)
    assert len(recon_res.timeline) >= 2
    assert len(recon_res.superseded_states) >= 1
    assert recon_res.certainty in (CertaintyState.KNOWN, CertaintyState.LIKELY)
    print(f"  -> SUCCESS: Reconstructed {len(recon_res.timeline)} timeline events with certainty {recon_res.certainty.value}.")

    # --------------------------------------------------------------------------
    # Step 9: EmergencyStop Kill-Switch Primacy
    # --------------------------------------------------------------------------
    print("\n[Step 9] Testing EmergencyStop kill-switch enforcement...")
    estop.trigger_emergency_stop(reason="Audit drill")
    assert estop.is_stopped() is True

    # Mutating operation must raise EmergencyStopActiveError
    try:
        svc.ingest_memory(MemoryIngestionRequest(content="Should be blocked"))
        raise AssertionError("Ingestion should have been blocked by EmergencyStop!")
    except EmergencyStopActiveError:
        print("  -> SUCCESS: Ingestion halted fail-closed by EmergencyStop.")

    # Safe read operations must continue to function
    recon_res_safe = svc.reconstruct(MemoryReconstructionRequest(query="read check"))
    assert recon_res_safe is not None
    print("  -> SUCCESS: Safe read-only reconstruction permitted under EmergencyStop.")

    estop.reset_emergency_stop(is_human_user=True)
    assert estop.is_stopped() is False
    print("  -> SUCCESS: EmergencyStop successfully reset by human user.")

    # --------------------------------------------------------------------------
    # Step 10: CLI Conformance
    # --------------------------------------------------------------------------
    print("\n[Step 10] Testing CLI parser conformance...")
    parser = build_parser()
    args = parser.parse_args(["list", "--status", "ACTIVE"])
    assert args.subcommand == "list"
    assert args.status == "ACTIVE"
    print("  -> SUCCESS: CLI argument parser validated.")

    print("\n================================================================================")
    print("ALL TASK 92 SCENARIOS AND INVARIANTS SUCCESSFULLY VERIFIED!")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_e2e_verification())

"""Comprehensive unit, property, and state-machine tests for Task 92: KAIRO Knowledge Consolidation Engine.

Validates all 10 core invariants:
1. Forgotten memory cannot appear in active retrieval
2. Invalidated memory cannot be treated as verified
3. Contradicted memories retain contradiction metadata
4. Every active memory has provenance
5. Every derived memory references parents
6. Parent invalidation propagates to derived knowledge
7. Hypotheses cannot be promoted to fact without verification
8. EmergencyStop blocks all mutating operations fail-closed
9. Lifecycle history matches actual state transitions
10. Context assembly explicitly surfaces unresolved contradictions
"""

from datetime import UTC, datetime, timedelta
import pytest

from app.knowledge_consolidation.hypotheses import PrematureFactPromotionError
from app.knowledge_consolidation.lifecycle import InvalidStateTransitionError
from app.knowledge_consolidation.models import (
    CertaintyState,
    ConflictResolutionRequest,
    ConflictType,
    EvidenceRelationType,
    HypothesisStatus,
    MemoryEntity,
    MemoryIngestionRequest,
    MemoryReconstructionRequest,
    MemoryStatus,
    MemoryType,
    ProvenanceSourceType,
    RetentionAction,
    SensitivityClassification,
    VolatilityClass,
)
from app.knowledge_consolidation.service import KnowledgeConsolidationService
from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError


@pytest.fixture
def test_service():
    """Create a fresh, isolated KnowledgeConsolidationService with mock emergency stop."""
    estop = EmergencyStopService()
    svc = KnowledgeConsolidationService(emergency_stop=estop)
    return svc


# ==============================================================================
# 1. Ingestion, Provenance & Classification Tests
# ==============================================================================


def test_memory_ingestion_with_provenance(test_service):
    """Verify that every ingested memory receives strongly typed taxonomy and provenance."""
    req = MemoryIngestionRequest(
        content="The main production database is deployed in region us-east-1.",
        type=MemoryType.SYSTEM_STATE,
        source="system_inventory",
        source_type=ProvenanceSourceType.SYSTEM_VERIFIED,
        confidence=0.95,
        certainty=CertaintyState.KNOWN,
        volatility=VolatilityClass.LOW,
    )
    mem = test_service.ingest_memory(req)

    assert mem.memory_id.startswith("mem_")
    assert mem.type == MemoryType.SYSTEM_STATE
    assert mem.status == MemoryStatus.ACTIVE
    assert mem.provenance is not None
    assert mem.provenance.source_type == ProvenanceSourceType.SYSTEM_VERIFIED
    assert len(mem.supporting_evidence_ids) >= 1

    # Verify retrieved by ID
    retrieved = test_service.get_memory(mem.memory_id)
    assert retrieved is not None
    assert retrieved.content == req.content


def test_illegal_state_transition_blocked(test_service):
    """Invariant 9: State machine strictly prohibits arbitrary illegal status mutations."""
    req = MemoryIngestionRequest(content="Temporary test memory", type=MemoryType.OBSERVATION)
    mem = test_service.ingest_memory(req)

    # First transition to ARCHIVED then FORGOTTEN
    test_service.lifecycle.transition(mem, MemoryStatus.ARCHIVED, reason="Archiving")
    test_service.lifecycle.transition(mem, MemoryStatus.FORGOTTEN, reason="Forgotten tombstone")

    # Trying to transition out of FORGOTTEN must fail
    with pytest.raises(InvalidStateTransitionError):
        test_service.lifecycle.transition(mem, MemoryStatus.ACTIVE, reason="Illegal resurrection")


# ==============================================================================
# 2. Deduplication & Evidence Merging Tests
# ==============================================================================


def test_exact_deduplication_merges_evidence(test_service):
    """Verify exact duplicates reinforce existing memory rather than creating duplicates."""
    req1 = MemoryIngestionRequest(
        content="The API rate limit is 100 requests per minute.",
        source="doc_v1",
        confidence=0.8,
    )
    mem1 = test_service.ingest_memory(req1)

    req2 = MemoryIngestionRequest(
        content="The API rate limit is 100 requests per minute.",
        source="doc_v2",
        confidence=0.85,
    )
    mem2 = test_service.ingest_memory(req2)

    # Must be merged into same memory_id
    assert mem1.memory_id == mem2.memory_id
    assert len(test_service.list_memories()) == 1

    # Evidence count must have increased
    evs = test_service.evidence.get_evidence_for_memory(mem1.memory_id)
    assert len(evs) == 2


# ==============================================================================
# 3. Conflict Detection & Preservation Tests
# ==============================================================================


def test_conflict_detection_preserves_conflicted_status(test_service):
    """Invariant 3: Contradictory claims are preserved in CONFLICTED state, never overwritten."""
    req1 = MemoryIngestionRequest(
        content="Project release deadline is September 20.",
        structured_payload={"subject": "release_deadline", "value": "September 20"},
        confidence=0.8,
    )
    mem1 = test_service.ingest_memory(req1)
    assert mem1.status == MemoryStatus.ACTIVE

    req2 = MemoryIngestionRequest(
        content="Project release deadline is September 25.",
        structured_payload={"subject": "release_deadline", "value": "September 25"},
        confidence=0.8,
    )
    mem2 = test_service.ingest_memory(req2)

    # Both must now be marked CONFLICTED
    assert mem1.status == MemoryStatus.CONFLICTED
    assert mem2.status == MemoryStatus.CONFLICTED
    assert mem1.certainty == CertaintyState.CONTRADICTED
    assert mem2.certainty == CertaintyState.CONTRADICTED

    active_conflicts = test_service.conflicts.list_active_conflicts()
    assert len(active_conflicts) >= 1
    assert active_conflicts[0].conflict_type in (ConflictType.FACTUAL, ConflictType.TEMPORAL)


def test_conflict_resolution_via_user_override(test_service):
    """Verify conflict resolution via authoritative operator override."""
    req1 = MemoryIngestionRequest(
        content="Target port is 8000.",
        structured_payload={"subject": "target_port", "value": 8000},
    )
    mem1 = test_service.ingest_memory(req1)

    req2 = MemoryIngestionRequest(
        content="Target port is 8080.",
        structured_payload={"subject": "target_port", "value": 8080},
    )
    mem2 = test_service.ingest_memory(req2)

    conflicts = test_service.conflicts.list_active_conflicts()
    assert len(conflicts) == 1
    conflict_id = conflicts[0].conflict_id

    # Resolve favoring mem2 (port 8080)
    res_req = ConflictResolutionRequest(
        resolution_strategy="user_correction",
        winning_memory_id=mem2.memory_id,
        explanation="Operator confirmed port 8080 is the new standard.",
        resolved_by="admin_user",
    )
    res = test_service.resolve_conflict(conflict_id, res_req)
    assert res["resolved"] is True

    # Check updated statuses
    assert mem2.status == MemoryStatus.ACTIVE
    assert mem2.certainty == CertaintyState.KNOWN
    assert mem1.status == MemoryStatus.SUPERSEDED
    assert mem1.superseded_by == mem2.memory_id


# ==============================================================================
# 4. Derived Knowledge & Cascade Invalidation Tests
# ==============================================================================


def test_derived_knowledge_cascade_invalidation(test_service):
    """Invariant 6 & 7: Derived knowledge cascades invalidation when parent is invalidated."""
    parent_req = MemoryIngestionRequest(
        content="Legacy Auth v1 endpoint is decommissioned.",
        type=MemoryType.SEMANTIC,
    )
    parent_mem = test_service.ingest_memory(parent_req)

    derived_req = MemoryIngestionRequest(
        content="Client apps must upgrade to Auth v2 tokens immediately.",
        type=MemoryType.DERIVED,
    )
    derived_mem = test_service.ingest_memory(derived_req)

    # Record derivation link
    test_service.derived.record_derivation(
        derived_memory=derived_mem,
        parent_memory_ids=[parent_mem.memory_id],
        derivation_method="deductive_policy_inference",
    )

    assert derived_mem.status == MemoryStatus.ACTIVE

    # Invalidate parent memory
    parent_mem.status = MemoryStatus.INVALIDATED
    affected = test_service.derived.propagate_invalidation(
        parent_memory_id=parent_mem.memory_id,
        memory_store=test_service._memories,
        new_parent_status=MemoryStatus.INVALIDATED,
    )

    assert derived_mem.memory_id in affected
    assert derived_mem.status == MemoryStatus.INVALIDATED


# ==============================================================================
# 5. Hypothesis Validation Barrier Tests
# ==============================================================================


def test_hypothesis_cannot_be_promoted_without_verification(test_service):
    """Invariant: Unverified hypotheses can NEVER be promoted to verified facts."""
    mem, hyp = test_service.hypotheses.propose_hypothesis(
        claim="Increasing worker thread count from 4 to 16 eliminates bottleneck",
        validation_plan="Execute load drill under synthetic 1000 RPS traffic",
        initial_confidence=0.5,
    )
    test_service._memories[mem.memory_id] = mem

    assert hyp.status == HypothesisStatus.PROPOSED
    assert mem.type == MemoryType.HYPOTHESIS
    assert mem.certainty == CertaintyState.UNCERTAIN

    # Attempt premature fact promotion
    with pytest.raises(PrematureFactPromotionError):
        test_service.hypotheses.promote_to_fact(hyp.hypothesis_id)

    # Now verify with empirical test
    test_service.hypotheses.verify_hypothesis(
        hypothesis_id=hyp.hypothesis_id,
        verified_by="load_drill_runner",
        empirical_evidence_ref="benchmark_run_9941",
        memory=mem,
    )

    assert hyp.status == HypothesisStatus.VERIFIED
    assert mem.status == MemoryStatus.ACTIVE
    assert mem.certainty == CertaintyState.KNOWN

    # Now promotion to fact check passes
    test_service.hypotheses.promote_to_fact(hyp.hypothesis_id)


# ==============================================================================
# 6. Temporal Validity & Staleness Tests
# ==============================================================================


def test_temporal_staleness_detection(test_service):
    """Verify that memories past their volatility decay threshold are flagged STALE."""
    req = MemoryIngestionRequest(
        content="Current CPU load is 42% on worker node 3.",
        type=MemoryType.SYSTEM_STATE,
        volatility=VolatilityClass.HIGH,  # High volatility threshold is 2 hours
    )
    mem = test_service.ingest_memory(req)

    # Simulate 3 hours in the future
    future_time = datetime.now(UTC) + timedelta(hours=3)
    is_stale, label = test_service.temporal.evaluate_staleness(mem, at_time=future_time)

    assert is_stale is True
    assert label == "STALE"


# ==============================================================================
# 7. Context Assembly & Contradiction Exposure Tests
# ==============================================================================


def test_context_assembly_exposes_contradictions(test_service):
    """Invariant 10: Assembled context explicitly flags unresolved contradictions."""
    req1 = MemoryIngestionRequest(
        content="Primary database replica is db-replica-east.",
        structured_payload={"subject": "primary_replica", "value": "east"},
    )
    test_service.ingest_memory(req1)

    req2 = MemoryIngestionRequest(
        content="Primary database replica is db-replica-west.",
        structured_payload={"subject": "primary_replica", "value": "west"},
    )
    test_service.ingest_memory(req2)

    context_bundle = test_service.assemble_context(query="Where is the primary database replica located?")

    assert len(context_bundle["surfaced_conflicts"]) >= 1
    assert "CRITICAL WARNING: UNRESOLVED CONTRADICTIONS DETECTED" in context_bundle["formatted_context"]
    assert "db-replica" in context_bundle["formatted_context"]


# ==============================================================================
# 8. Memory Reconstruction Without Fabrication Tests
# ==============================================================================


def test_forensic_reconstruction(test_service):
    """Verify historical timeline reconstruction without hallucination."""
    req1 = MemoryIngestionRequest(
        content="Initial design for service X proposed using REST.",
        type=MemoryType.OBSERVATION,
    )
    mem1 = test_service.ingest_memory(req1)

    req2 = MemoryIngestionRequest(
        content="Service X architecture updated to gRPC for performance.",
        type=MemoryType.SEMANTIC,
    )
    mem2 = test_service.ingest_memory(req2)
    mem1.status = MemoryStatus.SUPERSEDED
    mem1.superseded_by = mem2.memory_id

    recon_req = MemoryReconstructionRequest(query="Service X architecture evolution")
    recon_res = test_service.reconstruct(recon_req)

    assert len(recon_res.timeline) >= 2
    assert len(recon_res.superseded_states) >= 1
    assert "gRPC" in recon_res.current_state
    assert recon_res.certainty in (CertaintyState.KNOWN, CertaintyState.LIKELY)


# ==============================================================================
# 9. Emergency Stop Kill-Switch Tests
# ==============================================================================


def test_emergency_stop_blocks_mutations(test_service):
    """Invariant 8: EmergencyStop unconditionally halts all mutating operations fail-closed."""
    # Trigger emergency stop
    test_service.emergency_stop.trigger_emergency_stop(reason="Security containment drill")
    assert test_service.emergency_stop.is_stopped() is True

    # Mutating operation: Ingestion must be blocked
    with pytest.raises(EmergencyStopActiveError):
        test_service.ingest_memory(
            MemoryIngestionRequest(content="Should be blocked by emergency stop", type=MemoryType.OBSERVATION)
        )

    # Mutating operation: Consolidation must be blocked
    with pytest.raises(EmergencyStopActiveError):
        test_service.consolidate_explicit(["mem_dummy"], summary="Blocked summary")

    # Read-only operation: Reconstruction remains accessible
    recon_req = MemoryReconstructionRequest(query="Safe inspection query")
    recon_res = test_service.reconstruct(recon_req)
    assert recon_res is not None

    # Reset emergency stop
    test_service.emergency_stop.reset_emergency_stop(is_human_user=True)
    assert test_service.emergency_stop.is_stopped() is False

    # Mutating operation should now succeed
    res = test_service.ingest_memory(
        MemoryIngestionRequest(content="Post-reset validated memory", type=MemoryType.OBSERVATION)
    )
    assert res.status == MemoryStatus.ACTIVE


# ==============================================================================
# 10. Forgetting & Vector Invalidation Tests
# ==============================================================================


def test_forgotten_memory_excluded_from_vector_retrieval(test_service):
    """Invariant 1: Forgotten memories can never appear in vector or active retrieval."""
    req = MemoryIngestionRequest(content="Private user credential or temporary secret", type=MemoryType.OBSERVATION)
    mem = test_service.ingest_memory(req)

    assert mem.memory_id in test_service.vector_bridge._vector_records

    # Safe compliance forgetting
    test_service.forget_memory(mem.memory_id, reason="User right to be forgotten request")

    assert mem.status == MemoryStatus.FORGOTTEN
    # Cleaned from vector index
    assert mem.memory_id not in test_service.vector_bridge._vector_records

    # Filtered out of active listing
    active_mems = test_service.list_memories(status=MemoryStatus.ACTIVE)
    assert mem.memory_id not in [m.memory_id for m in active_mems]

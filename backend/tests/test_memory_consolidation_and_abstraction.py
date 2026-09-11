"""Unit tests for Deduplication, Autonomous Consolidation, and Hierarchical Abstraction (Task 68)."""

from datetime import UTC, datetime

from app.memory_consolidation.consolidation import AutonomousConsolidationEngine
from app.memory_consolidation.deduplication import DeduplicationEngine
from app.memory_consolidation.schemas import (
    AbstractionLevel,
    CognitiveClassification,
    DurableMemory,
    MemoryLifecycleState,
    MemoryProvenance,
    MemoryType,
)
from app.memory_consolidation.worker import AutonomousConsolidationWorker


def test_deduplication_exact_and_near():
    """Verify exact hash and near token duplicate detection."""
    now = datetime.now(UTC)
    m1 = DurableMemory(
        content="Primary PostgreSQL database running on host db-01 port 5432.",
        status=MemoryLifecycleState.ACTIVE,
        tenant_id="t1",
        observed_at=now,
    )
    m2 = DurableMemory(
        content="Kubernetes ingress controller handles SSL termination via cert-manager.",
        status=MemoryLifecycleState.ACTIVE,
        tenant_id="t1",
        observed_at=now,
    )

    existing = [m1, m2]

    # Exact duplicate
    dup, score, match_type = DeduplicationEngine.find_duplicate(
        "primary postgresql database running on host db-01 port 5432", existing
    )
    assert dup is not None
    assert dup.memory_id == m1.memory_id
    assert match_type == "EXACT_HASH_MATCH"
    assert score == 1.0

    # Near duplicate
    dup_near, score_near, match_near = DeduplicationEngine.find_duplicate(
        "PostgreSQL database running on host db-01 port 5432 with active connections", existing
    )
    assert dup_near is not None
    assert dup_near.memory_id == m1.memory_id
    assert match_near == "NEAR_DUPLICATE_SIMILARITY"
    assert score_near > 0.65


def test_repetition_does_not_inflate_confidence():
    """INVARIANT: Simple repetition from correlated/dependent sources does not prove truth (Spec 8, 19)."""
    now = datetime.now(UTC)
    canonical = DurableMemory(
        content="Server node-04 is reporting memory pressure.",
        confidence=0.70,
        provenance=MemoryProvenance(source_refs=["agent_alpha"]),
        observed_at=now,
    )

    initial_conf = canonical.confidence

    # Merging repeated observation from dependent/correlated source
    DeduplicationEngine.merge_references_into_canonical(
        canonical, duplicate_source_ref="agent_beta", is_independent_source=False
    )
    assert canonical.confidence == initial_conf  # Must NOT increase
    assert "agent_beta" in canonical.provenance.source_refs


def test_hierarchical_abstraction_consolidation():
    """Verify episodic memories are clustered and elevated to next abstraction tier (Spec 9, 10)."""
    now = datetime.now(UTC)
    cluster = [
        DurableMemory(
            content="Task worker A executed database migration 0041 successfully.",
            abstraction_level=AbstractionLevel.RAW_OBSERVATION,
            memory_type=MemoryType.EPISODIC_MEMORY,
            confidence=0.85,
            importance=0.6,
            structured_payload={"domain": "database", "entities": ["migration_0041", "postgres"]},
            observed_at=now,
        ),
        DurableMemory(
            content="Task worker B executed database migration 0042 successfully.",
            abstraction_level=AbstractionLevel.RAW_OBSERVATION,
            memory_type=MemoryType.EPISODIC_MEMORY,
            confidence=0.85,
            importance=0.6,
            structured_payload={"domain": "database", "entities": ["migration_0042", "postgres"]},
            observed_at=now,
        ),
    ]

    candidate, consolidated = AutonomousConsolidationEngine.consolidate_cluster(cluster, tenant_id="t_cns")

    # Verify next tier abstraction
    assert consolidated.abstraction_level == AbstractionLevel.EPISODE
    assert consolidated.cognitive_type == CognitiveClassification.SUMMARY
    assert consolidated.memory_type == MemoryType.SEMANTIC_MEMORY
    # Invariant: Summaries preserve parent source IDs
    assert consolidated.provenance.derived_from_ids is not None
    assert len(consolidated.provenance.derived_from_ids) >= 1
    assert (
        consolidated.provenance.is_independent_source is False
    )  # Derived is not independent empirical source


def test_worker_sweep_idempotency():
    """Verify autonomous consolidation worker sweeps are idempotent (Spec 26, 30, 32)."""
    now = datetime.now(UTC)
    memories = [
        DurableMemory(
            memory_id="mem_ep_1",
            content="API gateway timeout on endpoint /v1/orders.",
            memory_type=MemoryType.EPISODIC_MEMORY,
            status=MemoryLifecycleState.ACTIVE,
            structured_payload={"domain": "orders_api", "entities": ["gateway", "orders"]},
            observed_at=now,
        ),
        DurableMemory(
            memory_id="mem_ep_2",
            content="API gateway retry succeeded for /v1/orders.",
            memory_type=MemoryType.EPISODIC_MEMORY,
            status=MemoryLifecycleState.ACTIVE,
            structured_payload={"domain": "orders_api", "entities": ["gateway", "orders"]},
            observed_at=now,
        ),
    ]

    worker = AutonomousConsolidationWorker(tenant_id="tenant_sweep")

    # First sweep: performs consolidation
    res1 = worker.run_sweep(memories)
    assert res1["new_consolidations_created"] == 1

    # Second sweep: idempotent check prevents duplicate creation
    res2 = worker.run_sweep(memories)
    assert res2["new_consolidations_created"] == 0

"""Unit tests for Multi-Factor Explainable Retrieval and Cognitive Context Assembly (Task 68)."""

from datetime import UTC, datetime

from app.memory_consolidation.retrieval import MemoryRetrievalEngine
from app.memory_consolidation.schemas import (
    CognitiveClassification,
    ContextAssemblyRequest,
    DurableMemory,
    MemoryLifecycleState,
    MemorySearchRequest,
    MemoryType,
    TrustLevel,
)


def test_explainable_multi_factor_search():
    """Verify search returns explainable scoring breakdown and justification reasons (Spec 20, 21)."""
    now = datetime.now(UTC)
    memories = [
        DurableMemory(
            memory_id="mem_auth",
            content="OAuth2 token validation configured via Keycloak identity provider.",
            cognitive_type=CognitiveClassification.VERIFIED_FACT,
            memory_type=MemoryType.SEMANTIC_MEMORY,
            trust_level=TrustLevel.VERIFIED,
            importance=0.9,
            confidence=0.95,
            status=MemoryLifecycleState.ACTIVE,
            observed_at=now,
        ),
        DurableMemory(
            memory_id="mem_other",
            content="Frontend UI assets cached in Cloudflare CDN edge servers.",
            cognitive_type=CognitiveClassification.MEMORY,
            memory_type=MemoryType.EPISODIC_MEMORY,
            importance=0.4,
            confidence=0.7,
            status=MemoryLifecycleState.ACTIVE,
            observed_at=now,
        ),
    ]

    req = MemorySearchRequest(query="Keycloak OAuth2 validation", top_k=5)
    results = MemoryRetrievalEngine.search(memories, req)

    assert len(results) >= 1
    top = results[0]
    assert top.memory.memory_id == "mem_auth"
    assert top.composite_score > 0.5
    assert top.verification_state == TrustLevel.VERIFIED.value
    # Explainable justification assertions
    assert "relevance" in top.retrieval_reason.lower() or "match" in top.retrieval_reason.lower()
    assert "verification" in top.retrieval_reason.lower() or "verified" in top.retrieval_reason.lower()


def test_context_assembly_cognitive_partitioning():
    """Verify context assembly strictly partitions memory into cognitive blocks with token bounds (Spec 2, 22)."""
    now = datetime.now(UTC)
    memories = [
        DurableMemory(
            memory_id="mem_fact",
            content="Production Kubernetes cluster uses Calico CNI networking.",
            cognitive_type=CognitiveClassification.VERIFIED_FACT,
            trust_level=TrustLevel.VERIFIED,
            importance=0.85,
            confidence=0.95,
            status=MemoryLifecycleState.ACTIVE,
            observed_at=now,
        ),
        DurableMemory(
            memory_id="mem_claim",
            content="Claim from external documentation: service mesh proxy adds 1ms latency.",
            cognitive_type=CognitiveClassification.CLAIM,
            trust_level=TrustLevel.UNVERIFIED,
            importance=0.6,
            confidence=0.65,
            status=MemoryLifecycleState.ACTIVE,
            observed_at=now,
        ),
        DurableMemory(
            memory_id="mem_sim",
            content="Simulated scenario: 50% node drain causes memory spike on remaining pods.",
            cognitive_type=CognitiveClassification.SIMULATION,
            importance=0.5,
            confidence=0.6,
            status=MemoryLifecycleState.ACTIVE,
            observed_at=now,
        ),
    ]

    req = ContextAssemblyRequest(
        task_intent="Kubernetes cluster configuration",
        max_tokens=2000,
        include_simulations=True,
    )
    result = MemoryRetrievalEngine.assemble_context(memories, req)

    assert len(result.facts) >= 1
    assert any("Calico CNI" in f for f in result.facts)

    # Invariant: Simulations demarcated in distinct section
    assert len(result.simulations) >= 1
    assert any("Simulated scenario" in s for s in result.simulations)

    # Invariant: Prompt injection defense wrapper applied
    assert "[CONTEXT_DATA" in result.context_string
    assert "INSTRUCTION_PRIORITY=NONE" in result.context_string

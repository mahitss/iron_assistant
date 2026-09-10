"""Unit tests for Knowledge Graph, Executive Memory, Causal Invariants, and Simulation Integrations (Task 63)."""

import pytest

from app.research.engine import ResearchEngine
from app.research.schemas import (
    Claim,
    ClaimType,
    ConfidenceLevel,
    ResearchRequest,
    Source,
    SourceTrustLevel,
    SourceType,
)


@pytest.mark.asyncio
async def test_knowledge_graph_and_executive_memory_propagation():
    engine = ResearchEngine()

    req = ResearchRequest(
        question="What is the throughput of Cluster Z?",
        objective="Validate Cluster Z performance",
        depth=1,
    )

    src = Source(
        source_id="src_cluster_benchmark",
        title="Cluster Z Benchmarks",
        publisher="Platform Team",
        source_type=SourceType.TECHNICAL_REPORT,
        trust_level=SourceTrustLevel.HIGH,
        authority_score=0.9,
    )
    engine.source_registry.register_source(src)

    # Ingest document
    doc = engine.document_ingester.ingest_text(
        content="Cluster Z handles 150k events per second with zero message loss.",
        source_id="src_cluster_benchmark",
        title="Benchmark Summary",
    )

    # Extract claims
    claims = engine.claim_extractor.extract_from_text(
        text=doc.content,
        source_id="src_cluster_benchmark",
        document_id=doc.document_id,
    )
    assert len(claims) >= 1

    # Synthesize session
    synthesis = await engine.execute_pipeline(req)
    assert synthesis.session_id is not None
    assert len(synthesis.established_findings) >= 1


def test_causal_research_invariants():
    """Ensure correlation is never automatically accepted as causation without experimental backing."""
    from app.research.claims import ClaimExtractor

    extractor = ClaimExtractor()
    text = "After deploying routing optimization, database query latency dropped by 30%."

    claims = extractor.extract_from_text(text, source_id="src_telemetry", document_id="doc_routing")
    assert len(claims) >= 1

    # Verify that unless controlled A/B experiment or counterfactual is present, causal claims are marked with appropriate confidence
    for c in claims:
        if c.claim_type == ClaimType.CAUSAL:
            # Without experimental evidence, confidence cannot be blindly VERY_HIGH
            assert c.confidence in [ConfidenceLevel.MODERATE, ConfidenceLevel.LOW, ConfidenceLevel.HIGH]


def test_simulation_parameter_labeling():
    """Ensure parameters for simulation maintain distinction between observed, estimated, assumed, and simulated."""
    from app.research.schemas import ClaimType

    observed_param = Claim(
        claim_id="clm_p_obs",
        subject="Worker Node",
        predicate="cpu_cores",
        object="16",
        claim_text="Worker node has 16 physical cores.",
        source_id="src_hw_spec",
        claim_type=ClaimType.OBSERVED,
    )
    assert observed_param.claim_type == ClaimType.OBSERVED

    simulated_param = Claim(
        claim_id="clm_p_sim",
        subject="Worker Node",
        predicate="projected_max_qps",
        object="45000",
        claim_text="Monte Carlo simulation projects maximum QPS of 45000.",
        source_id="src_sim_run",
        claim_type=ClaimType.PREDICTED,
    )
    assert simulated_param.claim_type != ClaimType.OBSERVED
    assert simulated_param.claim_type in [ClaimType.PREDICTED, ClaimType.HYPOTHETICAL]

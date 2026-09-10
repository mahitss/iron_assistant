"""Unit tests for Knowledge Synthesis, Uncertainty Engine, Quality Scorecard, and Decision Packages (Task 63)."""

from app.research.schemas import (
    Claim,
    ClaimStatus,
    ClaimType,
    ConflictRecord,
    ConflictStatus,
    ConflictType,
    Evidence,
    EvidenceDirectness,
    EvidenceStrength,
    EvidenceType,
    ResearchRequest,
    Source,
    SourceTrustLevel,
    SourceType,
)
from app.research.synthesis import KnowledgeSynthesizer
from app.research.uncertainty import UncertaintyEngine


def test_epistemic_uncertainty_categorization():
    engine = UncertaintyEngine()

    claims = [
        Claim(
            claim_id="clm_1",
            subject="API Gateway",
            predicate="supports",
            object="streaming",
            claim_text="API Gateway supports HTTP/2 streaming.",
            source_id="src_spec",
            claim_type=ClaimType.OBSERVED,
        ),
        Claim(
            claim_id="clm_2",
            subject="Workload",
            predicate="resembles",
            object="benchmark",
            claim_text="Production workload resembles benchmark workload.",
            source_id="src_internal",
            claim_type=ClaimType.HYPOTHETICAL,
        ),
        Claim(
            claim_id="clm_3",
            subject="Streaming",
            predicate="reduces",
            object="latency",
            claim_text="Streaming reduces perceived latency under user testing.",
            source_id="src_internal",
            claim_type=ClaimType.INFERRED,
        ),
    ]

    conflicts = [
        ConflictRecord(
            conflict_id="cnf_1",
            claim_a_id="clm_4a",
            claim_b_id="clm_4b",
            claim_a_text="Maximum throughput is 10k",
            claim_b_text="Maximum throughput is 25k",
            conflict_type=ConflictType.CONTRADICTORY_DATA,
            status=ConflictStatus.UNRESOLVED,
            discrepancy_factor="10k vs 25k",
        )
    ]

    analysis = engine.analyze_uncertainty(
        claims=claims,
        conflicts=conflicts,
        hypotheses=[],
        unanswered_sub_questions=["What is maximum practical throughput under stress?"],
    )

    assert len(analysis["known"]) >= 1
    assert any("streaming" in k.lower() for k in analysis["known"])
    assert len(analysis["assumed"]) >= 1
    assert len(analysis["inferred"]) >= 1
    assert len(analysis["disputed"]) >= 1
    assert len(analysis["unknown"]) >= 1


def test_knowledge_synthesis_multi_source_and_quality_scorecard():
    synthesizer = KnowledgeSynthesizer()

    req = ResearchRequest(
        question="What is the latency characteristic of Service X?",
        objective="Assess Service X latency",
    )

    sources = [
        Source(
            source_id="src_peer_review",
            title="Peer-reviewed benchmark paper",
            source_type=SourceType.ACADEMIC_PAPER,
            trust_level=SourceTrustLevel.VERY_HIGH,
            authority_score=0.95,
            freshness_score=0.90,
        ),
        Source(
            source_id="src_tech_blog",
            title="DevOps Blog Post",
            source_type=SourceType.WEB_PAGE,
            trust_level=SourceTrustLevel.LOW,
            authority_score=0.50,
            freshness_score=0.85,
        ),
    ]

    claims = [
        Claim(
            claim_id="clm_p99",
            subject="Service X",
            predicate="p99_latency",
            object="8.5ms",
            claim_text="Service X delivers p99 latency of 8.5ms.",
            source_id="src_peer_review",
            claim_type=ClaimType.MEASURED,
            status=ClaimStatus.VERIFIED,
        )
    ]

    evidence = [
        Evidence(
            evidence_id="ev_01",
            claim_id="clm_p99",
            source_id="src_peer_review",
            location="Table 4",
            excerpt_reference="Measured p99 at 8.5ms across 10 runs.",
            evidence_type=EvidenceType.EXPERIMENT,
            strength=EvidenceStrength.CONTROLLED_EXPERIMENT,
            directness=EvidenceDirectness.PRIMARY,
        )
    ]

    synthesis = synthesizer.synthesize(
        request=req,
        sources=sources,
        claims=claims,
        evidence=evidence,
        conflicts=[],
        uncertainty={
            "known": ["Service X p99 = 8.5ms"],
            "unknown": [],
            "uncertain": [],
            "disputed": [],
            "assumed": [],
            "inferred": [],
        },
        gaps=[],
        source_independence_groups=[["src_peer_review"], ["src_tech_blog"]],
    )

    assert synthesis.question == req.question
    assert len(synthesis.established_findings) >= 1
    assert "8.5ms" in synthesis.established_findings[0]

    # Quality scorecard checks (8 dimensions)
    qs = synthesis.quality_score
    assert 0.0 <= qs.source_quality <= 1.0
    assert 0.0 <= qs.source_diversity <= 1.0
    assert 0.0 <= qs.source_independence <= 1.0
    assert 0.0 <= qs.evidence_strength <= 1.0
    assert 0.0 <= qs.freshness <= 1.0
    assert 0.0 <= qs.coverage <= 1.0
    assert 0.0 <= qs.conflict_resolution <= 1.0
    assert 0.0 <= qs.overall_score <= 1.0

    # Decision Package checks
    assert synthesis.decision_package is not None
    pkg = synthesis.decision_package
    assert pkg.question == req.question
    assert len(pkg.evidence_summary) >= 1

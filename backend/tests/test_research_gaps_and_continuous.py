"""Unit tests for Knowledge Gap Detection, Follow-up Questions, Knowledge Decay, and Continuous Change Detection (Task 63)."""

from datetime import datetime, timedelta, timezone

from app.research.claims import ClaimExtractor
from app.research.continuous import ContinuousResearchEngine
from app.research.gaps import KnowledgeGapDetector
from app.research.schemas import (
    Claim,
    ClaimType,
    ConflictRecord,
    ConflictStatus,
    ConflictType,
    Source,
    SourceType,
)
from app.research.sources import SourceRegistry


def test_knowledge_gap_detection_and_follow_up_generation():
    detector = KnowledgeGapDetector()

    # Sub-questions asked vs claims extracted
    sub_questions = [
        "What is the compute cost of Option A?",
        "What is the storage and network cost of Option A?",
        "What is the failure tolerance of Option A under partition?",
    ]

    claims = [
        Claim(
            claim_id="clm_compute",
            subject="Option A",
            predicate="compute_cost",
            object="$500/mo",
            claim_text="Option A compute cost is $500 per month.",
            source_id="src_billing",
            claim_type=ClaimType.MEASURED,
        )
    ]

    conflicts = [
        ConflictRecord(
            conflict_id="cnf_partition",
            claim_a_id="clm_p1",
            claim_b_id="clm_p2",
            claim_a_text="Option A handles partition safely",
            claim_b_text="Option A splits brain during partition",
            conflict_type=ConflictType.CONTRADICTORY_DATA,
            status=ConflictStatus.UNRESOLVED,
            discrepancy_factor="safe vs split-brain",
        )
    ]

    gaps = detector.detect_gaps(
        sub_questions=sub_questions,
        claims=claims,
        conflicts=conflicts,
    )

    assert len(gaps) >= 1
    # Gaps should identify missing storage/network cost or partition failure
    descriptions = [g.description.lower() for g in gaps]
    assert any("storage" in d or "cost" in d or "partition" in d or "unresolved" in d for d in descriptions)

    follow_ups = detector.generate_follow_up_questions(gaps)
    assert len(follow_ups) >= 1
    assert any("?" in q for q in follow_ups)


def test_knowledge_decay_scoring():
    engine = ContinuousResearchEngine()

    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=730)  # 2 years old

    # Tech API docs decay quickly
    decay_api = engine.calculate_decay_score(
        domain_volatility="HIGH",
        published_at=old_date,
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
    )

    # Academic paper or mathematical theorem decays very slowly
    decay_math = engine.calculate_decay_score(
        domain_volatility="LOW",
        published_at=old_date,
        source_type=SourceType.ACADEMIC_PAPER,
    )

    assert decay_api > decay_math
    assert 0.0 <= decay_api <= 1.0
    assert 0.0 <= decay_math <= 1.0


def test_continuous_research_source_change_and_invalidation():
    registry = SourceRegistry()
    extractor = ClaimExtractor()
    engine = ContinuousResearchEngine()

    src = Source(
        source_id="src_vendor_api",
        title="Vendor API Docs v1",
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
        authority_score=0.9,
    )
    registry.register_source(src)

    claim = extractor.create_claim(
        subject="Vendor API",
        predicate="supports",
        object="v1 endpoints",
        claim_text="Vendor API supports v1 endpoints indefinitely.",
        source_id="src_vendor_api",
        claim_type=ClaimType.OBSERVED,
    )

    # Invalidate source (e.g. deprecation/change detected)
    events = engine.detect_and_propagate_change(
        source_id="src_vendor_api",
        change_type="API_VERSION_DEPRECATION",
        description="Vendor announced deprecation of v1 endpoints.",
        affected_claims=[claim],
        affected_decisions=["dec_arch_v1"],
        affected_plans=["plan_migration_2026"],
    )

    assert len(events) >= 1
    event = events[0]
    assert event.source_id == "src_vendor_api"
    assert "dec_arch_v1" in event.affected_decisions
    assert "plan_migration_2026" in event.affected_plans

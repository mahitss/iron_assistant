"""Unit tests for Evidence Linking, Strength Hierarchy, and Conflict Detection (Task 63)."""

from app.research.conflicts import ConflictDetector
from app.research.evidence import EvidenceManager
from app.research.schemas import (
    Claim,
    ClaimType,
    ConflictStatus,
    ConflictType,
    EvidenceDirectness,
    EvidenceStrength,
    EvidenceType,
)


def test_evidence_linking_and_strength_hierarchy():
    manager = EvidenceManager()

    ev1 = manager.create_evidence(
        claim_id="clm_001",
        source_id="src_telemetry",
        location="metrics.prom:L45",
        excerpt_reference="Measured p99 latency 18.4ms over 1,000,000 requests.",
        evidence_type=EvidenceType.MEASUREMENT,
        strength=EvidenceStrength.DIRECT_MEASUREMENT,
        directness=EvidenceDirectness.PRIMARY,
    )
    assert ev1.strength == EvidenceStrength.DIRECT_MEASUREMENT
    assert ev1.directness == EvidenceDirectness.PRIMARY

    ev2 = manager.create_evidence(
        claim_id="clm_001",
        source_id="src_blog",
        location="page.html:p3",
        excerpt_reference="A blogger noted that latency felt roughly 20ms.",
        evidence_type=EvidenceType.DOCUMENT_STATEMENT,
        strength=EvidenceStrength.UNVERIFIED_ASSERTION,
        directness=EvidenceDirectness.TERTIARY,
    )
    assert ev2.strength == EvidenceStrength.UNVERIFIED_ASSERTION

    # Weight comparison: direct measurement strictly outranks unverified assertion
    weight1 = manager.get_strength_weight(ev1.strength)
    weight2 = manager.get_strength_weight(ev2.strength)
    assert weight1 > weight2
    assert weight1 >= 0.95
    assert weight2 <= 0.35


def test_conflict_detection_numerical_contradiction():
    detector = ConflictDetector()

    claim_a = Claim(
        claim_id="clm_lat_a",
        subject="System X",
        predicate="latency",
        object="200ms",
        claim_text="System X latency is 200ms.",
        source_id="src_vendor_report",
        claim_type=ClaimType.MEASURED,
    )

    claim_b = Claim(
        claim_id="clm_lat_b",
        subject="System X",
        predicate="latency",
        object="350ms",
        claim_text="System X latency is 350ms under standard test suite.",
        source_id="src_independent_lab",
        claim_type=ClaimType.MEASURED,
    )

    conflicts = detector.detect_conflicts([claim_a, claim_b])
    assert len(conflicts) >= 1
    conflict = conflicts[0]
    assert conflict.conflict_type in [
        ConflictType.CONTRADICTORY_DATA,
        ConflictType.METHODOLOGY_DIFFERENCE,
        ConflictType.ENVIRONMENT_DIFFERENCE,
        ConflictType.MEASUREMENT_DISCREPANCY,
        ConflictType.DIRECT_CONTRADICTION,
    ]
    assert conflict.status == ConflictStatus.UNRESOLVED
    assert "200ms" in conflict.claim_a_text
    assert "350ms" in conflict.claim_b_text


def test_conflict_detection_reconciliation_factors():
    detector = ConflictDetector()

    claim_old = Claim(
        claim_id="clm_v1",
        subject="Protocol Y",
        predicate="throughput",
        object="10k",
        claim_text="Protocol Y achieves 10k qps in 2024 deployment.",
        source_id="src_2024",
        claim_type=ClaimType.MEASURED,
    )

    claim_new = Claim(
        claim_id="clm_v2",
        subject="Protocol Y",
        predicate="throughput",
        object="50k",
        claim_text="Protocol Y achieves 50k qps in 2026 deployment.",
        source_id="src_2026",
        claim_type=ClaimType.MEASURED,
    )

    # Both claims describe Protocol Y throughput, but differ in temporal scope
    conflicts = detector.detect_conflicts([claim_old, claim_new])
    if conflicts:
        conflict = conflicts[0]
        # Should flag discrepancy or environment/version differences
        assert conflict.discrepancy_factor != ""

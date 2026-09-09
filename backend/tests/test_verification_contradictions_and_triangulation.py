"""Tests for Contradiction Detection, Authority Resolution, and Triangulation (Task 42)."""

from datetime import datetime, timedelta, timezone
import pytest
from app.verification.claims import Claim, ClaimType, TruthStatus
from app.verification.contradictions import ContradictionEngine, ContradictionType
from app.verification.evidence import Evidence, EvidenceType
from app.verification.triangulation import SourceTriangulator


def test_direct_conflict_detection():
    """Conflicting states for the same resource at same time produce DIRECT_CONFLICT (Spec 74)."""
    engine = ContradictionEngine()
    now = datetime.now(timezone.utc)

    c1 = Claim(
        claim_id="clm-1",
        statement="Worker service is RUNNING",
        subject="worker_service",
        predicate="state",
        object_ref="RUNNING",
        observed_at=now,
    )
    c2 = Claim(
        claim_id="clm-2",
        statement="Worker service is STOPPED",
        subject="worker_service",
        predicate="state",
        object_ref="STOPPED",
        observed_at=now,
    )

    conflicts = engine.detect_conflicts(c1, [c2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ContradictionType.DIRECT_CONFLICT
    assert conflicts[0].target_claim_id == "clm-1"
    assert conflicts[0].conflicting_claim_id == "clm-2"


def test_scope_isolation_no_conflict():
    """Claims referring to different projects or users must not conflict (Spec 76)."""
    engine = ContradictionEngine()
    now = datetime.now(timezone.utc)

    c_proj1 = Claim(
        claim_id="clm-p1",
        statement="Build status SUCCESS",
        subject="ci_build",
        predicate="status",
        object_ref="SUCCESS",
        scope={"project_id": "project_alpha"},
        observed_at=now,
    )
    c_proj2 = Claim(
        claim_id="clm-p2",
        statement="Build status FAILED",
        subject="ci_build",
        predicate="status",
        object_ref="FAILED",
        scope={"project_id": "project_beta"},
        observed_at=now,
    )

    conflicts = engine.detect_conflicts(c_proj1, [c_proj2])
    assert len(conflicts) == 0


def test_authority_hierarchy_resolution():
    """Direct observation has higher authority than model assertion (Spec 77)."""
    engine = ContradictionEngine()
    now = datetime.now(timezone.utc)

    c_model = Claim(
        claim_id="c-mod",
        statement="Server is healthy",
        subject="server",
        predicate="status",
        object_ref="healthy",
        claim_type=ClaimType.MODEL_ASSERTION,
        observed_at=now,
    )
    c_obs = Claim(
        claim_id="c-obs",
        statement="Server is down",
        subject="server",
        predicate="status",
        object_ref="down",
        claim_type=ClaimType.STATE,
        source="direct_observation",
        observed_at=now,
    )

    winner = engine.resolve_conflict(c_model, c_obs)
    assert winner.claim_id == c_obs.claim_id


def test_temporal_conflict_newer_state_wins():
    """A newer verified observation supersedes an older observation (Spec 35, 165)."""
    engine = ContradictionEngine()
    t_old = datetime.now(timezone.utc) - timedelta(hours=2)
    t_new = datetime.now(timezone.utc)

    c_old_fail = Claim(
        claim_id="c-old",
        statement="Service down",
        subject="payment_gw",
        predicate="status",
        object_ref="down",
        claim_type=ClaimType.STATE,
        observed_at=t_old,
    )
    c_new_ok = Claim(
        claim_id="c-new",
        statement="Service operational",
        subject="payment_gw",
        predicate="status",
        object_ref="operational",
        claim_type=ClaimType.STATE,
        observed_at=t_new,
    )

    winner = engine.resolve_conflict(c_old_fail, c_new_ok)
    assert winner.claim_id == c_new_ok.claim_id


def test_triangulation_independent_sources():
    """Triangulating across 2 independent sources corroborates claim as VERIFIED (Spec 33)."""
    triangulator = SourceTriangulator(min_independent_sources=2)
    claim = Claim(
        claim_id="clm-release",
        statement="Release deployed",
        subject="release",
        predicate="status",
        object_ref="success",
    )

    ev1 = Evidence(
        evidence_id="ev-api",
        source_type=EvidenceType.API_RESPONSE,
        source_reference="deploy_gateway",
        observation={"status": "success"},
    )
    ev2 = Evidence(
        evidence_id="ev-health",
        source_type=EvidenceType.HEALTH_CHECK,
        source_reference="prod_health",
        observation={"status": "success"},
    )

    result = triangulator.triangulate(claim, [ev1, ev2])
    assert result.is_corroborated is True
    assert result.num_independent_sources == 2
    assert result.status == TruthStatus.VERIFIED


def test_same_source_limitation():
    """Model repeating itself or duplicate source does NOT constitute independent verification (Spec 19)."""
    triangulator = SourceTriangulator(min_independent_sources=2)
    claim = Claim(
        claim_id="clm-model-repeat",
        statement="Build passed",
        subject="build",
        object_ref="success",
    )

    # Two evidences from the same origin
    ev1 = Evidence(
        evidence_id="ev-m1",
        source_type=EvidenceType.MODEL_INFERENCE,
        source_reference="llm_session_1",
        observation={"status": "success"},
    )
    ev2 = Evidence(
        evidence_id="ev-m2",
        source_type=EvidenceType.MODEL_INFERENCE,
        source_reference="llm_session_1",
        observation={"status": "success"},
    )

    result = triangulator.triangulate(claim, [ev1, ev2])
    # Distinct origins count is only 1
    assert result.num_independent_sources == 1
    assert result.is_corroborated is False
    assert result.status != TruthStatus.VERIFIED


def test_divergent_sources_produce_contradicted_not_silent_choice():
    """Disagreement between sources produces CONTRADICTED, never silently picking one (Spec 34, 164)."""
    triangulator = SourceTriangulator()
    claim = Claim(
        claim_id="clm-divergent",
        statement="Database online",
        subject="database",
        object_ref="healthy",
    )

    ev_ok = Evidence(
        evidence_id="ev-1",
        source_type=EvidenceType.TOOL_RESULT,
        source_reference="tool_status",
        observation={"status": "healthy"},
    )
    ev_fail = Evidence(
        evidence_id="ev-2",
        source_type=EvidenceType.DIRECT_OBSERVATION,
        source_reference="system_monitor",
        observation={"status": "failed"},
    )

    result = triangulator.triangulate(claim, [ev_ok, ev_fail])
    assert result.status == TruthStatus.CONTRADICTED
    assert len(result.discrepancies) > 0

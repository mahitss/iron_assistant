"""Unit tests for Investigation Planning, Safe Diagnostics, and Hypothesis Management (Task 61)."""

from app.incident_response.hypotheses import HypothesisManager
from app.incident_response.investigation import InvestigationEngine
from app.incident_response.schemas import (
    CausalHypothesisItem,
    EvidenceItem,
    HypothesisStatus,
)


def test_investigation_plan_prioritizes_safe_read_only_diagnostics():
    """Test Invariant 13 & 14: Investigation != Mitigation. All diagnostic tasks are safe and read-only."""
    engine = InvestigationEngine()

    hyp = CausalHypothesisItem(
        hypothesis_id="hyp_deploy_1",
        candidate_cause="Recent deployment v2.1 regression",
        status=HypothesisStatus.PROPOSED,
        confidence=0.6,
    )

    plan = engine.build_investigation_plan(
        incident_id="inc_inv_01",
        affected_resources=["checkout-service"],
        hypotheses=[hyp],
    )

    assert len(plan.tasks) >= 2
    # All tasks must be read-only
    assert all(t.is_read_only for t in plan.tasks)
    # The deployment task must have high VOI score (>= 0.90) and be sorted first
    top_task = plan.tasks[0]
    assert top_task.voi_score >= 0.90
    assert "deployment" in top_task.name.lower() or "deploy" in top_task.name.lower()


def test_hypothesis_lifecycle_and_evidence_attachment():
    """Test hypothesis confidence and status progression on supporting vs contradictory evidence."""
    mgr = HypothesisManager()

    h = CausalHypothesisItem(
        hypothesis_id="hyp_db_1",
        candidate_cause="Database connection pool exhaustion",
        status=HypothesisStatus.PROPOSED,
        confidence=0.5,
    )

    # 1. Add supporting evidence
    ev_sup = EvidenceItem(
        source="prometheus",
        trust_level="TRUSTED_SYSTEM",
        is_verified=True,
        details={"active_connections": 100, "max_connections": 100},
    )
    mgr.add_evidence([h], "hyp_db_1", ev_sup, is_supporting=True)

    assert h.status == HypothesisStatus.SUPPORTED
    assert h.confidence > 0.5
    assert len(h.evidence_supporting) == 1

    # 2. Add second verified supporting evidence -> transitions to VERIFIED
    ev_sup2 = EvidenceItem(
        source="pg_stat_activity",
        trust_level="TRUSTED_SYSTEM",
        is_verified=True,
        details={"waiting_queries": 45},
    )
    mgr.add_evidence([h], "hyp_db_1", ev_sup2, is_supporting=True)
    assert h.status == HypothesisStatus.VERIFIED
    assert h.confidence >= 0.80


def test_contradictory_evidence_weakens_and_rejects_hypothesis():
    """Verify that contradictory evidence reduces confidence and marks hypothesis REJECTED."""
    mgr = HypothesisManager()

    h = CausalHypothesisItem(
        hypothesis_id="hyp_net_1",
        candidate_cause="Cross-AZ network partition",
        status=HypothesisStatus.PROPOSED,
        confidence=0.4,
    )

    ev_contra = EvidenceItem(
        source="network_probe",
        trust_level="TRUSTED_SYSTEM",
        is_verified=True,
        details={"ping_loss_percent": 0.0, "latency_ms": 1.2},
    )
    mgr.add_evidence([h], "hyp_net_1", ev_contra, is_supporting=False)

    assert h.status in (HypothesisStatus.WEAKENED, HypothesisStatus.REJECTED)
    assert h.confidence < 0.30
    assert len(h.evidence_contradictory) == 1


def test_root_cause_unknown_when_evidence_is_inconclusive():
    """Test Invariant 21: Root cause is never forced; ROOT_CAUSE_UNKNOWN is returned when uncertain."""
    mgr = HypothesisManager()

    weak_hyps = [
        CausalHypothesisItem(
            hypothesis_id="hyp_a",
            candidate_cause="Transient GC pause",
            status=HypothesisStatus.PROPOSED,
            confidence=0.35,
        ),
        CausalHypothesisItem(
            hypothesis_id="hyp_b",
            candidate_cause="Minor memory leak",
            status=HypothesisStatus.PROPOSED,
            confidence=0.30,
        ),
    ]

    diagnosis = mgr.diagnose_root_cause(weak_hyps)
    assert diagnosis["leading_cause"] == "ROOT_CAUSE_UNKNOWN"
    assert diagnosis["status"] == HypothesisStatus.UNKNOWN

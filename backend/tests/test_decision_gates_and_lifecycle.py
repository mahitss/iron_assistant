"""Tests for 10 Decision Gates, Lifecycle transitions, Overrides, and Commitments (Task 57)."""

import pytest

from app.decision.commitments import CommitmentManager
from app.decision.decisions import DecisionLifecycleManager
from app.decision.gates import GateEvaluationEngine
from app.decision.schemas import (
    CandidateOption,
    DecisionRanking,
    DecisionRequest,
    EvidenceSet,
    GateEvaluationStatus,
    OptionEvaluation,
    OptionType,
    Recommendation,
    ReversibilityLevel,
    UncertaintyAssessment,
)


def test_ten_decision_gates_evaluation():
    engine = GateEvaluationEngine()

    req = DecisionRequest(
        question="Should we roll out the canary build?",
        intent="CANARY_ROLLOUT",
    )

    opt = CandidateOption(
        name="Canary Rollout",
        is_feasible=True,
        hard_constraints_satisfied=True,
        reversibility=ReversibilityLevel.REVERSIBLE,
        option_type=OptionType.STANDARD,
    )

    ev_set = EvidenceSet(decision_id=req.request_id)
    uncertainty = UncertaintyAssessment(overall_uncertainty="LOW", confidence=0.9, safe_to_proceed=True)

    gates, approval_required = engine.evaluate_gates(
        request=req,
        leading_option=opt,
        evidence_set=ev_set,
        risks=[],
        uncertainty=uncertainty,
        is_authorized=True,
        is_production=False,
    )

    assert len(gates) == 10
    assert gates["gate_1_context"].status == GateEvaluationStatus.PASSED
    assert gates["gate_3_constraints"].status == GateEvaluationStatus.PASSED
    assert gates["gate_7_authorization"].status == GateEvaluationStatus.PASSED


def test_irreversible_production_action_triggers_approval_gate():
    engine = GateEvaluationEngine()

    req = DecisionRequest(
        question="Purge deprecated customer dataset?",
        intent="DATA_PURGE",
    )

    opt_destructive = CandidateOption(
        name="Cold Storage Purge",
        is_feasible=True,
        hard_constraints_satisfied=True,
        reversibility=ReversibilityLevel.IRREVERSIBLE,
        option_type=OptionType.AGGRESSIVE,
    )

    gates, approval_required = engine.evaluate_gates(
        request=req,
        leading_option=opt_destructive,
        evidence_set=EvidenceSet(decision_id=req.request_id),
        risks=[],
        uncertainty=UncertaintyAssessment(confidence=0.8),
        is_authorized=True,
        is_production=True,
    )

    # Invariant: Irreversible and production operations MUST mandate approval
    assert approval_required
    assert gates["gate_8_approval"].status == GateEvaluationStatus.PENDING_APPROVAL


def test_user_override_preservation():
    lifecycle = DecisionLifecycleManager()

    req = DecisionRequest(question="Select cluster strategy")
    rec = Recommendation(
        decision_id="dec_override_test",
        recommended_option_id="opt_engine_choice",
        headline="Recommend Option Engine Choice",
        why_selected="Optimal balance.",
    )
    ranking = DecisionRanking(
        recommended_option_id="opt_engine_choice",
        ranked_options=[
            OptionEvaluation(option_id="opt_engine_choice", name="Engine Choice", rank=1, normalized_score=1.0),
            OptionEvaluation(option_id="opt_user_choice", name="User Preferred Choice", rank=2, normalized_score=0.8),
        ],
        confidence=0.9,
    )

    record = lifecycle.create_record(
        request=req,
        recommendation=rec,
        ranking=ranking,
        gates={},
        approval_required=False,
        provenance={"fingerprint": "hash123"},
    )

    assert record.selected_option_id == "opt_engine_choice"
    assert not record.user_override

    # User explicitly selects lower-ranked option
    updated_record, revision = lifecycle.select_option(
        record=record,
        chosen_option_id="opt_user_choice",
        actor="operator_alice",
    )

    # Invariant: Both recommendation and user decision must remain immutably preserved
    assert updated_record.recommendation.recommended_option_id == "opt_engine_choice"
    assert updated_record.selected_option_id == "opt_user_choice"
    assert updated_record.user_override is True
    assert updated_record.version == 2
    assert "USER OVERRIDE" in revision.reason


def test_commitments_cannot_be_silently_authorized():
    mgr = CommitmentManager()

    # Propose commitment
    com = mgr.propose_commitment(
        decision_id="dec_infra_001",
        owner="sre_team",
        title="Upgrade load balancer SSL certs",
    )

    # Invariant: Recommendation must NOT silently create real commitment
    assert com.status == "PROPOSED"
    assert com.authorized_by is None

    # Cannot fulfill without authorization
    with pytest.raises(ValueError):
        mgr.fulfill_commitment(com)

    # Authorize explicitly
    auth_com = mgr.authorize_commitment(com, authorized_by="sec_admin")
    assert auth_com.status == "AUTHORIZED"
    assert auth_com.authorized_by == "sec_admin"

    # Fulfill
    fulfilled = mgr.fulfill_commitment(auth_com)
    assert fulfilled.status == "FULFILLED"

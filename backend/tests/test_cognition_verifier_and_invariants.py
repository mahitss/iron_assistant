"""Unit tests for CognitiveVerifier, anti self-attestation, and invariant enforcement (Task 41)."""

import pytest
from app.cognition.steps import PlanStep, StepRiskLevel, VerificationSpec
from app.cognition.verifier import (
    CognitiveVerifier,
    InvariantViolationError,
)


def test_anti_self_attestation_rejection():
    # Spec 75: Model saying 'done' does NOT count as verification
    step = PlanStep(
        step_id="step_deploy",
        plan_id="p1",
        sequence=1,
        objective="Deploy API",
        action="deploy",
        risk=StepRiskLevel.WRITE,
        verification=VerificationSpec(
            check_type="OUTPUT_MATCH",
            target="deployed",
            expected=True,
        ),
    )

    # Output consisting solely of self-attestation
    self_attested_output = {"message": "done"}
    res = CognitiveVerifier.verify_postconditions(step, self_attested_output, current_state={})

    assert not res.verified
    assert not res.postconditions_satisfied
    assert "self-attestation" in res.failure_reason.lower()


def test_verification_success_with_empirical_output():
    step = PlanStep(
        step_id="step_test",
        plan_id="p1",
        sequence=1,
        objective="Run tests",
        action="test_runner",
        verification=VerificationSpec(
            check_type="OUTPUT_MATCH",
            target="failures",
            expected=0,
        ),
    )

    valid_output = {"failures": 0, "tests_run": 42, "status": "success"}
    res = CognitiveVerifier.verify_postconditions(step, valid_output, current_state={})

    assert res.verified
    assert res.postconditions_satisfied


def test_invariant_violation_halts_execution():
    step = PlanStep(
        step_id="step_critical",
        plan_id="p1",
        sequence=1,
        objective="Restart worker",
        action="restart_worker",
        verification=VerificationSpec(
            invariants=["Production service must remain operational and healthy."],
        ),
    )

    # State indicates system is unhealthy
    unhealthy_state = {"system_healthy": False}
    with pytest.raises(InvariantViolationError) as exc_info:
        CognitiveVerifier.verify_postconditions(step, output_result={"restarted": True}, current_state=unhealthy_state)

    assert "Critical invariant violated" in str(exc_info.value)

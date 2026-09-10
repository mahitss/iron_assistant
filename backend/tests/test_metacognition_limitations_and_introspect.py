"""Unit tests for limitation detection, secret-safe explanations, and the 5 introspection questions."""

from app.metacognition.capabilities import CapabilityManager
from app.metacognition.explanations import ExplanationGenerator
from app.metacognition.failures import FailureClassifier
from app.metacognition.introspection import IntrospectionConsole
from app.metacognition.limitations import LimitationDetector
from app.metacognition.schemas import (
    FailureType,
    LimitationCategory,
    LimitationSeverity,
    UncertaintyType,
)
from app.metacognition.uncertainty import UncertaintyModel


def test_limitation_detection_and_safe_explanations():
    detector = LimitationDetector()

    lim = detector.register_limitation(
        category=LimitationCategory.PERMISSION,
        description="Deployment token is missing or unauthorized.",
        severity=LimitationSeverity.BLOCKING,
        mitigation_suggestion="Request deploy token from project owner.",
    )

    explanation = detector.explain_limitation(lim.limitation_id)
    assert explanation["category"] == LimitationCategory.PERMISSION.value
    assert "Request deploy token" in explanation["suggested_action"]

    # Invariant 175 & 178: Redaction of internal credentials from explanations
    raw_leak = "Failed with key sk-1234567890abcdef123456 and password=secret123 on internal_ip:10.0.0.1"
    sanitized = ExplanationGenerator.sanitize_explanation(raw_leak)
    assert "sk-1234567890" not in sanitized
    assert "secret123" not in sanitized
    assert "[REDACTED_INTERNAL_CREDENTIAL]" in sanitized


def test_introspection_five_core_questions():
    caps = CapabilityManager()
    limits = LimitationDetector()
    uncertainty = UncertaintyModel()
    failures = FailureClassifier()

    console = IntrospectionConsole(caps, limits, uncertainty, failures)

    # 1. What can you do? (Invariant 74)
    res_what = console.answer_what_can_you_do()
    assert res_what.question_type == "WHAT_CAN_YOU_DO"
    assert "text_generation" in res_what.grounded_answer

    # 2. Why can't you do this? (Invariant 75)
    limits.register_limitation(
        category=LimitationCategory.NETWORK,
        description="Network is offline, external APIs unreachable.",
        severity=LimitationSeverity.BLOCKING,
    )
    res_why = console.answer_why_cant_you_do_this("network")
    assert res_why.question_type == "WHY_CANT_YOU"
    assert "Network is offline" in res_why.grounded_answer

    # 3. How sure are you? (Invariant 76)
    uncertainty.record_uncertainty(
        subject="ReleaseDate",
        uncertainty_type=UncertaintyType.MISSING_DATA,
        confidence=0.45,
    )
    res_how_sure = console.answer_how_sure_are_you("ReleaseDate")
    assert res_how_sure.question_type == "HOW_SURE"
    assert res_how_sure.confidence == 0.45

    # 4. Did you actually do it? (Invariant 77)
    res_did_not = console.answer_did_you_actually_do_it("delete_cluster", execution_log=None)
    assert res_did_not.confidence == 0.0
    assert "NOT verified" in res_did_not.grounded_answer

    res_did = console.answer_did_you_actually_do_it("build_app", execution_log={"verified": True, "timestamp": "now"})
    assert res_did.confidence == 1.0
    assert "was executed and verified" in res_did.grounded_answer

    # 5. What went wrong? (Invariant 78)
    failures.record_failure(
        action="compile_c_code",
        failure_type=FailureType.TOOL_FAILURE,
        cause="gcc: fatal error: stdio.h missing",
    )
    res_wrong = console.answer_what_went_wrong()
    assert res_wrong.question_type == "WHAT_WENT_WRONG"
    assert "stdio.h missing" in res_wrong.grounded_answer

"""Unit tests for Reasoning Trace Audit, Decision Review, and Brier Confidence Calibration (Task 67)."""

from app.self_audit.calibration import CalibrationEngine
from app.self_audit.reasoning_audit import ClaimAuditor, DecisionAuditor, ReasoningAuditor
from app.self_audit.schemas import ConfidenceCalibrationState


def test_reasoning_auditor_epistemic_checks():
    # 1. False Certainty Check (Spec 10)
    issues = ReasoningAuditor.audit_reasoning_trace(
        claims=["System will achieve 100% availability"],
        assumptions=["Standard traffic"],
        evidence_references=["Single telemetry ping"],
        confidence_reported=0.999,
    )
    assert any(i["check"] == "FALSE_CERTAINTY" for i in issues)

    # 2. Unsupported Assumptions (Spec 10)
    issues_asm = ReasoningAuditor.audit_reasoning_trace(
        claims=["Deployment will finish in 5 minutes"],
        assumptions=["Database lock contention will remain zero"],
        evidence_references=["Git commit hash is verified"],
        confidence_reported=0.8,
    )
    assert any(i["check"] == "UNSUPPORTED_ASSUMPTION" for i in issues_asm)

    # 3. Confirmation Bias (Spec 10)
    issues_bias = ReasoningAuditor.audit_reasoning_trace(
        claims=["Database upgrade is risk-free"],
        assumptions=[],
        evidence_references=["Lab tests passed"],
        confidence_reported=0.85,
        contradictory_evidence=["Staging tests triggered deadlocks on foreign keys"],
    )
    assert any(i["check"] == "CONFIRMATION_BIAS" for i in issues_bias)

    # 4. Causal Overreach (Spec 10)
    issues_causal = ReasoningAuditor.audit_reasoning_trace(
        claims=[
            "High memory usage directly caused and guarantees the network latency spike, showing strong correlation"
        ],
        assumptions=[],
        evidence_references=["Memory is at 90%"],
        confidence_reported=0.8,
    )
    assert any(i["check"] == "CAUSAL_OVERREACH" for i in issues_causal)


def test_claim_and_decision_auditor():
    # Claim Audit (Spec 12)
    claim_eval = ClaimAuditor.audit_claim(
        claim="API responds under 100ms",
        sources=["Datadog metrics", "Prometheus exporter"],
        is_verified=True,
    )
    assert claim_eval["is_independently_supported"] is True
    assert claim_eval["quality_grade"] == "VERIFIED"

    # Claim with contradictions
    disputed_eval = ClaimAuditor.audit_claim(
        claim="Zero security vulnerabilities present",
        sources=["SourceClear scanner"],
        is_verified=False,
        contradictory_sources=["Snyk alert #9901"],
    )
    assert disputed_eval["quality_grade"] == "UNVERIFIED_OR_DISPUTED"

    # Decision Audit (Spec 13, 14)
    dec_eval = DecisionAuditor.audit_decision(
        decision_id="dec_412",
        objective="Minimize latency",
        selected_option="Route traffic to secondary replica",
        predicted_outcome="Latency will drop to 50ms",
        actual_outcome="Latency dropped to 48ms",
    )
    assert dec_eval["outcome_matched"] is True
    assert dec_eval["has_error"] is False

    # Decision with discrepancy
    err_eval = DecisionAuditor.audit_decision(
        decision_id="dec_413",
        objective="Reduce memory usage",
        selected_option="Enable aggressive GC",
        predicted_outcome="GC pause time will remain under 10ms",
        actual_outcome="GC stop-the-world pauses spiked to 250ms causing HTTP 504 timeouts",
        constraints_violated=["p99 SLA < 100ms"],
    )
    assert err_eval["has_error"] is True
    assert err_eval["decision_error_class"] in ("PREDICTION_DISCREPANCY", "CONSTRAINT_VIOLATION")


def test_confidence_calibration_and_brier_scoring():
    engine = CalibrationEngine()

    # Record 3 predictions
    p1 = engine.record_prediction("service_a", "Service will sustain 5000 QPS", 0.90, "Success")
    p2 = engine.record_prediction("service_b", "DB migration will take < 10m", 0.85, "Success")
    p3 = engine.record_prediction("service_c", "Memory will stay under 1GB", 0.20, "Success")

    # Resolve outcomes
    engine.record_actual_outcome(p1.prediction_id, "Sustained 5000 QPS without error", success=True)
    engine.record_actual_outcome(p2.prediction_id, "Migration timed out after 35m", success=False)
    engine.record_actual_outcome(p3.prediction_id, "Memory stayed under 800MB", success=True)

    agg = engine.compute_aggregate_calibration()
    assert agg["sample_size"] == 3
    assert agg["mean_brier_score"] > 0.0
    assert "buckets" in agg


def test_systematic_overconfidence_detection():
    engine = CalibrationEngine()

    # 4 predictions with 90% confidence that all fail (Spec 25)
    for i in range(4):
        p = engine.record_prediction(f"task_{i}", "Task succeeds", 0.90, "Success")
        engine.record_actual_outcome(p.prediction_id, "Task failed", success=False)

    agg = engine.compute_aggregate_calibration()
    assert agg["calibration_state"] == ConfidenceCalibrationState.OVERCONFIDENT.value
    assert any("SYSTEMATIC_OVERCONFIDENCE" in alert for alert in agg["alerts"])

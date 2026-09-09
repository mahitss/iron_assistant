"""Tests for Root-Cause Analysis (RCA) and user-safe diagnostics (Task 38)."""

from datetime import UTC, datetime

from app.observability.diagnostics import DiagnosticService
from app.observability.root_cause import RootCauseAnalysisEngine
from app.observability.schemas import (
    ConfidenceLevel,
    Span,
    SpanEvent,
    SpanStatus,
    Trace,
    TraceStatus,
)


def test_rca_identifies_root_cause_and_cites_concrete_evidence():
    """RCA identifies primary failure chronologically and cites concrete observable facts."""
    engine = RootCauseAnalysisEngine()

    now = datetime.now(UTC)
    s1 = Span(
        span_id="spn_1",
        trace_id="trc_test",
        operation="fetch_external_api",
        component="github",
        started_at=now,
        status=SpanStatus.ERROR,
        error_code="TIMEOUT",
        events=[
            SpanEvent(
                name="error",
                timestamp=now,
                attributes={"message": "Connection timed out after 5000ms", "dependency": "github_api"},
            )
        ],
    )
    s2 = Span(
        span_id="spn_2",
        trace_id="trc_test",
        parent_span_id="spn_1",
        operation="process_payload",
        component="task_engine",
        started_at=now,
        status=SpanStatus.ERROR,
        error_code="DEPENDENCY_FAILURE",
    )

    trace = Trace(
        trace_id="trc_test",
        root_operation="sync_repo",
        status=TraceStatus.ERROR,
        error_count=2,
        spans=[s1, s2],
    )

    rca = engine.analyze_trace(trace)

    assert rca.confidence == ConfidenceLevel.HIGH
    assert "github" in rca.affected_components
    assert "github_api" in rca.affected_components
    assert "github" in rca.probable_root_cause or "deadline" in rca.probable_root_cause.lower()
    assert len(rca.evidence) >= 2
    assert any("Connection timed out" in ev for ev in rca.evidence)
    assert len(rca.contributing_causes) == 1
    assert "task_engine" in rca.contributing_causes[0]


def test_rca_distinguishes_governance_policy_denial_from_system_bug():
    """Policy denial is identified as governance enforcement, not a runtime bug."""
    engine = RootCauseAnalysisEngine()
    now = datetime.now(UTC)

    s_pol = Span(
        span_id="spn_pol",
        trace_id="trc_pol",
        operation="evaluate_policy",
        component="policy",
        started_at=now,
        status=SpanStatus.ERROR,
        error_code="POLICY_DENIAL",
        attributes={"decision": "DENY", "reason": "Operation outside authorized project scope"},
    )
    trace = Trace(
        trace_id="trc_pol",
        root_operation="delete_production_table",
        status=TraceStatus.ERROR,
        spans=[s_pol],
    )

    rca = engine.analyze_trace(trace)
    assert "governance policy" in rca.probable_root_cause.lower()
    assert "approval" in rca.recommended_next_action.lower()


def test_user_safe_diagnostics_produces_friendly_explanation():
    """DiagnosticService produces plain-English explanations without stack traces."""
    now = datetime.now(UTC)
    s_err = Span(
        span_id="spn_gh",
        trace_id="trc_user",
        operation="clone_repository",
        component="github",
        started_at=now,
        status=SpanStatus.ERROR,
        error_code="TIMEOUT",
    )
    trace = Trace(
        trace_id="trc_user",
        root_operation="setup_workspace",
        status=TraceStatus.ERROR,
        spans=[s_err],
    )

    report = DiagnosticService.generate_user_diagnostic(trace)
    assert report.target_ref == "trc_user"
    assert "GitHub was temporarily slow or unavailable" in report.what_happened
    assert "retry automatically" in report.next_steps

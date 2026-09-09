"""User-safe diagnostics and operator diagnostic reports (Task 38)."""

from typing import Any

from app.observability.schemas import DiagnosticReport, SpanStatus, Trace


class DiagnosticService:
    """Provides user-facing plain English explanations and operator diagnostic deep-dives."""

    @classmethod
    def generate_user_diagnostic(cls, trace: Trace) -> DiagnosticReport:
        """Translates technical execution telemetry into user-safe plain language ('What happened?')."""
        timeline: list[dict[str, Any]] = []
        for span in trace.spans:
            timeline.append({
                "operation": span.operation,
                "component": span.component,
                "status": span.status.value,
                "duration_ms": round(span.duration_ms or 0.0, 1),
            })

        failing_spans = [s for s in trace.spans if s.status == SpanStatus.ERROR]
        if not failing_spans:
            return DiagnosticReport(
                target_ref=trace.trace_id,
                summary="Task completed normally.",
                what_happened="All operations succeeded within expected latency parameters.",
                status="HEALTHY",
                timeline=timeline,
                evidence=["Zero operational failures recorded"],
                next_steps="None. Execution completed successfully.",
            )

        primary = failing_spans[0]
        comp = primary.component
        err = primary.error_code or "ERROR"

        # Friendly user translations
        if comp == "policy":
            what_happened = "The operation was paused because it required additional permissions or human approval."
            next_steps = "Check the Approvals center to approve the requested action."
        elif "github" in comp.lower() or "github" in str(primary.attributes).lower():
            what_happened = "GitHub was temporarily slow or unavailable, so Kairo paused the task."
            next_steps = "Kairo will retry automatically once GitHub connectivity stabilizes."
        elif comp in ("model_router", "provider"):
            what_happened = "The primary AI provider encountered a temporary service hiccup."
            next_steps = "Kairo attempted a safe fallback model to fulfill your request."
        elif err == "TIMEOUT":
            what_happened = f"An external service took longer than expected to respond during {primary.operation}."
            next_steps = "Verify network connectivity or try again."
        else:
            what_happened = f"Kairo encountered an unexpected error during {primary.operation}."
            next_steps = "Please try again or contact your administrator."

        return DiagnosticReport(
            target_ref=trace.trace_id,
            summary=f"Issue detected in {comp} during {primary.operation}.",
            what_happened=what_happened,
            status="DEGRADED" if trace.status != SpanStatus.ERROR else "FAILED",
            timeline=timeline,
            evidence=[f"Failure in {comp} with code {err}"],
            next_steps=next_steps,
        )

    @classmethod
    def generate_operator_diagnostic(cls, trace: Trace) -> dict[str, Any]:
        """Provides full technical diagnostic information for system administrators."""
        return {
            "trace_id": trace.trace_id,
            "root_operation": trace.root_operation,
            "status": trace.status.value,
            "total_duration_ms": trace.duration_ms,
            "error_count": trace.error_count,
            "span_count": len(trace.spans),
            "spans": [
                {
                    "span_id": s.span_id,
                    "parent_span_id": s.parent_span_id,
                    "component": s.component,
                    "operation": s.operation,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error_code": s.error_code,
                    "attributes": s.attributes,
                    "events": [e.model_dump() for e in s.events],
                }
                for s in trace.spans
            ],
        }


diagnostic_service = DiagnosticService()

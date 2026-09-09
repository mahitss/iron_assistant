"""Evidence-backed Root-Cause Analysis (RCA) engine with strict non-remediation invariant (Task 38)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.observability.schemas import (
    ConfidenceLevel,
    RootCauseAnalysis,
    SpanStatus,
    Trace,
)


class RootCauseAnalysisEngine:
    """Produces structured, evidence-backed diagnostic root-cause analyses.

    HARD ARCHITECTURAL INVARIANT:
    Root cause is a diagnosis. It is NOT automatically an action.
    This engine MUST NOT execute any remediation or mutate system state.
    """

    def analyze_trace(self, trace: Trace, external_evidence: list[str] | None = None) -> RootCauseAnalysis:
        """Analyzes a distributed execution trace to determine probable cause citing concrete facts."""
        rca_id = f"rca_{uuid.uuid4().hex[:12]}"
        evidence: list[str] = list(external_evidence or [])
        contributing: list[str] = []
        affected_components: set[str] = set()

        # Find first failing span chronologically
        failing_spans = [s for s in trace.spans if s.status == SpanStatus.ERROR or s.error_code is not None]
        failing_spans.sort(key=lambda s: s.started_at)

        if not failing_spans:
            return RootCauseAnalysis(
                id=rca_id,
                target_ref=trace.trace_id,
                probable_root_cause="No execution failures detected in trace",
                evidence=["All recorded spans completed with SUCCESS status"],
                contributing_causes=[],
                affected_components=list(set(s.component for s in trace.spans)),
                confidence=ConfidenceLevel.HIGH,
                recommended_next_action="No diagnostic action required.",
                analyzed_at=datetime.now(UTC),
            )

        # Primary failure is the earliest chronologically failing span
        primary_failure = failing_spans[0]
        affected_components.add(primary_failure.component)

        # Gather concrete observable evidence
        evidence.append(
            f"First failure occurred in component '{primary_failure.component}' "
            f"during operation '{primary_failure.operation}' with error code '{primary_failure.error_code or 'UNKNOWN'}'"
        )

        for evt in primary_failure.events:
            if evt.name == "error":
                msg = evt.attributes.get("message")
                dep = evt.attributes.get("dependency")
                if msg:
                    evidence.append(f"Error detail: {msg}")
                if dep:
                    evidence.append(f"Downstream dependency involved: {dep}")
                    affected_components.add(dep)

        # Look for contributing failures downstream
        for sec_span in failing_spans[1:]:
            affected_components.add(sec_span.component)
            contributing.append(
                f"Cascading failure in '{sec_span.component}:{sec_span.operation}' ({sec_span.error_code})"
            )

        # Determine probable root cause and confidence
        confidence = ConfidenceLevel.HIGH if len(evidence) >= 2 else ConfidenceLevel.MEDIUM
        probable_cause: str
        next_action: str

        if primary_failure.component == "policy":
            probable_cause = f"Operation halted by governance policy: {primary_failure.attributes.get('decision', 'DENY')}"
            next_action = "Review task risk scope or request elevated user approval."
        elif primary_failure.error_code in ("TIMEOUT", "DEADLINE_EXCEEDED"):
            probable_cause = f"Upstream service latency exceeded bounded deadline in {primary_failure.component}"
            next_action = "Inspect downstream provider network latency and connection pools."
        elif "rate_limit" in str(primary_failure.attributes).lower() or primary_failure.error_code == "RATE_LIMITED":
            probable_cause = f"Provider rate limit exhausted in {primary_failure.component}"
            next_action = "Check quota allocation and backoff delay curves."
        elif primary_failure.component in ("model_router", "provider"):
            probable_cause = f"Model provider failure or unavailable endpoint during '{primary_failure.operation}'"
            next_action = "Inspect provider circuit breaker state and verify API endpoint health."
        else:
            probable_cause = f"Execution fault in component '{primary_failure.component}' during '{primary_failure.operation}'"
            next_action = f"Inspect logs for span {primary_failure.span_id} and verify target resource availability."

        return RootCauseAnalysis(
            id=rca_id,
            target_ref=trace.trace_id,
            probable_root_cause=probable_cause,
            evidence=evidence,
            contributing_causes=contributing,
            affected_components=sorted(list(affected_components)),
            confidence=confidence,
            recommended_next_action=next_action,
            analyzed_at=datetime.now(UTC),
        )


rca_engine = RootCauseAnalysisEngine()

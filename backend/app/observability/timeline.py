"""Execution timeline reconstruction, causal failure correlation, and deterministic error fingerprinting (Task 86)."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
import hashlib
import logging
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.events.schemas import Event, EventOutcome, EventSeverity

logger = logging.getLogger("kairo.observability.timeline")


class TimelineEntry(BaseModel):
    """A single canonical point in the execution timeline derived from an event."""

    model_config = ConfigDict(extra="ignore")

    event_id: str
    event_type: str
    timestamp: datetime
    monotonic_timestamp: float
    component: str
    operation: str
    status: str
    domain: str
    severity: str
    causation_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    summary: str
    resource_metrics: dict[str, Any] = Field(default_factory=dict)
    security_decision: dict[str, Any] | None = None


class ExecutionTimeline(BaseModel):
    """Complete, deterministic forensic reconstruction of an operation by correlation_id."""

    model_config = ConfigDict(extra="ignore")

    correlation_id: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    overall_status: str = "UNKNOWN"
    entry_count: int = 0
    entries: list[TimelineEntry] = Field(default_factory=list)
    causal_chains: list[dict[str, Any]] = Field(default_factory=list)
    root_cause: dict[str, Any] | None = None
    error_fingerprint: str | None = None


def compute_error_fingerprint(
    component: str,
    error_type: str,
    operation_class: str = "general",
    failure_category: str = "system",
) -> str:
    """Generate deterministic error fingerprint using ONLY stable attributes (Section 30).

    Hard Invariant: Never fingerprint using timestamps, random UUIDs, user text, or secret values.
    """
    normalized = f"{component.strip().lower()}:{error_type.strip().lower()}:{operation_class.strip().lower()}:{failure_category.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class TimelineReconstructor:
    """In-memory bounded store and deterministic reconstruction engine for execution events."""

    def __init__(self, max_retained_correlations: int = 2000, max_events_per_correlation: int = 500) -> None:
        self.max_retained_correlations = max_retained_correlations
        self.max_events_per_correlation = max_events_per_correlation
        # correlation_id -> deque of Event
        self._correlation_events: dict[str, deque[Event]] = {}
        # Global ring buffer for recent events
        self._recent_events: deque[Event] = deque(maxlen=10_000)

    def ingest_event(self, event: Event) -> None:
        """Ingests an event into correlation indexing."""
        self._recent_events.append(event)
        cid = event.correlation_id or "unspecified"

        if cid not in self._correlation_events:
            if len(self._correlation_events) >= self.max_retained_correlations:
                # Evict oldest correlation
                oldest_key = next(iter(self._correlation_events))
                del self._correlation_events[oldest_key]
            self._correlation_events[cid] = deque(maxlen=self.max_events_per_correlation)

        self._correlation_events[cid].append(event)

    def get_raw_events(self, correlation_id: str) -> list[Event]:
        """Returns all ingested events for a correlation ID sorted deterministically."""
        events = list(self._correlation_events.get(correlation_id, []))
        events.sort(key=lambda e: (e.monotonic_timestamp, e.timestamp, e.event_id))
        return events

    def replay_events(self, correlation_id: str) -> list[dict[str, Any]]:
        """Data-only event replay (Section 26).

        HARD INVARIANT: An event replay is DATA. It never re-executes side effects.
        """
        events = self.get_raw_events(correlation_id)
        return [e.model_dump(mode="json") for e in events]

    def reconstruct_timeline(self, correlation_id: str) -> ExecutionTimeline:
        """Derives a canonical execution timeline directly from recorded events (Section 27 & 28)."""
        events = self.get_raw_events(correlation_id)

        if not events:
            return ExecutionTimeline(
                correlation_id=correlation_id,
                started_at=datetime.now(UTC),
                completed_at=None,
                duration_ms=0.0,
                overall_status="UNKNOWN",
                entry_count=0,
                entries=[],
            )

        started_at = events[0].timestamp
        completed_at = events[-1].timestamp if len(events) > 1 else None

        # Calculate monotonic duration if available
        start_mono = events[0].monotonic_timestamp
        end_mono = events[-1].monotonic_timestamp
        duration_ms = max(0.0, (end_mono - start_mono) * 1000.0) if end_mono >= start_mono else (
            (events[-1].timestamp - started_at).total_seconds() * 1000.0 if completed_at else 0.0
        )

        entries: list[TimelineEntry] = []
        root_cause_event: Event | None = None
        has_failure = False
        has_cancellation = False

        for ev in events:
            component = str(ev.source.value if hasattr(ev.source, "value") else ev.source)
            domain = str(ev.execution_domain.value if hasattr(ev.execution_domain, "value") else ev.execution_domain)
            status = ev.outcome.value if ev.outcome else ("SUCCESS" if ev.severity != EventSeverity.ERROR else "FAIL")

            if status in ("FAIL", "BLOCK") and root_cause_event is None:
                root_cause_event = ev
                has_failure = True
            elif status == "CANCEL":
                has_cancellation = True

            # Extract resource and security metadata
            res_metrics = {}
            if "duration_ms" in ev.payload:
                res_metrics["duration_ms"] = ev.payload["duration_ms"]
            if "bytes" in ev.payload:
                res_metrics["bytes"] = ev.payload["bytes"]

            sec_decision = None
            if "decision" in ev.payload or "risk_level" in ev.payload:
                sec_decision = {
                    "decision": ev.payload.get("decision", status),
                    "reason": ev.payload.get("reason", ""),
                    "tool": ev.payload.get("tool_name", ev.tool_id),
                }

            summary = ev.payload.get("summary") or ev.payload.get("message") or f"Executed {ev.event_type}"

            entry = TimelineEntry(
                event_id=ev.event_id,
                event_type=ev.event_type,
                timestamp=ev.timestamp,
                monotonic_timestamp=ev.monotonic_timestamp,
                component=component,
                operation=ev.event_type.split(".")[-1],
                status=status,
                domain=domain,
                severity=ev.severity.value,
                causation_id=ev.causation_id,
                trace_id=ev.trace_id,
                span_id=ev.span_id,
                summary=summary,
                resource_metrics=res_metrics,
                security_decision=sec_decision,
            )
            entries.append(entry)

        # Build causal failure links (Section 29)
        causal_chains: list[dict[str, Any]] = []
        root_cause_summary = None
        error_fingerprint = None

        if root_cause_event:
            err_type = root_cause_event.payload.get("error_type") or root_cause_event.event_type
            comp_name = str(root_cause_event.source.value if hasattr(root_cause_event.source, "value") else root_cause_event.source)
            op_class = str(root_cause_event.execution_domain.value if hasattr(root_cause_event.execution_domain, "value") else root_cause_event.execution_domain)
            error_fingerprint = compute_error_fingerprint(comp_name, err_type, op_class, "failure")

            root_cause_summary = {
                "event_id": root_cause_event.event_id,
                "event_type": root_cause_event.event_type,
                "component": comp_name,
                "reason": root_cause_event.payload.get("reason") or root_cause_event.payload.get("error") or "Operation failed",
                "fingerprint": error_fingerprint,
            }

            # Map downstream effects caused by this event
            downstream = [
                e.event_id for e in events
                if e.causation_id == root_cause_event.event_id or e.parent_event_id == root_cause_event.event_id
            ]
            causal_chains.append({
                "root_event_id": root_cause_event.event_id,
                "root_event_type": root_cause_event.event_type,
                "downstream_affected_event_ids": downstream,
            })

        overall_status = "FAILED" if has_failure else ("CANCELLED" if has_cancellation else "COMPLETED")

        return ExecutionTimeline(
            correlation_id=correlation_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round(duration_ms, 2),
            overall_status=overall_status,
            entry_count=len(entries),
            entries=entries,
            causal_chains=causal_chains,
            root_cause=root_cause_summary,
            error_fingerprint=error_fingerprint,
        )

    def query_recent_events(
        self,
        limit: int = 50,
        severity: str | None = None,
        event_type: str | None = None,
        domain: str | None = None,
        correlation_id: str | None = None,
    ) -> list[Event]:
        """Query recent events with filters and bounds."""
        matched: list[Event] = []
        bounded_limit = max(1, min(100, limit))

        for ev in reversed(self._recent_events):
            if severity and ev.severity.value != severity.upper():
                continue
            if event_type and not ev.event_type.startswith(event_type):
                continue
            if domain:
                dom_val = ev.execution_domain.value if hasattr(ev.execution_domain, "value") else str(ev.execution_domain)
                if dom_val != domain.lower():
                    continue
            if correlation_id and ev.correlation_id != correlation_id:
                continue

            matched.append(ev)
            if len(matched) >= bounded_limit:
                break

        return matched


# Global singleton reconstructor
timeline_reconstructor = TimelineReconstructor()

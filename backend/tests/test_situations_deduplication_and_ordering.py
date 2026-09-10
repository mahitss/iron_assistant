"""Unit tests for Event Deduplication, Out-of-Order Events, and Chronological Ordering (Task 60)."""

from datetime import datetime, timedelta, timezone

from app.situational_awareness.deduplication import EventDeduplicator
from app.situational_awareness.schemas import NormalizedEvent, SituationSeverity, SourceTrustLevel
from app.situational_awareness.timelines import TimelineEngine


def _make_event(
    event_id: str,
    event_type: str,
    source: str,
    subject: str,
    resource: str = "web-api",
    occurred_at: datetime | None = None,
) -> NormalizedEvent:
    now = datetime.now(timezone.utc)
    return NormalizedEvent(
        event_id=event_id,
        event_type=event_type,
        source=source,
        source_trust=SourceTrustLevel.TRUSTED_SYSTEM,
        environment="production",
        resource=resource,
        subject=subject,
        payload={"dummy": True},
        severity=SituationSeverity.MEDIUM,
        confidence=1.0,
        occurred_at=occurred_at or now,
        received_at=now,
    )


def test_sliding_window_deduplication():
    """Verify that identical events from multiple monitors within window are deduplicated."""
    dedup = EventDeduplicator(window_seconds=60.0)
    base_time = datetime(2026, 9, 10, 14, 0, 0, tzinfo=timezone.utc)

    evt1 = _make_event("evt_1", "deployment_started", "datadog", "deploy v2.1", occurred_at=base_time)
    evt2 = _make_event(
        "evt_2",
        "deployment_started",
        "github_webhook",
        "deploy v2.1",
        occurred_at=base_time + timedelta(seconds=5),
    )

    is_dup1, orig_id1 = dedup.is_duplicate(evt1)
    assert not is_dup1
    assert orig_id1 is None

    is_dup2, orig_id2 = dedup.is_duplicate(evt2)
    assert is_dup2
    assert orig_id2 == "evt_1"


def test_distinct_events_are_not_deduplicated():
    """Verify that distinct events with different subjects or resources are kept separate."""
    dedup = EventDeduplicator(window_seconds=60.0)
    base_time = datetime(2026, 9, 10, 14, 0, 0, tzinfo=timezone.utc)

    evt_a = _make_event(
        "evt_a", "threshold_exceeded", "monitor", "cpu > 90%", resource="db-primary", occurred_at=base_time
    )
    evt_b = _make_event(
        "evt_b", "threshold_exceeded", "monitor", "memory > 95%", resource="db-primary", occurred_at=base_time
    )
    evt_c = _make_event(
        "evt_c", "threshold_exceeded", "monitor", "cpu > 90%", resource="cache-redis", occurred_at=base_time
    )

    assert not dedup.is_duplicate(evt_a)[0]
    assert not dedup.is_duplicate(evt_b)[0]
    assert not dedup.is_duplicate(evt_c)[0]


def test_out_of_order_events_sorted_by_occurrence_time():
    """Verify that out-of-order/late-arriving events are chronologically sequenced in the timeline."""
    t0 = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=2)
    t2 = t0 + timedelta(minutes=5)
    t3 = t0 + timedelta(minutes=10)

    # Ingestion arrives out of order: t2 first, then t0, then t3, then t1
    evt_early = _make_event("evt_early", "config_change", "audit", "Config updated", occurred_at=t0)
    evt_deploy = _make_event("evt_deploy", "deployment", "k8s", "Deployment roll out", occurred_at=t1)
    evt_alert = _make_event("evt_alert", "alert_fired", "prometheus", "Latency spike", occurred_at=t2)
    evt_mitigate = _make_event("evt_mitigate", "scaled_up", "orchestrator", "Added replicas", occurred_at=t3)

    arrived_events = [evt_alert, evt_early, evt_mitigate, evt_deploy]

    timeline_engine = TimelineEngine()
    timeline = timeline_engine.build_timeline(arrived_events)

    assert len(timeline) == 4
    # Check that timestamps are strictly sorted
    assert timeline[0].evidence_id == "evt_early"
    assert timeline[1].evidence_id == "evt_deploy"
    assert timeline[2].evidence_id == "evt_alert"
    assert timeline[3].evidence_id == "evt_mitigate"


def test_fact_versus_inference_separation_in_timeline():
    """Test Invariant 104: Observed events are marked facts; causal conjectures are marked inference."""
    now = datetime.now(timezone.utc)
    evt = _make_event("evt_1", "cpu_spike", "prometheus", "CPU hit 98%")
    inferences = [
        {
            "timestamp": now + timedelta(seconds=1),
            "type": "HYPOTHESIS",
            "summary": "Deployment caused memory leak",
        }
    ]

    engine = TimelineEngine()
    timeline = engine.build_timeline([evt], inferences=inferences)

    assert len(timeline) == 2
    assert not timeline[0].is_inference
    assert timeline[1].is_inference
    assert "[INFERENCE]" in timeline[1].summary

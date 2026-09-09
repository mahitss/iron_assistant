"""Tests for Observations, Provenance, Latency, Clock Skew, and Freshness Expiration (Task 46)."""

from datetime import datetime, timedelta, timezone
import pytest

from app.perception.events import EventType, PerceptionEvent
from app.perception.freshness import FreshnessTracker
from app.perception.observations import Observation
from app.perception.provenance import ProvenanceTracker
from app.perception.sources import PerceptionSource, PrivacyLevel, SourceType


def utc_now():
    return datetime.now(timezone.utc)


def test_observation_creation_and_latency_measurement():
    source = PerceptionSource(
        source_id="src_svc_1",
        type=SourceType.SERVICE,
        name="Payment Service",
        reliability=0.92,
        privacy_level=PrivacyLevel.INTERNAL,
    )
    obs_time = utc_now() - timedelta(milliseconds=120)
    recv_time = utc_now()

    event = PerceptionEvent(
        event_id="evt_pay_1",
        event_type=EventType.HEALTH_CHANGED,
        source_id=source.source_id,
        subject="service:payment",
        timestamp=obs_time,
        received_at=recv_time,
        payload={"status": "DEGRADED", "latency_ms": 350},
        correlation_id="req_9988",
    )

    obs = Observation.from_event(event=event, source=source)

    assert obs.observation_id.startswith("obs_")
    assert obs.subject == "service:payment"
    assert obs.source_type == SourceType.SERVICE
    assert obs.confidence == 0.92
    assert obs.correlation_id == "req_9988"
    assert obs.data["status"] == "DEGRADED"

    # Latency tracking (Spec 23)
    assert obs.latency_ms >= 100.0  # observed 120ms earlier
    # Freshness
    assert obs.is_fresh(ttl_seconds=60) is True


def test_observation_describes_what_not_why():
    """Enforce Spec 7: Observation describes WHAT was observed. It does not automatically assert WHY."""
    source = PerceptionSource("src_dep", SourceType.DEPLOYMENT, "Deployer", reliability=0.9)
    event = PerceptionEvent(
        event_id="evt_dep_fail",
        event_type=EventType.FAILED,
        source_id="src_dep",
        subject="deployment:kairo_api:production",
        payload={"error": "OOMKilled", "exit_code": 137},
    )
    obs = Observation.from_event(event=event, source=source)

    # Observation holds the factual observed state, not causal claims
    assert obs.data["error"] == "OOMKilled"
    assert "caused_by" not in obs.data


def test_observation_confidence_not_absolute_truth():
    """Enforce Spec 136: Confidence is not verification / absolute truth."""
    source = PerceptionSource("src_untrusted", SourceType.API, "Third-Party Webhook", reliability=0.4)
    event = PerceptionEvent(
        event_id="evt_api_1",
        event_type=EventType.UPDATED,
        source_id="src_untrusted",
        subject="api:weather",
        payload={"temp": 25},
    )
    obs = Observation.from_event(event=event, source=source)
    assert obs.confidence == 0.4
    assert obs.confidence < 0.5


def test_clock_skew_and_stale_update_rejection():
    """Enforce Spec 20, 21: Account for clock skew; do not allow old events to overwrite newer verified state."""
    tracker = FreshnessTracker()

    # Source time in past vs local receive time
    src_time = utc_now() - timedelta(seconds=5)
    recv_time = utc_now()
    skew_seconds = tracker.calculate_clock_skew("src_remote", src_time, recv_time)
    assert abs(skew_seconds) >= 4.0

    # Record verified timestamp
    now = utc_now()
    tracker.record_observation_timestamp("service:database", now)

    # Late event with timestamp older than verified timestamp
    old_time = now - timedelta(seconds=10)
    is_stale = tracker.is_stale_update("service:database", old_time)
    assert is_stale is True

    # Newer event is fresh
    future_time = now + timedelta(seconds=2)
    assert tracker.is_stale_update("service:database", future_time) is False


def test_provenance_tracking():
    tracker = ProvenanceTracker()
    rec = tracker.record_provenance(
        observation_id="obs_123",
        source_id="src_device_1",
        source_type="DEVICE",
        adapter_name="DeviceAdapter",
        redaction_applied=True,
        signature_verified=True,
    )

    assert rec.observation_id == "obs_123"
    assert rec.redaction_applied is True
    assert rec.signature_verified is True

    retrieved = tracker.get_provenance("obs_123")
    assert retrieved is not None
    assert retrieved.source_id == "src_device_1"

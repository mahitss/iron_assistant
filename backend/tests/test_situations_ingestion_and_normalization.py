"""Unit tests for Event Ingestion and Normalization in Task 60 Situational Awareness."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.situational_awareness.normalization import EventNormalizer
from app.situational_awareness.schemas import (
    EventIngestRequest,
    NormalizedEvent,
    SituationSeverity,
    SourceTrustLevel,
)


def test_valid_event_normalization_full_fields():
    """Verify that a standard event normalizes timestamps, trust, severity, and preserves provenance."""
    normalizer = EventNormalizer()
    raw_req = EventIngestRequest(
        event_type="metric_threshold_crossed",
        source="prometheus",
        environment="production",
        resource="db-primary-pool",
        subject="cpu_usage_high",
        payload={"metric": "cpu", "value": 94.2, "threshold": 80.0},
        severity=SituationSeverity.HIGH,
        source_trust=SourceTrustLevel.TRUSTED_SYSTEM,
    )

    normalized = normalizer.normalize(raw_req)
    assert isinstance(normalized, NormalizedEvent)
    assert normalized.event_type == "metric_threshold_crossed"
    assert normalized.source == "prometheus"
    assert normalized.environment == "production"
    assert normalized.resource == "db-primary-pool"
    assert normalized.severity == SituationSeverity.HIGH
    assert normalized.source_trust == SourceTrustLevel.TRUSTED_SYSTEM
    assert normalized.confidence == 1.0
    assert normalized.provenance.get("original_source") == "prometheus"
    assert normalized.provenance.get("is_sanitized") is True
    assert normalized.occurred_at <= normalized.received_at + timedelta(seconds=1)


def test_source_trust_classification():
    """Test mapping of implicit sources to trust levels."""
    normalizer = EventNormalizer()

    req_sys = EventIngestRequest(event_type="sys", source="prometheus", subject="sub")
    assert normalizer.normalize(req_sys).source_trust == SourceTrustLevel.TRUSTED_SYSTEM

    req_ext = EventIngestRequest(event_type="hook", source="github_webhook", subject="sub")
    assert normalizer.normalize(req_ext).source_trust == SourceTrustLevel.VERIFIED_EXTERNAL

    req_user = EventIngestRequest(event_type="report", source="user_ui", subject="sub")
    assert normalizer.normalize(req_user).source_trust == SourceTrustLevel.USER_REPORTED

    req_model = EventIngestRequest(event_type="pred", source="model_agent", subject="sub")
    assert normalizer.normalize(req_model).source_trust == SourceTrustLevel.MODEL_GENERATED

    req_sim = EventIngestRequest(event_type="sim", source="simulator", subject="sub")
    assert normalizer.normalize(req_sim).source_trust == SourceTrustLevel.SIMULATED

    req_unverified = EventIngestRequest(event_type="rand", source="random_external", subject="sub")
    assert normalizer.normalize(req_unverified).source_trust == SourceTrustLevel.UNVERIFIED_EXTERNAL


def test_provenance_and_payload_sanitization():
    """Verify that original metadata and transformation markers are strictly preserved while secrets are sanitized."""
    normalizer = EventNormalizer()
    req = EventIngestRequest(
        event_type="app_log_error",
        source="datadog",
        environment="staging",
        subject="api timeout",
        payload={"msg": "timeout to service X", "code": 504, "token": "secret_abc_123"},
        severity=SituationSeverity.HIGH,
    )
    normalized = normalizer.normalize(req)
    assert normalized.provenance["original_source"] == "datadog"
    assert normalized.payload["msg"] == "timeout to service X"
    assert normalized.payload["token"] == "[REDACTED]"


def test_timestamp_preservation_and_timezone_handling():
    """Test that explicit occurred_at timestamps are preserved with timezone information."""
    normalizer = EventNormalizer()
    specific_time = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)

    req = EventIngestRequest(
        event_type="test_time",
        source="system",
        subject="timed event",
        occurred_at=specific_time,
    )
    normalized = normalizer.normalize(req)
    assert normalized.occurred_at == specific_time
    assert normalized.received_at >= specific_time


def test_empty_event_type_validation_failure():
    """Pydantic must reject invalid event requests missing required fields."""
    with pytest.raises(ValidationError):
        EventIngestRequest()

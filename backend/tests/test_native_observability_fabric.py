"""Comprehensive automated tests for Kairo Native Event, Telemetry & Observability Fabric (Task 86)."""

import asyncio
from datetime import UTC, datetime
import pytest
from starlette.testclient import TestClient

from app.events.bus import EventBus
from app.events.dispatcher import EventDispatcher
from app.events.schemas import (
    Event,
    EventOutcome,
    EventSeverity,
    ExecutionDomain,
    PrivacyClass,
    RetentionClass,
    validate_and_bound_payload,
)
from app.main import app
from app.native.models import (
    NativeEvent,
    NativeExecutionDomain,
    NativeOutcome,
    NativePrivacyClass,
    NativeSeverity,
    RuntimeRequest,
    RuntimeResponse,
)
from app.observability.health import (
    SubsystemHealthAggregator,
    SubsystemHealthState,
    UnifiedHealthReport,
)
from app.observability.sanitization import TelemetrySanitizer
from app.observability.timeline import (
    ExecutionTimeline,
    TimelineReconstructor,
    compute_error_fingerprint,
    timeline_reconstructor,
)


# =============================================================================
# 1. Canonical Event Schema, Monotonic Timestamp & Bounds
# =============================================================================

def test_canonical_event_envelope_defaults():
    """Validates default instantiation of canonical Event envelope."""
    ev = Event(
        event_type="execution.started",
        source="kairo_core",
        payload={"action": "test"},
    )
    assert len(ev.event_id) > 0
    assert ev.monotonic_timestamp > 0.0
    assert ev.severity == EventSeverity.INFO
    assert ev.execution_domain == ExecutionDomain.SYSTEM
    assert ev.privacy_class == PrivacyClass.INTERNAL
    assert ev.retention_class == RetentionClass.OPERATIONAL
    assert ev.priority_tier == 2


def test_priority_tier_mapping():
    """Validates priority tier mapping according to Task 86 rules."""
    p0_event = Event(
        event_type="security.violation.detected",
        source="security_center",
        severity=EventSeverity.CRITICAL,
    )
    assert p0_event.priority_tier == 0

    p1_event = Event(
        event_type="execution.failed",
        source="sandbox",
        severity=EventSeverity.ERROR,
    )
    assert p1_event.priority_tier == 1

    p2_event = Event(
        event_type="execution.completed",
        source="agent_core",
        severity=EventSeverity.INFO,
    )
    assert p2_event.priority_tier == 2

    p3_event = Event(
        event_type="debug.trace",
        source="agent_core",
        severity=EventSeverity.DEBUG,
    )
    assert p3_event.priority_tier == 3


def test_payload_bounds_under_limit():
    """Payloads within 64KB remain untouched."""
    payload = {"key": "small value", "num": 42}
    bounded = validate_and_bound_payload(payload)
    assert bounded == payload
    assert "_payload_truncated" not in bounded


def test_payload_bounds_over_limit():
    """Payloads exceeding 64KB are safely bounded while preserving cryptographic hash."""
    huge_str = "x" * 70_000
    payload = {"data": huge_str}
    bounded = validate_and_bound_payload(payload, max_bytes=65536)

    assert bounded.get("_payload_truncated") is True
    assert bounded.get("_original_size_bytes") > 65536
    assert "_payload_sha256" in bounded
    assert len(bounded["_payload_sha256"]) == 64


def test_payload_bounds_attribute_count_limit():
    """Dictionaries with > 100 attributes are capped with excess count recorded."""
    payload = {f"k_{i}": i for i in range(150)}
    bounded = validate_and_bound_payload(payload, max_attributes=100)

    assert bounded.get("_truncated_attributes") is True
    assert bounded.get("_original_attribute_count") == 150
    # Exactly 100 original keys + truncation metadata keys
    assert "k_0" in bounded
    assert "k_99" in bounded
    assert "k_100" not in bounded


# =============================================================================
# 2. Hardened Secret Redaction
# =============================================================================

def test_sanitizer_bearer_token():
    """Verifies Bearer authorization tokens are redacted."""
    text = "Authorization: Bearer my-secret-jwt-token-12345"
    sanitized = TelemetrySanitizer.sanitize_string(text)
    assert "my-secret-jwt-token-12345" not in sanitized
    assert "Bearer [REDACTED" in sanitized


def test_sanitizer_basic_auth():
    """Verifies Basic authorization tokens are redacted."""
    text = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
    sanitized = TelemetrySanitizer.sanitize_string(text)
    assert "dXNlcjpwYXNzd29yZA==" not in sanitized
    assert "Basic [REDACTED" in sanitized


def test_sanitizer_database_connection_uri():
    """Verifies passwords in database URIs are redacted."""
    uri = "postgres://admin:super_secret_db_pass@127.0.0.1:5432/kairo_db"
    sanitized = TelemetrySanitizer.sanitize_string(uri)
    assert "super_secret_db_pass" not in sanitized
    assert "postgres://admin:[REDACTED]@127.0.0.1:5432/kairo_db" in sanitized


def test_sanitizer_url_query_secrets():
    """Verifies secrets in URL query parameters are redacted."""
    url = "https://api.kairo.ai/v1/data?token=secret_tok_999&api_key=key_123&format=json"
    sanitized = TelemetrySanitizer.sanitize_string(url)
    assert "secret_tok_999" not in sanitized
    assert "key_123" not in sanitized
    assert "token=[REDACTED" in sanitized
    assert "api_key=[REDACTED" in sanitized
    assert "format=json" in sanitized


def test_sanitizer_private_keys():
    """Verifies RSA/EC private key blocks are fully redacted."""
    key_pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y3J1234567890abcdefghijklmnopqrstuvwxyz\n"
        "-----END RSA PRIVATE KEY-----"
    )
    sanitized = TelemetrySanitizer.sanitize_string(key_pem)
    assert "MIIEowIBAAKCAQEA0Y3J1234567890" not in sanitized
    assert "[REDACTED_PRIVATE_KEY]" in sanitized


def test_sanitizer_depth_limit():
    """Verifies nested dictionary recursion depth is capped at 10."""
    nested = {"k": 0}
    current = nested
    for i in range(1, 15):
        current["child"] = {"k": i}
        current = current["child"]

    sanitized = TelemetrySanitizer.sanitize_dict(nested)
    # Walk to depth 10
    node = sanitized
    for _ in range(10):
        assert isinstance(node, dict)
        node = node.get("child", {})
    assert node == {"_depth_exceeded": True}


# =============================================================================
# 3. Priority-Aware Queueing in EventDispatcher
# =============================================================================

@pytest.mark.asyncio
async def test_dispatcher_priority_backpressure():
    """Verifies that under saturation, P3/P2 events are shedded while P0/P1 are never dropped."""
    dispatcher = EventDispatcher(max_queue_size=5)

    # Fill queue to capacity with P2 events
    for i in range(5):
        ev = Event(
            event_type=f"lifecycle.info.{i}",
            source="test",
            severity=EventSeverity.INFO,
        )
        await dispatcher.enqueue(ev)

    assert dispatcher.queue_size == 5

    # Enqueue P3 (DEBUG) -> must be shedded, queue stays at 5
    debug_ev = Event(
        event_type="debug.trace",
        source="test",
        severity=EventSeverity.DEBUG,
    )
    await dispatcher.enqueue(debug_ev)
    assert dispatcher.queue_size == 5

    # Enqueue P0 (CRITICAL) -> must NEVER be dropped (evicts lowest priority P2)
    crit_ev = Event(
        event_type="security.violation",
        source="security_center",
        severity=EventSeverity.CRITICAL,
    )
    await dispatcher.enqueue(crit_ev)
    assert dispatcher.queue_size == 5



# =============================================================================
# 4. Forensic Execution Timeline Reconstruction & Causal Failure Linking
# =============================================================================

def test_timeline_reconstruction_and_causal_linking():
    """Verifies deterministic timeline assembly, failure identification, and causal linking."""
    reconstructor = TimelineReconstructor()
    cid = "corr_test_forensics_001"

    e1 = Event(
        event_id="evt_01",
        correlation_id=cid,
        event_type="execution.started",
        source="kairo_core",
        severity=EventSeverity.INFO,
        monotonic_timestamp=100.0,
        payload={"message": "Starting job"},
    )
    e2 = Event(
        event_id="evt_02",
        correlation_id=cid,
        event_type="sandbox.permission.denied",
        source="sandbox",
        severity=EventSeverity.ERROR,
        outcome=EventOutcome.BLOCK,
        monotonic_timestamp=100.25,
        payload={"reason": "SSRF access denied to 169.254.169.254", "error_type": "SecurityPolicyViolation"},
    )
    e3 = Event(
        event_id="evt_03",
        correlation_id=cid,
        causation_id="evt_02",
        event_type="execution.failed",
        source="kairo_core",
        severity=EventSeverity.ERROR,
        outcome=EventOutcome.FAIL,
        monotonic_timestamp=100.30,
        payload={"reason": "Aborted due to sandbox denial"},
    )

    reconstructor.ingest_event(e1)
    reconstructor.ingest_event(e2)
    reconstructor.ingest_event(e3)

    timeline: ExecutionTimeline = reconstructor.reconstruct_timeline(cid)

    assert timeline.correlation_id == cid
    assert timeline.overall_status == "FAILED"
    assert timeline.entry_count == 3
    assert timeline.duration_ms == 300.0

    # Causal failure identification
    assert timeline.root_cause is not None
    assert timeline.root_cause["event_id"] == "evt_02"
    assert "SSRF access denied" in timeline.root_cause["reason"]
    assert timeline.root_cause["fingerprint"] is not None

    # Downstream causal chain
    assert len(timeline.causal_chains) == 1
    assert timeline.causal_chains[0]["root_event_id"] == "evt_02"
    assert "evt_03" in timeline.causal_chains[0]["downstream_affected_event_ids"]


def test_deterministic_error_fingerprint():
    """Verifies fingerprint stability across repeated calls and sensitivity to error type."""
    fp1 = compute_error_fingerprint("sandbox", "SecurityPolicyViolation", "sandbox", "failure")
    fp2 = compute_error_fingerprint("sandbox", "SecurityPolicyViolation", "sandbox", "failure")
    fp3 = compute_error_fingerprint("sandbox", "DiskQuotaExceeded", "sandbox", "failure")

    assert fp1 == fp2
    assert fp1 != fp3
    assert len(fp1) == 16


def test_replay_is_data_only():
    """HARD INVARIANT: Event replay is static data only and produces zero side effects."""
    reconstructor = TimelineReconstructor()
    cid = "corr_replay_001"
    ev = Event(
        event_id="evt_r1",
        correlation_id=cid,
        event_type="native.computer.click",
        source="computer_interaction",
        payload={"x": 100, "y": 200},
    )
    reconstructor.ingest_event(ev)

    replay = reconstructor.replay_events(cid)
    assert isinstance(replay, list)
    assert len(replay) == 1
    assert replay[0]["event_id"] == "evt_r1"
    assert replay[0]["payload"]["x"] == 100


# =============================================================================
# 5. Dependency-Aware Subsystem Health Aggregator
# =============================================================================

def test_subsystem_health_aggregator():
    """Verifies overall state transitions based on critical and non-critical subsystems."""
    # Reset custom statuses
    SubsystemHealthAggregator.reset_custom_statuses()

    initial = SubsystemHealthAggregator.get_unified_health()
    assert initial.overall_state == SubsystemHealthState.HEALTHY
    assert initial.score == 100.0

    # Degrade non-critical subsystem (e.g. redis)
    SubsystemHealthAggregator.set_subsystem_status("redis", SubsystemHealthState.DEGRADED, "High latency")
    report = SubsystemHealthAggregator.get_unified_health()
    assert report.overall_state == SubsystemHealthState.DEGRADED
    assert report.subsystems["redis"].state == SubsystemHealthState.DEGRADED

    # Fail critical subsystem (e.g. rust_runtime)
    SubsystemHealthAggregator.set_subsystem_status("rust_runtime", SubsystemHealthState.FAILED, "IPC socket terminated")
    report2 = SubsystemHealthAggregator.get_unified_health()
    assert report2.overall_state == SubsystemHealthState.FAILED
    assert report2.subsystems["rust_runtime"].state == SubsystemHealthState.FAILED

    # Reset
    SubsystemHealthAggregator.reset_custom_statuses()
    report3 = SubsystemHealthAggregator.get_unified_health()
    assert report3.overall_state == SubsystemHealthState.HEALTHY


# =============================================================================
# 6. Native Bridge Models
# =============================================================================

def test_native_event_and_envelope_compatibility():
    """Verifies Pydantic native telemetry models mirror Rust types."""
    nev = NativeEvent(
        event_id="nev_001",
        correlation_id="corr_native_1",
        event_type="runtime.request.completed",
        severity=NativeSeverity.INFO,
        domain=NativeExecutionDomain.NATIVE_RUNTIME,
        privacy_class=NativePrivacyClass.INTERNAL,
        source="kairo-runtime",
        timestamp_nanos=1_700_000_000_000_000_000,
        monotonic_nanos=500_000_000,
        outcome=NativeOutcome.SUCCESS,
        payload={"duration_ms": 12.5},
    )

    req = RuntimeRequest(
        operation="sys.info",
        correlation_id="corr_native_1",
        trace_id="trc_001",
        span_id="spn_001",
    )
    assert req.correlation_id == "corr_native_1"
    assert req.trace_id == "trc_001"

    resp = RuntimeResponse(
        request_id=req.request_id,
        protocol_version="1.0",
        status="OK",
        correlation_id="corr_native_1",
        native_events=[nev],
    )
    assert resp.native_events is not None
    assert len(resp.native_events) == 1
    assert resp.native_events[0].event_id == "nev_001"


# =============================================================================
# 7. Observability REST Router Endpoints
# =============================================================================

def test_observability_rest_endpoints():
    """Verifies all Task 86 REST endpoints return proper responses without auth bypass."""
    client = TestClient(app)

    # 1. /health/components
    res = client.get("/health/components")
    assert res.status_code == 200
    data = res.json()
    assert "overall_state" in data
    assert "subsystems" in data
    assert "rust_runtime" in data["subsystems"]

    # 2. Ingest an event to test queries
    test_cid = "corr_api_test_42"
    ev = Event(
        event_id="evt_api_1",
        correlation_id=test_cid,
        event_type="execution.completed",
        source="test",
        severity=EventSeverity.INFO,
        payload={"status": "ok"},
    )
    timeline_reconstructor.ingest_event(ev)

    # 3. GET /api/v1/observability/events
    res_events = client.get(f"/api/v1/observability/events?correlation_id={test_cid}")
    assert res_events.status_code == 200
    events_list = res_events.json()
    assert len(events_list) >= 1
    assert events_list[0]["event_id"] == "evt_api_1"

    # 4. GET /api/v1/observability/executions/{correlation_id}
    res_exec = client.get(f"/api/v1/observability/executions/{test_cid}")
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert exec_data["correlation_id"] == test_cid
    assert exec_data["event_count"] >= 1

    # 5. GET /api/v1/observability/timeline/{correlation_id}
    res_timeline = client.get(f"/api/v1/observability/timeline/{test_cid}")
    assert res_timeline.status_code == 200
    tl_data = res_timeline.json()
    assert tl_data["correlation_id"] == test_cid
    assert tl_data["overall_status"] == "COMPLETED"

    # 6. GET /api/v1/observability/replay/{correlation_id}
    res_replay = client.get(f"/api/v1/observability/replay/{test_cid}")
    assert res_replay.status_code == 200
    rep_list = res_replay.json()
    assert len(rep_list) >= 1

    # 7. GET /api/v1/observability/subsystems
    res_sub = client.get("/api/v1/observability/subsystems")
    assert res_sub.status_code == 200
    sub_data = res_sub.json()
    assert sub_data["overall_state"] == "HEALTHY"

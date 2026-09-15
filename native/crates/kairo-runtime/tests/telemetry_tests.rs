use kairo_protocol::telemetry::{
    NativeEvent, NativeExecutionDomain, NativeOutcome, NativeSeverity,
};
use kairo_protocol::RuntimeRequest;
use kairo_runtime::cancellation::CancellationRegistry;
use kairo_runtime::capabilities::CapabilityRegistry;
use kairo_runtime::dispatcher::RequestDispatcher;
use kairo_runtime::lifecycle::LifecycleManager;
use kairo_runtime::metrics::RuntimeMetrics;
use kairo_runtime::telemetry::{NativeEventBuffer, NativeRedactor, NativeTracer};
use serde_json::json;
use std::sync::Arc;

#[test]
fn test_native_redactor_credentials_and_tokens() {
    // Bearer token
    let text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123";
    let redacted = NativeRedactor::redact_text(text);
    assert!(redacted.contains("[REDACTED_SECRET]"));
    assert!(!redacted.contains("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123"));

    // API key
    let key_text =
        "Connecting with sk-1234567890abcdef123456 and ghp_123456789012345678901234567890";
    let redacted_key = NativeRedactor::redact_text(key_text);
    assert!(redacted_key.contains("[REDACTED_SECRET]"));
    assert!(!redacted_key.contains("sk-1234567890abcdef123456"));
    assert!(!redacted_key.contains("ghp_123456789012345678901234567890"));

    // Password in key-value format
    let pass_text = "Connecting user=admin password=super_secret_password_123";
    let redacted_pass = NativeRedactor::redact_text(pass_text);
    assert!(redacted_pass.contains("[REDACTED_SECRET]"));
    assert!(!redacted_pass.contains("super_secret_password_123"));

    // Private key block
    let rsa_key =
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0\n-----END RSA PRIVATE KEY-----";
    let redacted_rsa = NativeRedactor::redact_text(rsa_key);
    assert!(redacted_rsa.contains("[REDACTED_PRIVATE_KEY]"));
    assert!(!redacted_rsa.contains("MIIEowIBAAKCAQEA0"));

    // URL auth credentials
    let url = "https://kairo_user:super_secret_pass@api.internal.local/v1";
    let redacted_url = NativeRedactor::redact_text(url);
    assert!(redacted_url.contains("https://kairo_user:[REDACTED]@api.internal.local/v1"));
    assert!(!redacted_url.contains("super_secret_pass"));
}

#[test]
fn test_native_redactor_json_payloads() {
    let payload = json!({
        "status": "active",
        "nested": {
            "api_key": "sk-secret999999999",
            "token": "tok_xyz_secret_12345",
            "normal_field": "safe_value"
        },
        "credentials": {
            "password": "my_password_xyz"
        }
    });

    let sanitized = NativeRedactor::redact_json(&payload);
    assert_eq!(sanitized["status"], "active");
    assert_eq!(sanitized["nested"]["normal_field"], "safe_value");
    assert_eq!(sanitized["nested"]["api_key"], "[REDACTED]");
    assert_eq!(sanitized["nested"]["token"], "[REDACTED]");
    assert_eq!(sanitized["credentials"], "[REDACTED]");
}

#[test]
fn test_native_tracer_span_lifecycle() {
    let tracer = NativeTracer::new();
    let trace_id = "trc_test_001";
    let span_id = tracer.start_span(trace_id, None, "test_operation", json!({"param": "value"}));
    assert!(!span_id.is_empty());

    let record = tracer.end_span(&span_id, "OK");
    assert!(record.is_some());
    let span_rec = record.unwrap();
    assert_eq!(span_rec.span_id, span_id);
    assert_eq!(span_rec.trace_id, trace_id);
    assert_eq!(span_rec.name, "test_operation");
    assert_eq!(span_rec.status, "OK");
    assert!(span_rec.duration_ns > 0);
}

#[test]
fn test_native_event_buffer_bounded_queue_and_priority_backpressure() {
    // Create a tiny buffer of capacity 5
    let buffer = NativeEventBuffer::new(5);

    // Record 2 P0 (Critical) events
    for i in 0..2 {
        let ev = NativeEvent::new(
            format!("test.critical.{}", i),
            NativeExecutionDomain::Security,
            NativeSeverity::Critical,
            NativeOutcome::Block,
            "security",
            json!({"alert": i}),
        );
        buffer.record(ev);
    }

    // Record 2 P1 (Error) events
    for i in 0..2 {
        let ev = NativeEvent::new(
            format!("test.error.{}", i),
            NativeExecutionDomain::Runtime,
            NativeSeverity::Error,
            NativeOutcome::Fail,
            "runtime",
            json!({"err": i}),
        );
        buffer.record(ev);
    }

    // Record 1 P3 (Debug) event - reaches capacity 5
    let debug_ev = NativeEvent::new(
        "test.debug.1",
        NativeExecutionDomain::Runtime,
        NativeSeverity::Debug,
        NativeOutcome::Unknown,
        "runtime",
        json!({"debug": true}),
    );
    buffer.record(debug_ev);

    let stats_before = buffer.stats();
    assert_eq!(stats_before.currently_buffered, 5);
    assert_eq!(stats_before.dropped_p3, 0);

    // Record a 6th event (P2 Info) -> should cause the P3 Debug event to be dropped!
    let info_ev = NativeEvent::new(
        "test.info.1",
        NativeExecutionDomain::Runtime,
        NativeSeverity::Info,
        NativeOutcome::Success,
        "runtime",
        json!({"info": true}),
    );
    buffer.record(info_ev);

    let stats_after = buffer.stats();
    assert_eq!(stats_after.currently_buffered, 5);
    assert_eq!(stats_after.dropped_p3, 1);
    assert_eq!(stats_after.critical_p0_emitted, 2);

    // Verify all Critical events are still present
    let recent = buffer.recent_events(10);
    assert_eq!(recent.len(), 5);
    assert!(recent.iter().any(|e| e.event_type == "test.critical.0"));
    assert!(recent.iter().any(|e| e.event_type == "test.critical.1"));
}

#[test]
fn test_native_event_buffer_correlation_drain() {
    let buffer = NativeEventBuffer::new(100);
    let target_corr = "corr_special_999";

    let ev1 = NativeEvent::new(
        "step.one",
        NativeExecutionDomain::Tool,
        NativeSeverity::Info,
        NativeOutcome::Success,
        "tool",
        json!({}),
    )
    .with_correlation(Some(target_corr.to_string()), None, None, None);

    let ev2 = NativeEvent::new(
        "step.two",
        NativeExecutionDomain::Network,
        NativeSeverity::Info,
        NativeOutcome::Success,
        "network",
        json!({}),
    )
    .with_correlation(Some(target_corr.to_string()), None, None, None);

    let ev3 = NativeEvent::new(
        "unrelated.step",
        NativeExecutionDomain::Runtime,
        NativeSeverity::Info,
        NativeOutcome::Success,
        "runtime",
        json!({}),
    )
    .with_correlation(Some("other_corr".to_string()), None, None, None);

    buffer.record(ev1);
    buffer.record(ev2);
    buffer.record(ev3);

    let drained = buffer.drain_for_correlation(target_corr);
    assert_eq!(drained.len(), 2);
    assert_eq!(drained[0].event_type, "step.one");
    assert_eq!(drained[1].event_type, "step.two");

    // Ensure unrelated event was NOT drained
    let remaining = buffer.recent_events(10);
    assert_eq!(remaining.len(), 1);
    assert_eq!(remaining[0].event_type, "unrelated.step");
}

#[tokio::test]
async fn test_dispatcher_telemetry_and_correlation_propagation() {
    let lifecycle = LifecycleManager::new(Arc::new(std::sync::atomic::AtomicU32::new(0)));
    lifecycle.set_ready().await;
    let capabilities = Arc::new(CapabilityRegistry::new());
    let cancellation = Arc::new(CancellationRegistry::new());
    let metrics = RuntimeMetrics::new();
    let event_buffer = NativeEventBuffer::new(500);
    let tracer = NativeTracer::new();

    let dispatcher = RequestDispatcher::with_telemetry(
        lifecycle.clone(),
        capabilities,
        cancellation,
        metrics.clone(),
        event_buffer.clone(),
        tracer.clone(),
    );

    let correlation_id = "corr_end_to_end_test";
    let trace_id = "trc_end_to_end_test";
    let span_id = "span_root_001";

    let mut req = RuntimeRequest::new("sys.ping", json!({"hello": "world"}));
    req.correlation_id = Some(correlation_id.to_string());
    req.trace_id = Some(trace_id.to_string());
    req.span_id = Some(span_id.to_string());

    let resp = dispatcher.dispatch(req).await;

    // Verify response metadata preservation
    assert_eq!(resp.correlation_id, Some(correlation_id.to_string()));
    assert_eq!(resp.trace_id, Some(trace_id.to_string()));
    assert!(resp.span_id.is_some());

    // Verify native events were attached to response
    assert!(resp.native_events.is_some());
    let events = resp.native_events.unwrap();
    assert!(!events.is_empty());
    assert!(events
        .iter()
        .any(|e| e.event_type == "runtime.request.received"));
    assert!(events
        .iter()
        .any(|e| e.event_type == "runtime.request.completed"));

    // Verify metrics tracked native events
    let snap = metrics.snapshot();
    assert!(snap.native_events_emitted_total >= 2);
}

#[tokio::test]
async fn test_dispatcher_obs_events_and_stats_capabilities() {
    let lifecycle = LifecycleManager::new(Arc::new(std::sync::atomic::AtomicU32::new(0)));
    lifecycle.set_ready().await;
    let capabilities = Arc::new(CapabilityRegistry::new());
    let cancellation = Arc::new(CancellationRegistry::new());
    let metrics = RuntimeMetrics::new();
    let dispatcher = RequestDispatcher::new(lifecycle, capabilities, cancellation, metrics);

    // Query obs.stats
    let stats_req = RuntimeRequest::new("obs.stats", json!({}));
    let stats_resp = dispatcher.dispatch(stats_req).await;
    assert_eq!(
        stats_resp.status,
        kairo_protocol::envelope::ResponseStatus::Ok
    );
    let stats_val = stats_resp.result.unwrap();
    assert!(stats_val.get("capacity").is_some());
    assert!(stats_val.get("total_emitted").is_some());

    // Query obs.events
    let events_req = RuntimeRequest::new("obs.events", json!({"limit": 10}));
    let events_resp = dispatcher.dispatch(events_req).await;
    assert_eq!(
        events_resp.status,
        kairo_protocol::envelope::ResponseStatus::Ok
    );
    let events_val = events_resp.result.unwrap();
    assert!(events_val.is_array());
}

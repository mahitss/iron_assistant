use kairo_protocol::*;
use serde_json::json;

#[test]
fn test_runtime_request_roundtrip() {
    let mut req = RuntimeRequest::new("sys.ping", json!({"ping": "pong"}));
    req.cancellation_id = Some("cancel-123".to_string());
    req.correlation_id = Some("trace-abc".to_string());
    req.caller_context = Some(RequestContext {
        user_id: Some("usr-1".to_string()),
        tenant_id: Some("ten-1".to_string()),
        security_level: Some("high".to_string()),
        auth_token_hash: Some("sha256:abc".to_string()),
        client_version: Some("1.0.0".to_string()),
    });

    let serialized = serde_json::to_string(&req).expect("serialize request");
    let deserialized: RuntimeRequest =
        serde_json::from_str(&serialized).expect("deserialize request");

    assert_eq!(req.request_id, deserialized.request_id);
    assert_eq!(req.operation, deserialized.operation);
    assert_eq!(req.cancellation_id, deserialized.cancellation_id);
    assert_eq!(req.correlation_id, deserialized.correlation_id);
    assert!(deserialized.validate().is_ok());
}

#[test]
fn test_protocol_version_mismatch() {
    let mut req = RuntimeRequest::new("sys.ping", json!({}));
    req.protocol_version = "99.0".to_string();

    let err = req
        .validate()
        .expect_err("should reject unsupported version");
    assert_eq!(err.category, ErrorCategory::ProtocolError);
    assert_eq!(err.code, "UNSUPPORTED_PROTOCOL_VERSION");
}

#[test]
fn test_resource_budget_bounds() {
    let valid_budget = ResourceBudget {
        max_cpu_percent: Some(50.0),
        max_memory_bytes: Some(1024 * 1024 * 100),
        max_execution_time_ms: Some(15_000),
        max_concurrency: Some(4),
        max_output_bytes: Some(1024 * 512),
    };
    assert!(valid_budget.validate().is_ok());

    // Invalid CPU > 100
    let bad_cpu = ResourceBudget {
        max_cpu_percent: Some(150.0),
        ..valid_budget.clone()
    };
    assert!(bad_cpu.validate().is_err());

    // Negative CPU
    let bad_cpu_neg = ResourceBudget {
        max_cpu_percent: Some(-5.0),
        ..valid_budget.clone()
    };
    assert!(bad_cpu_neg.validate().is_err());

    // Duration > 300,000 ms
    let bad_duration = ResourceBudget {
        max_execution_time_ms: Some(500_000),
        ..valid_budget.clone()
    };
    assert!(bad_duration.validate().is_err());

    // Zero duration
    let zero_duration = ResourceBudget {
        max_execution_time_ms: Some(0),
        ..valid_budget
    };
    assert!(zero_duration.validate().is_err());
}

#[test]
fn test_runtime_response_serialization() {
    let timing = TimingMetadata {
        queue_time_ms: 2,
        execution_time_ms: 10,
        total_time_ms: 12,
    };
    let resp = RuntimeResponse::ok("req-123", json!({"status": "healthy"}), timing);

    let json_str = serde_json::to_string(&resp).expect("serialize response");
    let parsed: RuntimeResponse = serde_json::from_str(&json_str).expect("deserialize");
    assert_eq!(parsed.status, ResponseStatus::Ok);
    assert_eq!(parsed.request_id, "req-123");
    assert!(parsed.result.is_some());
    assert!(parsed.error.is_none());
}

#[test]
fn test_runtime_error_categories() {
    let err = RuntimeError::auth_failure("BAD_SECRET", "Invalid handshake credentials");
    assert_eq!(err.category, ErrorCategory::AuthenticationFailure);
    assert!(!err.retryable);

    let err_deadline = RuntimeError::deadline_exceeded("TIMEOUT", "Took too long");
    assert_eq!(err_deadline.category, ErrorCategory::DeadlineExceeded);
    assert!(err_deadline.retryable);
}

#[test]
fn test_health_state_transitions() {
    assert!(HealthState::Ready.accepts_requests());
    assert!(HealthState::Degraded.accepts_requests());
    assert!(!HealthState::Draining.accepts_requests());
    assert!(!HealthState::Stopped.accepts_requests());
    assert!(HealthState::Stopped.is_terminal());
}

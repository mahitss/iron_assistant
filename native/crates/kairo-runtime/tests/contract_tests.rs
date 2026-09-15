use chrono::Utc;
use kairo_protocol::*;
use kairo_runtime::*;
use serde_json::json;
use std::sync::Arc;

fn create_test_dispatcher() -> (
    RequestDispatcher,
    Arc<LifecycleManager>,
    Arc<CancellationRegistry>,
) {
    let metrics = RuntimeMetrics::new();
    let cancellation = Arc::new(CancellationRegistry::new());
    let capabilities = Arc::new(CapabilityRegistry::new());
    let lifecycle = LifecycleManager::new(Arc::new(std::sync::atomic::AtomicU32::new(0)));
    let dispatcher = RequestDispatcher::new(
        lifecycle.clone(),
        capabilities.clone(),
        cancellation.clone(),
        metrics,
    );
    (dispatcher, lifecycle, cancellation)
}

#[tokio::test]
async fn test_version_negotiation_rules() {
    let v1 = ProtocolVersion::new(1, 0, 0);
    let v1_1 = ProtocolVersion::new(1, 1, 0);
    let v1_patch = ProtocolVersion::new(1, 0, 5);
    let v2 = ProtocolVersion::new(2, 0, 0);

    // Exact match
    assert!(v1.is_compatible_with(&v1));

    // Minor backward compatible: server 1.1 satisfies client 1.0, but server 1.0 cannot satisfy client 1.1
    assert!(v1_1.is_compatible_with(&v1));
    assert!(!v1.is_compatible_with(&v1_1));

    // Patch compatible
    assert!(v1_patch.is_compatible_with(&v1));

    // Major mismatch rejected
    assert!(!v2.is_compatible_with(&v1));
    assert!(!v1.is_compatible_with(&v2));

    // Negotiation
    let negotiated = v1_1.negotiate(&v1).expect("compatible negotiation");
    assert_eq!(negotiated, v1);

    let err = v2.negotiate(&v1);
    assert!(err.is_err());
}

#[tokio::test]
async fn test_capability_attestation_and_fingerprints() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    let cap_fp = lifecycle.capability_fingerprint().await;
    let cfg_fp = lifecycle.configuration_fingerprint().await;

    assert!(cap_fp.starts_with("cfp_"));
    assert!(cfg_fp.starts_with("cfg_"));

    // Query sys.capabilities
    let req = RuntimeRequest::new("sys.capabilities", json!({}));
    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);
    let result = resp.result.unwrap();
    let caps = result.as_array().unwrap();
    assert!(!caps.is_empty());

    // Verify attestation metadata exists on capabilities
    let first_cap = &caps[0];
    assert!(first_cap.get("enforcement_level").is_some());
    assert!(first_cap.get("platform").is_some());
    assert!(first_cap.get("status").is_some());

    // Query sys.contract
    let req_contract = RuntimeRequest::new("sys.contract", json!({}));
    let resp_contract = dispatcher.dispatch(req_contract).await;
    assert_eq!(resp_contract.status, ResponseStatus::Ok);
    let contract_res = resp_contract.result.unwrap();
    assert_eq!(contract_res.get("protocol_version").unwrap(), "1.0");
    assert_eq!(
        contract_res
            .get("capability_fingerprint")
            .unwrap()
            .as_str()
            .unwrap(),
        cap_fp
    );
    assert_eq!(
        contract_res
            .get("configuration_fingerprint")
            .unwrap()
            .as_str()
            .unwrap(),
        cfg_fp
    );
}

#[tokio::test]
async fn test_handshake_session_establishment() {
    let authenticator = HandshakeAuthenticator::new(Some("secret-123".to_string()));
    let (_dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    // Successful handshake
    let req = HandshakeRequest {
        protocol_version: "1.0.0".to_string(),
        secret: Some("secret-123".to_string()),
        client_id: "test-python-brain".to_string(),
        client_version: "1.0.0".to_string(),
        client_instance_id: Some("client-inst-1".to_string()),
        nonce: Some("nonce-abc".to_string()),
        requested_capabilities: None,
    };

    let session_id = lifecycle.get_session_id().await;
    let cap_fp = lifecycle.capability_fingerprint().await;
    let cfg_fp = lifecycle.configuration_fingerprint().await;

    let resp = authenticator.authenticate_with_session(
        &req,
        vec![],
        "0.1.0",
        Some(lifecycle.runtime_instance_id().to_string()),
        session_id.clone(),
        Some(cap_fp.clone()),
        Some(cfg_fp),
    );

    assert!(resp.authenticated);
    assert_eq!(resp.session_id, session_id);
    assert!(resp.capability_fingerprint.unwrap().starts_with("cfp_"));

    // Incompatible major version handshake
    let bad_version_req = HandshakeRequest {
        protocol_version: "2.0.0".to_string(),
        secret: Some("secret-123".to_string()),
        client_id: "test-client".to_string(),
        client_version: "1.0.0".to_string(),
        ..Default::default()
    };
    let bad_version_resp = authenticator.authenticate(&bad_version_req, vec![], "0.1.0");
    assert!(!bad_version_resp.authenticated);
    assert!(bad_version_resp
        .error
        .unwrap()
        .contains("Protocol version mismatch"));
}

#[tokio::test]
async fn test_session_binding_and_validation() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    let valid_session = lifecycle.get_session_id().await;

    // Valid session succeeds
    let mut req_valid = RuntimeRequest::new("sys.ping", json!({"ping": "1"}));
    req_valid.session_id = valid_session.clone();
    let resp_valid = dispatcher.dispatch(req_valid).await;
    assert_eq!(resp_valid.status, ResponseStatus::Ok);

    // Mismatched / invalid session is rejected
    let mut req_invalid = RuntimeRequest::new("sys.ping", json!({"ping": "2"}));
    req_invalid.session_id = Some("invalid-stale-session-999".to_string());
    let resp_invalid = dispatcher.dispatch(req_invalid).await;
    assert_ne!(resp_valid.status, ResponseStatus::Error);
    assert_eq!(resp_invalid.status, ResponseStatus::Error);
    let err = resp_invalid.error.expect("error envelope");
    assert_eq!(err.code, "SESSION_INVALID");
}

#[tokio::test]
async fn test_replay_protection_and_duplicate_detection() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    let mut req1 = RuntimeRequest::new("sys.ping", json!({"key": "val"}));
    let msg_id = "msg-unique-test-123".to_string();
    req1.message_id = msg_id.clone();
    req1.session_id = lifecycle.get_session_id().await;

    // First dispatch succeeds
    let resp1 = dispatcher.dispatch(req1.clone()).await;
    assert_eq!(resp1.status, ResponseStatus::Ok);

    // Replay of same message_id should return the cached response
    let resp2 = dispatcher.dispatch(req1).await;
    assert_eq!(resp2.status, ResponseStatus::Ok);
    assert_eq!(resp2.request_id, resp1.request_id);
}

#[tokio::test]
async fn test_deadline_and_freshness_expiration() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    // Past deadline
    let mut req_expired = RuntimeRequest::new("sys.ping", json!({}));
    req_expired.session_id = lifecycle.get_session_id().await;
    req_expired.deadline = Some(Utc::now() - chrono::Duration::seconds(5));

    let resp_expired = dispatcher.dispatch(req_expired).await;
    assert_eq!(resp_expired.status, ResponseStatus::Error);
    let err = resp_expired.error.expect("error envelope");
    assert_eq!(err.code, "REQUEST_DEADLINE_EXPIRED");

    // Stale created_at (> 5 minutes ago)
    let mut req_stale = RuntimeRequest::new("sys.ping", json!({}));
    req_stale.session_id = lifecycle.get_session_id().await;
    req_stale.created_at = Some(Utc::now() - chrono::Duration::seconds(400));

    let resp_stale = dispatcher.dispatch(req_stale).await;
    assert_eq!(resp_stale.status, ResponseStatus::Error);
    let err_stale = resp_stale.error.expect("stale error");
    assert_eq!(err_stale.code, "REQUEST_TIMESTAMP_STALE");
}

#[tokio::test]
async fn test_authorization_and_approval_binding() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    // 1. Expired authorization context
    let mut req_auth_expired = RuntimeRequest::new("sys.ping", json!({}));
    req_auth_expired.session_id = lifecycle.get_session_id().await;
    req_auth_expired.authorization_context = Some(AuthorizationContext {
        decision_id: "dec-1".to_string(),
        policy_id: Some("pol-1".to_string()),
        security_level: "high".to_string(),
        approval_id: None,
        approved_tool: None,
        approved_target: None,
        granted_at: Utc::now() - chrono::Duration::seconds(60),
        expires_at: Some(Utc::now() - chrono::Duration::seconds(10)),
        signature_hash: None,
    });
    let resp = dispatcher.dispatch(req_auth_expired).await;
    assert_eq!(resp.status, ResponseStatus::Error);
    assert_eq!(resp.error.unwrap().code, "AUTHORIZATION_EXPIRED");

    // 2. Approval tool mismatch (approved for tool_alpha, executing sys.ping)
    let mut req_tool_mismatch = RuntimeRequest::new("sys.ping", json!({}));
    req_tool_mismatch.session_id = lifecycle.get_session_id().await;
    req_tool_mismatch.authorization_context = Some(AuthorizationContext {
        decision_id: "dec-2".to_string(),
        policy_id: Some("pol-2".to_string()),
        security_level: "critical".to_string(),
        approval_id: Some("appr-123".to_string()),
        approved_tool: Some("tool_alpha".to_string()),
        approved_target: None,
        granted_at: Utc::now(),
        expires_at: Some(Utc::now() + chrono::Duration::seconds(60)),
        signature_hash: None,
    });
    let resp_tool = dispatcher.dispatch(req_tool_mismatch).await;
    assert_eq!(resp_tool.status, ResponseStatus::Error);
    assert_eq!(resp_tool.error.unwrap().code, "APPROVAL_INVALID");

    // 3. Approval target mismatch
    let mut req_target_mismatch = RuntimeRequest::new("sys.ping", json!({}));
    req_target_mismatch.session_id = lifecycle.get_session_id().await;
    req_target_mismatch.authorization_context = Some(AuthorizationContext {
        decision_id: "dec-3".to_string(),
        policy_id: Some("pol-3".to_string()),
        security_level: "critical".to_string(),
        approval_id: Some("appr-456".to_string()),
        approved_tool: Some("sys.ping".to_string()),
        approved_target: Some("host_a.internal".to_string()),
        granted_at: Utc::now(),
        expires_at: Some(Utc::now() + chrono::Duration::seconds(60)),
        signature_hash: None,
    });
    req_target_mismatch.target_context = Some(OperationTargetContext {
        target_type: "host".to_string(),
        target_identifier: "host_b.internal".to_string(),
        expected_hash: None,
    });
    let resp_target = dispatcher.dispatch(req_target_mismatch).await;
    assert_eq!(resp_target.status, ResponseStatus::Error);
    assert_eq!(resp_target.error.unwrap().code, "APPROVAL_INVALID");
}

#[tokio::test]
async fn test_resource_allocation_binding() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    // 1. Expired resource allocation
    let mut req_res_expired = RuntimeRequest::new("sys.ping", json!({}));
    req_res_expired.session_id = lifecycle.get_session_id().await;
    req_res_expired.resource_context = Some(ResourceAllocationContext {
        allocation_id: "alloc-1".to_string(),
        request_id: req_res_expired.request_id.clone(),
        capability_id: "sys.ping".to_string(),
        limits: ResourceBudget::default(),
        remaining_budget: None,
        expires_at: Utc::now() - chrono::Duration::seconds(10),
    });
    let resp = dispatcher.dispatch(req_res_expired).await;
    assert_eq!(resp.status, ResponseStatus::Error);
    assert_eq!(resp.error.unwrap().code, "RESOURCE_EXPIRED");

    // 2. Request ID mismatch with allocation
    let mut req_mismatch = RuntimeRequest::new("sys.ping", json!({}));
    req_mismatch.session_id = lifecycle.get_session_id().await;
    req_mismatch.resource_context = Some(ResourceAllocationContext {
        allocation_id: "alloc-2".to_string(),
        request_id: "some-other-req-id".to_string(),
        capability_id: "sys.ping".to_string(),
        limits: ResourceBudget::default(),
        remaining_budget: None,
        expires_at: Utc::now() + chrono::Duration::seconds(60),
    });
    let resp_mismatch = dispatcher.dispatch(req_mismatch).await;
    assert_eq!(resp_mismatch.status, ResponseStatus::Error);
    assert_eq!(resp_mismatch.error.unwrap().code, "RESOURCE_INVALID");
}

#[tokio::test]
async fn test_target_anti_toctou_validation() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    // Correct expected hash
    let mut req_ok = RuntimeRequest::new("sys.ping", json!({}));
    req_ok.session_id = lifecycle.get_session_id().await;
    req_ok.target_context = Some(OperationTargetContext {
        target_type: "file".to_string(),
        target_identifier: "target-file.txt".to_string(),
        expected_hash: Some("sha256:abc123expected".to_string()),
    });
    req_ok.payload = json!({"current_hash": "sha256:abc123expected"});
    let resp_ok = dispatcher.dispatch(req_ok).await;
    assert_eq!(resp_ok.status, ResponseStatus::Ok);

    // Mismatched expected hash
    let mut req_bad = RuntimeRequest::new("sys.ping", json!({}));
    req_bad.session_id = lifecycle.get_session_id().await;
    req_bad.target_context = Some(OperationTargetContext {
        target_type: "file".to_string(),
        target_identifier: "target-file.txt".to_string(),
        expected_hash: Some("sha256:abc123expected".to_string()),
    });
    req_bad.payload = json!({"current_hash": "sha256:TAMPERED_HASH"});
    let resp_bad = dispatcher.dispatch(req_bad).await;
    assert_eq!(resp_bad.status, ResponseStatus::Error);
    assert_eq!(resp_bad.error.unwrap().code, "TARGET_CHANGED");
}

#[tokio::test]
async fn test_emergency_stop_priority_and_drain() {
    let (dispatcher, lifecycle, cancellation) = create_test_dispatcher();
    lifecycle.set_ready().await;

    // Register a dummy active task in cancellation registry
    let cancel_token = cancellation.register("dummy-active-task-1").await;
    assert!(!cancel_token.is_cancelled());

    // Dispatch sys.stop
    let req_stop =
        RuntimeRequest::new("sys.stop", json!({"reason": "security_perimeter_breached"}));
    let resp_stop = dispatcher.dispatch(req_stop).await;

    assert!(
        resp_stop.status == ResponseStatus::EmergencyStopped
            || resp_stop.status == ResponseStatus::Ok
    );
    let res = resp_stop.result.unwrap();
    assert_eq!(res.get("status").unwrap(), "EMERGENCY_STOPPED");

    // All active tokens must now be cancelled
    assert!(cancel_token.is_cancelled());

    // Subsequent executions must be rejected due to stopping/draining state
    let req_subsequent = RuntimeRequest::new("sys.ping", json!({}));
    let resp_subsequent = dispatcher.dispatch(req_subsequent).await;
    assert_eq!(resp_subsequent.status, ResponseStatus::ShuttingDown);
}

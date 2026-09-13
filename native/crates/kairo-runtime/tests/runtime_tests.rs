use futures::{SinkExt, StreamExt};
use kairo_protocol::*;
use kairo_runtime::*;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;
use tokio::net::{TcpListener, TcpStream};
use tokio_util::codec::Framed;

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
async fn test_dispatcher_ping_pong() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    let req = RuntimeRequest::new("sys.ping", json!({"hello": "world"}));
    let resp = dispatcher.dispatch(req).await;

    assert_eq!(resp.status, ResponseStatus::Ok);
    let result = resp.result.expect("result should exist");
    assert_eq!(result.get("reply").unwrap(), "pong");
    assert_eq!(result.get("echo").unwrap().get("hello").unwrap(), "world");
    assert!(resp.timing.is_some());
}

#[tokio::test]
async fn test_dispatcher_info_and_health() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    let req_info = RuntimeRequest::new("sys.info", json!({}));
    let resp_info = dispatcher.dispatch(req_info).await;
    assert_eq!(resp_info.status, ResponseStatus::Ok);
    let info_val = resp_info.result.unwrap();
    assert_eq!(info_val.get("protocol_version").unwrap(), "1.0");

    let req_health = RuntimeRequest::new("sys.health", json!({}));
    let resp_health = dispatcher.dispatch(req_health).await;
    assert_eq!(resp_health.status, ResponseStatus::Ok);
    let health_val = resp_health.result.unwrap();
    assert_eq!(health_val.get("state").unwrap(), "READY");
}

#[tokio::test]
async fn test_dispatcher_cooperative_cancellation() {
    let (dispatcher, lifecycle, cancellation) = create_test_dispatcher();
    lifecycle.set_ready().await;

    let mut req = RuntimeRequest::new("sys.sleep", json!({"duration_ms": 2000}));
    req.cancellation_id = Some("cancel-target-1".to_string());

    let disp_clone = dispatcher.clone();
    let handle = tokio::spawn(async move { disp_clone.dispatch(req).await });

    // Allow task to start sleeping
    tokio::time::sleep(Duration::from_millis(50)).await;

    // Trigger cancellation
    let cancelled = cancellation.cancel("cancel-target-1").await;
    assert!(cancelled);

    let resp = handle.await.expect("task join");
    assert_eq!(resp.status, ResponseStatus::Cancelled);
    assert_eq!(resp.error.unwrap().category, ErrorCategory::Cancelled);
}

#[tokio::test]
async fn test_dispatcher_deadline_enforcement() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.set_ready().await;

    let mut req = RuntimeRequest::new("sys.sleep", json!({"duration_ms": 1000}));
    req.deadline_ms = Some(50); // hard deadline of 50ms

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Error);
    let err = resp.error.expect("error must be present");
    assert_eq!(err.category, ErrorCategory::DeadlineExceeded);
}

#[tokio::test]
async fn test_dispatcher_draining_rejection() {
    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    lifecycle.drain().await;

    let req = RuntimeRequest::new("sys.ping", json!({}));
    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::ShuttingDown);
    assert_eq!(resp.error.unwrap().category, ErrorCategory::ShuttingDown);
}

#[tokio::test]
async fn test_handshake_authentication() {
    let authenticator = HandshakeAuthenticator::new(Some("secret-key-xyz".to_string()));

    let bad_req = HandshakeRequest {
        protocol_version: "1.0".to_string(),
        secret: Some("wrong-secret".to_string()),
        client_id: "test".to_string(),
        client_version: "1.0.0".to_string(),
    };
    let bad_resp = authenticator.authenticate(&bad_req, vec![], "0.1.0");
    assert!(!bad_resp.authenticated);

    let good_req = HandshakeRequest {
        protocol_version: "1.0".to_string(),
        secret: Some("secret-key-xyz".to_string()),
        client_id: "test".to_string(),
        client_version: "1.0.0".to_string(),
    };
    let good_resp = authenticator.authenticate(&good_req, vec![], "0.1.0");
    assert!(good_resp.authenticated);
}

#[tokio::test]
async fn test_ipc_transport_tcp_roundtrip() {
    // Find an ephemeral port
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    drop(listener);

    let config = RuntimeConfig {
        host: "127.0.0.1".to_string(),
        port,
        secret: Some("test-secret-123".to_string()),
        max_message_bytes: 1_048_576,
        max_concurrency: 4,
        shutdown_timeout_secs: 5,
        log_level: "error".to_string(),
    };

    let (dispatcher, lifecycle, _) = create_test_dispatcher();
    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);
    let server = Arc::new(IpcServer::new(config.clone(), lifecycle, dispatcher));

    tokio::spawn({
        let server = server.clone();
        async move {
            let _ = server.run(shutdown_rx).await;
        }
    });

    // Wait for server to bind
    tokio::time::sleep(Duration::from_millis(100)).await;

    // Connect client
    let stream = TcpStream::connect(format!("127.0.0.1:{}", port))
        .await
        .expect("connect");
    let mut framed = Framed::new(stream, LengthPrefixedCodec::new(1_048_576));

    // Send handshake
    let handshake = HandshakeRequest {
        protocol_version: "1.0".to_string(),
        secret: Some("test-secret-123".to_string()),
        client_id: "test-client".to_string(),
        client_version: "1.0.0".to_string(),
    };
    framed
        .send(serde_json::to_vec(&handshake).unwrap())
        .await
        .unwrap();

    let handshake_resp_bytes = framed.next().await.unwrap().unwrap();
    let handshake_resp: HandshakeResponse = serde_json::from_slice(&handshake_resp_bytes).unwrap();
    assert!(handshake_resp.authenticated);

    // Send ping
    let ping_req = RuntimeRequest::new("sys.ping", json!({"ping": "roundtrip"}));
    framed
        .send(serde_json::to_vec(&ping_req).unwrap())
        .await
        .unwrap();

    let ping_resp_bytes = framed.next().await.unwrap().unwrap();
    let ping_resp: RuntimeResponse = serde_json::from_slice(&ping_resp_bytes).unwrap();
    assert_eq!(ping_resp.status, ResponseStatus::Ok);
    assert_eq!(
        ping_resp
            .result
            .unwrap()
            .get("echo")
            .unwrap()
            .get("ping")
            .unwrap(),
        "roundtrip"
    );

    // Shutdown server
    let _ = shutdown_tx.send(true);
}

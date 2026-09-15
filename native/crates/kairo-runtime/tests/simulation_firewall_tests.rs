use kairo_protocol::contract::SimulationContext;
use kairo_protocol::envelope::{ResponseStatus, RuntimeRequest};
use kairo_protocol::error::ErrorCategory;
use kairo_runtime::*;
use serde_json::json;
use std::sync::Arc;

async fn create_test_dispatcher() -> RequestDispatcher {
    let metrics = RuntimeMetrics::new();
    let cancellation = Arc::new(CancellationRegistry::new());
    let capabilities = Arc::new(CapabilityRegistry::new());
    let lifecycle = LifecycleManager::new(Arc::new(std::sync::atomic::AtomicU32::new(0)));
    lifecycle.set_ready().await;

    RequestDispatcher::new(lifecycle, capabilities, cancellation, metrics)
}

#[tokio::test]
async fn test_sys_snapshot_capability() {
    let dispatcher = create_test_dispatcher().await;
    let req = RuntimeRequest::new("sys.snapshot", json!({}));
    let resp = dispatcher.dispatch(req).await;

    assert_eq!(resp.status, ResponseStatus::Ok);
    let result = resp.result.unwrap();
    assert!(result.get("runtime_instance_id").is_some());
    assert!(result.get("capability_fingerprint").is_some());
    assert!(result.get("configuration_fingerprint").is_some());
    assert!(result.get("memory_rss_bytes").is_some());
    assert!(result.get("capabilities_count").is_some());
}

#[tokio::test]
async fn test_simulation_firewall_blocks_mutating_capability() {
    let dispatcher = create_test_dispatcher().await;
    let sim_ctx = SimulationContext::new_sandboxed("sim_drill_42");

    // Attempting emergency stop or mutation under simulation context must be blocked
    let req = RuntimeRequest::new("sys.stop", json!({"reason": "simulated test"}))
        .with_simulation_context(sim_ctx.clone());

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Error);
    assert_eq!(
        resp.error.as_ref().unwrap().category,
        ErrorCategory::SimulationMutationBlocked
    );
    assert_eq!(
        resp.error.as_ref().unwrap().code,
        "SIMULATION_MUTATION_BLOCKED"
    );
}

#[tokio::test]
async fn test_simulation_firewall_allows_safe_read_inspection() {
    let dispatcher = create_test_dispatcher().await;
    let sim_ctx = SimulationContext::new_sandboxed("sim_drill_42");

    // Safe read-only inspection capability must succeed under simulation context
    let req = RuntimeRequest::new("sys.ping", json!({"probe": "read_only"}))
        .with_simulation_context(sim_ctx);

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);
    let result = resp.result.unwrap();
    assert_eq!(result.get("reply").unwrap(), "pong");
}

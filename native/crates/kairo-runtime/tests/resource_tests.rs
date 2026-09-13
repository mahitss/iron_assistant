use kairo_protocol::{ResponseStatus, RuntimeRequest};
use kairo_runtime::cancellation::CancellationRegistry;
use kairo_runtime::capabilities::CapabilityRegistry;
use kairo_runtime::lifecycle::LifecycleManager;
use kairo_runtime::metrics::RuntimeMetrics;
use kairo_runtime::sandbox::resources::{ResourceEnforceability, CROSS_PLATFORM_MATRIX};
use kairo_runtime::RequestDispatcher;
use serde_json::json;
use std::sync::atomic::AtomicU32;
use std::sync::Arc;

async fn setup_dispatcher() -> (RequestDispatcher, Arc<LifecycleManager>) {
    let lifecycle = LifecycleManager::new(Arc::new(AtomicU32::new(0)));
    let capabilities = Arc::new(CapabilityRegistry::new());
    let cancellation = Arc::new(CancellationRegistry::new());
    let metrics = RuntimeMetrics::new();

    let dispatcher = RequestDispatcher::new(
        lifecycle.clone(),
        capabilities.clone(),
        cancellation.clone(),
        metrics,
    );
    lifecycle.set_ready().await;
    (dispatcher, lifecycle)
}

#[tokio::test]
async fn test_cross_platform_matrix_honesty() {
    // Assert no fake limits: check that CPU is observed and memory on Windows is hard-enforced
    let cpu_entry = CROSS_PLATFORM_MATRIX
        .iter()
        .find(|e| e.resource_name == "CPU_TIME")
        .expect("CPU matrix entry");
    assert_eq!(
        cpu_entry.windows_support,
        ResourceEnforceability::ObservableOnly
    );

    let mem_entry = CROSS_PLATFORM_MATRIX
        .iter()
        .find(|e| e.resource_name == "MEMORY")
        .expect("Memory matrix entry");
    assert_eq!(
        mem_entry.windows_support,
        ResourceEnforceability::NativeEnforceable
    );

    let time_entry = CROSS_PLATFORM_MATRIX
        .iter()
        .find(|e| e.resource_name == "WALL_CLOCK_TIME")
        .expect("Time matrix entry");
    assert_eq!(
        time_entry.windows_support,
        ResourceEnforceability::NativeEnforceable
    );
}

#[tokio::test]
async fn test_successful_workload_telemetry_reporting() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.execute",
        json!({
            "request_id": "req_telem_1",
            "capability_id": "sandbox.echo",
            "arguments": ["telemetry_payload_alpha"]
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected result");
    assert_eq!(result["state"], "COMPLETED");
    assert!(result["resource_telemetry"].is_object());

    let telem = &result["resource_telemetry"];
    assert!(telem["wall_time_ms"].as_u64().is_some());
    assert!(telem["output_bytes"].as_u64().is_some());
    assert!(telem["workspace_bytes"].as_u64().is_some());
    assert_eq!(result["resource_violation"].is_null(), true);
}

#[tokio::test]
async fn test_memory_limit_exceeded_violation() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.execute",
        json!({
            "request_id": "req_mem_violation_1",
            "capability_id": "sandbox.probe",
            "payload": {
                "mode": "memory_burn",
                "megabytes": 128
            },
            "sandbox_policy": {
                "resource_budget": {
                    "max_memory_bytes": 64 * 1024 * 1024 // 64 MB limit, probe requests 128 MB
                }
            }
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected result");
    assert_eq!(result["state"], "RESOURCE_EXCEEDED");
    assert!(result["resource_violation"].is_object());

    let violation = &result["resource_violation"];
    assert_eq!(violation["violation_type"], "MEMORY_LIMIT_EXCEEDED");
    assert_eq!(violation["severity"], "HARD_LIMIT");
    assert_eq!(violation["enforcement_action"], "TERMINATE");
}

#[tokio::test]
async fn test_disk_limit_exceeded_violation() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.execute",
        json!({
            "request_id": "req_disk_violation_1",
            "capability_id": "sandbox.probe",
            "payload": {
                "mode": "disk_flood",
                "file_count": 5,
                "bytes_per_file": 20 * 1024 // 100 KB total
            },
            "sandbox_policy": {
                "resource_budget": {
                    "max_disk_bytes": 50 * 1024 // 50 KB limit
                }
            }
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected result");
    assert_eq!(result["state"], "RESOURCE_EXCEEDED");
    assert!(result["resource_violation"].is_object());

    let violation = &result["resource_violation"];
    assert_eq!(violation["violation_type"], "DISK_LIMIT_EXCEEDED");
}

#[tokio::test]
async fn test_file_count_limit_exceeded_violation() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.execute",
        json!({
            "request_id": "req_fc_violation_1",
            "capability_id": "sandbox.probe",
            "payload": {
                "mode": "disk_flood",
                "file_count": 25,
                "bytes_per_file": 100
            },
            "sandbox_policy": {
                "resource_budget": {
                    "max_file_count": 10 // only 10 files allowed
                }
            }
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected result");
    assert_eq!(result["state"], "RESOURCE_EXCEEDED");
    assert!(result["resource_violation"].is_object());

    let violation = &result["resource_violation"];
    assert_eq!(violation["violation_type"], "FILE_COUNT_LIMIT_EXCEEDED");
}

#[tokio::test]
async fn test_output_limit_exceeded_violation() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.execute",
        json!({
            "request_id": "req_out_violation_1",
            "capability_id": "sandbox.probe",
            "payload": {
                "mode": "flood"
            },
            "sandbox_policy": {
                "output_limits": {
                    "max_stdout_bytes": 1024,
                    "max_stderr_bytes": 1024,
                    "max_combined_bytes": 2048
                }
            }
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected result");
    assert_eq!(result["state"], "RESOURCE_EXCEEDED");
    assert_eq!(result["output_metadata"]["truncated"], true);
}

#[tokio::test]
async fn test_time_limit_exceeded_violation() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.execute",
        json!({
            "request_id": "req_time_violation_1",
            "capability_id": "sandbox.probe",
            "payload": {
                "mode": "sleep",
                "duration_ms": 2000
            },
            "sandbox_policy": {
                "resource_budget": {
                    "max_execution_time_ms": 100 // 100ms deadline, probe sleeps 2000ms
                }
            }
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected result");
    assert_eq!(result["state"], "TIMED_OUT");
    assert_eq!(result["timeout_state"], true);
    assert!(result["resource_violation"].is_object());

    let violation = &result["resource_violation"];
    assert_eq!(violation["violation_type"], "TIME_LIMIT_EXCEEDED");
}

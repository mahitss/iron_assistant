use kairo_protocol::sandbox::{
    EnvironmentPolicy, ExecutionRequest, ExecutionState, OutputLimits, SandboxPolicy,
};
use kairo_protocol::{ResourceBudget, ResponseStatus, RuntimeRequest};
use kairo_runtime::cancellation::CancellationRegistry;
use kairo_runtime::capabilities::CapabilityRegistry;
use kairo_runtime::lifecycle::LifecycleManager;
use kairo_runtime::metrics::RuntimeMetrics;
use kairo_runtime::sandbox::{
    validate_path_safety, IsolatedWorkspace, SandboxCapabilityRegistry, SandboxExecutor,
};
use kairo_runtime::RequestDispatcher;
use serde_json::json;
use std::path::PathBuf;
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
async fn test_sandbox_preflight_success() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.preflight",
        json!({
            "capability_id": "sandbox.echo"
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected preflight result");
    assert_eq!(result["accepted"], true);
    assert_eq!(result["capability_id"], "sandbox.echo");
    assert_eq!(result["platform_support"]["isolated_temp_workspace"], true);
}

#[tokio::test]
async fn test_sandbox_preflight_unknown_capability() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.preflight",
        json!({
            "capability_id": "non_existent_capability"
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected result");
    assert_eq!(result["accepted"], false);
    assert!(result["rejection_reason"]
        .as_str()
        .unwrap()
        .contains("Unknown native capability"));
}

#[tokio::test]
async fn test_sandbox_safe_echo() {
    let (dispatcher, _) = setup_dispatcher().await;

    let req = RuntimeRequest::new(
        "sandbox.echo",
        json!({
            "arguments": ["Kairo", "Secure", "Sandbox"]
        }),
    );

    let resp = dispatcher.dispatch(req).await;
    assert_eq!(resp.status, ResponseStatus::Ok);

    let result = resp.result.expect("Expected result");
    assert_eq!(result["state"], "COMPLETED");
    assert_eq!(result["stdout"], "Kairo Secure Sandbox");
    assert_eq!(result["verification_metadata"]["process_exited"], true);
    assert_eq!(result["verification_metadata"]["workspace_cleaned"], true);
}

#[tokio::test]
async fn test_sandbox_output_flood_truncation() {
    let executor = SandboxExecutor::new(
        Arc::new(SandboxCapabilityRegistry::new()),
        Arc::new(CancellationRegistry::new()),
        RuntimeMetrics::new(),
        4,
    );

    let req = ExecutionRequest {
        request_id: "req_flood".to_string(),
        capability_id: "sandbox.probe".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits {
            max_stdout_bytes: 4096, // 4KB limit
            max_stderr_bytes: 4096,
            max_combined_bytes: 8192,
        },
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            output_limits: OutputLimits {
                max_stdout_bytes: 4096,
                max_stderr_bytes: 4096,
                max_combined_bytes: 8192,
            },
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({"mode": "flood"}),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::ResourceExceeded);
    assert_eq!(result.output_metadata.truncated, true);
    assert_eq!(result.output_metadata.output_limit_exceeded, true);
    assert_eq!(result.stdout.len(), 4096);
    assert_eq!(result.verification_metadata.workspace_cleaned, true);
}

#[tokio::test]
async fn test_sandbox_timeout_enforcement() {
    let executor = SandboxExecutor::new(
        Arc::new(SandboxCapabilityRegistry::new()),
        Arc::new(CancellationRegistry::new()),
        RuntimeMetrics::new(),
        4,
    );

    let req = ExecutionRequest {
        request_id: "req_timeout".to_string(),
        capability_id: "sandbox.probe".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget {
            max_execution_time_ms: Some(200), // 200ms timeout
            ..Default::default()
        },
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            resource_budget: ResourceBudget {
                max_execution_time_ms: Some(200),
                ..Default::default()
            },
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({
            "mode": "sleep",
            "duration_ms": 2000 // Requests 2 seconds
        }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::TimedOut);
    assert_eq!(result.timeout_state, true);
    assert_eq!(result.verification_metadata.workspace_cleaned, true);
}

#[tokio::test]
async fn test_sandbox_cancellation_enforcement() {
    let cancellation = Arc::new(CancellationRegistry::new());
    let executor = SandboxExecutor::new(
        Arc::new(SandboxCapabilityRegistry::new()),
        cancellation.clone(),
        RuntimeMetrics::new(),
        4,
    );

    let cancel_id = "sbx_cancel_001".to_string();
    let req = ExecutionRequest {
        request_id: "req_cancel".to_string(),
        capability_id: "sandbox.probe".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget {
            max_execution_time_ms: Some(10000),
            ..Default::default()
        },
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy::default(),
        correlation_id: None,
        cancellation_id: Some(cancel_id.clone()),
        payload: json!({
            "mode": "sleep",
            "duration_ms": 5000
        }),
    };

    let exec_task = tokio::spawn(async move { executor.execute(req).await });

    tokio::time::sleep(std::time::Duration::from_millis(200)).await;
    let cancelled = cancellation.cancel(&cancel_id).await;
    assert!(cancelled);

    let result = exec_task.await.expect("Task failed");
    assert_eq!(result.state, ExecutionState::Cancelled);
    assert_eq!(result.verification_metadata.workspace_cleaned, true);
}

#[tokio::test]
async fn test_sandbox_path_traversal_defense() {
    let ws = IsolatedWorkspace::create("test_traversal").expect("Failed to create workspace");
    let allowed_roots = vec![PathBuf::from("/safe/root")];

    // Attempt traversal outside workspace with ../
    let hostile_path = std::path::Path::new("../../etc/passwd");
    let res = validate_path_safety(hostile_path, &allowed_roots, Some(ws.path()));
    assert!(res.is_err());
    let err = res.err().unwrap();
    assert_eq!(err.code, "PATH_TRAVERSAL_DETECTED");
}

#[tokio::test]
async fn test_sandbox_environment_leak_defense() {
    let executor = SandboxExecutor::new(
        Arc::new(SandboxCapabilityRegistry::new()),
        Arc::new(CancellationRegistry::new()),
        RuntimeMetrics::new(),
        4,
    );

    let req = ExecutionRequest {
        request_id: "req_env".to_string(),
        capability_id: "sandbox.probe".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy::default(),
        correlation_id: None,
        cancellation_id: None,
        payload: json!({"mode": "env_leak"}),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::Completed);
    assert!(result.stdout.contains("0 sensitive keys leaked"));
}

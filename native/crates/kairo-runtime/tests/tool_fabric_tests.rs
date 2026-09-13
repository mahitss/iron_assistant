use kairo_protocol::sandbox::{
    EnvironmentPolicy, ExecutionRequest, ExecutionState, OutputLimits, SandboxPolicy,
    SandboxProfile,
};
use kairo_protocol::ResourceBudget;
use kairo_runtime::cancellation::CancellationRegistry;
use kairo_runtime::metrics::RuntimeMetrics;
use kairo_runtime::sandbox::capabilities::SandboxCapabilityRegistry;
use kairo_runtime::sandbox::executor::SandboxExecutor;
use serde_json::json;
use std::sync::Arc;

fn create_test_executor() -> SandboxExecutor {
    SandboxExecutor::new(
        Arc::new(SandboxCapabilityRegistry::new()),
        Arc::new(CancellationRegistry::new()),
        RuntimeMetrics::new(),
        4,
    )
}

#[tokio::test]
async fn test_native_capabilities_registered() {
    let registry = SandboxCapabilityRegistry::new();
    assert!(registry.get("native.sysinfo").is_some());
    assert!(registry.get("native.file.inspect").is_some());
    assert!(registry.get("sandbox.hash").is_some());
    assert!(registry.get("sandbox.echo").is_some());
}

#[tokio::test]
async fn test_native_sysinfo_execution() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-sysinfo-1".to_string(),
        capability_id: "native.sysinfo".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Minimal,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({}),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.exit_code, Some(0));
    assert_eq!(result.state, ExecutionState::Completed);
    assert!(result.stderr.is_empty());

    let parsed: serde_json::Value =
        serde_json::from_str(&result.stdout).expect("Valid JSON stdout");
    assert!(parsed.get("os").is_some());
    assert!(parsed.get("architecture").is_some());
    assert!(parsed.get("cores").is_some());
    assert_eq!(parsed["runtime_version"], "0.1.0");
    assert_eq!(parsed["is_sandboxed"], true);
}

#[tokio::test]
async fn test_native_file_inspect_execution() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-file-inspect-1".to_string(),
        capability_id: "native.file.inspect".to_string(),
        arguments: vec!["sample.txt".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Standard,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({
            "path": "sample.txt",
            "content": "Line 1\nLine 2\nLine 3\n"
        }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.exit_code, Some(0));
    assert_eq!(result.state, ExecutionState::Completed);

    let parsed: serde_json::Value =
        serde_json::from_str(&result.stdout).expect("Valid JSON stdout");
    assert_eq!(parsed["path"], "sample.txt");
    assert_eq!(parsed["is_file"], true);
    assert_eq!(parsed["is_binary"], false);
    assert_eq!(parsed["line_count"], 4); // 3 newlines gives 4 splits
    assert!(parsed["size_bytes"].as_u64().unwrap() > 0);
    assert_eq!(parsed["sha256"].as_str().unwrap().len(), 64);
}

#[tokio::test]
async fn test_native_file_inspect_path_traversal_rejection() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-file-inspect-traverse".to_string(),
        capability_id: "native.file.inspect".to_string(),
        arguments: vec!["../../etc/passwd".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Standard,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({
            "path": "../../etc/passwd"
        }),
    };

    let result = executor.execute(req).await;
    assert!(result.exit_code.is_none() || result.exit_code == Some(1));
    assert!(result.error.is_some());
    assert_eq!(
        result.failure_classification,
        Some("PATH_TRAVERSAL_DETECTED".to_string())
    );
}

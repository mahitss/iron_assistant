use kairo_protocol::sandbox::{
    EnforcementAction, EnvironmentMode, EnvironmentPolicy, ExecutionRequest, ExecutionResult,
    ExecutionState, FilesystemMode, FilesystemPolicy, MeasurementQuality, NetworkMode,
    NetworkPolicy, OutputLimits, OutputMetadata, PreflightResult, ProcessTreePolicy,
    ResourceUsageTelemetry, ResourceViolation, ResourceViolationType, SandboxPolicy,
    SandboxProfile, VerificationMetadata, ViolationSeverity,
};
use kairo_protocol::ResourceBudget;
use std::path::PathBuf;

#[test]
fn test_sandbox_policy_defaults() {
    let policy = SandboxPolicy::default();
    assert_eq!(policy.profile, SandboxProfile::Standard);
    assert_eq!(policy.filesystem.mode, FilesystemMode::ReadOnly);
    assert_eq!(policy.network.mode, NetworkMode::NoNetwork);
    assert_eq!(policy.environment.mode, EnvironmentMode::Allowlist);
    assert!(!policy.process_tree.allow_child_processes);
    assert!(policy.process_tree.kill_on_parent_exit);
    assert_eq!(policy.output_limits.max_stdout_bytes, 1024 * 1024);
}

#[test]
fn test_sandbox_policy_intersection_most_restrictive() {
    let permissive = SandboxPolicy {
        profile: SandboxProfile::Minimal,
        filesystem: FilesystemPolicy {
            mode: FilesystemMode::ReadWrite,
            allowed_read_roots: vec![PathBuf::from("/a"), PathBuf::from("/b")],
            allowed_write_roots: vec![PathBuf::from("/b")],
            isolated_workspace: true,
        },
        network: NetworkPolicy {
            mode: NetworkMode::Allowlist,
            allowed_hosts: vec!["api.example.com".to_string(), "kairo.internal".to_string()],
        },
        environment: EnvironmentPolicy {
            mode: EnvironmentMode::InheritSafe,
            allowed_variables: vec!["PATH".to_string(), "CUSTOM".to_string()],
            explicit_variables: Default::default(),
        },
        process_tree: ProcessTreePolicy {
            allow_child_processes: true,
            max_children: 10,
            kill_on_parent_exit: true,
        },
        output_limits: OutputLimits {
            max_stdout_bytes: 10 * 1024 * 1024,
            max_stderr_bytes: 10 * 1024 * 1024,
            max_combined_bytes: 20 * 1024 * 1024,
        },
        resource_budget: ResourceBudget {
            max_cpu_percent: Some(90.0),
            max_memory_bytes: Some(1024 * 1024 * 1024),
            max_execution_time_ms: Some(60_000),
            max_concurrency: Some(4),
            max_output_bytes: Some(10 * 1024 * 1024),
            max_disk_bytes: Some(1024 * 1024 * 1024),
            max_file_count: Some(5000),
        },
    };

    let restrictive = SandboxPolicy {
        profile: SandboxProfile::Strict,
        filesystem: FilesystemPolicy {
            mode: FilesystemMode::ReadOnly,
            allowed_read_roots: vec![PathBuf::from("/b"), PathBuf::from("/c")],
            allowed_write_roots: vec![],
            isolated_workspace: true,
        },
        network: NetworkPolicy {
            mode: NetworkMode::NoNetwork,
            allowed_hosts: vec![],
        },
        environment: EnvironmentPolicy {
            mode: EnvironmentMode::Empty,
            allowed_variables: vec!["PATH".to_string()],
            explicit_variables: Default::default(),
        },
        process_tree: ProcessTreePolicy {
            allow_child_processes: false,
            max_children: 0,
            kill_on_parent_exit: true,
        },
        output_limits: OutputLimits {
            max_stdout_bytes: 512 * 1024,
            max_stderr_bytes: 512 * 1024,
            max_combined_bytes: 1024 * 1024,
        },
        resource_budget: ResourceBudget {
            max_cpu_percent: Some(50.0),
            max_memory_bytes: Some(256 * 1024 * 1024),
            max_execution_time_ms: Some(15_000),
            max_concurrency: Some(1),
            max_output_bytes: Some(512 * 1024),
            max_disk_bytes: Some(100 * 1024 * 1024),
            max_file_count: Some(500),
        },
    };

    let effective = permissive.intersect(&restrictive);

    // Profile must be Strict
    assert_eq!(effective.profile, SandboxProfile::Strict);
    // Filesystem must be ReadOnly and intersection of roots is /b
    assert_eq!(effective.filesystem.mode, FilesystemMode::ReadOnly);
    assert_eq!(
        effective.filesystem.allowed_read_roots,
        vec![PathBuf::from("/b")]
    );
    assert!(effective.filesystem.allowed_write_roots.is_empty());
    // Network must be NoNetwork
    assert_eq!(effective.network.mode, NetworkMode::NoNetwork);
    assert!(effective.network.allowed_hosts.is_empty());
    // Environment must be Empty
    assert_eq!(effective.environment.mode, EnvironmentMode::Empty);
    // Process tree must prohibit children
    assert!(!effective.process_tree.allow_child_processes);
    assert_eq!(effective.process_tree.max_children, 0);
    // Limits and budget must take the stricter minimums
    assert_eq!(effective.output_limits.max_stdout_bytes, 512 * 1024);
    assert_eq!(effective.resource_budget.max_cpu_percent, Some(50.0));
    assert_eq!(
        effective.resource_budget.max_memory_bytes,
        Some(256 * 1024 * 1024)
    );
    assert_eq!(
        effective.resource_budget.max_execution_time_ms,
        Some(15_000)
    );
    assert_eq!(effective.resource_budget.max_concurrency, Some(1));
    assert_eq!(
        effective.resource_budget.max_disk_bytes,
        Some(100 * 1024 * 1024)
    );
    assert_eq!(effective.resource_budget.max_file_count, Some(500));
}

#[test]
fn test_execution_request_and_result_roundtrip() {
    let req = ExecutionRequest {
        request_id: "req-sbx-001".to_string(),
        capability_id: "sandbox.echo".to_string(),
        arguments: vec!["hello".to_string(), "world".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy::default(),
        correlation_id: Some("corr-123".to_string()),
        cancellation_id: Some("cancel-456".to_string()),
        payload: serde_json::json!({"test": true}),
    };

    let json_str = serde_json::to_string(&req).expect("Failed to serialize ExecutionRequest");
    let deserialized: ExecutionRequest =
        serde_json::from_str(&json_str).expect("Failed to deserialize ExecutionRequest");
    assert_eq!(req, deserialized);

    let res = ExecutionResult {
        request_id: "req-sbx-001".to_string(),
        execution_id: "exec-999".to_string(),
        capability_id: "sandbox.echo".to_string(),
        state: ExecutionState::Completed,
        exit_code: Some(0),
        stdout: "hello world\n".to_string(),
        stderr: String::new(),
        output_metadata: OutputMetadata {
            stdout_bytes: 12,
            stderr_bytes: 0,
            truncated: false,
            output_limit_exceeded: false,
        },
        duration_ms: 45,
        resource_usage: Some(ResourceBudget::default()),
        resource_telemetry: None,
        resource_violation: None,
        cancellation_state: None,
        timeout_state: false,
        failure_classification: None,
        verification_metadata: VerificationMetadata {
            process_exited: true,
            descendants_cleaned: true,
            workspace_cleaned: true,
            resources_released: true,
        },
        error: None,
        timestamp: chrono::Utc::now(),
    };

    let res_json = serde_json::to_string(&res).expect("Failed to serialize ExecutionResult");
    let res_deserialized: ExecutionResult =
        serde_json::from_str(&res_json).expect("Failed to deserialize ExecutionResult");
    assert_eq!(res.execution_id, res_deserialized.execution_id);
    assert_eq!(res.state, res_deserialized.state);
}

#[test]
fn test_preflight_result_serialization() {
    let preflight = PreflightResult {
        accepted: true,
        capability_id: "sandbox.echo".to_string(),
        effective_policy: SandboxPolicy::default(),
        effective_budget: ResourceBudget::default(),
        rejection_reason: None,
        platform_support: Default::default(),
    };

    let json_val = serde_json::to_value(&preflight).expect("Failed to serialize PreflightResult");
    assert_eq!(json_val["accepted"], true);
    assert_eq!(json_val["capability_id"], "sandbox.echo");
}

#[test]
fn test_resource_telemetry_and_violation_serialization() {
    let telemetry = ResourceUsageTelemetry {
        wall_time_ms: 120,
        cpu_time_ms: Some(85),
        peak_memory_bytes: Some(340 * 1024 * 1024),
        current_memory_bytes: Some(250 * 1024 * 1024),
        process_count: 2,
        output_bytes: 4096,
        workspace_bytes: 1024 * 1024,
        file_count: 5,
        measurement_quality: MeasurementQuality::Exact,
    };

    let violation = ResourceViolation {
        violation_type: ResourceViolationType::MemoryLimitExceeded,
        severity: ViolationSeverity::HardLimit,
        limit_value: 256 * 1024 * 1024,
        actual_value: 340 * 1024 * 1024,
        unit: "bytes".to_string(),
        message: "Peak memory exceeded hard limit".to_string(),
        enforcement_action: EnforcementAction::Terminate,
    };

    let val = serde_json::to_value(&telemetry).expect("serialize telemetry");
    assert_eq!(val["peak_memory_bytes"], 340 * 1024 * 1024);
    assert_eq!(val["measurement_quality"], "EXACT");

    let v_val = serde_json::to_value(&violation).expect("serialize violation");
    assert_eq!(v_val["violation_type"], "MEMORY_LIMIT_EXCEEDED");
    assert_eq!(v_val["severity"], "HARD_LIMIT");
    assert_eq!(v_val["enforcement_action"], "TERMINATE");
}

use kairo_protocol::computer::{DisplayMetadata, ProcessMetadata, TargetContext, WindowMetadata};
use kairo_protocol::sandbox::{
    EnvironmentPolicy, ExecutionRequest, ExecutionState, OutputLimits, SandboxPolicy,
    SandboxProfile,
};
use kairo_protocol::ResourceBudget;
use kairo_runtime::cancellation::CancellationRegistry;
use kairo_runtime::metrics::RuntimeMetrics;
use kairo_runtime::sandbox::capabilities::SandboxCapabilityRegistry;
use kairo_runtime::sandbox::computer::InputStateTracker;
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
async fn test_native_computer_capabilities_registered() {
    let registry = SandboxCapabilityRegistry::new();
    assert!(registry.get("native.window.inspect").is_some());
    assert!(registry.get("native.process.inspect").is_some());
    assert!(registry.get("native.display.inspect").is_some());
    assert!(registry.get("native.screen.capture").is_some());
    assert!(registry.get("native.clipboard.read").is_some());
    assert!(registry.get("native.clipboard.write").is_some());
    assert!(registry.get("native.input.mouse").is_some());
    assert!(registry.get("native.input.keyboard").is_some());
}

#[tokio::test]
async fn test_native_window_inspect() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-win-1".to_string(),
        capability_id: "native.window.inspect".to_string(),
        arguments: vec![],
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
        payload: json!({ "limit": 20 }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.exit_code, Some(0));
    assert_eq!(result.state, ExecutionState::Completed);

    let parsed: serde_json::Value = serde_json::from_str(&result.stdout).expect("Valid JSON");
    let windows: Vec<WindowMetadata> =
        serde_json::from_value(parsed["windows"].clone()).expect("Valid WindowMetadata JSON");
    assert_eq!(parsed["count"].as_u64().unwrap() as usize, windows.len());
    assert!(
        !windows.is_empty(),
        "Expected at least one window metadata item"
    );
}

#[tokio::test]
async fn test_native_process_inspect() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-proc-1".to_string(),
        capability_id: "native.process.inspect".to_string(),
        arguments: vec![],
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
        payload: json!({ "limit": 1000 }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.exit_code, Some(0));
    assert_eq!(result.state, ExecutionState::Completed);

    let parsed: serde_json::Value = serde_json::from_str(&result.stdout).expect("Valid JSON");
    let procs: Vec<ProcessMetadata> =
        serde_json::from_value(parsed["processes"].clone()).expect("Valid ProcessMetadata JSON");
    assert_eq!(parsed["count"].as_u64().unwrap() as usize, procs.len());
    assert!(
        !procs.is_empty(),
        "Expected at least one process metadata item"
    );
    assert!(procs.iter().any(|p| !p.name.is_empty()));
    let current_pid = std::process::id();
    assert!(
        procs.iter().any(|p| p.pid == current_pid),
        "Expected current PID {} in process list of {} items",
        current_pid,
        procs.len()
    );
}

#[tokio::test]
async fn test_native_display_inspect() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-disp-1".to_string(),
        capability_id: "native.display.inspect".to_string(),
        arguments: vec![],
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
        payload: json!({}),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.exit_code, Some(0));
    assert_eq!(result.state, ExecutionState::Completed);

    let parsed: serde_json::Value = serde_json::from_str(&result.stdout).expect("Valid JSON");
    let displays: Vec<DisplayMetadata> =
        serde_json::from_value(parsed["displays"].clone()).expect("Valid DisplayMetadata JSON");
    assert_eq!(parsed["count"].as_u64().unwrap() as usize, displays.len());
    assert!(
        !displays.is_empty(),
        "Expected at least one display monitor"
    );
    assert!(displays[0].width > 0);
    assert!(displays[0].height > 0);
}

#[tokio::test]
async fn test_native_screen_capture_bounded() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-cap-1".to_string(),
        capability_id: "native.screen.capture".to_string(),
        arguments: vec![],
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
        payload: json!({ "max_width": 1280, "max_height": 720 }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.exit_code, Some(0));
    assert_eq!(result.state, ExecutionState::Completed);

    let parsed: serde_json::Value =
        serde_json::from_str(&result.stdout).expect("Valid screen capture JSON");
    assert_eq!(parsed["status"], "CAPTURED");
    assert_eq!(parsed["privacy_screened"], true);
    assert!(parsed["bounded_width"].as_u64().unwrap() <= 1280);
    assert!(parsed["bounded_height"].as_u64().unwrap() <= 720);
}

#[tokio::test]
async fn test_native_clipboard_read_write() {
    let executor = create_test_executor();
    let test_msg = format!("kairo_test_token_{}", uuid::Uuid::new_v4());

    // 1. Write to clipboard
    let write_req = ExecutionRequest {
        request_id: "req-clip-w".to_string(),
        capability_id: "native.clipboard.write".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy::default(),
        correlation_id: None,
        cancellation_id: None,
        payload: json!({ "text": test_msg }),
    };
    let w_res = executor.execute(write_req).await;
    assert_eq!(w_res.exit_code, Some(0));

    // 2. Read from clipboard
    let read_req = ExecutionRequest {
        request_id: "req-clip-r".to_string(),
        capability_id: "native.clipboard.read".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy::default(),
        correlation_id: None,
        cancellation_id: None,
        payload: json!({}),
    };
    let r_res = executor.execute(read_req).await;
    assert_eq!(r_res.exit_code, Some(0));
    let parsed: serde_json::Value =
        serde_json::from_str(&r_res.stdout).expect("Valid clipboard JSON");
    assert_eq!(parsed["text"], test_msg);
}

#[tokio::test]
async fn test_input_state_tracker_and_emergency_release() {
    let tracker = InputStateTracker::new();
    tracker.record_key_down("ctrl");
    tracker.record_key_down("shift");
    tracker.record_button_down("left");
    tracker.set_active_operation(Some("mouse.drag".to_string()));

    let state = tracker.get_state();
    assert_eq!(state.pressed_keys.len(), 2);
    assert_eq!(state.pressed_buttons.len(), 1);
    assert_eq!(state.active_operation, Some("mouse.drag".to_string()));

    // Emergency reset must clear all active buttons and keys
    let (released_keys, released_buttons) = tracker.emergency_reset_input();
    assert_eq!(released_keys, 2);
    assert_eq!(released_buttons, 1);

    let clean_state = tracker.get_state();
    assert!(clean_state.pressed_keys.is_empty());
    assert!(clean_state.pressed_buttons.is_empty());
    assert_eq!(clean_state.active_operation, None);
}

#[tokio::test]
async fn test_native_target_mismatch_aborts_safely() {
    let executor = create_test_executor();
    // Intentionally target a non-existent window title
    let mismatch_target = TargetContext {
        window_id: Some(999999999),
        expected_title: Some("NonExistentImpossibleWindow_XYZ99999".to_string()),
        expected_process_name: Some("nonexistent_process.exe".to_string()),
        ..Default::default()
    };

    let req = ExecutionRequest {
        request_id: "req-target-mismatch".to_string(),
        capability_id: "native.input.mouse".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy::default(),
        correlation_id: None,
        cancellation_id: None,
        payload: json!({
            "action": "move",
            "x": 100,
            "y": 100,
            "target_context": mismatch_target,
        }),
    };

    let result = executor.execute(req).await;
    // Must be rejected or fail with ABORT_TARGET_CHANGED
    assert_ne!(result.exit_code, Some(0));
    assert!(
        result.stderr.contains("ABORT_TARGET_CHANGED")
            || result.failure_classification.as_deref() == Some("ABORT_TARGET_CHANGED"),
        "Expected ABORT_TARGET_CHANGED, got: {:?}",
        result.failure_classification
    );
}

#[tokio::test]
async fn test_native_coordinate_bounds_enforced() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-coord-bounds".to_string(),
        capability_id: "native.input.mouse".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy::default(),
        correlation_id: None,
        cancellation_id: None,
        payload: json!({
            "action": "move",
            "x": -9999,
            "y": -9999,
        }),
    };

    let result = executor.execute(req).await;
    assert_ne!(result.exit_code, Some(0));
    assert!(
        result.stderr.contains("COORDINATES_OUT_OF_BOUNDS")
            || result.failure_classification.as_deref() == Some("COORDINATES_OUT_OF_BOUNDS"),
        "Expected COORDINATES_OUT_OF_BOUNDS, got: {:?}",
        result.failure_classification
    );
}

#[tokio::test]
async fn test_emergency_stop_rejects_consequential_input() {
    let executor = create_test_executor();
    // Activate Emergency Stop on substrate
    executor.computer().tracker().set_emergency_stop(true);

    let req = ExecutionRequest {
        request_id: "req-estop".to_string(),
        capability_id: "native.input.mouse".to_string(),
        arguments: vec![],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy::default(),
        correlation_id: None,
        cancellation_id: None,
        payload: json!({
            "action": "click",
            "x": 200,
            "y": 200,
            "button": "left"
        }),
    };

    let result = executor.execute(req).await;
    assert_ne!(result.exit_code, Some(0));
    assert!(
        result.stderr.contains("EMERGENCY_STOP_ACTIVE")
            || result.failure_classification.as_deref() == Some("EMERGENCY_STOP_ACTIVE")
    );

    // Reset emergency stop
    executor.computer().tracker().set_emergency_stop(false);
}

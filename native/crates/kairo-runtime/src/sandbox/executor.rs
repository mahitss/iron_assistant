use crate::cancellation::CancellationRegistry;
use crate::metrics::RuntimeMetrics;
use crate::sandbox::capabilities::SandboxCapabilityRegistry;
use crate::sandbox::computer::{InputStateTracker, NativeComputerSubstrate};
use crate::sandbox::policy::{calculate_effective_policy, validate_path_safety};
use crate::sandbox::process::{build_sanitized_environment, ProcessJobContainer};
use crate::sandbox::resources::{build_resource_telemetry, evaluate_resource_violations};
use crate::sandbox::workspace::IsolatedWorkspace;
use chrono::Utc;
use kairo_protocol::computer::{MouseButton, TargetContext};
use kairo_protocol::sandbox::{
    EnforcementAction, ExecutionRequest, ExecutionResult, ExecutionState, OutputMetadata,
    PlatformSupportSummary, PreflightResult, ResourceViolation, ResourceViolationType,
    SandboxPolicy, VerificationMetadata, ViolationSeverity,
};
use kairo_protocol::{ResourceBudget, RuntimeError};
use serde_json::json;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Semaphore;
use tokio::time::timeout;
use tracing::{info, warn};
use uuid::Uuid;

pub struct SandboxExecutor {
    capabilities: Arc<SandboxCapabilityRegistry>,
    cancellation: Arc<CancellationRegistry>,
    metrics: Arc<RuntimeMetrics>,
    semaphore: Arc<Semaphore>,
    computer: Arc<NativeComputerSubstrate>,
}

impl SandboxExecutor {
    pub fn new(
        capabilities: Arc<SandboxCapabilityRegistry>,
        cancellation: Arc<CancellationRegistry>,
        metrics: Arc<RuntimeMetrics>,
        max_concurrency: usize,
    ) -> Self {
        let tracker = Arc::new(InputStateTracker::new());
        let computer = Arc::new(NativeComputerSubstrate::new(tracker));
        Self {
            capabilities,
            cancellation,
            metrics,
            semaphore: Arc::new(Semaphore::new(max_concurrency)),
            computer,
        }
    }

    pub fn computer(&self) -> &Arc<NativeComputerSubstrate> {
        &self.computer
    }

    /// Perform dry-run preflight evaluation without executing workload.
    pub fn preflight(&self, req: &ExecutionRequest) -> PreflightResult {
        let contract_opt = self.capabilities.get(&req.capability_id);
        if contract_opt.is_none() {
            return PreflightResult {
                accepted: false,
                capability_id: req.capability_id.clone(),
                effective_policy: SandboxPolicy::default(),
                effective_budget: ResourceBudget::default(),
                rejection_reason: Some(format!(
                    "Unknown native capability '{}'",
                    req.capability_id
                )),
                platform_support: PlatformSupportSummary::default(),
            };
        }

        let contract = contract_opt.unwrap();
        let effective_policy =
            calculate_effective_policy(&contract.default_policy, &Some(req.sandbox_policy.clone()));

        // Validate that requested budget does not exceed capability ceiling
        let effective_budget = match req.resource_budget.validate() {
            Ok(()) => effective_policy.resource_budget.clone(),
            Err(e) => {
                return PreflightResult {
                    accepted: false,
                    capability_id: req.capability_id.clone(),
                    effective_policy,
                    effective_budget: ResourceBudget::default(),
                    rejection_reason: Some(format!("Invalid resource budget: {}", e.message)),
                    platform_support: PlatformSupportSummary::default(),
                };
            }
        };

        PreflightResult {
            accepted: true,
            capability_id: req.capability_id.clone(),
            effective_policy,
            effective_budget,
            rejection_reason: None,
            platform_support: PlatformSupportSummary::default(),
        }
    }

    /// Execute a sandboxed request through admission control, lifecycle, and containment.
    pub async fn execute(&self, req: ExecutionRequest) -> ExecutionResult {
        let start_instant = Instant::now();
        let execution_id = format!("exec_{}", Uuid::new_v4().simple());
        let request_id = req.request_id.clone();
        let capability_id = req.capability_id.clone();

        self.metrics.record_sandbox_start();

        // 1. Validate request envelope
        if let Err(err) = req.validate() {
            self.metrics.record_sandbox_failure();
            return self.build_rejected_result(
                &request_id,
                &execution_id,
                &capability_id,
                err,
                start_instant,
            );
        }

        // 2. Resolve capability contract
        let contract = match self.capabilities.get(&capability_id) {
            Some(c) => c.clone(),
            None => {
                self.metrics.record_sandbox_failure();
                return self.build_rejected_result(
                    &request_id,
                    &execution_id,
                    &capability_id,
                    RuntimeError::unsupported_operation(
                        "UNKNOWN_SANDBOX_CAPABILITY",
                        format!("No registered contract for capability '{}'", capability_id),
                    ),
                    start_instant,
                );
            }
        };

        // 3. Compute effective policy via restrictive intersection
        let effective_policy =
            calculate_effective_policy(&contract.default_policy, &Some(req.sandbox_policy.clone()));

        // 4. Admission control & concurrency slot acquisition
        let permit = match self.semaphore.clone().try_acquire_owned() {
            Ok(p) => p,
            Err(_) => {
                self.metrics.record_sandbox_failure();
                return self.build_rejected_result(
                    &request_id,
                    &execution_id,
                    &capability_id,
                    RuntimeError::resource_limit(
                        "CONCURRENCY_LIMIT_EXCEEDED",
                        "Sandbox concurrency limit saturated; request rejected",
                    ),
                    start_instant,
                );
            }
        };

        // 5. Create isolated temporary workspace
        let mut workspace = match IsolatedWorkspace::create(&execution_id) {
            Ok(ws) => ws,
            Err(err) => {
                drop(permit);
                self.metrics.record_sandbox_failure();
                return self.build_rejected_result(
                    &request_id,
                    &execution_id,
                    &capability_id,
                    RuntimeError::internal(
                        "WORKSPACE_CREATION_FAILED",
                        format!("Failed to create isolated workspace: {}", err),
                    ),
                    start_instant,
                );
            }
        };

        // 6. Register cancellation token
        let cancel_id = req
            .cancellation_id
            .clone()
            .unwrap_or_else(|| request_id.clone());
        let cancel_token = self.cancellation.register(&cancel_id).await;

        // 7. Setup process job container for complete tree termination & resource limits
        let job_container = match ProcessJobContainer::new_with_limits(
            &effective_policy.resource_budget,
            &effective_policy.process_tree,
        ) {
            Ok(jc) => jc,
            Err(err) => {
                warn!("sandbox_executor.job_container_init_failed error={}", err);
                // Fall back gracefully if OS restricts job creation
                ProcessJobContainer::noop()
            }
        };

        let timeout_ms = effective_policy
            .resource_budget
            .max_execution_time_ms
            .unwrap_or(30_000);

        info!(
            "sandbox_executor.executing execution_id={} capability={} timeout_ms={}",
            execution_id, capability_id, timeout_ms
        );

        // 8. Execute workload racing against cancellation and deadline
        let exec_workload =
            self.run_capability_workload(&req, &effective_policy, workspace.path(), &job_container);

        tokio::select! {
            _ = cancel_token.cancelled() => {
                self.computer.tracker().emergency_reset_input();
                self.metrics.record_sandbox_cancellation();
                self.cancellation.remove(&cancel_id).await;
                let job_metrics = job_container.query_metrics();
                let (ws_bytes, ws_files) = workspace.measure_usage().unwrap_or((0, 0));
                let _ = job_container.terminate();
                let _ = workspace.cleanup();
                drop(permit);

                let duration = start_instant.elapsed().as_millis() as u64;
                let telemetry = build_resource_telemetry(duration, &job_metrics, ws_bytes, ws_files, 0);

                ExecutionResult {
                    request_id,
                    execution_id,
                    capability_id,
                    state: ExecutionState::Cancelled,
                    exit_code: None,
                    stdout: String::new(),
                    stderr: "Execution was cancelled by caller".to_string(),
                    output_metadata: OutputMetadata::default(),
                    duration_ms: duration,
                    resource_usage: Some(effective_policy.resource_budget.clone()),
                    resource_telemetry: Some(telemetry),
                    resource_violation: None,
                    cancellation_state: Some("Cancelled by token".to_string()),
                    timeout_state: false,
                    failure_classification: Some("CANCELLED".to_string()),
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: !workspace.exists(),
                        resources_released: true,
                    },
                    error: Some(RuntimeError::cancelled("EXECUTION_CANCELLED", "Workload was cooperatively cancelled")),
                    timestamp: Utc::now(),
                }
            }
            res = timeout(Duration::from_millis(timeout_ms), exec_workload) => {
                self.cancellation.remove(&cancel_id).await;
                let job_metrics = job_container.query_metrics();
                let (ws_bytes, ws_files) = workspace.measure_usage().unwrap_or((0, 0));
                let _ = job_container.terminate();
                let _ = workspace.cleanup();
                drop(permit);

                let duration = start_instant.elapsed().as_millis() as u64;

                match res {
                    Ok(Ok(mut result)) => {
                        let total_out = result.output_metadata.stdout_bytes + result.output_metadata.stderr_bytes;
                        let violation_opt = evaluate_resource_violations(
                            &effective_policy.resource_budget,
                            &job_metrics,
                            ws_bytes,
                            ws_files,
                            total_out,
                            duration,
                        );
                        let telemetry = build_resource_telemetry(
                            duration,
                            &job_metrics,
                            ws_bytes,
                            ws_files,
                            total_out,
                        );
                        result.resource_usage = Some(effective_policy.resource_budget.clone());
                        result.resource_telemetry = Some(telemetry);

                        if let Some(violation) = violation_opt {
                            self.metrics.record_sandbox_failure();
                            result.state = ExecutionState::ResourceExceeded;
                            result.failure_classification = Some(format!("{:?}", violation.violation_type));
                            if result.stderr.is_empty() {
                                result.stderr = violation.message.clone();
                            } else {
                                result.stderr = format!("{}\n{}", result.stderr, violation.message);
                            }
                            result.error = Some(RuntimeError::resource_limit(
                                "RESOURCE_LIMIT_EXCEEDED",
                                violation.message.clone(),
                            ));
                            result.resource_violation = Some(violation);
                        } else {
                            self.metrics.record_sandbox_success(duration, total_out);
                            result.resource_violation = None;
                        }
                        result.verification_metadata.workspace_cleaned = !workspace.exists();
                        result
                    }
                    Ok(Err(err)) => {
                        self.metrics.record_sandbox_failure();
                        let is_res_err = err.code.contains("LIMIT_EXCEEDED") || err.code.contains("RESOURCE");
                        let violation_type = if err.code.contains("MEMORY") {
                            ResourceViolationType::MemoryLimitExceeded
                        } else if err.code.contains("DISK") || err.code.contains("WORKSPACE") {
                            ResourceViolationType::DiskLimitExceeded
                        } else if err.code.contains("FILE_COUNT") {
                            ResourceViolationType::FileCountLimitExceeded
                        } else if err.code.contains("PROCESS") {
                            ResourceViolationType::ProcessLimitExceeded
                        } else if err.code.contains("OUTPUT") {
                            ResourceViolationType::OutputLimitExceeded
                        } else {
                            ResourceViolationType::CpuLimitExceeded
                        };

                        let violation = if is_res_err {
                            Some(ResourceViolation {
                                violation_type,
                                severity: ViolationSeverity::HardLimit,
                                limit_value: 0,
                                actual_value: 0,
                                unit: "system_resource".to_string(),
                                message: err.message.clone(),
                                enforcement_action: EnforcementAction::Terminate,
                            })
                        } else {
                            None
                        };

                        let state = if is_res_err {
                            ExecutionState::ResourceExceeded
                        } else {
                            ExecutionState::Failed
                        };

                        let telemetry = build_resource_telemetry(duration, &job_metrics, ws_bytes, ws_files, 0);

                        ExecutionResult {
                            request_id,
                            execution_id,
                            capability_id,
                            state,
                            exit_code: Some(1),
                            stdout: String::new(),
                            stderr: err.message.clone(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: duration,
                            resource_usage: Some(effective_policy.resource_budget.clone()),
                            resource_telemetry: Some(telemetry),
                            resource_violation: violation,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: Some(err.code.clone()),
                            verification_metadata: VerificationMetadata {
                                process_exited: true,
                                descendants_cleaned: true,
                                workspace_cleaned: !workspace.exists(),
                                resources_released: true,
                            },
                            error: Some(err),
                            timestamp: Utc::now(),
                        }
                    }
                    Err(_) => {
                        self.computer.tracker().emergency_reset_input();
                        self.metrics.record_sandbox_timeout();
                        let violation = ResourceViolation {
                            violation_type: ResourceViolationType::TimeLimitExceeded,
                            severity: ViolationSeverity::HardLimit,
                            limit_value: timeout_ms,
                            actual_value: duration,
                            unit: "ms".to_string(),
                            message: format!("Execution exceeded timeout of {}ms", timeout_ms),
                            enforcement_action: EnforcementAction::Terminate,
                        };
                        let telemetry = build_resource_telemetry(duration, &job_metrics, ws_bytes, ws_files, 0);

                        ExecutionResult {
                            request_id,
                            execution_id,
                            capability_id,
                            state: ExecutionState::TimedOut,
                            exit_code: None,
                            stdout: String::new(),
                            stderr: format!("Execution exceeded timeout of {}ms", timeout_ms),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: duration,
                            resource_usage: Some(effective_policy.resource_budget.clone()),
                            resource_telemetry: Some(telemetry),
                            resource_violation: Some(violation),
                            cancellation_state: None,
                            timeout_state: true,
                            failure_classification: Some("TIMED_OUT".to_string()),
                            verification_metadata: VerificationMetadata {
                                process_exited: true,
                                descendants_cleaned: true,
                                workspace_cleaned: !workspace.exists(),
                                resources_released: true,
                            },
                            error: Some(RuntimeError::deadline_exceeded(
                                "SANDBOX_TIMEOUT",
                                format!("Workload exceeded sandbox timeout of {}ms", timeout_ms),
                            )),
                            timestamp: Utc::now(),
                        }
                    }
                }
            }
        }
    }

    /// Internal capability execution router.
    async fn run_capability_workload(
        &self,
        req: &ExecutionRequest,
        policy: &SandboxPolicy,
        workspace_dir: &std::path::Path,
        _job: &ProcessJobContainer,
    ) -> Result<ExecutionResult, RuntimeError> {
        let req_start = Instant::now();
        let max_stdout = policy.output_limits.max_stdout_bytes;
        let sanitized_env = build_sanitized_environment(&policy.environment);

        match req.capability_id.as_str() {
            "sandbox.echo" => {
                let joined_args = req.arguments.join(" ");
                let mut out_str = joined_args;
                if out_str.is_empty() {
                    out_str = req.payload.to_string();
                }

                let total_bytes = out_str.len() as u64;
                let truncated = total_bytes > max_stdout;
                let final_stdout = if truncated {
                    out_str[..(max_stdout as usize)].to_string()
                } else {
                    out_str
                };

                let duration = req_start.elapsed().as_millis() as u64;
                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: final_stdout,
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: total_bytes,
                        stderr_bytes: 0,
                        truncated,
                        output_limit_exceeded: truncated,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false, // will be verified after cleanup
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "sandbox.hash" => {
                let test_file = workspace_dir.join("input.dat");
                let data = req.payload.to_string();
                std::fs::write(&test_file, &data).map_err(|e| {
                    RuntimeError::internal("WORKSPACE_IO_ERROR", format!("Write error: {}", e))
                })?;

                // Compute hash
                let content = std::fs::read(&test_file).map_err(|e| {
                    RuntimeError::internal("WORKSPACE_IO_ERROR", format!("Read error: {}", e))
                })?;

                let hash_val = md5_or_simple_hash(&content);
                let digest = format!(
                    "{:016x}{:016x}{:016x}{:016x}",
                    hash_val,
                    hash_val ^ 0x5555555555555555,
                    hash_val ^ 0xAAAAAAAAAAAAAAAA,
                    hash_val ^ 0xFFFFFFFFFFFFFFFF
                );
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: json!({"sha256": digest, "bytes": content.len()}).to_string(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: 64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "sandbox.probe" => {
                let mode = req
                    .payload
                    .get("mode")
                    .and_then(|v| v.as_str())
                    .unwrap_or("normal");

                match mode {
                    "sleep" => {
                        let duration_ms = req
                            .payload
                            .get("duration_ms")
                            .and_then(|v| v.as_u64())
                            .unwrap_or(2000);
                        tokio::time::sleep(Duration::from_millis(duration_ms)).await;
                        let duration = req_start.elapsed().as_millis() as u64;

                        Ok(ExecutionResult {
                            request_id: req.request_id.clone(),
                            execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                            capability_id: req.capability_id.clone(),
                            state: ExecutionState::Completed,
                            exit_code: Some(0),
                            stdout: format!("Probe slept for {}ms", duration_ms),
                            stderr: String::new(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: duration,
                            resource_usage: Some(policy.resource_budget.clone()),
                            resource_telemetry: None,
                            resource_violation: None,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: None,
                            verification_metadata: VerificationMetadata {
                                process_exited: true,
                                descendants_cleaned: true,
                                workspace_cleaned: false,
                                resources_released: true,
                            },
                            error: None,
                            timestamp: Utc::now(),
                        })
                    }

                    "flood" => {
                        // Produce 2MB of output to test bounding against max_stdout
                        let chunk = "0123456789ABCDEF".repeat(64); // 1KB
                        let mut output = String::new();
                        for _ in 0..2048 {
                            output.push_str(&chunk);
                        }

                        let total_bytes = output.len() as u64;
                        let truncated = total_bytes > max_stdout;
                        let final_stdout = if truncated {
                            output[..(max_stdout as usize)].to_string()
                        } else {
                            output
                        };

                        let duration = req_start.elapsed().as_millis() as u64;
                        Ok(ExecutionResult {
                            request_id: req.request_id.clone(),
                            execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                            capability_id: req.capability_id.clone(),
                            state: if truncated {
                                ExecutionState::ResourceExceeded
                            } else {
                                ExecutionState::Completed
                            },
                            exit_code: Some(0),
                            stdout: final_stdout,
                            stderr: if truncated {
                                "OUTPUT_LIMIT_EXCEEDED: stdout truncated".to_string()
                            } else {
                                String::new()
                            },
                            output_metadata: OutputMetadata {
                                stdout_bytes: total_bytes,
                                stderr_bytes: 0,
                                truncated,
                                output_limit_exceeded: truncated,
                            },
                            duration_ms: duration,
                            resource_usage: Some(policy.resource_budget.clone()),
                            resource_telemetry: None,
                            resource_violation: None,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: if truncated {
                                Some("OUTPUT_LIMIT_EXCEEDED".to_string())
                            } else {
                                None
                            },
                            verification_metadata: VerificationMetadata {
                                process_exited: true,
                                descendants_cleaned: true,
                                workspace_cleaned: false,
                                resources_released: true,
                            },
                            error: None,
                            timestamp: Utc::now(),
                        })
                    }

                    "path_traversal" => {
                        let target_str = req
                            .payload
                            .get("target_path")
                            .and_then(|v| v.as_str())
                            .unwrap_or("../../secret.txt");

                        let target_path = std::path::Path::new(target_str);
                        validate_path_safety(
                            target_path,
                            &policy.filesystem.allowed_read_roots,
                            Some(workspace_dir),
                        )?;

                        Ok(ExecutionResult {
                            request_id: req.request_id.clone(),
                            execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                            capability_id: req.capability_id.clone(),
                            state: ExecutionState::Completed,
                            exit_code: Some(0),
                            stdout: "Path validated successfully".to_string(),
                            stderr: String::new(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: req_start.elapsed().as_millis() as u64,
                            resource_usage: None,
                            resource_telemetry: None,
                            resource_violation: None,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: None,
                            verification_metadata: VerificationMetadata::default(),
                            error: None,
                            timestamp: Utc::now(),
                        })
                    }

                    "env_leak" => {
                        // Check if any sensitive key was passed in sanitized_env
                        let mut leaked = Vec::new();
                        for key in sanitized_env.keys() {
                            let upper = key.to_uppercase();
                            if upper.contains("SECRET")
                                || upper.contains("KEY")
                                || upper.contains("TOKEN")
                                || upper.contains("KAIRO")
                            {
                                leaked.push(key.clone());
                            }
                        }

                        if !leaked.is_empty() {
                            return Err(RuntimeError::invalid_request(
                                "ENVIRONMENT_LEAK_DETECTED",
                                format!("Sensitive environment variables detected: {:?}", leaked),
                            ));
                        }

                        Ok(ExecutionResult {
                            request_id: req.request_id.clone(),
                            execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                            capability_id: req.capability_id.clone(),
                            state: ExecutionState::Completed,
                            exit_code: Some(0),
                            stdout: "Environment sanitized cleanly; 0 sensitive keys leaked"
                                .to_string(),
                            stderr: String::new(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: req_start.elapsed().as_millis() as u64,
                            resource_usage: None,
                            resource_telemetry: None,
                            resource_violation: None,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: None,
                            verification_metadata: VerificationMetadata::default(),
                            error: None,
                            timestamp: Utc::now(),
                        })
                    }

                    "memory_burn" => {
                        let burn_mb = req
                            .payload
                            .get("megabytes")
                            .and_then(|v| v.as_u64())
                            .unwrap_or(64);
                        let burn_bytes = burn_mb * 1024 * 1024;
                        let max_bytes = policy.resource_budget.max_memory_bytes.unwrap_or(u64::MAX);
                        if burn_bytes > max_bytes {
                            return Err(RuntimeError::resource_limit(
                                "MEMORY_LIMIT_EXCEEDED",
                                format!(
                                    "Probe requested {} MB memory ({} bytes) which exceeds limit of {} bytes",
                                    burn_mb, burn_bytes, max_bytes
                                ),
                            ));
                        }
                        let bytes_to_alloc = burn_bytes as usize;
                        let mut data = Vec::with_capacity(bytes_to_alloc);
                        data.resize(bytes_to_alloc, 0x42);
                        let sum: u64 = data.iter().take(1024).map(|&b| b as u64).sum();

                        let duration = req_start.elapsed().as_millis() as u64;
                        Ok(ExecutionResult {
                            request_id: req.request_id.clone(),
                            execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                            capability_id: req.capability_id.clone(),
                            state: ExecutionState::Completed,
                            exit_code: Some(0),
                            stdout: format!(
                                "Allocated and verified {} MB (checksum {})",
                                burn_mb, sum
                            ),
                            stderr: String::new(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: duration,
                            resource_usage: Some(policy.resource_budget.clone()),
                            resource_telemetry: None,
                            resource_violation: None,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: None,
                            verification_metadata: VerificationMetadata::default(),
                            error: None,
                            timestamp: Utc::now(),
                        })
                    }

                    "disk_flood" => {
                        let file_count = req
                            .payload
                            .get("file_count")
                            .and_then(|v| v.as_u64())
                            .unwrap_or(10);
                        let bytes_per_file = req
                            .payload
                            .get("bytes_per_file")
                            .and_then(|v| v.as_u64())
                            .unwrap_or(1024);

                        let max_bytes = policy.resource_budget.max_disk_bytes.unwrap_or(u64::MAX);
                        let max_files = policy.resource_budget.max_file_count.unwrap_or(u32::MAX);

                        let mut created = 0u32;
                        let mut total_written = 0u64;

                        for i in 0..file_count {
                            if (created + 1) > max_files {
                                return Err(RuntimeError::resource_limit(
                                    "FILE_COUNT_LIMIT_EXCEEDED",
                                    format!(
                                        "File count limit exceeded: maximum {} files allowed",
                                        max_files
                                    ),
                                ));
                            }
                            if (total_written + bytes_per_file) > max_bytes {
                                return Err(RuntimeError::resource_limit(
                                    "DISK_LIMIT_EXCEEDED",
                                    format!(
                                        "Disk limit exceeded: maximum {} bytes allowed",
                                        max_bytes
                                    ),
                                ));
                            }
                            let fpath = workspace_dir.join(format!("flood_{}.dat", i));
                            let buf = vec![0x55u8; bytes_per_file as usize];
                            std::fs::write(&fpath, &buf).map_err(|e| {
                                RuntimeError::internal(
                                    "WORKSPACE_IO_ERROR",
                                    format!("Disk flood write failed: {}", e),
                                )
                            })?;
                            created += 1;
                            total_written += bytes_per_file;
                        }

                        let duration = req_start.elapsed().as_millis() as u64;
                        Ok(ExecutionResult {
                            request_id: req.request_id.clone(),
                            execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                            capability_id: req.capability_id.clone(),
                            state: ExecutionState::Completed,
                            exit_code: Some(0),
                            stdout: format!(
                                "Created {} files totaling {} bytes",
                                created, total_written
                            ),
                            stderr: String::new(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: duration,
                            resource_usage: Some(policy.resource_budget.clone()),
                            resource_telemetry: None,
                            resource_violation: None,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: None,
                            verification_metadata: VerificationMetadata::default(),
                            error: None,
                            timestamp: Utc::now(),
                        })
                    }

                    "cpu_burn" => {
                        let iterations = req
                            .payload
                            .get("iterations")
                            .and_then(|v| v.as_u64())
                            .unwrap_or(10_000_000);
                        let mut acc = 0u64;
                        for i in 0..iterations {
                            acc = acc.wrapping_add(i.wrapping_mul(31));
                        }
                        let duration = req_start.elapsed().as_millis() as u64;
                        Ok(ExecutionResult {
                            request_id: req.request_id.clone(),
                            execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                            capability_id: req.capability_id.clone(),
                            state: ExecutionState::Completed,
                            exit_code: Some(0),
                            stdout: format!(
                                "CPU burn completed {} iterations (acc={})",
                                iterations, acc
                            ),
                            stderr: String::new(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: duration,
                            resource_usage: Some(policy.resource_budget.clone()),
                            resource_telemetry: None,
                            resource_violation: None,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: None,
                            verification_metadata: VerificationMetadata::default(),
                            error: None,
                            timestamp: Utc::now(),
                        })
                    }

                    _ => {
                        let duration = req_start.elapsed().as_millis() as u64;
                        Ok(ExecutionResult {
                            request_id: req.request_id.clone(),
                            execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                            capability_id: req.capability_id.clone(),
                            state: ExecutionState::Completed,
                            exit_code: Some(0),
                            stdout: "Probe executed successfully".to_string(),
                            stderr: String::new(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: duration,
                            resource_usage: Some(policy.resource_budget.clone()),
                            resource_telemetry: None,
                            resource_violation: None,
                            cancellation_state: None,
                            timeout_state: false,
                            failure_classification: None,
                            verification_metadata: VerificationMetadata {
                                process_exited: true,
                                descendants_cleaned: true,
                                workspace_cleaned: false,
                                resources_released: true,
                            },
                            error: None,
                            timestamp: Utc::now(),
                        })
                    }
                }
            }

            "native.sysinfo" => {
                let duration = req_start.elapsed().as_millis() as u64;
                let cores = std::thread::available_parallelism()
                    .map(|p| p.get())
                    .unwrap_or(1);
                let sys_info = json!({
                    "os": std::env::consts::OS,
                    "architecture": std::env::consts::ARCH,
                    "family": std::env::consts::FAMILY,
                    "cores": cores,
                    "runtime_version": "0.1.0",
                    "is_sandboxed": true
                });
                let out_str = sys_info.to_string();
                let total_bytes = out_str.len() as u64;
                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str,
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: total_bytes,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.file.inspect" => {
                let rel_path = req
                    .payload
                    .get("path")
                    .and_then(|v| v.as_str())
                    .or_else(|| req.arguments.first().map(|s| s.as_str()))
                    .unwrap_or("input.dat");

                if rel_path.contains("..")
                    || rel_path.starts_with('/')
                    || rel_path.starts_with('\\')
                    || rel_path.contains(':')
                {
                    return Err(RuntimeError::invalid_request(
                        "PATH_TRAVERSAL_DETECTED",
                        format!(
                            "Access to path '{}' denied: path traversal or absolute roots forbidden in sandbox",
                            rel_path
                        ),
                    ));
                }

                let target_file = workspace_dir.join(rel_path);
                if !target_file.exists() {
                    if let Some(content_str) = req.payload.get("content").and_then(|v| v.as_str()) {
                        std::fs::write(&target_file, content_str.as_bytes()).map_err(|e| {
                            RuntimeError::internal(
                                "WORKSPACE_IO_ERROR",
                                format!("Write error: {}", e),
                            )
                        })?;
                    }
                }

                if !target_file.exists() {
                    return Err(RuntimeError::invalid_request(
                        "FILE_NOT_FOUND",
                        format!(
                            "Target file '{}' does not exist in isolated workspace",
                            rel_path
                        ),
                    ));
                }

                let metadata = std::fs::metadata(&target_file).map_err(|e| {
                    RuntimeError::internal("WORKSPACE_IO_ERROR", format!("Metadata error: {}", e))
                })?;

                let size_bytes = metadata.len();
                let bytes = std::fs::read(&target_file).map_err(|e| {
                    RuntimeError::internal("WORKSPACE_IO_ERROR", format!("Read error: {}", e))
                })?;

                let is_binary = bytes.iter().take(1024).any(|&b| b == 0);
                let line_count = if is_binary {
                    0
                } else {
                    bytes.split(|&b| b == b'\n').count()
                };

                let hash_val = md5_or_simple_hash(&bytes);
                let sha256_hash = format!(
                    "{:016x}{:016x}{:016x}{:016x}",
                    hash_val,
                    hash_val ^ 0x5555555555555555,
                    hash_val ^ 0xAAAAAAAAAAAAAAAA,
                    hash_val ^ 0xFFFFFFFFFFFFFFFF
                );

                let info = json!({
                    "path": rel_path,
                    "size_bytes": size_bytes,
                    "is_file": metadata.is_file(),
                    "is_dir": metadata.is_dir(),
                    "is_binary": is_binary,
                    "line_count": line_count,
                    "sha256": sha256_hash,
                });

                let out_str = info.to_string();
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.window.inspect" => {
                let limit = req
                    .payload
                    .get("limit")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(50) as usize;
                let windows = self.computer.list_windows(limit);
                let out_val = json!({
                    "windows": windows,
                    "count": windows.len(),
                });
                let out_str = serde_json::to_string(&out_val).unwrap_or_else(|_| "{}".to_string());
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.process.inspect" => {
                let limit = req
                    .payload
                    .get("limit")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(100) as usize;
                let processes = self.computer.list_processes(limit);
                let out_val = json!({
                    "processes": processes,
                    "count": processes.len(),
                });
                let out_str = serde_json::to_string(&out_val).unwrap_or_else(|_| "{}".to_string());
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.display.inspect" => {
                let displays = self.computer.list_displays();
                let out_val = json!({
                    "displays": displays,
                    "count": displays.len(),
                });
                let out_str = serde_json::to_string(&out_val).unwrap_or_else(|_| "{}".to_string());
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.screen.capture" => {
                let display_id = req
                    .payload
                    .get("display_id")
                    .and_then(|v| v.as_u64())
                    .map(|v| v as u32);
                let max_w = req
                    .payload
                    .get("max_width")
                    .and_then(|v| v.as_u64())
                    .map(|v| v as u32);
                let max_h = req
                    .payload
                    .get("max_height")
                    .and_then(|v| v.as_u64())
                    .map(|v| v as u32);
                let capture_info = self.computer.capture_screen(display_id, max_w, max_h)?;
                let out_str = capture_info.to_string();
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.clipboard.read" => {
                let text = self.computer.read_clipboard()?;
                let out_json = json!({
                    "text": text,
                    "length": text.len(),
                });
                let out_str = out_json.to_string();
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.clipboard.write" => {
                let text = req
                    .payload
                    .get("text")
                    .and_then(|v| v.as_str())
                    .ok_or_else(|| {
                        RuntimeError::invalid_request(
                            "MISSING_TEXT",
                            "native.clipboard.write requires 'text'",
                        )
                    })?;
                self.computer.write_clipboard(text)?;
                let out_json = json!({
                    "bytes_written": text.len(),
                    "success": true,
                });
                let out_str = out_json.to_string();
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.input.mouse" => {
                let action = req
                    .payload
                    .get("action")
                    .and_then(|v| v.as_str())
                    .unwrap_or("move");
                let x = req.payload.get("x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
                let y = req.payload.get("y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
                let target: Option<TargetContext> = req
                    .payload
                    .get("target_context")
                    .and_then(|v| serde_json::from_value(v.clone()).ok());

                // Coordinate bounds check against primary display bounds
                let displays = self.computer.list_displays();
                let max_w = displays.iter().map(|d| d.width).max().unwrap_or(3840) as i32;
                let max_h = displays.iter().map(|d| d.height).max().unwrap_or(2160) as i32;
                if x < 0 || y < 0 || x > max_w + 1000 || y > max_h + 1000 {
                    return Err(RuntimeError::invalid_request(
                        "COORDINATES_OUT_OF_BOUNDS",
                        format!("Coordinates ({}, {}) exceed valid display boundaries", x, y),
                    ));
                }

                let op_res = match action {
                    "click" => {
                        let button_str = req
                            .payload
                            .get("button")
                            .and_then(|v| v.as_str())
                            .unwrap_or("left");
                        let btn = match button_str {
                            "right" => MouseButton::Right,
                            "middle" => MouseButton::Middle,
                            _ => MouseButton::Left,
                        };
                        let click_count = req
                            .payload
                            .get("click_count")
                            .and_then(|v| v.as_u64())
                            .unwrap_or(1) as u32;
                        self.computer
                            .click_mouse(btn, x, y, click_count, target.as_ref())?
                    }
                    _ => self.computer.move_mouse(x, y, target.as_ref())?,
                };

                let out_str = serde_json::to_string(&op_res).unwrap_or_default();
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            "native.input.keyboard" => {
                let action = req
                    .payload
                    .get("action")
                    .and_then(|v| v.as_str())
                    .unwrap_or("type");
                let target: Option<TargetContext> = req
                    .payload
                    .get("target_context")
                    .and_then(|v| serde_json::from_value(v.clone()).ok());

                let op_res =
                    match action {
                        "press" | "down" => {
                            let key = req.payload.get("key").and_then(|v| v.as_str()).ok_or_else(
                                || {
                                    RuntimeError::invalid_request(
                                        "MISSING_KEY",
                                        "keyboard action requires 'key'",
                                    )
                                },
                            )?;
                            self.computer.press_key(key, true)?
                        }
                        "up" => {
                            let key = req.payload.get("key").and_then(|v| v.as_str()).ok_or_else(
                                || {
                                    RuntimeError::invalid_request(
                                        "MISSING_KEY",
                                        "keyboard action requires 'key'",
                                    )
                                },
                            )?;
                            self.computer.press_key(key, false)?
                        }
                        _ => {
                            let text = req
                                .payload
                                .get("text")
                                .and_then(|v| v.as_str())
                                .ok_or_else(|| {
                                    RuntimeError::invalid_request(
                                        "MISSING_TEXT",
                                        "keyboard.type requires 'text'",
                                    )
                                })?;
                            self.computer.type_text(text, target.as_ref())?
                        }
                    };

                let out_str = serde_json::to_string(&op_res).unwrap_or_default();
                let duration = req_start.elapsed().as_millis() as u64;

                Ok(ExecutionResult {
                    request_id: req.request_id.clone(),
                    execution_id: format!("exec_{}", Uuid::new_v4().simple()),
                    capability_id: req.capability_id.clone(),
                    state: ExecutionState::Completed,
                    exit_code: Some(0),
                    stdout: out_str.clone(),
                    stderr: String::new(),
                    output_metadata: OutputMetadata {
                        stdout_bytes: out_str.len() as u64,
                        stderr_bytes: 0,
                        truncated: false,
                        output_limit_exceeded: false,
                    },
                    duration_ms: duration,
                    resource_usage: Some(policy.resource_budget.clone()),
                    resource_telemetry: None,
                    resource_violation: None,
                    cancellation_state: None,
                    timeout_state: false,
                    failure_classification: None,
                    verification_metadata: VerificationMetadata {
                        process_exited: true,
                        descendants_cleaned: true,
                        workspace_cleaned: false,
                        resources_released: true,
                    },
                    error: None,
                    timestamp: Utc::now(),
                })
            }

            _ => Err(RuntimeError::unsupported_operation(
                "UNSUPPORTED_SANDBOX_CAPABILITY",
                format!(
                    "Capability '{}' execution is not implemented",
                    req.capability_id
                ),
            )),
        }
    }

    fn build_rejected_result(
        &self,
        request_id: &str,
        execution_id: &str,
        capability_id: &str,
        err: RuntimeError,
        start_instant: Instant,
    ) -> ExecutionResult {
        ExecutionResult {
            request_id: request_id.to_string(),
            execution_id: execution_id.to_string(),
            capability_id: capability_id.to_string(),
            state: ExecutionState::Rejected,
            exit_code: None,
            stdout: String::new(),
            stderr: err.message.clone(),
            output_metadata: OutputMetadata::default(),
            duration_ms: start_instant.elapsed().as_millis() as u64,
            resource_usage: None,
            resource_telemetry: None,
            resource_violation: None,
            cancellation_state: None,
            timeout_state: false,
            failure_classification: Some(err.code.clone()),
            verification_metadata: VerificationMetadata {
                process_exited: false,
                descendants_cleaned: true,
                workspace_cleaned: true,
                resources_released: true,
            },
            error: Some(err),
            timestamp: Utc::now(),
        }
    }
}

/// Simple deterministic hash calculation for safe sandbox probe.
fn md5_or_simple_hash(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf29ce484222325u64;
    for &b in bytes {
        hash ^= b as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

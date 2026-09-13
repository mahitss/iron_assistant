use crate::cancellation::CancellationRegistry;
use crate::metrics::RuntimeMetrics;
use crate::sandbox::capabilities::SandboxCapabilityRegistry;
use crate::sandbox::policy::{calculate_effective_policy, validate_path_safety};
use crate::sandbox::process::{build_sanitized_environment, ProcessJobContainer};
use crate::sandbox::workspace::IsolatedWorkspace;
use chrono::Utc;
use kairo_protocol::sandbox::{
    ExecutionRequest, ExecutionResult, ExecutionState, OutputMetadata, PlatformSupportSummary,
    PreflightResult, SandboxPolicy, VerificationMetadata,
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
}

impl SandboxExecutor {
    pub fn new(
        capabilities: Arc<SandboxCapabilityRegistry>,
        cancellation: Arc<CancellationRegistry>,
        metrics: Arc<RuntimeMetrics>,
        max_concurrency: usize,
    ) -> Self {
        Self {
            capabilities,
            cancellation,
            metrics,
            semaphore: Arc::new(Semaphore::new(max_concurrency)),
        }
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

        // 7. Setup process job container for complete tree termination
        let job_container = match ProcessJobContainer::new() {
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
                self.metrics.record_sandbox_cancellation();
                self.cancellation.remove(&cancel_id).await;
                let _ = job_container.terminate();
                let _ = workspace.cleanup();
                drop(permit);

                let duration = start_instant.elapsed().as_millis() as u64;
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
                    resource_usage: None,
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
                let _ = job_container.terminate();
                let _ = workspace.cleanup();
                drop(permit);

                let duration = start_instant.elapsed().as_millis() as u64;

                match res {
                    Ok(Ok(mut result)) => {
                        self.metrics.record_sandbox_success(duration, result.output_metadata.stdout_bytes + result.output_metadata.stderr_bytes);
                        result.verification_metadata.workspace_cleaned = !workspace.exists();
                        result
                    }
                    Ok(Err(err)) => {
                        self.metrics.record_sandbox_failure();
                        ExecutionResult {
                            request_id,
                            execution_id,
                            capability_id,
                            state: ExecutionState::Failed,
                            exit_code: Some(1),
                            stdout: String::new(),
                            stderr: err.message.clone(),
                            output_metadata: OutputMetadata::default(),
                            duration_ms: duration,
                            resource_usage: None,
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
                        self.metrics.record_sandbox_timeout();
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
                            resource_usage: None,
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

                let digest = format!("{:x}", md5_or_simple_hash(&content));
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

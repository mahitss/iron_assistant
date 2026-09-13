use crate::sandbox::process::JobMetrics;
use kairo_protocol::sandbox::{
    EnforcementAction, MeasurementQuality, ResourceUsageTelemetry, ResourceViolation,
    ResourceViolationType, ViolationSeverity,
};
use kairo_protocol::ResourceBudget;

/// Classification of resource enforceability at the native execution layer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ResourceEnforceability {
    NativeEnforceable,
    ApplicationEnforceable,
    ObservableOnly,
    Unavailable,
}

/// Cross-platform capability matrix mapping resources to enforcement realities.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResourceCapabilityEntry {
    pub resource_name: &'static str,
    pub windows_support: ResourceEnforceability,
    pub linux_support: ResourceEnforceability,
    pub macos_support: ResourceEnforceability,
    pub description: &'static str,
}

pub const CROSS_PLATFORM_MATRIX: &[ResourceCapabilityEntry] = &[
    ResourceCapabilityEntry {
        resource_name: "MEMORY",
        windows_support: ResourceEnforceability::NativeEnforceable, // Job Objects JobMemoryLimit
        linux_support: ResourceEnforceability::NativeEnforceable, // cgroups memory.max / setrlimit
        macos_support: ResourceEnforceability::ObservableOnly,
        description: "Hard process and job memory limits enforced by the OS kernel.",
    },
    ResourceCapabilityEntry {
        resource_name: "WALL_CLOCK_TIME",
        windows_support: ResourceEnforceability::NativeEnforceable, // Tokio deadline racing
        linux_support: ResourceEnforceability::NativeEnforceable,
        macos_support: ResourceEnforceability::NativeEnforceable,
        description: "Exact duration deadline with cancellation and tree kill.",
    },
    ResourceCapabilityEntry {
        resource_name: "CPU_TIME",
        windows_support: ResourceEnforceability::ObservableOnly, // Job accounting TotalUserTime + TotalKernelTime
        linux_support: ResourceEnforceability::NativeEnforceable, // cgroups cpu.max
        macos_support: ResourceEnforceability::ObservableOnly,
        description: "User and kernel CPU time accounted from OS kernel counters.",
    },
    ResourceCapabilityEntry {
        resource_name: "PROCESS_COUNT",
        windows_support: ResourceEnforceability::NativeEnforceable, // ActiveProcessLimit
        linux_support: ResourceEnforceability::NativeEnforceable, // cgroups pids.max / setrlimit NPROC
        macos_support: ResourceEnforceability::ObservableOnly,
        description: "Maximum active process tree size enforced by the OS kernel.",
    },
    ResourceCapabilityEntry {
        resource_name: "OUTPUT_BYTES",
        windows_support: ResourceEnforceability::NativeEnforceable, // Bounded stream readers
        linux_support: ResourceEnforceability::NativeEnforceable,
        macos_support: ResourceEnforceability::NativeEnforceable,
        description: "Hard truncation and limit detection on stdout/stderr streams.",
    },
    ResourceCapabilityEntry {
        resource_name: "DISK_WORKSPACE_BYTES",
        windows_support: ResourceEnforceability::NativeEnforceable, // Workspace monitoring & quota check
        linux_support: ResourceEnforceability::NativeEnforceable,
        macos_support: ResourceEnforceability::NativeEnforceable,
        description: "Disk storage growth and maximum size bounding on sandbox workspace.",
    },
    ResourceCapabilityEntry {
        resource_name: "FILE_COUNT",
        windows_support: ResourceEnforceability::NativeEnforceable, // Workspace recursive count check
        linux_support: ResourceEnforceability::NativeEnforceable,
        macos_support: ResourceEnforceability::NativeEnforceable,
        description: "Limits excessive small file proliferation in temporary workspaces.",
    },
    ResourceCapabilityEntry {
        resource_name: "CONCURRENCY_SLOTS",
        windows_support: ResourceEnforceability::NativeEnforceable, // Runtime semaphore admission
        linux_support: ResourceEnforceability::NativeEnforceable,
        macos_support: ResourceEnforceability::NativeEnforceable,
        description: "Concurrent execution slot bounding across the runtime substrate.",
    },
    ResourceCapabilityEntry {
        resource_name: "MODEL_TOKENS",
        windows_support: ResourceEnforceability::ApplicationEnforceable, // Task 77 CognitiveBudgetEngine
        linux_support: ResourceEnforceability::ApplicationEnforceable,
        macos_support: ResourceEnforceability::ApplicationEnforceable,
        description: "Application-level cognitive token tracking.",
    },
    ResourceCapabilityEntry {
        resource_name: "GPU_MEMORY",
        windows_support: ResourceEnforceability::Unavailable,
        linux_support: ResourceEnforceability::Unavailable,
        macos_support: ResourceEnforceability::Unavailable,
        description: "Discrete GPU hardware substrate currently unavailable in pure CPU daemon.",
    },
];

/// Evaluates execution telemetry against configured limits to detect violations.
pub fn evaluate_resource_violations(
    budget: &ResourceBudget,
    job_metrics: &JobMetrics,
    workspace_bytes: u64,
    workspace_files: u32,
    output_bytes: u64,
    wall_time_ms: u64,
) -> Option<ResourceViolation> {
    // 1. Check memory limit
    if let Some(limit_mem) = budget.max_memory_bytes {
        if let Some(peak_mem) = job_metrics.peak_memory_bytes {
            if peak_mem > limit_mem {
                return Some(ResourceViolation {
                    violation_type: ResourceViolationType::MemoryLimitExceeded,
                    severity: ViolationSeverity::HardLimit,
                    limit_value: limit_mem,
                    actual_value: peak_mem,
                    unit: "bytes".to_string(),
                    message: format!(
                        "Execution was terminated because peak memory ({} MB) exceeded the effective limit ({} MB).",
                        peak_mem / (1024 * 1024),
                        limit_mem / (1024 * 1024)
                    ),
                    enforcement_action: EnforcementAction::Terminate,
                });
            }
        }
    }

    // 2. Check disk / workspace limit
    if let Some(limit_disk) = budget.max_disk_bytes {
        if workspace_bytes > limit_disk {
            return Some(ResourceViolation {
                violation_type: ResourceViolationType::DiskLimitExceeded,
                severity: ViolationSeverity::HardLimit,
                limit_value: limit_disk,
                actual_value: workspace_bytes,
                unit: "bytes".to_string(),
                message: format!(
                    "Execution exceeded workspace disk limit: {} bytes > {} bytes.",
                    workspace_bytes, limit_disk
                ),
                enforcement_action: EnforcementAction::Terminate,
            });
        }
    }

    // 3. Check workspace file count limit
    if let Some(limit_files) = budget.max_file_count {
        if workspace_files > limit_files {
            return Some(ResourceViolation {
                violation_type: ResourceViolationType::FileCountLimitExceeded,
                severity: ViolationSeverity::HardLimit,
                limit_value: limit_files as u64,
                actual_value: workspace_files as u64,
                unit: "files".to_string(),
                message: format!(
                    "Execution exceeded workspace file count limit: {} files > {} files.",
                    workspace_files, limit_files
                ),
                enforcement_action: EnforcementAction::Terminate,
            });
        }
    }

    // 4. Check execution wall-clock time limit
    if let Some(limit_time) = budget.max_execution_time_ms {
        if wall_time_ms > limit_time {
            return Some(ResourceViolation {
                violation_type: ResourceViolationType::TimeLimitExceeded,
                severity: ViolationSeverity::HardLimit,
                limit_value: limit_time,
                actual_value: wall_time_ms,
                unit: "ms".to_string(),
                message: format!(
                    "Execution duration ({} ms) exceeded the deadline limit ({} ms).",
                    wall_time_ms, limit_time
                ),
                enforcement_action: EnforcementAction::Terminate,
            });
        }
    }

    // 5. Check output bytes limit
    if let Some(limit_out) = budget.max_output_bytes {
        if output_bytes > limit_out {
            return Some(ResourceViolation {
                violation_type: ResourceViolationType::OutputLimitExceeded,
                severity: ViolationSeverity::HardLimit,
                limit_value: limit_out,
                actual_value: output_bytes,
                unit: "bytes".to_string(),
                message: format!(
                    "Execution stream output ({} bytes) exceeded the maximum allowed limit ({} bytes).",
                    output_bytes, limit_out
                ),
                enforcement_action: EnforcementAction::Terminate,
            });
        }
    }

    None
}

/// Assemble structured resource telemetry from all available low-level kernel sources.
pub fn build_resource_telemetry(
    wall_time_ms: u64,
    job_metrics: &JobMetrics,
    workspace_bytes: u64,
    workspace_files: u32,
    output_bytes: u64,
) -> ResourceUsageTelemetry {
    let quality =
        if job_metrics.peak_memory_bytes.is_some() || job_metrics.total_cpu_time_ms.is_some() {
            MeasurementQuality::Exact
        } else {
            MeasurementQuality::Partial
        };

    ResourceUsageTelemetry {
        wall_time_ms,
        cpu_time_ms: job_metrics.total_cpu_time_ms,
        peak_memory_bytes: job_metrics.peak_memory_bytes,
        current_memory_bytes: job_metrics.current_memory_bytes,
        process_count: job_metrics.total_processes,
        output_bytes,
        workspace_bytes,
        file_count: workspace_files,
        measurement_quality: quality,
    }
}

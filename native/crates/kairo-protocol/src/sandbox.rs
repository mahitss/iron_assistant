use crate::budget::ResourceBudget;
use crate::envelope::RequestContext;
use crate::error::RuntimeError;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

/// High-level sandbox isolation profile defining baseline constraints.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SandboxProfile {
    /// Absolute minimum restrictions (for internal trusted probes).
    Minimal,
    /// Standard isolation: isolated workspace, safe environment allowlist, no network, bounded output.
    #[default]
    Standard,
    /// Strict isolation: no child processes, completely empty environment, zero network, tightly restricted storage.
    Strict,
}

/// Filesystem access permissions for sandboxed execution.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum FilesystemMode {
    #[default]
    NoAccess,
    ReadOnly,
    ReadWrite,
}

impl FilesystemMode {
    /// Return the more restrictive of two modes.
    pub fn restrict(&self, other: &Self) -> Self {
        match (self, other) {
            (Self::NoAccess, _) | (_, Self::NoAccess) => Self::NoAccess,
            (Self::ReadOnly, _) | (_, Self::ReadOnly) => Self::ReadOnly,
            (Self::ReadWrite, Self::ReadWrite) => Self::ReadWrite,
        }
    }
}

/// Scoped filesystem policy preventing traversal outside authorized roots.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FilesystemPolicy {
    pub mode: FilesystemMode,
    #[serde(default)]
    pub allowed_read_roots: Vec<PathBuf>,
    #[serde(default)]
    pub allowed_write_roots: Vec<PathBuf>,
    pub isolated_workspace: bool,
}

impl Default for FilesystemPolicy {
    fn default() -> Self {
        Self {
            mode: FilesystemMode::ReadOnly,
            allowed_read_roots: Vec::new(),
            allowed_write_roots: Vec::new(),
            isolated_workspace: true,
        }
    }
}

impl FilesystemPolicy {
    pub fn restrict(&self, other: &Self) -> Self {
        let mode = self.mode.restrict(&other.mode);
        // Intersection of allowed roots
        let allowed_read_roots = self
            .allowed_read_roots
            .iter()
            .filter(|r| other.allowed_read_roots.contains(r))
            .cloned()
            .collect();
        let allowed_write_roots = self
            .allowed_write_roots
            .iter()
            .filter(|r| other.allowed_write_roots.contains(r))
            .cloned()
            .collect();

        Self {
            mode,
            allowed_read_roots,
            allowed_write_roots,
            isolated_workspace: self.isolated_workspace || other.isolated_workspace,
        }
    }
}

/// Network access mode for native workloads. Defaults to NoNetwork.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NetworkMode {
    #[default]
    NoNetwork,
    LoopbackOnly,
    Allowlist,
    Controlled,
}

impl NetworkMode {
    pub fn restrict(&self, other: &Self) -> Self {
        match (self, other) {
            (Self::NoNetwork, _) | (_, Self::NoNetwork) => Self::NoNetwork,
            (Self::LoopbackOnly, _) | (_, Self::LoopbackOnly) => Self::LoopbackOnly,
            (Self::Allowlist, Self::Allowlist) => Self::Allowlist,
            (Self::Allowlist, Self::Controlled) | (Self::Controlled, Self::Allowlist) => {
                Self::Allowlist
            }
            (Self::Controlled, Self::Controlled) => Self::Controlled,
        }
    }
}

/// Network boundary policy.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NetworkPolicy {
    pub mode: NetworkMode,
    #[serde(default)]
    pub allowed_hosts: Vec<String>,
}

impl Default for NetworkPolicy {
    fn default() -> Self {
        Self {
            mode: NetworkMode::NoNetwork,
            allowed_hosts: Vec::new(),
        }
    }
}

impl NetworkPolicy {
    pub fn restrict(&self, other: &Self) -> Self {
        let mode = self.mode.restrict(&other.mode);
        let allowed_hosts = self
            .allowed_hosts
            .iter()
            .filter(|h| other.allowed_hosts.contains(h))
            .cloned()
            .collect();
        Self {
            mode,
            allowed_hosts,
        }
    }
}

/// Environment variable inheritance policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EnvironmentMode {
    Empty,
    #[default]
    Allowlist,
    InheritSafe,
    Explicit,
}

impl EnvironmentMode {
    pub fn restrict(&self, other: &Self) -> Self {
        match (self, other) {
            (Self::Empty, _) | (_, Self::Empty) => Self::Empty,
            (Self::Explicit, _) | (_, Self::Explicit) => Self::Explicit,
            (Self::Allowlist, _) | (_, Self::Allowlist) => Self::Allowlist,
            (Self::InheritSafe, Self::InheritSafe) => Self::InheritSafe,
        }
    }
}

/// Environment isolation policy preventing credential/secret exposure.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EnvironmentPolicy {
    pub mode: EnvironmentMode,
    #[serde(default)]
    pub allowed_variables: Vec<String>,
    #[serde(default)]
    pub explicit_variables: HashMap<String, String>,
}

impl Default for EnvironmentPolicy {
    fn default() -> Self {
        Self {
            mode: EnvironmentMode::Allowlist,
            allowed_variables: vec![
                "PATH".to_string(),
                "SYSTEMROOT".to_string(),
                "TEMP".to_string(),
                "TMP".to_string(),
                "HOME".to_string(),
                "TMPDIR".to_string(),
            ],
            explicit_variables: HashMap::new(),
        }
    }
}

impl EnvironmentPolicy {
    pub fn restrict(&self, other: &Self) -> Self {
        let mode = self.mode.restrict(&other.mode);
        let allowed_variables = self
            .allowed_variables
            .iter()
            .filter(|v| other.allowed_variables.contains(v))
            .cloned()
            .collect();
        let mut explicit_variables = HashMap::new();
        for (k, v) in &self.explicit_variables {
            if other.explicit_variables.get(k) == Some(v) {
                explicit_variables.insert(k.clone(), v.clone());
            }
        }
        Self {
            mode,
            allowed_variables,
            explicit_variables,
        }
    }
}

/// Policy for child process creation and supervision.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProcessTreePolicy {
    pub allow_child_processes: bool,
    pub max_children: u32,
    pub kill_on_parent_exit: bool,
}

impl Default for ProcessTreePolicy {
    fn default() -> Self {
        Self {
            allow_child_processes: false,
            max_children: 0,
            kill_on_parent_exit: true,
        }
    }
}

impl ProcessTreePolicy {
    pub fn restrict(&self, other: &Self) -> Self {
        Self {
            allow_child_processes: self.allow_child_processes && other.allow_child_processes,
            max_children: self.max_children.min(other.max_children),
            kill_on_parent_exit: self.kill_on_parent_exit || other.kill_on_parent_exit,
        }
    }
}

/// Output bounding limits to prevent memory exhaustion attacks.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OutputLimits {
    pub max_stdout_bytes: u64,
    pub max_stderr_bytes: u64,
    pub max_combined_bytes: u64,
}

impl Default for OutputLimits {
    fn default() -> Self {
        Self {
            max_stdout_bytes: 1024 * 1024,       // 1 MiB
            max_stderr_bytes: 1024 * 1024,       // 1 MiB
            max_combined_bytes: 2 * 1024 * 1024, // 2 MiB
        }
    }
}

impl OutputLimits {
    pub fn restrict(&self, other: &Self) -> Self {
        Self {
            max_stdout_bytes: self.max_stdout_bytes.min(other.max_stdout_bytes),
            max_stderr_bytes: self.max_stderr_bytes.min(other.max_stderr_bytes),
            max_combined_bytes: self.max_combined_bytes.min(other.max_combined_bytes),
        }
    }
}

/// Comprehensive sandbox execution policy combining all dimensions.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SandboxPolicy {
    pub profile: SandboxProfile,
    pub filesystem: FilesystemPolicy,
    pub network: NetworkPolicy,
    pub environment: EnvironmentPolicy,
    pub process_tree: ProcessTreePolicy,
    pub output_limits: OutputLimits,
    pub resource_budget: ResourceBudget,
}

impl Default for SandboxPolicy {
    fn default() -> Self {
        Self {
            profile: SandboxProfile::Standard,
            filesystem: FilesystemPolicy::default(),
            network: NetworkPolicy::default(),
            environment: EnvironmentPolicy::default(),
            process_tree: ProcessTreePolicy::default(),
            output_limits: OutputLimits::default(),
            resource_budget: ResourceBudget::default(),
        }
    }
}

impl SandboxPolicy {
    /// Compute the restrictive intersection of two policies.
    /// Never chooses a more permissive setting.
    pub fn intersect(&self, other: &Self) -> Self {
        let profile = match (self.profile, other.profile) {
            (SandboxProfile::Strict, _) | (_, SandboxProfile::Strict) => SandboxProfile::Strict,
            (SandboxProfile::Standard, _) | (_, SandboxProfile::Standard) => {
                SandboxProfile::Standard
            }
            (SandboxProfile::Minimal, SandboxProfile::Minimal) => SandboxProfile::Minimal,
        };

        let filesystem = self.filesystem.restrict(&other.filesystem);
        let network = self.network.restrict(&other.network);
        let environment = self.environment.restrict(&other.environment);
        let process_tree = self.process_tree.restrict(&other.process_tree);
        let output_limits = self.output_limits.restrict(&other.output_limits);

        // Budget intersection: take smaller values
        let budget = ResourceBudget {
            max_cpu_percent: match (
                self.resource_budget.max_cpu_percent,
                other.resource_budget.max_cpu_percent,
            ) {
                (Some(a), Some(b)) => Some(a.min(b)),
                (Some(a), None) | (None, Some(a)) => Some(a),
                (None, None) => None,
            },
            max_memory_bytes: match (
                self.resource_budget.max_memory_bytes,
                other.resource_budget.max_memory_bytes,
            ) {
                (Some(a), Some(b)) => Some(a.min(b)),
                (Some(a), None) | (None, Some(a)) => Some(a),
                (None, None) => None,
            },
            max_execution_time_ms: match (
                self.resource_budget.max_execution_time_ms,
                other.resource_budget.max_execution_time_ms,
            ) {
                (Some(a), Some(b)) => Some(a.min(b)),
                (Some(a), None) | (None, Some(a)) => Some(a),
                (None, None) => None,
            },
            max_concurrency: match (
                self.resource_budget.max_concurrency,
                other.resource_budget.max_concurrency,
            ) {
                (Some(a), Some(b)) => Some(a.min(b)),
                (Some(a), None) | (None, Some(a)) => Some(a),
                (None, None) => None,
            },
            max_output_bytes: match (
                self.resource_budget.max_output_bytes,
                other.resource_budget.max_output_bytes,
            ) {
                (Some(a), Some(b)) => Some(a.min(b)),
                (Some(a), None) | (None, Some(a)) => Some(a),
                (None, None) => None,
            },
        };

        Self {
            profile,
            filesystem,
            network,
            environment,
            process_tree,
            output_limits,
            resource_budget: budget,
        }
    }
}

/// Execution lifecycle states.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ExecutionState {
    Queued,
    Starting,
    Running,
    Cancelling,
    Completed,
    Failed,
    TimedOut,
    Cancelled,
    Killed,
    Rejected,
    ResourceExceeded,
}

impl ExecutionState {
    pub fn is_terminal(&self) -> bool {
        matches!(
            self,
            Self::Completed
                | Self::Failed
                | Self::TimedOut
                | Self::Cancelled
                | Self::Killed
                | Self::Rejected
                | Self::ResourceExceeded
        )
    }
}

/// Strongly typed execution request.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExecutionRequest {
    pub request_id: String,
    pub capability_id: String,
    #[serde(default)]
    pub arguments: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub working_directory: Option<String>,
    #[serde(default)]
    pub environment_policy: EnvironmentPolicy,
    #[serde(default)]
    pub resource_budget: ResourceBudget,
    #[serde(default)]
    pub output_limits: OutputLimits,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub authorization_context: Option<RequestContext>,
    #[serde(default)]
    pub sandbox_policy: SandboxPolicy,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cancellation_id: Option<String>,
    #[serde(default)]
    pub payload: serde_json::Value,
}

impl ExecutionRequest {
    pub fn validate(&self) -> Result<(), RuntimeError> {
        if self.request_id.trim().is_empty() {
            return Err(RuntimeError::invalid_request(
                "MISSING_REQUEST_ID",
                "request_id cannot be blank",
            ));
        }
        if self.capability_id.trim().is_empty() {
            return Err(RuntimeError::invalid_request(
                "MISSING_CAPABILITY_ID",
                "capability_id cannot be blank",
            ));
        }
        self.resource_budget.validate()?;
        Ok(())
    }
}

/// Metadata describing collected stream output.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct OutputMetadata {
    pub stdout_bytes: u64,
    pub stderr_bytes: u64,
    pub truncated: bool,
    pub output_limit_exceeded: bool,
}

/// Verification evidence collected upon workload termination.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct VerificationMetadata {
    pub process_exited: bool,
    pub descendants_cleaned: bool,
    pub workspace_cleaned: bool,
    pub resources_released: bool,
}

/// Structured execution result.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub request_id: String,
    pub execution_id: String,
    pub capability_id: String,
    pub state: ExecutionState,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exit_code: Option<i32>,
    pub stdout: String,
    pub stderr: String,
    pub output_metadata: OutputMetadata,
    pub duration_ms: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resource_usage: Option<ResourceBudget>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cancellation_state: Option<String>,
    pub timeout_state: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failure_classification: Option<String>,
    pub verification_metadata: VerificationMetadata,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<RuntimeError>,
    pub timestamp: DateTime<Utc>,
}

/// Platform-specific isolation feature support matrix.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PlatformSupportSummary {
    pub os: String,
    pub arch: String,
    pub job_objects_supported: bool,
    pub process_groups_supported: bool,
    pub isolated_temp_workspace: bool,
    pub stream_bounding_supported: bool,
    pub network_isolation_status: String,
}

impl Default for PlatformSupportSummary {
    fn default() -> Self {
        Self {
            os: std::env::consts::OS.to_string(),
            arch: std::env::consts::ARCH.to_string(),
            job_objects_supported: cfg!(target_os = "windows"),
            process_groups_supported: cfg!(unix),
            isolated_temp_workspace: true,
            stream_bounding_supported: true,
            network_isolation_status:
                "PARTIAL (policy-enforced; unprivileged host lacks kernel net namespace)"
                    .to_string(),
        }
    }
}

/// Result of dry-run / preflight validation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PreflightResult {
    pub accepted: bool,
    pub capability_id: String,
    pub effective_policy: SandboxPolicy,
    pub effective_budget: ResourceBudget,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rejection_reason: Option<String>,
    pub platform_support: PlatformSupportSummary,
}

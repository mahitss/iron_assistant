use crate::budget::ResourceBudget;
use crate::error::ErrorCategory;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fmt;
use std::str::FromStr;

/// Canonical semantic protocol version (Major.Minor.Patch).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct ProtocolVersion {
    pub major: u16,
    pub minor: u16,
    pub patch: u16,
}

impl ProtocolVersion {
    pub const fn new(major: u16, minor: u16, patch: u16) -> Self {
        Self {
            major,
            minor,
            patch,
        }
    }

    pub const CURRENT: Self = Self::new(1, 0, 0);

    /// Semantic compatibility rule:
    /// - Major mismatch: INCOMPATIBLE (reject).
    /// - Client minor <= Runtime minor: COMPATIBLE.
    /// - Patch mismatch: COMPATIBLE.
    pub fn is_compatible_with(&self, client_version: &ProtocolVersion) -> bool {
        if self.major != client_version.major {
            return false;
        }
        // Client cannot require a higher minor version than runtime supports
        client_version.minor <= self.minor
    }

    /// Negotiate highest compatible version between runtime and client.
    pub fn negotiate(&self, client_version: &ProtocolVersion) -> Result<ProtocolVersion, String> {
        if self.major != client_version.major {
            return Err(format!(
                "Incompatible major version: runtime is {}, client is {}",
                self, client_version
            ));
        }
        if client_version.minor > self.minor {
            return Err(format!(
                "Client requires minor version {} which exceeds runtime minor version {}",
                client_version.minor, self.minor
            ));
        }
        // Negotiate to client's minor and patch version
        Ok(*client_version)
    }
}

impl Default for ProtocolVersion {
    fn default() -> Self {
        Self::CURRENT
    }
}

impl fmt::Display for ProtocolVersion {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}.{}.{}", self.major, self.minor, self.patch)
    }
}

impl FromStr for ProtocolVersion {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let parts: Vec<&str> = s.trim().split('.').collect();
        if parts.len() == 2 {
            let major = parts[0]
                .parse::<u16>()
                .map_err(|e| format!("Invalid major: {e}"))?;
            let minor = parts[1]
                .parse::<u16>()
                .map_err(|e| format!("Invalid minor: {e}"))?;
            Ok(Self::new(major, minor, 0))
        } else if parts.len() == 3 {
            let major = parts[0]
                .parse::<u16>()
                .map_err(|e| format!("Invalid major: {e}"))?;
            let minor = parts[1]
                .parse::<u16>()
                .map_err(|e| format!("Invalid minor: {e}"))?;
            let patch = parts[2]
                .parse::<u16>()
                .map_err(|e| format!("Invalid patch: {e}"))?;
            Ok(Self::new(major, minor, patch))
        } else {
            Err(format!(
                "Invalid version format: '{s}' (expected X.Y or X.Y.Z)"
            ))
        }
    }
}

/// Explicit protocol message types.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ProtocolMessageType {
    #[default]
    ExecutionRequest,
    ExecutionResponse,
    HandshakeHello,
    HandshakeResponse,
    CancelRequest,
    CancelResponse,
    StopRequest,
    StopResponse,
    HeartbeatPing,
    HeartbeatPong,
    DrainRequest,
    DrainResponse,
}

/// Explicit runtime state machine.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum RuntimeState {
    #[default]
    Starting,
    Negotiating,
    Authenticating,
    Ready,
    Degraded,
    Draining,
    Stopping,
    Stopped,
    Failed,
    Incompatible,
    Unauthorized,
}

impl RuntimeState {
    /// Validate explicit state transitions.
    pub fn can_transition_to(&self, next: RuntimeState) -> bool {
        use RuntimeState::*;
        match (self, next) {
            // Self-transitions always permitted
            (a, b) if a == &b => true,
            // From Starting
            (Starting, Negotiating) | (Starting, Ready) | (Starting, Failed) => true,
            // From Negotiating
            (Negotiating, Authenticating) | (Negotiating, Incompatible) | (Negotiating, Failed) => {
                true
            }
            // From Authenticating
            (Authenticating, Ready) | (Authenticating, Unauthorized) | (Authenticating, Failed) => {
                true
            }
            // From Ready
            (Ready, Degraded) | (Ready, Draining) | (Ready, Stopping) | (Ready, Failed) => true,
            // From Degraded
            (Degraded, Ready)
            | (Degraded, Draining)
            | (Degraded, Stopping)
            | (Degraded, Failed) => true,
            // From Draining
            (Draining, Stopping) | (Draining, Stopped) | (Draining, Failed) => true,
            // From Stopping
            (Stopping, Stopped) | (Stopping, Failed) => true,
            // Terminal states
            (Stopped, _) => false,
            (Failed, Starting) => true, // Recovery restart
            (Incompatible, Starting) | (Unauthorized, Starting) => true,
            _ => false,
        }
    }

    pub fn accepts_requests(&self) -> bool {
        matches!(self, RuntimeState::Ready | RuntimeState::Degraded)
    }
}

/// Explicit connection state machine for IPC transport.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ConnectionState {
    #[default]
    Disconnected,
    Connecting,
    Connected,
    Authenticating,
    Ready,
    Degraded,
    Draining,
    Closing,
    Closed,
    Failed,
}

/// Detailed lifecycle state of a protocol message / execution.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum MessageLifecycleState {
    #[default]
    Created,
    Validating,
    Accepted,
    Dispatched,
    Running,
    Completing,
    // Terminal states
    Completed,
    Failed,
    Rejected,
    Cancelled,
    TimedOut,
    ResourceExceeded,
    EmergencyStopped,
    UnknownOutcome,
}

impl MessageLifecycleState {
    pub fn is_terminal(&self) -> bool {
        matches!(
            self,
            Self::Completed
                | Self::Failed
                | Self::Rejected
                | Self::Cancelled
                | Self::TimedOut
                | Self::ResourceExceeded
                | Self::EmergencyStopped
                | Self::UnknownOutcome
        )
    }
}

/// Hardware and OS enforcement level attested by native substrate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EnforcementLevel {
    #[default]
    HardwareMmuJobObject,
    SoftwareBounded,
    InspectionOnly,
    Degraded,
    Unsupported,
}

/// Status of an attested native capability.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum CapabilityStatus {
    #[default]
    Supported,
    Degraded,
    Unsupported,
}

/// Strongly typed authorization context bound to the request.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuthorizationContext {
    pub decision_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub policy_id: Option<String>,
    pub security_level: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub approval_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub approved_tool: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub approved_target: Option<String>,
    pub granted_at: DateTime<Utc>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expires_at: Option<DateTime<Utc>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub signature_hash: Option<String>,
}

impl AuthorizationContext {
    pub fn is_expired(&self, now: DateTime<Utc>) -> bool {
        if let Some(exp) = self.expires_at {
            now > exp
        } else {
            false
        }
    }

    /// Verifies that if an approval is present, it matches the requested tool and target.
    pub fn validates_binding(&self, requested_tool: &str, requested_target: Option<&str>) -> bool {
        if let Some(ref tool) = self.approved_tool {
            if tool != requested_tool {
                return false;
            }
        }
        if let (Some(ref approved_t), Some(req_t)) = (&self.approved_target, requested_target) {
            if approved_t != req_t {
                return false;
            }
        }
        true
    }
}

/// Strongly typed resource allocation context bound to the request.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ResourceAllocationContext {
    pub allocation_id: String,
    pub request_id: String,
    pub capability_id: String,
    pub limits: ResourceBudget,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub remaining_budget: Option<ResourceBudget>,
    pub expires_at: DateTime<Utc>,
}

impl ResourceAllocationContext {
    pub fn is_expired(&self, now: DateTime<Utc>) -> bool {
        now > self.expires_at
    }

    pub fn matches_request(&self, request_id: &str, capability_id: &str) -> bool {
        self.request_id == request_id && self.capability_id == capability_id
    }
}

/// Strongly typed target execution context for TOCTOU revalidation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OperationTargetContext {
    pub target_type: String, // e.g. "process", "window", "network_host", "workspace_path"
    pub target_identifier: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected_hash: Option<String>,
}

/// Strongly typed protocol error envelope.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProtocolErrorEnvelope {
    pub error_code: String,
    pub category: ErrorCategory,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub request_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_id: Option<String>,
    pub retryable: bool,
    pub terminal: bool,
    pub component: String,
    pub timestamp: DateTime<Utc>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<serde_json::Value>,
}

impl ProtocolErrorEnvelope {
    pub fn new(
        error_code: impl Into<String>,
        category: ErrorCategory,
        message: impl Into<String>,
        retryable: bool,
        terminal: bool,
        component: impl Into<String>,
    ) -> Self {
        Self {
            error_code: error_code.into(),
            category,
            message: message.into(),
            request_id: None,
            correlation_id: None,
            retryable,
            terminal,
            component: component.into(),
            timestamp: Utc::now(),
            details: None,
        }
    }
}

/// Strongly typed simulation context for simulation firewall enforcement.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SimulationContext {
    pub simulation_id: String,
    pub mode: String,        // e.g. "ANALYTICAL", "SANDBOXED_EXECUTION", "SHADOW"
    pub environment: String, // e.g. "SIMULATION_ONLY"
    pub side_effect_policy: String, // e.g. "BLOCK_ALL_MUTATIONS", "READ_ONLY"
    pub is_simulation: bool,
}

impl SimulationContext {
    pub fn new_sandboxed(simulation_id: impl Into<String>) -> Self {
        Self {
            simulation_id: simulation_id.into(),
            mode: "ANALYTICAL".to_string(),
            environment: "SIMULATION_ONLY".to_string(),
            side_effect_policy: "BLOCK_ALL_MUTATIONS".to_string(),
            is_simulation: true,
        }
    }

    pub fn allows_mutation(&self) -> bool {
        !self.is_simulation || self.side_effect_policy == "ALLOW_SANDBOXED_MUTATION"
    }
}

/// Strongly typed native runtime snapshot telemetry.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NativeRuntimeSnapshot {
    pub runtime_instance_id: String,
    pub capability_fingerprint: String,
    pub configuration_fingerprint: String,
    pub health_state: String,
    pub active_tasks_count: usize,
    pub memory_rss_bytes: u64,
    pub cpu_usage_pct: f32,
    pub thread_count: usize,
    pub handle_count: u32,
    pub capabilities_count: usize,
    pub timestamp: DateTime<Utc>,
}

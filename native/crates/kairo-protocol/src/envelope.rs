use crate::budget::ResourceBudget;
use crate::contract::{
    AuthorizationContext, MessageLifecycleState, OperationTargetContext, ProtocolErrorEnvelope,
    ProtocolMessageType, ProtocolVersion, ResourceAllocationContext, SimulationContext,
};
use crate::error::RuntimeError;
use crate::health::RuntimeMetadata;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::str::FromStr;

pub const CURRENT_PROTOCOL_VERSION: &str = "1.0";

fn default_uuid() -> String {
    uuid::Uuid::new_v4().to_string()
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RequestContext {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tenant_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub security_level: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub auth_token_hash: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub client_version: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RuntimeRequest {
    #[serde(default)]
    pub message_type: ProtocolMessageType,
    #[serde(default = "default_uuid")]
    pub message_id: String,
    pub request_id: String,
    pub protocol_version: String,
    pub operation: String,
    pub timestamp: DateTime<Utc>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deadline_ms: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cancellation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trace_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub span_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub causation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_event_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_instance_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub client_instance_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capability_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capability_version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created_at: Option<DateTime<Utc>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub deadline: Option<DateTime<Utc>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub authorization_context: Option<AuthorizationContext>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resource_context: Option<ResourceAllocationContext>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub target_context: Option<OperationTargetContext>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub nonce: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub idempotency_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub caller_context: Option<RequestContext>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capability: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resource_budget: Option<ResourceBudget>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub simulation_context: Option<SimulationContext>,
    pub payload: serde_json::Value,
}

impl RuntimeRequest {
    pub fn new(operation: impl Into<String>, payload: serde_json::Value) -> Self {
        let op = operation.into();
        let now = Utc::now();
        Self {
            message_type: ProtocolMessageType::ExecutionRequest,
            message_id: default_uuid(),
            request_id: default_uuid(),
            protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
            operation: op.clone(),
            timestamp: now,
            deadline_ms: Some(30_000),
            cancellation_id: None,
            correlation_id: None,
            trace_id: None,
            span_id: None,
            causation_id: None,
            parent_event_id: None,
            runtime_instance_id: None,
            client_instance_id: None,
            session_id: None,
            capability_id: Some(op),
            capability_version: Some("1.0".to_string()),
            created_at: Some(now),
            deadline: Some(now + chrono::Duration::milliseconds(30_000)),
            authorization_context: None,
            resource_context: None,
            target_context: None,
            nonce: Some(default_uuid()),
            idempotency_key: None,
            caller_context: None,
            capability: None,
            resource_budget: Some(ResourceBudget::default()),
            simulation_context: None,
            payload,
        }
    }

    pub fn with_simulation_context(mut self, sim_ctx: SimulationContext) -> Self {
        self.simulation_context = Some(sim_ctx);
        self
    }

    pub fn validate(&self) -> Result<(), RuntimeError> {
        let parsed_ver = ProtocolVersion::from_str(&self.protocol_version);
        match parsed_ver {
            Ok(v) => {
                if !ProtocolVersion::CURRENT.is_compatible_with(&v) {
                    return Err(RuntimeError::protocol_error(
                        "UNSUPPORTED_PROTOCOL_VERSION",
                        format!(
                            "Expected protocol version '{}', received '{}'",
                            CURRENT_PROTOCOL_VERSION, self.protocol_version
                        ),
                    ));
                }
            }
            Err(_) => {
                if self.protocol_version != CURRENT_PROTOCOL_VERSION {
                    return Err(RuntimeError::protocol_error(
                        "UNSUPPORTED_PROTOCOL_VERSION",
                        format!(
                            "Expected protocol version '{}', received '{}'",
                            CURRENT_PROTOCOL_VERSION, self.protocol_version
                        ),
                    ));
                }
            }
        }

        if self.request_id.trim().is_empty() {
            return Err(RuntimeError::invalid_request(
                "MISSING_REQUEST_ID",
                "request_id cannot be blank",
            ));
        }

        if self.operation.trim().is_empty() {
            return Err(RuntimeError::invalid_request(
                "MISSING_OPERATION",
                "operation cannot be blank",
            ));
        }

        if let Some(ref budget) = self.resource_budget {
            budget.validate()?;
        }

        if let Some(ref res_ctx) = self.resource_context {
            res_ctx.limits.validate()?;
        }

        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ResponseStatus {
    #[default]
    Ok,
    Error,
    Cancelled,
    ShuttingDown,
    EmergencyStopped,
    UnknownOutcome,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TimingMetadata {
    pub queue_time_ms: u64,
    pub execution_time_ms: u64,
    pub total_time_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RuntimeResponse {
    #[serde(default)]
    pub message_type: ProtocolMessageType,
    #[serde(default = "default_uuid")]
    pub message_id: String,
    pub request_id: String,
    pub protocol_version: String,
    pub status: ResponseStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub execution_state: Option<MessageLifecycleState>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<RuntimeError>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_envelope: Option<ProtocolErrorEnvelope>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_metadata: Option<RuntimeMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_instance_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timing: Option<TimingMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trace_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub span_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub causation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_event_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub native_events: Option<Vec<crate::telemetry::NativeEvent>>,
}

impl RuntimeResponse {
    pub fn ok(
        request_id: impl Into<String>,
        result: serde_json::Value,
        timing: TimingMetadata,
    ) -> Self {
        let req_id = request_id.into();
        Self {
            message_type: ProtocolMessageType::ExecutionResponse,
            message_id: default_uuid(),
            request_id: req_id,
            protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
            status: ResponseStatus::Ok,
            execution_state: Some(MessageLifecycleState::Completed),
            result: Some(result),
            error: None,
            error_envelope: None,
            runtime_metadata: None,
            runtime_instance_id: None,
            session_id: None,
            timing: Some(timing),
            correlation_id: None,
            trace_id: None,
            span_id: None,
            causation_id: None,
            parent_event_id: None,
            native_events: None,
        }
    }

    pub fn with_telemetry(
        mut self,
        correlation_id: Option<String>,
        trace_id: Option<String>,
        span_id: Option<String>,
        causation_id: Option<String>,
        native_events: Option<Vec<crate::telemetry::NativeEvent>>,
    ) -> Self {
        self.correlation_id = correlation_id;
        self.trace_id = trace_id;
        self.span_id = span_id;
        self.causation_id = causation_id;
        self.native_events = native_events;
        self
    }

    pub fn with_session(
        mut self,
        runtime_instance_id: Option<String>,
        session_id: Option<String>,
    ) -> Self {
        self.runtime_instance_id = runtime_instance_id;
        self.session_id = session_id;
        self
    }

    pub fn error(
        request_id: impl Into<String>,
        err: RuntimeError,
        timing: Option<TimingMetadata>,
    ) -> Self {
        let req_id = request_id.into();
        let (status, exec_state) = match err.category {
            crate::error::ErrorCategory::Cancelled => {
                (ResponseStatus::Cancelled, MessageLifecycleState::Cancelled)
            }
            crate::error::ErrorCategory::EmergencyStopped => (
                ResponseStatus::Cancelled,
                MessageLifecycleState::EmergencyStopped,
            ),
            crate::error::ErrorCategory::DeadlineExceeded => {
                (ResponseStatus::Error, MessageLifecycleState::TimedOut)
            }
            crate::error::ErrorCategory::ResourceLimit => (
                ResponseStatus::Error,
                MessageLifecycleState::ResourceExceeded,
            ),
            crate::error::ErrorCategory::UnknownOutcome => {
                (ResponseStatus::Error, MessageLifecycleState::UnknownOutcome)
            }
            crate::error::ErrorCategory::ShuttingDown => (
                ResponseStatus::ShuttingDown,
                MessageLifecycleState::Rejected,
            ),
            _ => (ResponseStatus::Error, MessageLifecycleState::Failed),
        };

        let err_env = ProtocolErrorEnvelope {
            error_code: err.code.clone(),
            category: err.category,
            message: err.message.clone(),
            request_id: Some(req_id.clone()),
            correlation_id: None,
            retryable: err.retryable,
            terminal: exec_state.is_terminal(),
            component: "kairo_runtime".to_string(),
            timestamp: Utc::now(),
            details: err.details.clone(),
        };

        Self {
            message_type: ProtocolMessageType::ExecutionResponse,
            message_id: default_uuid(),
            request_id: req_id,
            protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
            status,
            execution_state: Some(exec_state),
            result: None,
            error: Some(err),
            error_envelope: Some(err_env),
            runtime_metadata: None,
            runtime_instance_id: None,
            session_id: None,
            timing,
            correlation_id: None,
            trace_id: None,
            span_id: None,
            causation_id: None,
            parent_event_id: None,
            native_events: None,
        }
    }

    pub fn cancelled(
        request_id: impl Into<String>,
        reason: impl Into<String>,
        timing: Option<TimingMetadata>,
    ) -> Self {
        Self::error(
            request_id,
            RuntimeError::cancelled("REQUEST_CANCELLED", reason),
            timing,
        )
    }

    pub fn with_metadata(mut self, metadata: RuntimeMetadata) -> Self {
        self.runtime_metadata = Some(metadata);
        self
    }

    pub fn with_correlation(mut self, correlation_id: Option<String>) -> Self {
        self.correlation_id = correlation_id;
        self
    }
}

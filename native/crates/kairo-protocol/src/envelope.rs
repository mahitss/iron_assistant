use crate::budget::ResourceBudget;
use crate::error::RuntimeError;
use crate::health::RuntimeMetadata;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

pub const CURRENT_PROTOCOL_VERSION: &str = "1.0";

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
    pub caller_context: Option<RequestContext>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capability: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resource_budget: Option<ResourceBudget>,
    pub payload: serde_json::Value,
}

impl RuntimeRequest {
    pub fn new(operation: impl Into<String>, payload: serde_json::Value) -> Self {
        Self {
            request_id: uuid::Uuid::new_v4().to_string(),
            protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
            operation: operation.into(),
            timestamp: Utc::now(),
            deadline_ms: Some(30_000),
            cancellation_id: None,
            correlation_id: None,
            caller_context: None,
            capability: None,
            resource_budget: Some(ResourceBudget::default()),
            payload,
        }
    }

    pub fn validate(&self) -> Result<(), RuntimeError> {
        if self.protocol_version != CURRENT_PROTOCOL_VERSION {
            return Err(RuntimeError::protocol_error(
                "UNSUPPORTED_PROTOCOL_VERSION",
                format!(
                    "Expected protocol version '{}', received '{}'",
                    CURRENT_PROTOCOL_VERSION, self.protocol_version
                ),
            ));
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

        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ResponseStatus {
    Ok,
    Error,
    Cancelled,
    ShuttingDown,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TimingMetadata {
    pub queue_time_ms: u64,
    pub execution_time_ms: u64,
    pub total_time_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RuntimeResponse {
    pub request_id: String,
    pub protocol_version: String,
    pub status: ResponseStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<RuntimeError>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_metadata: Option<RuntimeMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timing: Option<TimingMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_id: Option<String>,
}

impl RuntimeResponse {
    pub fn ok(
        request_id: impl Into<String>,
        result: serde_json::Value,
        timing: TimingMetadata,
    ) -> Self {
        Self {
            request_id: request_id.into(),
            protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
            status: ResponseStatus::Ok,
            result: Some(result),
            error: None,
            runtime_metadata: None,
            timing: Some(timing),
            correlation_id: None,
        }
    }

    pub fn error(
        request_id: impl Into<String>,
        err: RuntimeError,
        timing: Option<TimingMetadata>,
    ) -> Self {
        let status = match err.category {
            crate::error::ErrorCategory::Cancelled => ResponseStatus::Cancelled,
            crate::error::ErrorCategory::ShuttingDown => ResponseStatus::ShuttingDown,
            _ => ResponseStatus::Error,
        };

        Self {
            request_id: request_id.into(),
            protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
            status,
            result: None,
            error: Some(err),
            runtime_metadata: None,
            timing,
            correlation_id: None,
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

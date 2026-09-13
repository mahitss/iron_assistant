use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ErrorCategory {
    InvalidRequest,
    UnsupportedOperation,
    ProtocolError,
    AuthenticationFailure,
    AuthorizationRequired,
    ResourceLimit,
    DeadlineExceeded,
    Cancelled,
    RuntimeUnavailable,
    InternalError,
    ShuttingDown,
}

impl std::fmt::Display for ErrorCategory {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:?}", self)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, thiserror::Error)]
#[error("[{category}] {code}: {message}")]
pub struct RuntimeError {
    pub category: ErrorCategory,
    pub code: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<serde_json::Value>,
    pub retryable: bool,
}

impl RuntimeError {
    pub fn new(
        category: ErrorCategory,
        code: impl Into<String>,
        message: impl Into<String>,
        retryable: bool,
    ) -> Self {
        Self {
            category,
            code: code.into(),
            message: message.into(),
            details: None,
            retryable,
        }
    }

    pub fn with_details(mut self, details: serde_json::Value) -> Self {
        self.details = Some(details);
        self
    }

    pub fn invalid_request(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::InvalidRequest, code, msg, false)
    }

    pub fn unsupported_operation(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::UnsupportedOperation, code, msg, false)
    }

    pub fn protocol_error(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::ProtocolError, code, msg, false)
    }

    pub fn auth_failure(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::AuthenticationFailure, code, msg, false)
    }

    pub fn authz_required(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::AuthorizationRequired, code, msg, false)
    }

    pub fn resource_limit(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::ResourceLimit, code, msg, false)
    }

    pub fn deadline_exceeded(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::DeadlineExceeded, code, msg, true)
    }

    pub fn cancelled(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::Cancelled, code, msg, false)
    }

    pub fn unavailable(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::RuntimeUnavailable, code, msg, true)
    }

    pub fn internal(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::InternalError, code, msg, false)
    }

    pub fn shutting_down(code: impl Into<String>, msg: impl Into<String>) -> Self {
        Self::new(ErrorCategory::ShuttingDown, code, msg, false)
    }
}

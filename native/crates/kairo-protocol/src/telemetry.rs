use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Canonical severity classification for native events.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NativeSeverity {
    Debug,
    #[default]
    Info,
    Notice,
    Warning,
    Error,
    Critical,
}

impl NativeSeverity {
    pub fn priority_tier(&self) -> u8 {
        match self {
            Self::Critical => 0,
            Self::Error | Self::Warning => 1,
            Self::Notice | Self::Info => 2,
            Self::Debug => 3,
        }
    }
}

/// Explicit privacy sensitivity classification for native events.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NativePrivacyClass {
    #[default]
    PublicSafe,
    Internal,
    Sensitive,
    Secret,
    Restricted,
}

/// Execution domain originating the event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NativeExecutionDomain {
    #[default]
    Runtime,
    Execution,
    Resource,
    Security,
    Computer,
    Network,
    Tool,
    Health,
}

/// Terminal or observational outcome reported by the event.
/// Observability reports outcomes, but NEVER determines authorization.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NativeOutcome {
    Allow,
    Deny,
    Block,
    Fail,
    Cancel,
    Timeout,
    Success,
    #[default]
    Unknown,
}

/// Strongly typed factual low-level event emitted by native execution substrate.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NativeEvent {
    pub event_id: String,
    pub event_type: String,
    pub monotonic_timestamp_ns: u64,
    pub wall_timestamp_utc: DateTime<Utc>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub correlation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub causation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub trace_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub span_id: Option<String>,
    pub execution_domain: NativeExecutionDomain,
    pub severity: NativeSeverity,
    pub privacy_class: NativePrivacyClass,
    pub outcome: NativeOutcome,
    pub component: String,
    pub payload: serde_json::Value,
}

impl NativeEvent {
    pub fn new(
        event_type: impl Into<String>,
        domain: NativeExecutionDomain,
        severity: NativeSeverity,
        outcome: NativeOutcome,
        component: impl Into<String>,
        payload: serde_json::Value,
    ) -> Self {
        Self {
            event_id: uuid::Uuid::new_v4().to_string(),
            event_type: event_type.into(),
            monotonic_timestamp_ns: 0,
            wall_timestamp_utc: Utc::now(),
            correlation_id: None,
            causation_id: None,
            trace_id: None,
            span_id: None,
            execution_domain: domain,
            severity,
            privacy_class: NativePrivacyClass::Internal,
            outcome,
            component: component.into(),
            payload,
        }
    }

    pub fn with_correlation(
        mut self,
        correlation_id: Option<String>,
        causation_id: Option<String>,
        trace_id: Option<String>,
        span_id: Option<String>,
    ) -> Self {
        self.correlation_id = correlation_id;
        self.causation_id = causation_id;
        self.trace_id = trace_id;
        self.span_id = span_id;
        self
    }

    pub fn with_timestamps(mut self, monotonic_ns: u64, wall_utc: DateTime<Utc>) -> Self {
        self.monotonic_timestamp_ns = monotonic_ns;
        self.wall_timestamp_utc = wall_utc;
        self
    }

    pub fn with_privacy(mut self, privacy_class: NativePrivacyClass) -> Self {
        self.privacy_class = privacy_class;
        self
    }
}

/// Structured span record emitted by native distributed tracer.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NativeSpanRecord {
    pub span_id: String,
    pub trace_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_span_id: Option<String>,
    pub name: String,
    pub start_time_ns: u64,
    pub duration_ns: u64,
    pub status: String,
    #[serde(default)]
    pub attributes: serde_json::Value,
}

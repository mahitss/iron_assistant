use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum HealthState {
    Starting,
    Ready,
    Degraded,
    Draining,
    Stopping,
    Stopped,
    Failed,
}

impl HealthState {
    pub fn is_ready(&self) -> bool {
        matches!(self, HealthState::Ready)
    }

    pub fn accepts_requests(&self) -> bool {
        matches!(self, HealthState::Ready | HealthState::Degraded)
    }

    pub fn is_terminal(&self) -> bool {
        matches!(self, HealthState::Stopped | HealthState::Failed)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeMetadata {
    pub runtime_version: String,
    pub protocol_version: String,
    pub build_id: String,
    pub platform: String,
    pub arch: String,
    pub uptime_seconds: u64,
    pub active_requests: u32,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeHealth {
    pub state: HealthState,
    pub healthy: bool,
    pub message: String,
    pub metadata: RuntimeMetadata,
    pub last_heartbeat: DateTime<Utc>,
}

impl RuntimeHealth {
    pub fn ready(metadata: RuntimeMetadata, msg: impl Into<String>) -> Self {
        Self {
            state: HealthState::Ready,
            healthy: true,
            message: msg.into(),
            metadata,
            last_heartbeat: Utc::now(),
        }
    }

    pub fn degraded(metadata: RuntimeMetadata, msg: impl Into<String>) -> Self {
        Self {
            state: HealthState::Degraded,
            healthy: false,
            message: msg.into(),
            metadata,
            last_heartbeat: Utc::now(),
        }
    }

    pub fn draining(metadata: RuntimeMetadata, msg: impl Into<String>) -> Self {
        Self {
            state: HealthState::Draining,
            healthy: false,
            message: msg.into(),
            metadata,
            last_heartbeat: Utc::now(),
        }
    }

    pub fn stopped(metadata: RuntimeMetadata, msg: impl Into<String>) -> Self {
        Self {
            state: HealthState::Stopped,
            healthy: false,
            message: msg.into(),
            metadata,
            last_heartbeat: Utc::now(),
        }
    }

    pub fn failed(metadata: RuntimeMetadata, msg: impl Into<String>) -> Self {
        Self {
            state: HealthState::Failed,
            healthy: false,
            message: msg.into(),
            metadata,
            last_heartbeat: Utc::now(),
        }
    }
}

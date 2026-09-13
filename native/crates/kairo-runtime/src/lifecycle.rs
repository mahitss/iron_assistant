use kairo_protocol::{HealthState, RuntimeHealth, RuntimeMetadata, CURRENT_PROTOCOL_VERSION};
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::RwLock;

pub const RUNTIME_VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Debug)]
pub struct LifecycleManager {
    state: RwLock<HealthState>,
    start_time: Instant,
    active_requests: Arc<AtomicU32>,
    capabilities: RwLock<Vec<String>>,
}

impl LifecycleManager {
    pub fn new(active_requests: Arc<AtomicU32>) -> Arc<Self> {
        Arc::new(Self {
            state: RwLock::new(HealthState::Starting),
            start_time: Instant::now(),
            active_requests,
            capabilities: RwLock::new(Vec::new()),
        })
    }

    pub async fn set_capabilities(&self, caps: Vec<String>) {
        let mut w = self.capabilities.write().await;
        *w = caps;
    }

    pub async fn get_state(&self) -> HealthState {
        *self.state.read().await
    }

    pub async fn set_ready(&self) {
        let mut state = self.state.write().await;
        if *state == HealthState::Starting || *state == HealthState::Degraded {
            *state = HealthState::Ready;
            tracing::info!("Runtime lifecycle transitioned to READY");
        }
    }

    pub async fn set_degraded(&self, reason: &str) {
        let mut state = self.state.write().await;
        if *state == HealthState::Ready {
            *state = HealthState::Degraded;
            tracing::warn!("Runtime lifecycle transitioned to DEGRADED: {}", reason);
        }
    }

    pub async fn drain(&self) {
        let mut state = self.state.write().await;
        *state = HealthState::Draining;
        tracing::info!("Runtime lifecycle transitioned to DRAINING (rejecting new requests)");
    }

    pub async fn stop(&self) {
        let mut state = self.state.write().await;
        *state = HealthState::Stopped;
        tracing::info!("Runtime lifecycle transitioned to STOPPED");
    }

    pub async fn fail(&self, reason: &str) {
        let mut state = self.state.write().await;
        *state = HealthState::Failed;
        tracing::error!("Runtime lifecycle transitioned to FAILED: {}", reason);
    }

    pub async fn metadata(&self) -> RuntimeMetadata {
        let caps = self.capabilities.read().await.clone();
        RuntimeMetadata {
            runtime_version: RUNTIME_VERSION.to_string(),
            protocol_version: CURRENT_PROTOCOL_VERSION.to_string(),
            build_id: option_env!("BUILD_ID").unwrap_or("local-dev").to_string(),
            platform: std::env::consts::OS.to_string(),
            arch: std::env::consts::ARCH.to_string(),
            uptime_seconds: self.start_time.elapsed().as_secs(),
            active_requests: self.active_requests.load(Ordering::Relaxed),
            capabilities: caps,
        }
    }

    pub async fn health(&self) -> RuntimeHealth {
        let state = *self.state.read().await;
        let meta = self.metadata().await;
        match state {
            HealthState::Ready => RuntimeHealth::ready(meta, "Native runtime is operational"),
            HealthState::Starting => RuntimeHealth::ready(meta, "Native runtime is initializing"),
            HealthState::Degraded => {
                RuntimeHealth::degraded(meta, "Native runtime is in degraded state")
            }
            HealthState::Draining => {
                RuntimeHealth::draining(meta, "Native runtime is draining in-flight work")
            }
            HealthState::Stopping => RuntimeHealth::draining(meta, "Native runtime is stopping"),
            HealthState::Stopped => RuntimeHealth::stopped(meta, "Native runtime is stopped"),
            HealthState::Failed => {
                RuntimeHealth::failed(meta, "Native runtime encountered critical failure")
            }
        }
    }
}

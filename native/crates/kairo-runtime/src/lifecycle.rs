use chrono::{DateTime, Utc};
use kairo_protocol::{
    CapabilityDescriptor, HealthState, RuntimeHealth, RuntimeMetadata, RuntimeState,
    CURRENT_PROTOCOL_VERSION,
};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::RwLock;

pub const RUNTIME_VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Debug)]
pub struct LifecycleManager {
    state: RwLock<HealthState>,
    runtime_state: RwLock<RuntimeState>,
    runtime_instance_id: String,
    session_id: RwLock<Option<String>>,
    startup_timestamp: DateTime<Utc>,
    start_time: Instant,
    active_requests: Arc<AtomicU32>,
    capabilities: RwLock<Vec<String>>,
    capability_fingerprint: RwLock<String>,
    configuration_fingerprint: RwLock<String>,
}

impl LifecycleManager {
    pub fn new(active_requests: Arc<AtomicU32>) -> Arc<Self> {
        let instance_id = format!("rt_inst_{}", uuid::Uuid::new_v4().simple());
        let now = Utc::now();
        Arc::new(Self {
            state: RwLock::new(HealthState::Starting),
            runtime_state: RwLock::new(RuntimeState::Starting),
            runtime_instance_id: instance_id,
            session_id: RwLock::new(None),
            startup_timestamp: now,
            start_time: Instant::now(),
            active_requests,
            capabilities: RwLock::new(Vec::new()),
            capability_fingerprint: RwLock::new("cfp_default".to_string()),
            configuration_fingerprint: RwLock::new("cfg_default".to_string()),
        })
    }

    pub fn runtime_instance_id(&self) -> &str {
        &self.runtime_instance_id
    }

    pub fn startup_timestamp(&self) -> DateTime<Utc> {
        self.startup_timestamp
    }

    pub async fn get_session_id(&self) -> Option<String> {
        self.session_id.read().await.clone()
    }

    pub async fn create_session(&self, _client_instance_id: &str) -> String {
        let sid = format!("sess_{}", uuid::Uuid::new_v4().simple());
        let mut w = self.session_id.write().await;
        *w = Some(sid.clone());
        sid
    }

    pub async fn invalidate_session(&self) {
        let mut w = self.session_id.write().await;
        *w = None;
    }

    pub async fn capability_fingerprint(&self) -> String {
        self.capability_fingerprint.read().await.clone()
    }

    pub async fn configuration_fingerprint(&self) -> String {
        self.configuration_fingerprint.read().await.clone()
    }

    pub async fn set_capabilities_and_fingerprints(
        &self,
        caps: &[CapabilityDescriptor],
        config_summary: &str,
    ) {
        let mut cap_names = Vec::new();
        let mut hasher = DefaultHasher::new();
        for c in caps {
            cap_names.push(c.capability_id.clone());
            c.capability_id.hash(&mut hasher);
            c.version.hash(&mut hasher);
            format!("{:?}", c.enforcement_level).hash(&mut hasher);
        }
        let cap_hash = format!("cfp_{:016x}", hasher.finish());

        let mut cfg_hasher = DefaultHasher::new();
        config_summary.hash(&mut cfg_hasher);
        std::env::consts::OS.hash(&mut cfg_hasher);
        RUNTIME_VERSION.hash(&mut cfg_hasher);
        let cfg_hash = format!("cfg_{:016x}", cfg_hasher.finish());

        let mut w_caps = self.capabilities.write().await;
        *w_caps = cap_names;
        let mut w_cfp = self.capability_fingerprint.write().await;
        *w_cfp = cap_hash;
        let mut w_cfg = self.configuration_fingerprint.write().await;
        *w_cfg = cfg_hash;
    }

    pub async fn set_capabilities(&self, caps: Vec<String>) {
        let mut w = self.capabilities.write().await;
        *w = caps;
    }

    pub async fn get_state(&self) -> HealthState {
        *self.state.read().await
    }

    pub async fn get_runtime_state(&self) -> RuntimeState {
        *self.runtime_state.read().await
    }

    pub async fn transition_runtime_state(&self, next: RuntimeState) -> Result<(), String> {
        let mut curr = self.runtime_state.write().await;
        if curr.can_transition_to(next) {
            *curr = next;
            // Also synchronize HealthState
            let mut hs = self.state.write().await;
            *hs = match next {
                RuntimeState::Ready => HealthState::Ready,
                RuntimeState::Degraded => HealthState::Degraded,
                RuntimeState::Draining => HealthState::Draining,
                RuntimeState::Stopping => HealthState::Stopping,
                RuntimeState::Stopped => HealthState::Stopped,
                RuntimeState::Failed | RuntimeState::Unauthorized | RuntimeState::Incompatible => {
                    HealthState::Failed
                }
                _ => HealthState::Starting,
            };
            tracing::info!("RuntimeState successfully transitioned to {:?}", next);
            Ok(())
        } else {
            let err = format!(
                "Invalid runtime state transition from {:?} to {:?}",
                *curr, next
            );
            tracing::warn!("{}", err);
            Err(err)
        }
    }

    pub async fn set_ready(&self) {
        let _ = self.transition_runtime_state(RuntimeState::Ready).await;
    }

    pub async fn set_degraded(&self, reason: &str) {
        tracing::warn!("Runtime lifecycle transitioned to DEGRADED: {}", reason);
        let _ = self.transition_runtime_state(RuntimeState::Degraded).await;
    }

    pub async fn drain(&self) {
        tracing::info!("Runtime lifecycle transitioned to DRAINING (rejecting new requests)");
        let _ = self.transition_runtime_state(RuntimeState::Draining).await;
    }

    pub async fn stop(&self) {
        tracing::info!("Runtime lifecycle transitioned to STOPPED");
        let _ = self.transition_runtime_state(RuntimeState::Stopped).await;
        self.invalidate_session().await;
    }

    pub async fn fail(&self, reason: &str) {
        tracing::error!("Runtime lifecycle transitioned to FAILED: {}", reason);
        let _ = self.transition_runtime_state(RuntimeState::Failed).await;
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

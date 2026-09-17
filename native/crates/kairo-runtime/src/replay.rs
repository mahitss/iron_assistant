use chrono::Utc;
use kairo_protocol::{
    MessageLifecycleState, ResponseStatus, RuntimeError, RuntimeRequest, RuntimeResponse,
};
use std::collections::{HashMap, VecDeque};
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone)]
pub struct CachedExecution {
    pub request_id: String,
    pub session_id: String,
    pub state: MessageLifecycleState,
    pub is_idempotent: bool,
    pub response: Option<RuntimeResponse>,
    pub timestamp_utc: chrono::DateTime<Utc>,
}

#[derive(Debug)]
pub enum ReplayDecision {
    Proceed,
    AlreadyInFlight,
    Cached(Box<RuntimeResponse>),
}

/// Thread-safe, bounded replay and duplicate execution guard.
pub struct ReplayGuard {
    capacity: usize,
    entries: RwLock<HashMap<String, CachedExecution>>,
    order: RwLock<VecDeque<String>>,
}

impl ReplayGuard {
    pub fn new(capacity: usize) -> Arc<Self> {
        Arc::new(Self {
            capacity,
            entries: RwLock::new(HashMap::with_capacity(capacity)),
            order: RwLock::new(VecDeque::with_capacity(capacity)),
        })
    }

    /// Check a request against session, expiration, replay, and duplicate states.
    pub async fn check_and_register(
        &self,
        req: &RuntimeRequest,
        current_session_id: &str,
    ) -> Result<ReplayDecision, RuntimeError> {
        let now = Utc::now();

        // 1. Session validation (if session_id is present on request)
        if let Some(ref sid) = req.session_id {
            if sid != current_session_id {
                return Err(RuntimeError::session_invalid(
                    "SESSION_INVALID",
                    format!(
                        "Request session '{}' does not match active runtime session '{}'",
                        sid, current_session_id
                    ),
                ));
            }
        }

        // 2. Absolute deadline expiration
        if let Some(deadline) = req.deadline {
            if now > deadline {
                return Err(RuntimeError::request_expired(
                    "REQUEST_DEADLINE_EXPIRED",
                    format!(
                        "Request deadline '{}' expired at current time '{}'",
                        deadline, now
                    ),
                ));
            }
        }

        // 3. Stale request age (freshness / nonce protection)
        if let Some(created_at) = req.created_at {
            let age_sec = (now - created_at).num_seconds();
            if age_sec > 300 {
                return Err(RuntimeError::request_expired(
                    "REQUEST_TIMESTAMP_STALE",
                    format!(
                        "Request created_at '{}' is older than 300 seconds (age: {}s)",
                        created_at, age_sec
                    ),
                ));
            }
        }

        // 4. Duplicate and replay detection
        let mut entries = self.entries.write().await;
        if let Some(existing) = entries.get(&req.request_id) {
            // Already running
            if !existing.state.is_terminal() {
                return Ok(ReplayDecision::AlreadyInFlight);
            }

            // Already completed
            if existing.state == MessageLifecycleState::Completed {
                // Safe read or explicitly idempotent
                if existing.is_idempotent || req.idempotency_key.is_some() {
                    if let Some(ref cached_resp) = existing.response {
                        return Ok(ReplayDecision::Cached(Box::new(cached_resp.clone())));
                    }
                }
                // Non-idempotent operation replayed: REJECT
                return Err(RuntimeError::request_duplicate(
                    "DUPLICATE_EXECUTION_BLOCKED",
                    format!(
                        "Non-idempotent request '{}' was already completed. Replay rejected.",
                        req.request_id
                    ),
                ));
            }

            // Already failed or cancelled
            if let Some(ref cached_resp) = existing.response {
                return Ok(ReplayDecision::Cached(Box::new(cached_resp.clone())));
            } else {
                return Err(RuntimeError::request_duplicate(
                    "REQUEST_ALREADY_TERMINATED",
                    format!(
                        "Request '{}' already terminated with state {:?}",
                        req.request_id, existing.state
                    ),
                ));
            }
        }

        // Register fresh in-flight execution
        let is_idempotent = req.idempotency_key.is_some()
            || req.operation.starts_with("sys.info")
            || req.operation.starts_with("sys.health")
            || req.operation.starts_with("sys.ping");
        let new_entry = CachedExecution {
            request_id: req.request_id.clone(),
            session_id: current_session_id.to_string(),
            state: MessageLifecycleState::Running,
            is_idempotent,
            response: None,
            timestamp_utc: now,
        };

        // Bounded capacity check
        let mut order = self.order.write().await;
        if order.len() >= self.capacity {
            if let Some(evicted_id) = order.pop_front() {
                entries.remove(&evicted_id);
            }
        }

        order.push_back(req.request_id.clone());
        entries.insert(req.request_id.clone(), new_entry);

        Ok(ReplayDecision::Proceed)
    }

    /// Record terminal completion outcome and cached response.
    pub async fn record_completion(
        &self,
        request_id: &str,
        session_id: &str,
        resp: &RuntimeResponse,
        is_idempotent: bool,
    ) {
        let state = match resp.status {
            ResponseStatus::Ok => MessageLifecycleState::Completed,
            ResponseStatus::Cancelled => MessageLifecycleState::Cancelled,
            ResponseStatus::ShuttingDown => MessageLifecycleState::EmergencyStopped,
            ResponseStatus::EmergencyStopped => MessageLifecycleState::EmergencyStopped,
            ResponseStatus::UnknownOutcome => MessageLifecycleState::UnknownOutcome,
            ResponseStatus::Error => {
                if let Some(ref err) = resp.error {
                    match err.category {
                        kairo_protocol::ErrorCategory::DeadlineExceeded => {
                            MessageLifecycleState::TimedOut
                        }
                        kairo_protocol::ErrorCategory::ResourceLimit => {
                            MessageLifecycleState::ResourceExceeded
                        }
                        kairo_protocol::ErrorCategory::UnknownOutcome => {
                            MessageLifecycleState::UnknownOutcome
                        }
                        kairo_protocol::ErrorCategory::EmergencyStopped => {
                            MessageLifecycleState::EmergencyStopped
                        }
                        _ => MessageLifecycleState::Failed,
                    }
                } else {
                    MessageLifecycleState::Failed
                }
            }
        };

        let mut entries = self.entries.write().await;
        if let Some(entry) = entries.get_mut(request_id) {
            entry.state = state;
            entry.is_idempotent = is_idempotent;
            entry.response = Some(resp.clone());
        } else {
            let mut order = self.order.write().await;
            if order.len() >= self.capacity {
                if let Some(evicted_id) = order.pop_front() {
                    entries.remove(&evicted_id);
                }
            }
            order.push_back(request_id.to_string());
            entries.insert(
                request_id.to_string(),
                CachedExecution {
                    request_id: request_id.to_string(),
                    session_id: session_id.to_string(),
                    state,
                    is_idempotent,
                    response: Some(resp.clone()),
                    timestamp_utc: Utc::now(),
                },
            );
        }
    }

    
    pub async fn clear(&self) {
        let mut entries = self.entries.write().await;
        let mut order = self.order.write().await;
        entries.clear();
        order.clear();
    }
}

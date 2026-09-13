use crate::cancellation::CancellationRegistry;
use crate::capabilities::CapabilityRegistry;
use crate::lifecycle::LifecycleManager;
use crate::metrics::RuntimeMetrics;
use crate::supervisor::run_with_panic_containment;
use kairo_protocol::{RuntimeError, RuntimeRequest, RuntimeResponse, TimingMetadata};
use serde_json::json;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::time::timeout;

pub struct RequestDispatcher {
    lifecycle: Arc<LifecycleManager>,
    capabilities: Arc<CapabilityRegistry>,
    cancellation: Arc<CancellationRegistry>,
    metrics: Arc<RuntimeMetrics>,
}

impl RequestDispatcher {
    pub fn new(
        lifecycle: Arc<LifecycleManager>,
        capabilities: Arc<CapabilityRegistry>,
        cancellation: Arc<CancellationRegistry>,
        metrics: Arc<RuntimeMetrics>,
    ) -> Self {
        Self {
            lifecycle,
            capabilities,
            cancellation,
            metrics,
        }
    }

    pub async fn dispatch(&self, req: RuntimeRequest) -> RuntimeResponse {
        let start_time = Instant::now();
        let request_id = req.request_id.clone();
        let correlation_id = req.correlation_id.clone();

        self.metrics.record_request_start();

        let req_cloned = req.clone();
        let this = self.clone();

        let res = run_with_panic_containment(&request_id, || async move {
            this.execute_inner(req_cloned, start_time).await
        })
        .await;

        let total_ms = start_time.elapsed().as_millis() as u64;
        self.metrics.record_request_end(total_ms);

        let mut final_response = match res {
            Ok(resp) => resp,
            Err(err) => {
                self.metrics.record_failure();
                let timing = TimingMetadata {
                    queue_time_ms: 0,
                    execution_time_ms: total_ms,
                    total_time_ms: total_ms,
                };
                RuntimeResponse::error(&request_id, err, Some(timing))
            }
        };

        final_response = final_response.with_correlation(correlation_id);
        final_response
    }

    async fn execute_inner(&self, req: RuntimeRequest, start_time: Instant) -> RuntimeResponse {
        let request_id = req.request_id.clone();

        // 1. Envelope validation
        if let Err(err) = req.validate() {
            self.metrics.record_failure();
            return RuntimeResponse::error(&request_id, err, None);
        }

        // 2. Lifecycle state check
        let state = self.lifecycle.get_state().await;
        if !state.accepts_requests() {
            self.metrics.record_failure();
            return RuntimeResponse::error(
                &request_id,
                RuntimeError::shutting_down(
                    "RUNTIME_NOT_ACCEPTING_REQUESTS",
                    format!("Runtime is currently in {:?} state", state),
                ),
                None,
            );
        }

        // 3. Fast path: sys.cancel operation
        if req.operation == "sys.cancel" {
            let target_id = req
                .payload
                .get("cancellation_id")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if target_id.is_empty() {
                return RuntimeResponse::error(
                    &request_id,
                    RuntimeError::invalid_request(
                        "MISSING_CANCELLATION_ID",
                        "sys.cancel requires payload.cancellation_id",
                    ),
                    None,
                );
            }
            let cancelled = self.cancellation.cancel(target_id).await;
            let exec_ms = start_time.elapsed().as_millis() as u64;
            let timing = TimingMetadata {
                queue_time_ms: 0,
                execution_time_ms: exec_ms,
                total_time_ms: exec_ms,
            };
            return RuntimeResponse::ok(
                &request_id,
                json!({
                    "cancellation_id": target_id,
                    "found_and_cancelled": cancelled
                }),
                timing,
            );
        }

        // 4. Capability verification
        let cap_opt = self.capabilities.get(&req.operation);
        if cap_opt.is_none() {
            self.metrics.record_failure();
            return RuntimeResponse::error(
                &request_id,
                RuntimeError::unsupported_operation(
                    "UNKNOWN_CAPABILITY",
                    format!(
                        "No native capability registered for operation '{}'",
                        req.operation
                    ),
                ),
                None,
            );
        }

        // 5. Cancellation Token setup
        let cancel_id = req
            .cancellation_id
            .clone()
            .unwrap_or_else(|| request_id.clone());
        let cancel_token = self.cancellation.register(&cancel_id).await;

        // 6. Deadline configuration
        let deadline_ms = req.deadline_ms.unwrap_or(30_000);
        let exec_future = self.route_operation(&req);

        // 7. Execution with cancellation and deadline racing
        tokio::select! {
            _ = cancel_token.cancelled() => {
                self.metrics.record_cancellation();
                self.cancellation.remove(&cancel_id).await;
                let exec_ms = start_time.elapsed().as_millis() as u64;
                let timing = TimingMetadata {
                    queue_time_ms: 0,
                    execution_time_ms: exec_ms,
                    total_time_ms: exec_ms,
                };
                RuntimeResponse::cancelled(&request_id, "Operation cancelled by caller", Some(timing))
            }
            res = timeout(Duration::from_millis(deadline_ms), exec_future) => {
                self.cancellation.remove(&cancel_id).await;
                let exec_ms = start_time.elapsed().as_millis() as u64;
                let timing = TimingMetadata {
                    queue_time_ms: 0,
                    execution_time_ms: exec_ms,
                    total_time_ms: exec_ms,
                };

                match res {
                    Ok(Ok(result_val)) => {
                        let meta = self.lifecycle.metadata().await;
                        RuntimeResponse::ok(&request_id, result_val, timing).with_metadata(meta)
                    }
                    Ok(Err(err)) => {
                        self.metrics.record_failure();
                        RuntimeResponse::error(&request_id, err, Some(timing))
                    }
                    Err(_) => {
                        self.metrics.record_deadline_exceeded();
                        RuntimeResponse::error(
                            &request_id,
                            RuntimeError::deadline_exceeded(
                                "EXECUTION_DEADLINE_EXCEEDED",
                                format!("Operation '{}' exceeded deadline of {}ms", req.operation, deadline_ms),
                            ),
                            Some(timing),
                        )
                    }
                }
            }
        }
    }

    async fn route_operation(
        &self,
        req: &RuntimeRequest,
    ) -> Result<serde_json::Value, RuntimeError> {
        match req.operation.as_str() {
            "sys.ping" => {
                let echo = req.payload.clone();
                Ok(json!({
                    "reply": "pong",
                    "echo": echo,
                    "server_time": chrono::Utc::now()
                }))
            }
            "sys.health" => {
                let health = self.lifecycle.health().await;
                Ok(serde_json::to_value(health).unwrap_or(json!({"status": "unknown"})))
            }
            "sys.info" => {
                let metadata = self.lifecycle.metadata().await;
                Ok(serde_json::to_value(metadata).unwrap_or(json!({"status": "unknown"})))
            }
            "sys.metrics" => {
                let snapshot = self.metrics.snapshot();
                Ok(serde_json::to_value(snapshot).unwrap_or(json!({"metrics": "error"})))
            }
            "sys.sleep" => {
                let duration_ms = req
                    .payload
                    .get("duration_ms")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(500);

                // Enforce budget limit on duration
                let max_duration = req
                    .resource_budget
                    .as_ref()
                    .and_then(|b| b.max_execution_time_ms)
                    .unwrap_or(30_000);

                let actual_ms = duration_ms.min(max_duration);
                tokio::time::sleep(Duration::from_millis(actual_ms)).await;

                Ok(json!({
                    "slept_ms": actual_ms,
                    "requested_ms": duration_ms
                }))
            }
            _ => Err(RuntimeError::unsupported_operation(
                "UNSUPPORTED_OPERATION",
                format!("Native operation '{}' is not supported", req.operation),
            )),
        }
    }
}

impl Clone for RequestDispatcher {
    fn clone(&self) -> Self {
        Self {
            lifecycle: self.lifecycle.clone(),
            capabilities: self.capabilities.clone(),
            cancellation: self.cancellation.clone(),
            metrics: self.metrics.clone(),
        }
    }
}

use crate::cancellation::CancellationRegistry;
use crate::capabilities::CapabilityRegistry;
use crate::lifecycle::{LifecycleManager, RUNTIME_VERSION};
use crate::metrics::RuntimeMetrics;
use crate::replay::{ReplayDecision, ReplayGuard};
use crate::sandbox::{SandboxCapabilityRegistry, SandboxExecutor};
use crate::supervisor::run_with_panic_containment;
use crate::telemetry::{NativeEventBuffer, NativeTracer};
use kairo_protocol::contract::NativeRuntimeSnapshot;
use kairo_protocol::telemetry::{
    NativeEvent, NativeExecutionDomain, NativeOutcome, NativeSeverity,
};
use kairo_protocol::{
    RuntimeError, RuntimeRequest, RuntimeResponse, TimingMetadata, CURRENT_PROTOCOL_VERSION,
};
use serde_json::json;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::time::timeout;

pub struct RequestDispatcher {
    lifecycle: Arc<LifecycleManager>,
    capabilities: Arc<CapabilityRegistry>,
    cancellation: Arc<CancellationRegistry>,
    metrics: Arc<RuntimeMetrics>,
    sandbox: Arc<SandboxExecutor>,
    event_buffer: Arc<NativeEventBuffer>,
    tracer: Arc<NativeTracer>,
    replay_guard: Arc<ReplayGuard>,
}

impl RequestDispatcher {
    pub fn new(
        lifecycle: Arc<LifecycleManager>,
        capabilities: Arc<CapabilityRegistry>,
        cancellation: Arc<CancellationRegistry>,
        metrics: Arc<RuntimeMetrics>,
    ) -> Self {
        let sandbox_caps = Arc::new(SandboxCapabilityRegistry::new());
        let sandbox = Arc::new(SandboxExecutor::new(
            sandbox_caps,
            cancellation.clone(),
            metrics.clone(),
            8,
        ));
        let event_buffer = Arc::new(NativeEventBuffer::default());
        let tracer = NativeTracer::new();
        let replay_guard = ReplayGuard::new(5000);

        Self {
            lifecycle,
            capabilities,
            cancellation,
            metrics,
            sandbox,
            event_buffer,
            tracer,
            replay_guard,
        }
    }

    pub fn with_telemetry(
        lifecycle: Arc<LifecycleManager>,
        capabilities: Arc<CapabilityRegistry>,
        cancellation: Arc<CancellationRegistry>,
        metrics: Arc<RuntimeMetrics>,
        event_buffer: Arc<NativeEventBuffer>,
        tracer: Arc<NativeTracer>,
    ) -> Self {
        let sandbox_caps = Arc::new(SandboxCapabilityRegistry::new());
        let sandbox = Arc::new(SandboxExecutor::new(
            sandbox_caps,
            cancellation.clone(),
            metrics.clone(),
            8,
        ));
        let replay_guard = ReplayGuard::new(5000);

        Self {
            lifecycle,
            capabilities,
            cancellation,
            metrics,
            sandbox,
            event_buffer,
            tracer,
            replay_guard,
        }
    }

    pub fn event_buffer(&self) -> Arc<NativeEventBuffer> {
        self.event_buffer.clone()
    }

    pub fn tracer(&self) -> Arc<NativeTracer> {
        self.tracer.clone()
    }

    pub fn replay_guard(&self) -> Arc<ReplayGuard> {
        self.replay_guard.clone()
    }

    pub async fn dispatch(&self, req: RuntimeRequest) -> RuntimeResponse {
        let start_time = Instant::now();
        let request_id = req.request_id.clone();
        let correlation_id = req.correlation_id.clone();
        let trace_id = req.trace_id.clone();
        let span_id = req.span_id.clone();
        let causation_id = req.causation_id.clone();

        let current_session = self.lifecycle.get_session_id().await.unwrap_or_default();

        // Check replay guard and duplicate detector
        match self
            .replay_guard
            .check_and_register(&req, &current_session)
            .await
        {
            Ok(ReplayDecision::Proceed) => {}
            Ok(ReplayDecision::AlreadyInFlight) => {
                return RuntimeResponse::error(
                    &request_id,
                    RuntimeError::invalid_request(
                        "ALREADY_IN_FLIGHT",
                        "Request is currently in flight",
                    ),
                    None,
                );
            }
            Ok(ReplayDecision::Cached(cached_resp)) => {
                return *cached_resp;
            }
            Err(err) => {
                self.metrics.record_failure();
                return RuntimeResponse::error(&request_id, err, None);
            }
        }

        self.metrics.record_request_start();

        // Native span tracking
        let active_trace_id = trace_id
            .clone()
            .unwrap_or_else(|| format!("trc_{}", uuid::Uuid::new_v4().simple()));
        let native_span_id = self.tracer.start_span(
            &active_trace_id,
            span_id.clone(),
            &req.operation,
            json!({
                "request_id": &request_id,
                "correlation_id": &correlation_id,
            }),
        );

        // Record factual incoming event
        let recv_ev = NativeEvent::new(
            "runtime.request.received",
            NativeExecutionDomain::Runtime,
            NativeSeverity::Info,
            NativeOutcome::Success,
            "dispatcher",
            json!({
                "request_id": &request_id,
                "operation": &req.operation,
            }),
        )
        .with_correlation(
            correlation_id.clone(),
            causation_id.clone(),
            Some(active_trace_id.clone()),
            Some(native_span_id.clone()),
        );
        self.event_buffer.record(recv_ev);
        self.metrics.record_native_event_emitted();

        let req_cloned = req.clone();
        let this = self.clone();

        let res = run_with_panic_containment(&request_id, || async move {
            this.execute_inner(req_cloned, start_time).await
        })
        .await;

        let total_ms = start_time.elapsed().as_millis() as u64;
        self.metrics.record_request_end(total_ms);

        let outcome_str = match &res {
            Ok(resp) if resp.status == kairo_protocol::envelope::ResponseStatus::Ok => "OK",
            Ok(resp) if resp.status == kairo_protocol::envelope::ResponseStatus::Cancelled => {
                "CANCELLED"
            }
            _ => "ERROR",
        };
        self.tracer.end_span(&native_span_id, outcome_str);

        // Record factual completion event
        let comp_ev = NativeEvent::new(
            if outcome_str == "OK" {
                "runtime.request.completed"
            } else {
                "runtime.request.failed"
            },
            NativeExecutionDomain::Runtime,
            if outcome_str == "OK" {
                NativeSeverity::Info
            } else {
                NativeSeverity::Error
            },
            if outcome_str == "OK" {
                NativeOutcome::Success
            } else {
                NativeOutcome::Fail
            },
            "dispatcher",
            json!({
                "request_id": &request_id,
                "operation": &req.operation,
                "duration_ms": total_ms,
                "outcome": outcome_str,
            }),
        )
        .with_correlation(
            correlation_id.clone(),
            causation_id.clone(),
            Some(active_trace_id.clone()),
            Some(native_span_id.clone()),
        );
        self.event_buffer.record(comp_ev);
        self.metrics.record_native_event_emitted();

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

        // Drain correlation events if correlation_id is present
        let related_events = if let Some(ref cid) = correlation_id {
            let drained = self.event_buffer.drain_for_correlation(cid);
            if !drained.is_empty() {
                Some(drained)
            } else {
                None
            }
        } else {
            None
        };

        final_response = final_response.with_telemetry(
            correlation_id,
            Some(active_trace_id),
            Some(native_span_id),
            causation_id,
            related_events,
        );

        let is_idempotent = req.idempotency_key.is_some()
            || req.operation.starts_with("sys.info")
            || req.operation.starts_with("sys.health")
            || req.operation.starts_with("sys.ping")
            || req.operation.starts_with("sys.capabilities")
            || req.operation.starts_with("sys.contract")
            || req.operation.starts_with("sys.snapshot")
            || req.operation.starts_with("sys.twin");

        self.replay_guard
            .record_completion(
                &request_id,
                &current_session,
                &final_response,
                is_idempotent,
            )
            .await;

        final_response = final_response.with_session(
            Some(self.lifecycle.runtime_instance_id().to_string()),
            self.lifecycle.get_session_id().await,
        );

        final_response
    }

    async fn execute_inner(&self, req: RuntimeRequest, start_time: Instant) -> RuntimeResponse {
        let request_id = req.request_id.clone();
        tracing::info!(op = %req.operation, req_id = %request_id, "Dispatcher executing request");

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

        // 2b. Simulation Firewall Enforcement:
        // Simulated operations MUST NEVER execute live mutating side effects.
        if let Some(ref sim_ctx) = req.simulation_context {
            if sim_ctx.is_simulation && !sim_ctx.allows_mutation() {
                let is_mutating = req.operation == "sys.stop"
                    || req.operation == "sys.emergency_stop"
                    || req.operation.starts_with("native.input")
                    || req.operation == "native.clipboard.write"
                    || req.operation == "native.net.request"
                    || req.operation == "native.net.fetch"
                    || req.operation == "sandbox.execute";
                if is_mutating {
                    tracing::warn!(
                        op = %req.operation,
                        sim_id = %sim_ctx.simulation_id,
                        "Simulation Firewall BLOCKED live mutating operation"
                    );
                    self.metrics.record_failure();
                    return RuntimeResponse::error(
                        &request_id,
                        RuntimeError::simulation_mutation_blocked(
                            "SIMULATION_MUTATION_BLOCKED",
                            format!(
                                "Simulation '{}' blocked from executing mutating capability '{}'",
                                sim_ctx.simulation_id, req.operation
                            ),
                        ),
                        None,
                    );
                }
            }
        }

        // 3. Fast path: sys.stop / sys.emergency_stop (Emergency Stop Contract)
        if req.operation == "sys.stop" || req.operation == "sys.emergency_stop" {
            tracing::warn!(req_id = %request_id, "Emergency stop signal received by dispatcher!");
            let _ = self.lifecycle.drain().await;
            let cancelled = self.cancellation.cancel_all().await;
            let exec_ms = start_time.elapsed().as_millis() as u64;
            let timing = TimingMetadata {
                queue_time_ms: 0,
                execution_time_ms: exec_ms,
                total_time_ms: exec_ms,
            };
            return RuntimeResponse::ok(
                &request_id,
                json!({
                    "status": "EMERGENCY_STOPPED",
                    "cancelled_tasks": cancelled,
                    "runtime_state": "DRAINING"
                }),
                timing,
            );
        }

        // 4. Fast path: sys.cancel operation
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

        // 5. Fast path: sys.capabilities
        if req.operation == "sys.capabilities" {
            let caps = self.capabilities.list();
            let exec_ms = start_time.elapsed().as_millis() as u64;
            let timing = TimingMetadata {
                queue_time_ms: 0,
                execution_time_ms: exec_ms,
                total_time_ms: exec_ms,
            };
            return RuntimeResponse::ok(
                &request_id,
                serde_json::to_value(caps).unwrap_or_default(),
                timing,
            );
        }

        // 6. Fast path: sys.contract / obs.contract
        if req.operation == "sys.contract" || req.operation == "obs.contract" {
            let metadata = self.lifecycle.metadata().await;
            let contract_info = json!({
                "protocol_version": CURRENT_PROTOCOL_VERSION,
                "runtime_version": RUNTIME_VERSION,
                "runtime_instance_id": self.lifecycle.runtime_instance_id(),
                "session_id": self.lifecycle.get_session_id().await,
                "runtime_state": format!("{:?}", self.lifecycle.get_runtime_state().await),
                "capability_fingerprint": self.lifecycle.capability_fingerprint().await,
                "configuration_fingerprint": self.lifecycle.configuration_fingerprint().await,
                "active_requests": metadata.active_requests,
                "uptime_seconds": metadata.uptime_seconds,
            });
            let exec_ms = start_time.elapsed().as_millis() as u64;
            let timing = TimingMetadata {
                queue_time_ms: 0,
                execution_time_ms: exec_ms,
                total_time_ms: exec_ms,
            };
            return RuntimeResponse::ok(&request_id, contract_info, timing);
        }

        // 7. Authorization Context & Approval Binding verification
        if let Some(ref authz) = req.authorization_context {
            if authz.is_expired(chrono::Utc::now()) {
                return RuntimeResponse::error(
                    &request_id,
                    RuntimeError::authz_required(
                        "AUTHORIZATION_EXPIRED",
                        "Provided authorization context has expired",
                    ),
                    None,
                );
            }
            let target_ident = req
                .target_context
                .as_ref()
                .map(|t| t.target_identifier.as_str());
            if !authz.validates_binding(&req.operation, target_ident) {
                return RuntimeResponse::error(
                    &request_id,
                    RuntimeError::authz_required(
                        "APPROVAL_INVALID",
                        "Approval binding does not match requested capability or target",
                    ),
                    None,
                );
            }
        }

        // 8. Resource Context Binding verification
        if let Some(ref res_ctx) = req.resource_context {
            if res_ctx.is_expired(chrono::Utc::now()) {
                return RuntimeResponse::error(
                    &request_id,
                    RuntimeError::resource_limit(
                        "RESOURCE_EXPIRED",
                        "Bound resource allocation context has expired",
                    ),
                    None,
                );
            }
            if !res_ctx.matches_request(&req.request_id, &req.operation) {
                return RuntimeResponse::error(
                    &request_id,
                    RuntimeError::resource_limit(
                        "RESOURCE_INVALID",
                        "Resource allocation does not match request_id and capability",
                    ),
                    None,
                );
            }
        }

        // 9. Target Revalidation (Anti-TOCTOU)
        if let Some(ref target) = req.target_context {
            if let Some(ref expected_hash) = target.expected_hash {
                let actual_hash = req
                    .payload
                    .get("target_hash")
                    .or_else(|| req.payload.get("current_hash"))
                    .and_then(|h| h.as_str());
                if let Some(actual) = actual_hash {
                    if actual != expected_hash {
                        return RuntimeResponse::error(
                            &request_id,
                            RuntimeError::target_changed(
                                "TARGET_CHANGED",
                                "Target state changed between validation and execution",
                            ),
                            None,
                        );
                    }
                }
            }
        }

        // 10. Capability verification
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

        // 11. Cancellation Token setup
        let cancel_id = req
            .cancellation_id
            .clone()
            .unwrap_or_else(|| request_id.clone());
        let cancel_token = self.cancellation.register(&cancel_id).await;

        // 12. Absolute Deadline calculation
        let deadline_ms = match (req.deadline, req.deadline_ms) {
            (Some(abs_deadline), Some(d_ms)) => {
                let remaining = abs_deadline - chrono::Utc::now();
                let rem_ms = remaining.num_milliseconds();
                if rem_ms <= 0 {
                    return RuntimeResponse::error(
                        &request_id,
                        RuntimeError::deadline_exceeded(
                            "REQUEST_DEADLINE_EXPIRED",
                            "Absolute request deadline has already expired before execution",
                        ),
                        None,
                    );
                }
                (rem_ms as u64).min(d_ms)
            }
            (Some(abs_deadline), None) => {
                let remaining = abs_deadline - chrono::Utc::now();
                let rem_ms = remaining.num_milliseconds();
                if rem_ms <= 0 {
                    return RuntimeResponse::error(
                        &request_id,
                        RuntimeError::deadline_exceeded(
                            "REQUEST_DEADLINE_EXPIRED",
                            "Absolute request deadline has already expired before execution",
                        ),
                        None,
                    );
                }
                rem_ms as u64
            }
            (None, Some(d_ms)) => d_ms,
            (None, None) => 30_000,
        };
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
            "sys.snapshot" | "sys.twin" => {
                let cap_fp = self.lifecycle.capability_fingerprint().await;
                let cfg_fp = self.lifecycle.configuration_fingerprint().await;
                let active_tasks =
                    self.metrics
                        .active_requests
                        .load(std::sync::atomic::Ordering::Relaxed) as usize;
                let caps_count = self.capabilities.list().len();
                let now = chrono::Utc::now();
                let snapshot = NativeRuntimeSnapshot {
                    runtime_instance_id: self.lifecycle.runtime_instance_id().to_string(),
                    capability_fingerprint: cap_fp,
                    configuration_fingerprint: cfg_fp,
                    health_state: format!("{:?}", self.lifecycle.get_state().await),
                    active_tasks_count: active_tasks,
                    memory_rss_bytes: 64 * 1024 * 1024,
                    cpu_usage_pct: 1.5,
                    thread_count: 4,
                    handle_count: 42,
                    capabilities_count: caps_count,
                    timestamp: now,
                };
                Ok(serde_json::to_value(snapshot).unwrap_or(json!({"status": "error"})))
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
            "sandbox.preflight" => {
                let exec_req: kairo_protocol::sandbox::ExecutionRequest =
                    if req.payload.is_object() && req.payload.get("request_id").is_some() {
                        serde_json::from_value(req.payload.clone()).map_err(|e| {
                            RuntimeError::invalid_request(
                                "INVALID_EXECUTION_REQUEST",
                                format!("Cannot parse ExecutionRequest: {}", e),
                            )
                        })?
                    } else {
                        let cap_id = req
                            .payload
                            .get("capability_id")
                            .and_then(|v| v.as_str())
                            .unwrap_or("sandbox.echo")
                            .to_string();
                        kairo_protocol::sandbox::ExecutionRequest {
                            request_id: req.request_id.clone(),
                            capability_id: cap_id,
                            arguments: vec![],
                            working_directory: None,
                            environment_policy: Default::default(),
                            resource_budget: req.resource_budget.clone().unwrap_or_default(),
                            output_limits: Default::default(),
                            authorization_context: req.caller_context.clone(),
                            sandbox_policy: Default::default(),
                            correlation_id: req.correlation_id.clone(),
                            cancellation_id: req.cancellation_id.clone(),
                            payload: req.payload.clone(),
                        }
                    };

                let preflight = self.sandbox.preflight(&exec_req);
                Ok(serde_json::to_value(preflight)
                    .unwrap_or(json!({"error": "preflight_serialization_failed"})))
            }
            "sandbox.execute"
            | "sandbox.echo"
            | "sandbox.hash"
            | "sandbox.probe"
            | "native.window.inspect"
            | "native.process.inspect"
            | "native.display.inspect"
            | "native.screen.capture"
            | "native.clipboard.read"
            | "native.clipboard.write"
            | "native.input.mouse"
            | "native.input.keyboard"
            | "native.net.resolve"
            | "native.net.fetch"
            | "native.net.request"
            | "native.net.health" => {
                let mut exec_req: kairo_protocol::sandbox::ExecutionRequest =
                    if req.payload.is_object() && req.payload.get("request_id").is_some() {
                        serde_json::from_value(req.payload.clone()).map_err(|e| {
                            RuntimeError::invalid_request(
                                "INVALID_EXECUTION_REQUEST",
                                format!("Cannot parse ExecutionRequest: {}", e),
                            )
                        })?
                    } else {
                        let args = req
                            .payload
                            .get("arguments")
                            .and_then(|v| v.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|x| x.as_str().map(|s| s.to_string()))
                                    .collect()
                            })
                            .unwrap_or_default();

                        let cap_id = if req.operation == "sandbox.execute" {
                            req.payload
                                .get("capability_id")
                                .and_then(|v| v.as_str())
                                .unwrap_or("sandbox.echo")
                                .to_string()
                        } else {
                            req.operation.clone()
                        };

                        kairo_protocol::sandbox::ExecutionRequest {
                            request_id: req.request_id.clone(),
                            capability_id: cap_id,
                            arguments: args,
                            working_directory: None,
                            environment_policy: Default::default(),
                            resource_budget: req.resource_budget.clone().unwrap_or_default(),
                            output_limits: Default::default(),
                            authorization_context: req.caller_context.clone(),
                            sandbox_policy: Default::default(),
                            correlation_id: req.correlation_id.clone(),
                            cancellation_id: req.cancellation_id.clone(),
                            payload: req.payload.clone(),
                        }
                    };

                if exec_req.cancellation_id.is_none() {
                    exec_req.cancellation_id = req.cancellation_id.clone();
                }

                let result = self.sandbox.execute(exec_req).await;
                Ok(serde_json::to_value(result)
                    .unwrap_or(json!({"error": "result_serialization_failed"})))
            }
            "obs.events" => {
                let limit = req
                    .payload
                    .get("limit")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(50) as usize;
                let events = if let Some(corr) = req
                    .correlation_id
                    .as_deref()
                    .or_else(|| req.payload.get("correlation_id").and_then(|v| v.as_str()))
                {
                    self.event_buffer.drain_for_correlation(corr)
                } else {
                    self.event_buffer.recent_events(limit)
                };
                Ok(serde_json::to_value(events).unwrap_or_default())
            }
            "obs.stats" => {
                let stats = self.event_buffer.stats();
                Ok(serde_json::to_value(stats).unwrap_or_default())
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
            sandbox: self.sandbox.clone(),
            event_buffer: self.event_buffer.clone(),
            tracer: self.tracer.clone(),
            replay_guard: self.replay_guard.clone(),
        }
    }
}

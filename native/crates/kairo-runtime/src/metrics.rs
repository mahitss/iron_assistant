use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::sync::Arc;

#[derive(Debug, Default)]
pub struct RuntimeMetrics {
    pub requests_total: AtomicU64,
    pub requests_failed: AtomicU64,
    pub requests_cancelled: AtomicU64,
    pub deadlines_exceeded: AtomicU64,
    pub active_requests: AtomicU32,
    pub total_execution_time_ms: AtomicU64,
    // Sandbox counters (Task 81)
    pub sandbox_executions_total: AtomicU64,
    pub sandbox_failures_total: AtomicU64,
    pub sandbox_cancellations_total: AtomicU64,
    pub sandbox_timeouts_total: AtomicU64,
    pub sandbox_active: AtomicU32,
    pub sandbox_output_bytes: AtomicU64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MetricsSnapshot {
    pub requests_total: u64,
    pub requests_failed: u64,
    pub requests_cancelled: u64,
    pub deadlines_exceeded: u64,
    pub active_requests: u32,
    pub average_latency_ms: f64,
    pub sandbox_executions_total: u64,
    pub sandbox_failures_total: u64,
    pub sandbox_cancellations_total: u64,
    pub sandbox_timeouts_total: u64,
    pub sandbox_active: u32,
    pub sandbox_output_bytes: u64,
}

impl RuntimeMetrics {
    pub fn new() -> Arc<Self> {
        Arc::new(Self::default())
    }

    pub fn record_request_start(&self) {
        self.requests_total.fetch_add(1, Ordering::Relaxed);
        self.active_requests.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_request_end(&self, execution_time_ms: u64) {
        self.active_requests.fetch_sub(1, Ordering::Relaxed);
        self.total_execution_time_ms
            .fetch_add(execution_time_ms, Ordering::Relaxed);
    }

    pub fn record_failure(&self) {
        self.requests_failed.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_cancellation(&self) {
        self.requests_cancelled.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_deadline_exceeded(&self) {
        self.deadlines_exceeded.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_sandbox_start(&self) {
        self.sandbox_executions_total
            .fetch_add(1, Ordering::Relaxed);
        self.sandbox_active.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_sandbox_success(&self, duration_ms: u64, output_bytes: u64) {
        self.sandbox_active.fetch_sub(1, Ordering::Relaxed);
        self.sandbox_output_bytes
            .fetch_add(output_bytes, Ordering::Relaxed);
        self.total_execution_time_ms
            .fetch_add(duration_ms, Ordering::Relaxed);
    }

    pub fn record_sandbox_failure(&self) {
        self.sandbox_active.fetch_sub(1, Ordering::Relaxed);
        self.sandbox_failures_total.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_sandbox_cancellation(&self) {
        self.sandbox_active.fetch_sub(1, Ordering::Relaxed);
        self.sandbox_cancellations_total
            .fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_sandbox_timeout(&self) {
        self.sandbox_active.fetch_sub(1, Ordering::Relaxed);
        self.sandbox_timeouts_total.fetch_add(1, Ordering::Relaxed);
    }

    pub fn snapshot(&self) -> MetricsSnapshot {
        let total = self.requests_total.load(Ordering::Relaxed);
        let exec_time = self.total_execution_time_ms.load(Ordering::Relaxed);
        let avg_latency = if total > 0 {
            exec_time as f64 / total as f64
        } else {
            0.0
        };

        MetricsSnapshot {
            requests_total: total,
            requests_failed: self.requests_failed.load(Ordering::Relaxed),
            requests_cancelled: self.requests_cancelled.load(Ordering::Relaxed),
            deadlines_exceeded: self.deadlines_exceeded.load(Ordering::Relaxed),
            active_requests: self.active_requests.load(Ordering::Relaxed),
            average_latency_ms: avg_latency,
            sandbox_executions_total: self.sandbox_executions_total.load(Ordering::Relaxed),
            sandbox_failures_total: self.sandbox_failures_total.load(Ordering::Relaxed),
            sandbox_cancellations_total: self.sandbox_cancellations_total.load(Ordering::Relaxed),
            sandbox_timeouts_total: self.sandbox_timeouts_total.load(Ordering::Relaxed),
            sandbox_active: self.sandbox_active.load(Ordering::Relaxed),
            sandbox_output_bytes: self.sandbox_output_bytes.load(Ordering::Relaxed),
        }
    }
}

use chrono::Utc;
use kairo_protocol::telemetry::{NativeEvent, NativeSpanRecord};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, LazyLock, RwLock};
use std::time::Instant;

static RE_BEARER: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)(Bearer\s+)[A-Za-z0-9_\-\.]{12,}").expect("valid bearer regex")
});
static RE_API_KEY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(sk-[a-zA-Z0-9_\-]{15,}|ghp_[a-zA-Z0-9]{20,}|key-[a-zA-Z0-9]{16,})")
        .expect("valid api_key regex")
});
static RE_GENERIC_SECRET: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)(password|secret|token|apikey|api_key|access_token|private_key)\s*[:=]\s*['\x22]?([^'\x22\s,]{6,})['\x22]?")
        .expect("valid secret regex")
});
static RE_PRIVATE_KEY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----")
        .expect("valid private key regex")
});
static RE_URL_AUTH: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(https?://[^:/@\s]+):([^@\s]+)@").expect("valid url auth regex"));

const SENSITIVE_KEYS: &[&str] = &[
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "private_key",
    "authorization",
    "cookie",
    "credentials",
    "session_secret",
];

const MAX_STRING_LEN: usize = 2048;
const MAX_DEPTH: usize = 10;
pub const DEFAULT_EVENT_BUFFER_CAPACITY: usize = 5000;

/// Centralized in-memory secret and credential redactor.
pub struct NativeRedactor;

impl NativeRedactor {
    pub fn redact_text(text: &str) -> String {
        if text.is_empty() {
            return String::new();
        }

        let mut out = RE_PRIVATE_KEY
            .replace_all(text, "[REDACTED_PRIVATE_KEY]")
            .into_owned();
        out = RE_BEARER
            .replace_all(&out, "${1}[REDACTED_SECRET]")
            .into_owned();
        out = RE_API_KEY
            .replace_all(&out, "[REDACTED_SECRET]")
            .into_owned();
        out = RE_GENERIC_SECRET
            .replace_all(&out, "${1}=[REDACTED_SECRET]")
            .into_owned();
        out = RE_URL_AUTH
            .replace_all(&out, "${1}:[REDACTED]@")
            .into_owned();

        if out.len() > MAX_STRING_LEN {
            let truncated_suffix = format!("... [truncated {} chars]", out.len() - MAX_STRING_LEN);
            out.truncate(MAX_STRING_LEN);
            out.push_str(&truncated_suffix);
        }

        out
    }

    pub fn redact_json(val: &serde_json::Value) -> serde_json::Value {
        Self::redact_json_depth(val, 0)
    }

    fn redact_json_depth(val: &serde_json::Value, depth: usize) -> serde_json::Value {
        if depth >= MAX_DEPTH {
            return serde_json::json!("[NESTING_DEPTH_LIMIT_EXCEEDED]");
        }

        match val {
            serde_json::Value::Object(map) => {
                let mut sanitized = serde_json::Map::with_capacity(map.len());
                for (k, v) in map {
                    let lower = k.to_lowercase();
                    if SENSITIVE_KEYS.iter().any(|sens| lower.contains(sens)) {
                        sanitized.insert(k.clone(), serde_json::json!("[REDACTED]"));
                    } else {
                        sanitized.insert(k.clone(), Self::redact_json_depth(v, depth + 1));
                    }
                }
                serde_json::Value::Object(sanitized)
            }
            serde_json::Value::Array(arr) => {
                let sanitized = arr
                    .iter()
                    .take(200)
                    .map(|v| Self::redact_json_depth(v, depth + 1))
                    .collect();
                serde_json::Value::Array(sanitized)
            }
            serde_json::Value::String(s) => serde_json::Value::String(Self::redact_text(s)),
            _ => val.clone(),
        }
    }
}

#[derive(Debug, Clone)]
struct ActiveSpan {
    span_id: String,
    trace_id: String,
    parent_span_id: Option<String>,
    name: String,
    start_instant: Instant,
    start_ns: u64,
    attributes: serde_json::Value,
}

/// Thread-safe native distributed tracer providing monotonic timing.
pub struct NativeTracer {
    process_start: Instant,
    active_spans: RwLock<HashMap<String, ActiveSpan>>,
}

impl NativeTracer {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            process_start: Instant::now(),
            active_spans: RwLock::new(HashMap::new()),
        })
    }

    pub fn elapsed_ns(&self) -> u64 {
        self.process_start.elapsed().as_nanos() as u64
    }

    pub fn start_span(
        &self,
        trace_id: impl Into<String>,
        parent_span_id: Option<String>,
        name: impl Into<String>,
        attributes: serde_json::Value,
    ) -> String {
        let span_id = format!("span_{}", uuid::Uuid::new_v4().simple());
        let active = ActiveSpan {
            span_id: span_id.clone(),
            trace_id: trace_id.into(),
            parent_span_id,
            name: name.into(),
            start_instant: Instant::now(),
            start_ns: self.elapsed_ns(),
            attributes: NativeRedactor::redact_json(&attributes),
        };

        if let Ok(mut spans) = self.active_spans.write() {
            // Guard against unbounded leak of abandoned spans
            if spans.len() > 10_000 {
                let oldest_key = spans.keys().next().cloned();
                if let Some(k) = oldest_key {
                    spans.remove(&k);
                }
            }
            spans.insert(span_id.clone(), active);
        }

        span_id
    }

    pub fn end_span(&self, span_id: &str, status: &str) -> Option<NativeSpanRecord> {
        let active = {
            let mut spans = self.active_spans.write().ok()?;
            spans.remove(span_id)?
        };

        let duration_ns = active.start_instant.elapsed().as_nanos() as u64;
        Some(NativeSpanRecord {
            span_id: active.span_id,
            trace_id: active.trace_id,
            parent_span_id: active.parent_span_id,
            name: active.name,
            start_time_ns: active.start_ns,
            duration_ns,
            status: status.to_string(),
            attributes: active.attributes,
        })
    }
}

impl Default for NativeTracer {
    fn default() -> Self {
        Self {
            process_start: Instant::now(),
            active_spans: RwLock::new(HashMap::new()),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventBufferStats {
    pub total_emitted: u64,
    pub currently_buffered: usize,
    pub capacity: usize,
    pub dropped_p3: u64,
    pub dropped_p2: u64,
    pub critical_p0_emitted: u64,
}

/// Thread-safe, bounded ring-buffer storing native factual events with priority-aware backpressure.
pub struct NativeEventBuffer {
    capacity: usize,
    events: RwLock<VecDeque<NativeEvent>>,
    process_start: Instant,
    total_emitted: AtomicU64,
    dropped_p3: AtomicU64,
    dropped_p2: AtomicU64,
    critical_p0: AtomicU64,
}

impl NativeEventBuffer {
    pub fn new(capacity: usize) -> Arc<Self> {
        Arc::new(Self {
            capacity,
            events: RwLock::new(VecDeque::with_capacity(capacity)),
            process_start: Instant::now(),
            total_emitted: AtomicU64::new(0),
            dropped_p3: AtomicU64::new(0),
            dropped_p2: AtomicU64::new(0),
            critical_p0: AtomicU64::new(0),
        })
    }

    pub fn record(&self, mut event: NativeEvent) {
        // Enforce monotonic timestamp if unset
        if event.monotonic_timestamp_ns == 0 {
            event.monotonic_timestamp_ns = self.process_start.elapsed().as_nanos() as u64;
        }
        event.wall_timestamp_utc = Utc::now();

        // Centralized secret redaction
        event.payload = NativeRedactor::redact_json(&event.payload);

        let priority = event.severity.priority_tier();
        if priority == 0 {
            self.critical_p0.fetch_add(1, Ordering::Relaxed);
        }

        self.total_emitted.fetch_add(1, Ordering::Relaxed);

        if let Ok(mut buf) = self.events.write() {
            // Priority-aware queue pressure management:
            // Under saturation, drop lowest priority (P3 then P2).
            // P0 and P1 events are NEVER dropped!
            if buf.len() >= self.capacity {
                // Look for oldest P3 event
                if let Some(idx) = buf.iter().position(|e| e.severity.priority_tier() >= 3) {
                    buf.remove(idx);
                    self.dropped_p3.fetch_add(1, Ordering::Relaxed);
                } else if let Some(idx) = buf.iter().position(|e| e.severity.priority_tier() == 2) {
                    buf.remove(idx);
                    self.dropped_p2.fetch_add(1, Ordering::Relaxed);
                } else {
                    // All queued items are P0/P1: discard oldest P1 only if absolutely required
                    buf.pop_front();
                }
            }
            buf.push_back(event);
        }
    }

    pub fn drain_for_correlation(&self, correlation_id: &str) -> Vec<NativeEvent> {
        if correlation_id.is_empty() {
            return Vec::new();
        }

        if let Ok(mut buf) = self.events.write() {
            let mut matched = Vec::new();
            let mut i = 0;
            while i < buf.len() {
                if buf[i]
                    .correlation_id
                    .as_deref()
                    .map(|c| c == correlation_id)
                    .unwrap_or(false)
                {
                    if let Some(ev) = buf.remove(i) {
                        matched.push(ev);
                    }
                } else {
                    i += 1;
                }
            }
            matched
        } else {
            Vec::new()
        }
    }

    pub fn recent_events(&self, limit: usize) -> Vec<NativeEvent> {
        if let Ok(buf) = self.events.read() {
            buf.iter().rev().take(limit).cloned().collect()
        } else {
            Vec::new()
        }
    }

    pub fn stats(&self) -> EventBufferStats {
        let buffered = self.events.read().map(|b| b.len()).unwrap_or(0);
        EventBufferStats {
            total_emitted: self.total_emitted.load(Ordering::Relaxed),
            currently_buffered: buffered,
            capacity: self.capacity,
            dropped_p3: self.dropped_p3.load(Ordering::Relaxed),
            dropped_p2: self.dropped_p2.load(Ordering::Relaxed),
            critical_p0_emitted: self.critical_p0.load(Ordering::Relaxed),
        }
    }
}

impl Default for NativeEventBuffer {
    fn default() -> Self {
        Self {
            capacity: DEFAULT_EVENT_BUFFER_CAPACITY,
            events: RwLock::new(VecDeque::with_capacity(DEFAULT_EVENT_BUFFER_CAPACITY)),
            process_start: Instant::now(),
            total_emitted: AtomicU64::new(0),
            dropped_p3: AtomicU64::new(0),
            dropped_p2: AtomicU64::new(0),
            critical_p0: AtomicU64::new(0),
        }
    }
}

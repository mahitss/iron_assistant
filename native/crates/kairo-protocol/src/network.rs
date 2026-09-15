use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Explicit classification of network side effects and operational characteristics.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NetworkOperationClass {
    Observe,
    #[default]
    Fetch,
    Stream,
    Connect,
    Resolve,
    Upload,
    ExternalWrite,
    ExternalDestructive,
}

/// Transport protocol used for network operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum NetworkProtocol {
    #[default]
    Http1,
    Http2,
    Tcp,
    Dns,
    Tls,
    WebSocket,
}

/// Governed policy constraints applied to network operations.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NetworkPolicy {
    #[serde(default)]
    pub hostname_policy: Vec<String>,
    #[serde(default)]
    pub denied_hostnames: Vec<String>,
    #[serde(default = "default_ports")]
    pub port_policy: Vec<u16>,
    #[serde(default)]
    pub allow_private_ips: bool,
    #[serde(default = "default_dns_timeout")]
    pub dns_timeout_ms: u64,
    #[serde(default = "default_connect_timeout")]
    pub connect_timeout_ms: u64,
    #[serde(default = "default_request_timeout")]
    pub request_timeout_ms: u64,
    #[serde(default = "default_deadline")]
    pub total_deadline_ms: u64,
    #[serde(default = "default_max_redirects")]
    pub max_redirects: u32,
    #[serde(default = "default_true")]
    pub allow_cross_origin_redirects: bool,
    #[serde(default = "default_true")]
    pub strip_credentials_cross_origin: bool,
    #[serde(default = "default_req_size")]
    pub request_size_limit_bytes: u64,
    #[serde(default = "default_resp_size")]
    pub response_size_limit_bytes: u64,
    #[serde(default = "default_retries")]
    pub max_retries: u32,
    #[serde(default = "default_rpm")]
    pub rate_limit_rpm: u32,
}

fn default_ports() -> Vec<u16> {
    vec![80, 443]
}
fn default_dns_timeout() -> u64 {
    5000
}
fn default_connect_timeout() -> u64 {
    5000
}
fn default_request_timeout() -> u64 {
    15000
}
fn default_deadline() -> u64 {
    30000
}
fn default_max_redirects() -> u32 {
    5
}
fn default_true() -> bool {
    true
}
fn default_req_size() -> u64 {
    1048576
} // 1MB
fn default_resp_size() -> u64 {
    10485760
} // 10MB
fn default_retries() -> u32 {
    2
}
fn default_rpm() -> u32 {
    120
}

impl Default for NetworkPolicy {
    fn default() -> Self {
        Self {
            hostname_policy: Vec::new(),
            denied_hostnames: Vec::new(),
            port_policy: default_ports(),
            allow_private_ips: false,
            dns_timeout_ms: default_dns_timeout(),
            connect_timeout_ms: default_connect_timeout(),
            request_timeout_ms: default_request_timeout(),
            total_deadline_ms: default_deadline(),
            max_redirects: default_max_redirects(),
            allow_cross_origin_redirects: true,
            strip_credentials_cross_origin: true,
            request_size_limit_bytes: default_req_size(),
            response_size_limit_bytes: default_resp_size(),
            max_retries: default_retries(),
            rate_limit_rpm: default_rpm(),
        }
    }
}

/// Request for bounded DNS resolution.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DnsResolveRequest {
    pub hostname: String,
    #[serde(default)]
    pub policy: Option<NetworkPolicy>,
}

/// Result from bounded DNS resolution.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DnsResolveResult {
    pub hostname: String,
    pub resolved_ips: Vec<String>,
    pub is_public: bool,
    pub ttl_seconds: u64,
    pub duration_ms: u64,
    #[serde(default)]
    pub error: Option<String>,
}

fn default_http_method() -> String {
    "GET".to_string()
}

/// Strongly-typed HTTP request descriptor.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HttpRequestDescriptor {
    #[serde(default = "default_http_method")]
    pub method: String,
    pub url: String,
    #[serde(default)]
    pub headers: HashMap<String, String>,
    #[serde(default)]
    pub body: Option<String>,
    #[serde(default)]
    pub operation_class: NetworkOperationClass,
    #[serde(default)]
    pub idempotency_key: Option<String>,
    #[serde(default)]
    pub policy: Option<NetworkPolicy>,
}

/// Strongly-typed HTTP response result.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HttpResponseResult {
    pub status_code: u16,
    pub status_text: String,
    #[serde(default)]
    pub headers: HashMap<String, String>,
    #[serde(default)]
    pub body: String,
    #[serde(default)]
    pub truncated: bool,
    #[serde(default)]
    pub raw_bytes_count: u64,
    #[serde(default)]
    pub duration_ms: u64,
    #[serde(default)]
    pub dns_latency_ms: u64,
    #[serde(default)]
    pub connect_latency_ms: u64,
    #[serde(default)]
    pub redirect_chain: Vec<String>,
    #[serde(default)]
    pub remote_address: Option<String>,
    #[serde(default)]
    pub protocol: String,
    #[serde(default)]
    pub security_classification: String,
    #[serde(default)]
    pub error: Option<String>,
}

/// Operational health and metrics report for the native network substrate.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NetworkHealthReport {
    pub state: String,
    pub active_connections: u32,
    pub idle_connections: u32,
    pub active_requests: u32,
    pub total_requests: u64,
    pub ssrf_blocks_count: u64,
    pub circuit_breaker_open: bool,
    pub pool_utilization: f32,
}

use kairo_protocol::network::{
    DnsResolveRequest, DnsResolveResult, HttpRequestDescriptor, HttpResponseResult,
    NetworkHealthReport,
};
use kairo_protocol::{ErrorCategory, RuntimeError};
use reqwest::header::{HeaderMap, HeaderName, HeaderValue};
use std::collections::HashMap;
use std::net::{IpAddr, Ipv4Addr, SocketAddr};
use std::str::FromStr;
use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{RwLock, Semaphore};
use tokio::time::timeout;
use tracing::{info, warn};
use url::Url;

use crate::cancellation::CancellationRegistry;

// ============================================================================
// 1. SSRF GUARD & IP CLASSIFICATION
// ============================================================================

/// Strict IP and hostname validation defending against SSRF, loopback,
/// link-local, private networks, cloud metadata endpoints, and rebinding.
pub struct SsrfGuard;

impl SsrfGuard {
    pub fn is_loopback(ip: &IpAddr) -> bool {
        match ip {
            IpAddr::V4(v4) => v4.is_loopback(),
            IpAddr::V6(v6) => v6.is_loopback(),
        }
    }

    pub fn is_unspecified(ip: &IpAddr) -> bool {
        match ip {
            IpAddr::V4(v4) => v4.is_unspecified(),
            IpAddr::V6(v6) => v6.is_unspecified(),
        }
    }

    pub fn is_multicast(ip: &IpAddr) -> bool {
        match ip {
            IpAddr::V4(v4) => v4.is_multicast(),
            IpAddr::V6(v6) => v6.is_multicast(),
        }
    }

    pub fn is_broadcast(ip: &IpAddr) -> bool {
        match ip {
            IpAddr::V4(v4) => v4.is_broadcast(),
            IpAddr::V6(_) => false,
        }
    }

    pub fn is_link_local(ip: &IpAddr) -> bool {
        match ip {
            IpAddr::V4(v4) => v4.is_link_local(),
            IpAddr::V6(v6) => (v6.segments()[0] & 0xffc0) == 0xfe80,
        }
    }

    pub fn is_private_ip(ip: &IpAddr) -> bool {
        match ip {
            IpAddr::V4(v4) => {
                let octets = v4.octets();
                // 10.0.0.0/8
                if octets[0] == 10 {
                    return true;
                }
                // 172.16.0.0/12 (172.16.0.0 - 172.31.255.255)
                if octets[0] == 172 && (16..=31).contains(&octets[1]) {
                    return true;
                }
                // 192.168.0.0/16
                if octets[0] == 192 && octets[1] == 168 {
                    return true;
                }
                // Shared carrier address space: 100.64.0.0/10
                if octets[0] == 100 && (64..=127).contains(&octets[1]) {
                    return true;
                }
                false
            }
            IpAddr::V6(v6) => {
                let seg0 = v6.segments()[0];
                // Unique local address: fc00::/7 (fc00 - fdff)
                (seg0 & 0xfe00) == 0xfc00
            }
        }
    }

    pub fn is_cloud_metadata(ip: &IpAddr) -> bool {
        match ip {
            IpAddr::V4(v4) => {
                // AWS/GCP/Azure link-local metadata 169.254.169.254
                v4 == &Ipv4Addr::new(169, 254, 169, 254)
            }
            IpAddr::V6(v6) => {
                // AWS IPv6 metadata: fd00:ec2::254
                let segs = v6.segments();
                segs[0] == 0xfd00 && segs[1] == 0x0ec2 && segs[7] == 0x0254
            }
        }
    }

    pub fn validate_ip(ip: &IpAddr, allow_private: bool) -> Result<(), String> {
        if Self::is_loopback(ip) {
            return Err(format!(
                "SSRF_BLOCKED: Loopback address '{}' is forbidden",
                ip
            ));
        }
        if Self::is_unspecified(ip) {
            return Err(format!(
                "SSRF_BLOCKED: Unspecified address '{}' is forbidden",
                ip
            ));
        }
        if Self::is_broadcast(ip) {
            return Err(format!(
                "SSRF_BLOCKED: Broadcast address '{}' is forbidden",
                ip
            ));
        }
        if Self::is_multicast(ip) {
            return Err(format!(
                "SSRF_BLOCKED: Multicast address '{}' is forbidden",
                ip
            ));
        }
        if Self::is_link_local(ip) {
            return Err(format!(
                "SSRF_BLOCKED: Link-local address '{}' is forbidden",
                ip
            ));
        }
        if Self::is_cloud_metadata(ip) {
            return Err(format!(
                "SSRF_BLOCKED: Cloud metadata address '{}' is forbidden",
                ip
            ));
        }
        if !allow_private && Self::is_private_ip(ip) {
            return Err(format!(
                "PRIVATE_IP_BLOCKED: RFC1918/RFC4193 private address '{}' is forbidden",
                ip
            ));
        }
        Ok(())
    }

    pub fn validate_hostname(host: &str) -> Result<(), String> {
        let h = host.to_lowercase();
        if h == "localhost"
            || h.ends_with(".localhost")
            || h == "ip6-localhost"
            || h == "ip6-loopback"
        {
            return Err(format!(
                "SSRF_BLOCKED: Localhost hostname '{}' is forbidden",
                host
            ));
        }
        if h == "metadata.google.internal"
            || h.ends_with(".internal")
            || h.ends_with(".local")
            || h.ends_with(".lan")
        {
            return Err(format!(
                "SSRF_BLOCKED: Internal metadata or local domain '{}' is forbidden",
                host
            ));
        }
        Ok(())
    }

    pub fn validate_port(port: u16, allowed_ports: &[u16]) -> Result<(), String> {
        if !allowed_ports.is_empty() && !allowed_ports.contains(&port) {
            return Err(format!(
                "PORT_RESTRICTED: Port {} is not in authorized ports list {:?}",
                port, allowed_ports
            ));
        }
        Ok(())
    }
}

// ============================================================================
// 2. BOUNDED DNS RESOLVER WITH CACHING & SSRF DEFENSE
// ============================================================================

struct DnsCacheEntry {
    ips: Vec<IpAddr>,
    expires_at: Instant,
}

pub struct DnsResolver {
    cache: RwLock<HashMap<String, DnsCacheEntry>>,
    max_cache_entries: usize,
    default_ttl: Duration,
}

impl DnsResolver {
    pub fn new(max_cache_entries: usize, default_ttl: Duration) -> Self {
        Self {
            cache: RwLock::new(HashMap::new()),
            max_cache_entries,
            default_ttl,
        }
    }

    pub async fn resolve(
        &self,
        hostname: &str,
        timeout_ms: u64,
        allow_private: bool,
    ) -> Result<(Vec<IpAddr>, u64), String> {
        let host_trimmed = hostname.trim().to_lowercase();
        SsrfGuard::validate_hostname(&host_trimmed)?;

        // If hostname is directly an IP literal
        if let Ok(ip) = host_trimmed.parse::<IpAddr>() {
            SsrfGuard::validate_ip(&ip, allow_private)?;
            return Ok((vec![ip], 0));
        }

        // Check cache
        let now = Instant::now();
        {
            let reader = self.cache.read().await;
            if let Some(entry) = reader.get(&host_trimmed) {
                if entry.expires_at > now {
                    return Ok((entry.ips.clone(), 0));
                }
            }
        }

        // Perform DNS lookup bounded by timeout
        let start = Instant::now();
        let lookup_fut = tokio::net::lookup_host(format!("{}:0", host_trimmed));
        let socket_addrs = match timeout(Duration::from_millis(timeout_ms), lookup_fut).await {
            Ok(Ok(addrs)) => addrs.collect::<Vec<SocketAddr>>(),
            Ok(Err(e)) => {
                return Err(format!(
                    "DNS_FAILED: Resolution failed for '{}': {}",
                    host_trimmed, e
                ))
            }
            Err(_) => {
                return Err(format!(
                    "DNS_TIMEOUT: Resolution timed out for '{}' after {}ms",
                    host_trimmed, timeout_ms
                ))
            }
        };

        if socket_addrs.is_empty() {
            return Err(format!(
                "DNS_FAILED: No IP records found for hostname '{}'",
                host_trimmed
            ));
        }

        let mut valid_ips = Vec::new();
        for s in socket_addrs {
            let ip = s.ip();
            SsrfGuard::validate_ip(&ip, allow_private)?;
            if !valid_ips.contains(&ip) {
                valid_ips.push(ip);
            }
        }

        let duration_ms = start.elapsed().as_millis() as u64;

        // Cache valid results with bounded eviction
        {
            let mut writer = self.cache.write().await;
            if writer.len() >= self.max_cache_entries {
                writer.retain(|_, v| v.expires_at > now);
                if writer.len() >= self.max_cache_entries {
                    writer.clear();
                }
            }
            writer.insert(
                host_trimmed,
                DnsCacheEntry {
                    ips: valid_ips.clone(),
                    expires_at: now + self.default_ttl,
                },
            );
        }

        Ok((valid_ips, duration_ms))
    }
}

// ============================================================================
// 3. CIRCUIT BREAKER
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

struct HostCircuit {
    state: CircuitState,
    consecutive_failures: u32,
    last_failure: Option<Instant>,
    half_open_probe_in_flight: bool,
}

pub struct CircuitBreaker {
    circuits: RwLock<HashMap<String, HostCircuit>>,
    failure_threshold: u32,
    cooldown_period: Duration,
}

impl CircuitBreaker {
    pub fn new(failure_threshold: u32, cooldown_period: Duration) -> Self {
        Self {
            circuits: RwLock::new(HashMap::new()),
            failure_threshold,
            cooldown_period,
        }
    }

    pub async fn can_execute(&self, host: &str) -> Result<(), String> {
        let host_key = host.to_lowercase();
        let mut map = self.circuits.write().await;
        let entry = map.entry(host_key.clone()).or_insert_with(|| HostCircuit {
            state: CircuitState::Closed,
            consecutive_failures: 0,
            last_failure: None,
            half_open_probe_in_flight: false,
        });

        match entry.state {
            CircuitState::Closed => Ok(()),
            CircuitState::Open => {
                if let Some(last_fail) = entry.last_failure {
                    if last_fail.elapsed() >= self.cooldown_period {
                        entry.state = CircuitState::HalfOpen;
                        entry.half_open_probe_in_flight = true;
                        info!(host = %host_key, "Circuit breaker transitioning Open -> HalfOpen");
                        return Ok(());
                    }
                }
                Err(format!(
                    "CIRCUIT_OPEN: Circuit breaker is OPEN for '{}' (failures: {})",
                    host, entry.consecutive_failures
                ))
            }
            CircuitState::HalfOpen => {
                if !entry.half_open_probe_in_flight {
                    entry.half_open_probe_in_flight = true;
                    Ok(())
                } else {
                    Err(format!(
                        "CIRCUIT_OPEN: HalfOpen probe already in flight for '{}'",
                        host
                    ))
                }
            }
        }
    }

    pub async fn record_success(&self, host: &str) {
        let host_key = host.to_lowercase();
        let mut map = self.circuits.write().await;
        if let Some(entry) = map.get_mut(&host_key) {
            entry.state = CircuitState::Closed;
            entry.consecutive_failures = 0;
            entry.last_failure = None;
            entry.half_open_probe_in_flight = false;
        }
    }

    pub async fn record_failure(&self, host: &str) {
        let host_key = host.to_lowercase();
        let mut map = self.circuits.write().await;
        let entry = map.entry(host_key.clone()).or_insert_with(|| HostCircuit {
            state: CircuitState::Closed,
            consecutive_failures: 0,
            last_failure: None,
            half_open_probe_in_flight: false,
        });

        entry.consecutive_failures += 1;
        entry.last_failure = Some(Instant::now());
        entry.half_open_probe_in_flight = false;

        if entry.consecutive_failures >= self.failure_threshold {
            entry.state = CircuitState::Open;
            warn!(
                host = %host_key,
                failures = entry.consecutive_failures,
                "Circuit breaker tripped OPEN"
            );
        }
    }

    pub async fn has_open_circuits(&self) -> bool {
        let map = self.circuits.read().await;
        map.values().any(|c| c.state == CircuitState::Open)
    }
}

// ============================================================================
// 4. RATE LIMITER (TOKEN BUCKET PER HOST)
// ============================================================================

struct TokenBucket {
    tokens: f64,
    last_update: Instant,
}

pub struct RateLimiter {
    buckets: RwLock<HashMap<String, TokenBucket>>,
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new()
    }
}

impl RateLimiter {
    pub fn new() -> Self {
        Self {
            buckets: RwLock::new(HashMap::new()),
        }
    }

    pub async fn check_and_consume(&self, host: &str, rpm: u32) -> Result<(), String> {
        if rpm == 0 {
            return Ok(());
        }

        let host_key = host.to_lowercase();
        let max_tokens = rpm as f64;
        let fill_rate_per_sec = max_tokens / 60.0;
        let now = Instant::now();

        let mut map = self.buckets.write().await;
        let bucket = map.entry(host_key.clone()).or_insert_with(|| TokenBucket {
            tokens: max_tokens,
            last_update: now,
        });

        let elapsed = now.duration_since(bucket.last_update).as_secs_f64();
        bucket.tokens = (bucket.tokens + elapsed * fill_rate_per_sec).min(max_tokens);
        bucket.last_update = now;

        if bucket.tokens >= 1.0 {
            bucket.tokens -= 1.0;
            Ok(())
        } else {
            Err(format!(
                "RATE_LIMITED: Exceeded rate limit of {} requests/min for '{}'",
                rpm, host
            ))
        }
    }
}

// ============================================================================
// 5. CONNECTION POOL & FABRIC HEALTH TRACKER
// ============================================================================

pub struct ConnectionPoolTracker {
    pub active_requests: AtomicU32,
    pub total_requests: AtomicU64,
    pub ssrf_blocks_count: AtomicU64,
    pub max_concurrency: u32,
}

impl ConnectionPoolTracker {
    pub fn new(max_concurrency: u32) -> Self {
        Self {
            active_requests: AtomicU32::new(0),
            total_requests: AtomicU64::new(0),
            ssrf_blocks_count: AtomicU64::new(0),
            max_concurrency,
        }
    }

    pub fn record_start(&self) {
        self.active_requests.fetch_add(1, Ordering::SeqCst);
        self.total_requests.fetch_add(1, Ordering::SeqCst);
    }

    pub fn record_end(&self) {
        self.active_requests.fetch_sub(1, Ordering::SeqCst);
    }

    pub fn record_ssrf_block(&self) {
        self.ssrf_blocks_count.fetch_add(1, Ordering::SeqCst);
    }
}

// ============================================================================
// 6. NATIVE NETWORK SUBSTRATE
// ============================================================================

pub struct NativeNetworkSubstrate {
    cancellation: Arc<CancellationRegistry>,
    concurrency_sem: Arc<Semaphore>,
    dns_resolver: Arc<DnsResolver>,
    circuit_breaker: Arc<CircuitBreaker>,
    rate_limiter: Arc<RateLimiter>,
    pool_tracker: Arc<ConnectionPoolTracker>,
    emergency_stopped: Arc<AtomicBool>,
}

impl NativeNetworkSubstrate {
    pub fn new(cancellation: Arc<CancellationRegistry>, max_concurrency: usize) -> Self {
        Self {
            cancellation,
            concurrency_sem: Arc::new(Semaphore::new(max_concurrency)),
            dns_resolver: Arc::new(DnsResolver::new(512, Duration::from_secs(60))),
            circuit_breaker: Arc::new(CircuitBreaker::new(5, Duration::from_secs(30))),
            rate_limiter: Arc::new(RateLimiter::new()),
            pool_tracker: Arc::new(ConnectionPoolTracker::new(max_concurrency as u32)),
            emergency_stopped: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn set_emergency_stop(&self, stopped: bool) {
        self.emergency_stopped.store(stopped, Ordering::SeqCst);
        if stopped {
            warn!("NativeNetworkSubstrate EmergencyStop activated: rejecting all network traffic");
        } else {
            info!("NativeNetworkSubstrate EmergencyStop reset");
        }
    }

    pub fn is_emergency_stopped(&self) -> bool {
        self.emergency_stopped.load(Ordering::SeqCst)
    }

    pub fn get_health(&self) -> NetworkHealthReport {
        let active = self.pool_tracker.active_requests.load(Ordering::SeqCst);
        let total = self.pool_tracker.total_requests.load(Ordering::SeqCst);
        let ssrf_blocks = self.pool_tracker.ssrf_blocks_count.load(Ordering::SeqCst);
        let max_conc = self.pool_tracker.max_concurrency;
        let util = if max_conc > 0 {
            active as f32 / max_conc as f32
        } else {
            0.0
        };

        let is_stopped = self.is_emergency_stopped();
        let state = if is_stopped {
            "STOPPED".to_string()
        } else if util > 0.9 {
            "SATURATED".to_string()
        } else if util > 0.7 {
            "DEGRADED".to_string()
        } else {
            "HEALTHY".to_string()
        };

        NetworkHealthReport {
            state,
            active_connections: active,
            idle_connections: 0,
            active_requests: active,
            total_requests: total,
            ssrf_blocks_count: ssrf_blocks,
            circuit_breaker_open: false,
            pool_utilization: util,
        }
    }

    /// Bounded DNS resolution with full SSRF and private IP rejection.
    pub async fn resolve_dns(
        &self,
        req: DnsResolveRequest,
    ) -> Result<DnsResolveResult, RuntimeError> {
        if self.is_emergency_stopped() {
            return Err(RuntimeError::internal(
                "EMERGENCY_STOP",
                "Network execution halted by EmergencyStop",
            ));
        }

        let policy = req.policy.unwrap_or_default();
        let timeout_ms = policy.dns_timeout_ms;
        let allow_private = policy.allow_private_ips;

        match self
            .dns_resolver
            .resolve(&req.hostname, timeout_ms, allow_private)
            .await
        {
            Ok((ips, duration_ms)) => {
                let ip_strings = ips.iter().map(|ip| ip.to_string()).collect::<Vec<_>>();
                let is_pub = ips.iter().all(|ip| !SsrfGuard::is_private_ip(ip));
                Ok(DnsResolveResult {
                    hostname: req.hostname,
                    resolved_ips: ip_strings,
                    is_public: is_pub,
                    ttl_seconds: 60,
                    duration_ms,
                    error: None,
                })
            }
            Err(err_msg) => {
                if err_msg.starts_with("SSRF_BLOCKED") || err_msg.starts_with("PRIVATE_IP_BLOCKED")
                {
                    self.pool_tracker.record_ssrf_block();
                    Err(RuntimeError::authz_required("SSRF_BLOCKED", err_msg))
                } else if err_msg.starts_with("DNS_TIMEOUT") {
                    Err(RuntimeError::deadline_exceeded("DNS_TIMEOUT", err_msg))
                } else {
                    Err(RuntimeError::invalid_request("DNS_FAILED", err_msg))
                }
            }
        }
    }

    /// Bounded, secure HTTP execution with SSRF defense, rebinding defense,
    /// redirect validation, circuit breaker, rate limiting, and size limits.
    pub async fn execute_http(
        &self,
        req: HttpRequestDescriptor,
        cancellation_id: Option<String>,
    ) -> Result<HttpResponseResult, RuntimeError> {
        if self.is_emergency_stopped() {
            return Err(RuntimeError::internal(
                "EMERGENCY_STOP",
                "Network execution halted by EmergencyStop",
            ));
        }

        // Bounded concurrency acquisition
        let _permit = self.concurrency_sem.try_acquire().map_err(|_| {
            RuntimeError::resource_limit(
                "CONCURRENCY_LIMITED",
                "Global network concurrency limit reached; backpressure engaged",
            )
        })?;

        self.pool_tracker.record_start();
        let res = self.execute_http_internal(req, cancellation_id).await;
        self.pool_tracker.record_end();
        res
    }

    async fn execute_http_internal(
        &self,
        req: HttpRequestDescriptor,
        cancellation_id: Option<String>,
    ) -> Result<HttpResponseResult, RuntimeError> {
        let policy = req.policy.clone().unwrap_or_default();
        let total_deadline = Duration::from_millis(policy.total_deadline_ms);
        let start_time = Instant::now();

        // 1. Initial URL validation
        let initial_url = Url::parse(&req.url).map_err(|e| {
            RuntimeError::invalid_request(
                "INVALID_URL",
                format!("Failed to parse target URL '{}': {}", req.url, e),
            )
        })?;

        let scheme = initial_url.scheme().to_lowercase();
        if scheme != "http" && scheme != "https" {
            return Err(RuntimeError::invalid_request(
                "UNSUPPORTED_PROTOCOL",
                format!(
                    "Protocol scheme '{}' is not supported; only HTTP/HTTPS are allowed",
                    scheme
                ),
            ));
        }

        if !initial_url.username().is_empty() || initial_url.password().is_some() {
            return Err(RuntimeError::authz_required(
                "CREDENTIALS_IN_URL_FORBIDDEN",
                "Embedded userinfo credentials in URLs are forbidden",
            ));
        }

        // 2. Cancellation token
        let cancel_token = if let Some(ref cid) = cancellation_id {
            Some(self.cancellation.register(cid).await)
        } else {
            None
        };

        // 3. Execution loop supporting redirect chains
        let mut current_url = initial_url;
        let mut redirect_chain: Vec<String> = Vec::new();
        let mut redirects_followed = 0;
        let mut current_headers = req.headers.clone();
        let is_idempotent = matches!(
            req.method.to_uppercase().as_str(),
            "GET" | "HEAD" | "OPTIONS"
        ) || req.idempotency_key.is_some();

        let mut retries_left = if is_idempotent { policy.max_retries } else { 0 };

        loop {
            // Check deadline
            if start_time.elapsed() >= total_deadline {
                return Err(RuntimeError::deadline_exceeded(
                    "DEADLINE_EXCEEDED",
                    format!("Total deadline of {}ms exceeded", policy.total_deadline_ms),
                ));
            }

            // Check EmergencyStop
            if self.is_emergency_stopped() {
                return Err(RuntimeError::internal(
                    "EMERGENCY_STOP",
                    "Network execution halted by EmergencyStop during execution",
                ));
            }

            // Check cancellation token
            if let Some(ref tok) = cancel_token {
                if tok.is_cancelled() {
                    return Err(RuntimeError::cancelled(
                        "CANCELLED",
                        "Network request cancelled by caller",
                    ));
                }
            }

            let host_str = current_url
                .host_str()
                .ok_or_else(|| {
                    RuntimeError::invalid_request("MISSING_HOST", "URL has no host component")
                })?
                .to_string();

            let port = current_url.port_or_known_default().ok_or_else(|| {
                RuntimeError::invalid_request("UNKNOWN_PORT", "Could not determine port")
            })?;

            // Hostname & Port policies
            if let Err(e) = SsrfGuard::validate_hostname(&host_str) {
                self.pool_tracker.record_ssrf_block();
                return Err(RuntimeError::authz_required("SSRF_BLOCKED", e));
            }

            if let Err(e) = SsrfGuard::validate_port(port, &policy.port_policy) {
                return Err(RuntimeError::authz_required("PORT_RESTRICTED", e));
            }

            if !policy.denied_hostnames.is_empty()
                && policy
                    .denied_hostnames
                    .iter()
                    .any(|d| d.eq_ignore_ascii_case(&host_str))
            {
                return Err(RuntimeError::authz_required(
                    "POLICY_DENIED_HOSTNAME",
                    format!("Hostname '{}' is explicitly denied by policy", host_str),
                ));
            }

            if !policy.hostname_policy.is_empty()
                && !policy
                    .hostname_policy
                    .iter()
                    .any(|allowed| allowed.eq_ignore_ascii_case(&host_str))
            {
                return Err(RuntimeError::authz_required(
                    "POLICY_RESTRICTED_HOSTNAME",
                    format!("Hostname '{}' is not in authorized host policy", host_str),
                ));
            }

            // Circuit breaker check
            if let Err(e) = self.circuit_breaker.can_execute(&host_str).await {
                return Err(RuntimeError::resource_limit("CIRCUIT_OPEN", e));
            }

            // Rate limit check
            if let Err(e) = self
                .rate_limiter
                .check_and_consume(&host_str, policy.rate_limit_rpm)
                .await
            {
                return Err(RuntimeError::resource_limit("RATE_LIMITED", e));
            }

            // DNS resolution & pre-validated IP binding
            let _dns_start = Instant::now();
            let (resolved_ips, dns_latency) = match self
                .dns_resolver
                .resolve(&host_str, policy.dns_timeout_ms, policy.allow_private_ips)
                .await
            {
                Ok(res) => res,
                Err(err_msg) => {
                    self.circuit_breaker.record_failure(&host_str).await;
                    if err_msg.starts_with("SSRF_BLOCKED")
                        || err_msg.starts_with("PRIVATE_IP_BLOCKED")
                    {
                        self.pool_tracker.record_ssrf_block();
                        return Err(RuntimeError::authz_required("SSRF_BLOCKED", err_msg));
                    }
                    return Err(RuntimeError::invalid_request(
                        "DNS_RESOLUTION_FAILED",
                        err_msg,
                    ));
                }
            };

            let validated_ip = resolved_ips[0];
            let target_socket_addr = SocketAddr::new(validated_ip, port);

            // Build HTTP Client configured with exact pre-validated IP to defeat DNS rebinding!
            let client_builder = reqwest::Client::builder()
                .connect_timeout(Duration::from_millis(policy.connect_timeout_ms))
                .timeout(Duration::from_millis(policy.request_timeout_ms))
                .redirect(reqwest::redirect::Policy::none()) // We control redirects manually
                .resolve(&host_str, target_socket_addr);

            let client = client_builder.build().map_err(|e| {
                RuntimeError::internal(
                    "HTTP_CLIENT_ERROR",
                    format!("Failed to build HTTP client: {}", e),
                )
            })?;

            // Prepare method and headers
            let method = reqwest::Method::from_str(&req.method.to_uppercase()).map_err(|e| {
                RuntimeError::invalid_request(
                    "INVALID_METHOD",
                    format!("Invalid HTTP method '{}': {}", req.method, e),
                )
            })?;

            let mut header_map = HeaderMap::new();
            for (k, v) in &current_headers {
                if let (Ok(hname), Ok(hval)) = (HeaderName::from_str(k), HeaderValue::from_str(v)) {
                    header_map.insert(hname, hval);
                }
            }

            let mut request_builder = client
                .request(method.clone(), current_url.clone())
                .headers(header_map);

            if let Some(ref body_content) = req.body {
                if body_content.len() as u64 > policy.request_size_limit_bytes {
                    return Err(RuntimeError::invalid_request(
                        "REQUEST_TOO_LARGE",
                        format!(
                            "Request body ({} bytes) exceeds limit of {} bytes",
                            body_content.len(),
                            policy.request_size_limit_bytes
                        ),
                    ));
                }
                request_builder = request_builder.body(body_content.clone());
            }

            // Dispatch HTTP request
            let conn_start = Instant::now();
            let remaining_time = total_deadline.saturating_sub(start_time.elapsed());
            let send_fut = request_builder.send();

            let response_result = match timeout(remaining_time, send_fut).await {
                Ok(res) => res,
                Err(_) => {
                    self.circuit_breaker.record_failure(&host_str).await;
                    return Err(RuntimeError::deadline_exceeded(
                        "REQUEST_TIMEOUT",
                        format!("Request to '{}' timed out", current_url),
                    ));
                }
            };

            let response = match response_result {
                Ok(resp) => {
                    self.circuit_breaker.record_success(&host_str).await;
                    resp
                }
                Err(err) => {
                    self.circuit_breaker.record_failure(&host_str).await;
                    if retries_left > 0 && is_idempotent {
                        retries_left -= 1;
                        warn!(
                            url = %current_url,
                            retries_left = retries_left,
                            error = %err,
                            "Transient network error; retrying request"
                        );
                        tokio::time::sleep(Duration::from_millis(150)).await;
                        continue;
                    }
                    if !is_idempotent {
                        // Ambiguous outcome for stateful write
                        return Err(RuntimeError::new(
                            ErrorCategory::InternalError,
                            "UNKNOWN_OUTCOME",
                            "Network connection dropped during non-idempotent operation; state unknown",
                            false,
                        ));
                    }
                    return Err(RuntimeError::internal(
                        "REMOTE_ERROR",
                        format!("HTTP execution failed for '{}': {}", current_url, err),
                    ));
                }
            };

            let status = response.status();
            let status_code = status.as_u16();

            // Check for redirect (301, 302, 303, 307, 308)
            if status.is_redirection() {
                if let Some(loc_header) = response.headers().get(reqwest::header::LOCATION) {
                    if let Ok(loc_str) = loc_header.to_str() {
                        redirects_followed += 1;
                        if redirects_followed > policy.max_redirects {
                            return Err(RuntimeError::authz_required(
                                "REDIRECT_BLOCKED",
                                format!(
                                    "Exceeded maximum redirect limit of {}",
                                    policy.max_redirects
                                ),
                            ));
                        }

                        let next_url = current_url.join(loc_str).map_err(|e| {
                            RuntimeError::invalid_request(
                                "INVALID_REDIRECT",
                                format!("Malformed redirect target '{}': {}", loc_str, e),
                            )
                        })?;

                        // Downgrade protection
                        if current_url.scheme() == "https" && next_url.scheme() == "http" {
                            return Err(RuntimeError::authz_required(
                                "REDIRECT_BLOCKED",
                                "HTTPS to HTTP downgrade redirect forbidden",
                            ));
                        }

                        // Origin comparison
                        let is_cross_origin = current_url.origin() != next_url.origin();
                        if is_cross_origin {
                            if !policy.allow_cross_origin_redirects {
                                return Err(RuntimeError::authz_required(
                                    "REDIRECT_BLOCKED",
                                    "Cross-origin redirect forbidden by policy",
                                ));
                            }
                            if policy.strip_credentials_cross_origin {
                                current_headers.remove("Authorization");
                                current_headers.remove("authorization");
                                current_headers.remove("Cookie");
                                current_headers.remove("cookie");
                                current_headers.remove("Proxy-Authorization");
                                current_headers.remove("proxy-authorization");
                            }
                        }

                        redirect_chain.push(current_url.to_string());
                        current_url = next_url;
                        continue;
                    }
                }
            }

            // Extract headers
            let mut resp_headers = HashMap::new();
            for (k, v) in response.headers() {
                if let Ok(str_val) = v.to_str() {
                    resp_headers.insert(k.as_str().to_string(), str_val.to_string());
                }
            }

            // Bounded response body reading
            let mut body_bytes = Vec::new();
            let mut truncated = false;
            let mut stream = response;

            while let Ok(Some(chunk)) = stream.chunk().await {
                if body_bytes.len() as u64 + chunk.len() as u64 > policy.response_size_limit_bytes {
                    let allowed = (policy.response_size_limit_bytes as usize)
                        .saturating_sub(body_bytes.len());
                    if allowed > 0 {
                        body_bytes.extend_from_slice(&chunk[..allowed]);
                    }
                    truncated = true;
                    break;
                } else {
                    body_bytes.extend_from_slice(&chunk);
                }
            }

            let raw_bytes_count = body_bytes.len() as u64;
            let body_str = String::from_utf8_lossy(&body_bytes).to_string();
            let total_dur = start_time.elapsed().as_millis() as u64;

            return Ok(HttpResponseResult {
                status_code,
                status_text: status.canonical_reason().unwrap_or("").to_string(),
                headers: resp_headers,
                body: body_str,
                truncated,
                raw_bytes_count,
                duration_ms: total_dur,
                dns_latency_ms: dns_latency,
                connect_latency_ms: conn_start.elapsed().as_millis() as u64,
                redirect_chain,
                remote_address: Some(validated_ip.to_string()),
                protocol: "HTTP/1.1".to_string(),
                security_classification: "UNTRUSTED_REMOTE_CONTENT".to_string(),
                error: None,
            });
        }
    }
}

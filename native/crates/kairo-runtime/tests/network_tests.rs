use kairo_protocol::network::{DnsResolveRequest, HttpRequestDescriptor};
use kairo_protocol::sandbox::{
    EnvironmentPolicy, ExecutionRequest, ExecutionState, OutputLimits, SandboxPolicy,
    SandboxProfile,
};
use kairo_protocol::ResourceBudget;
use kairo_runtime::cancellation::CancellationRegistry;
use kairo_runtime::metrics::RuntimeMetrics;
use kairo_runtime::sandbox::capabilities::SandboxCapabilityRegistry;
use kairo_runtime::sandbox::executor::SandboxExecutor;
use kairo_runtime::sandbox::network::{CircuitBreaker, RateLimiter, SsrfGuard};
use serde_json::json;
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};
use std::sync::Arc;
use std::time::Duration;

fn create_test_executor() -> SandboxExecutor {
    SandboxExecutor::new(
        Arc::new(SandboxCapabilityRegistry::new()),
        Arc::new(CancellationRegistry::new()),
        RuntimeMetrics::new(),
        8,
    )
}

#[tokio::test]
async fn test_native_net_capabilities_registered() {
    let registry = SandboxCapabilityRegistry::new();
    assert!(registry.get("native.net.resolve").is_some());
    assert!(registry.get("native.net.fetch").is_some());
    assert!(registry.get("native.net.request").is_some());
    assert!(registry.get("native.net.health").is_some());
}

#[test]
fn test_ssrf_guard_ip_classification() {
    // 1. Loopback
    let v4_loop = IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1));
    let v6_loop = IpAddr::V6(Ipv6Addr::LOCALHOST);
    assert!(SsrfGuard::is_loopback(&v4_loop));
    assert!(SsrfGuard::is_loopback(&v6_loop));
    assert!(SsrfGuard::validate_ip(&v4_loop, false).is_err());
    assert!(SsrfGuard::validate_ip(&v6_loop, false).is_err());

    // 2. Private IPv4 (RFC 1918)
    let p10 = IpAddr::V4(Ipv4Addr::new(10, 0, 1, 5));
    let p172 = IpAddr::V4(Ipv4Addr::new(172, 16, 0, 1));
    let p192 = IpAddr::V4(Ipv4Addr::new(192, 168, 1, 100));
    assert!(SsrfGuard::is_private_ip(&p10));
    assert!(SsrfGuard::is_private_ip(&p172));
    assert!(SsrfGuard::is_private_ip(&p192));
    assert!(SsrfGuard::validate_ip(&p10, false).is_err());
    assert!(SsrfGuard::validate_ip(&p172, false).is_err());
    assert!(SsrfGuard::validate_ip(&p192, false).is_err());

    // 3. Link-local & Cloud Metadata
    let meta_v4 = IpAddr::V4(Ipv4Addr::new(169, 254, 169, 254));
    let meta_v6 = "fd00:ec2::254".parse::<IpAddr>().unwrap();
    assert!(SsrfGuard::is_cloud_metadata(&meta_v4));
    assert!(SsrfGuard::is_cloud_metadata(&meta_v6));
    assert!(SsrfGuard::validate_ip(&meta_v4, false).is_err());
    assert!(SsrfGuard::validate_ip(&meta_v6, false).is_err());

    // 4. Multicast & Broadcast
    let multi = IpAddr::V4(Ipv4Addr::new(224, 0, 0, 1));
    let bcast = IpAddr::V4(Ipv4Addr::new(255, 255, 255, 255));
    assert!(SsrfGuard::is_multicast(&multi));
    assert!(SsrfGuard::is_broadcast(&bcast));
    assert!(SsrfGuard::validate_ip(&multi, false).is_err());
    assert!(SsrfGuard::validate_ip(&bcast, false).is_err());

    // 5. Public IP allows connection
    let pub_ip = IpAddr::V4(Ipv4Addr::new(8, 8, 8, 8));
    assert!(!SsrfGuard::is_private_ip(&pub_ip));
    assert!(!SsrfGuard::is_loopback(&pub_ip));
    assert!(SsrfGuard::validate_ip(&pub_ip, false).is_ok());
}

#[test]
fn test_ssrf_guard_hostname_validation() {
    assert!(SsrfGuard::validate_hostname("localhost").is_err());
    assert!(SsrfGuard::validate_hostname("sub.localhost").is_err());
    assert!(SsrfGuard::validate_hostname("metadata.google.internal").is_err());
    assert!(SsrfGuard::validate_hostname("service.local").is_err());
    assert!(SsrfGuard::validate_hostname("example.com").is_ok());
    assert!(SsrfGuard::validate_hostname("api.github.com").is_ok());
}

#[test]
fn test_ssrf_guard_port_validation() {
    let allowed = vec![80, 443];
    assert!(SsrfGuard::validate_port(80, &allowed).is_ok());
    assert!(SsrfGuard::validate_port(443, &allowed).is_ok());
    assert!(SsrfGuard::validate_port(22, &allowed).is_err());
    assert!(SsrfGuard::validate_port(3306, &allowed).is_err());
    assert!(SsrfGuard::validate_port(6379, &allowed).is_err());
}

#[tokio::test]
async fn test_circuit_breaker_transitions() {
    let cb = CircuitBreaker::new(3, Duration::from_millis(50));
    let host = "test-breaker.kairo";

    // Initially Closed
    assert!(cb.can_execute(host).await.is_ok());

    // Record 2 failures -> Still Closed
    cb.record_failure(host).await;
    cb.record_failure(host).await;
    assert!(cb.can_execute(host).await.is_ok());

    // 3rd failure trips to Open
    cb.record_failure(host).await;
    let res = cb.can_execute(host).await;
    assert!(res.is_err());
    assert!(res.unwrap_err().contains("CIRCUIT_OPEN"));

    // Cooldown elapsed -> Transitions to HalfOpen
    tokio::time::sleep(Duration::from_millis(60)).await;
    assert!(cb.can_execute(host).await.is_ok());

    // Success resets to Closed
    cb.record_success(host).await;
    assert!(cb.can_execute(host).await.is_ok());
}

#[tokio::test]
async fn test_rate_limiter_token_bucket() {
    let limiter = RateLimiter::new();
    let host = "test-rate.kairo";

    // 2 requests per minute limit
    assert!(limiter.check_and_consume(host, 2).await.is_ok());
    assert!(limiter.check_and_consume(host, 2).await.is_ok());

    // 3rd should be rate limited immediately
    let res = limiter.check_and_consume(host, 2).await;
    assert!(res.is_err());
    assert!(res.unwrap_err().contains("RATE_LIMITED"));
}

#[tokio::test]
async fn test_dns_resolve_ssrf_block_loopback() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-net-dns-1".to_string(),
        capability_id: "native.net.resolve".to_string(),
        arguments: vec!["127.0.0.1".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Standard,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({ "hostname": "127.0.0.1" }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::Failed);
    assert!(result.stderr.contains("SSRF_BLOCKED") || result.stderr.contains("Loopback"));
}

#[tokio::test]
async fn test_dns_resolve_ssrf_block_private() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-net-dns-2".to_string(),
        capability_id: "native.net.resolve".to_string(),
        arguments: vec!["10.254.1.1".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Standard,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({ "hostname": "10.254.1.1" }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::Failed);
    assert!(result.stderr.contains("PRIVATE_IP_BLOCKED") || result.stderr.contains("private"));
}

#[tokio::test]
async fn test_dns_resolve_ssrf_block_cloud_metadata() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-net-dns-3".to_string(),
        capability_id: "native.net.resolve".to_string(),
        arguments: vec!["169.254.169.254".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Standard,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({ "hostname": "169.254.169.254" }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::Failed);
    assert!(result.stderr.contains("SSRF_BLOCKED") || result.stderr.contains("Cloud metadata"));
}

#[tokio::test]
async fn test_emergency_stop_rejects_network() {
    let executor = create_test_executor();

    // 1. Activate Emergency Stop
    executor.network().set_emergency_stop(true);
    assert!(executor.network().is_emergency_stopped());

    // 2. Resolve DNS must be rejected
    let dns_res = executor
        .network()
        .resolve_dns(DnsResolveRequest {
            hostname: "example.com".to_string(),
            policy: None,
        })
        .await;
    assert!(dns_res.is_err());
    let err = dns_res.unwrap_err();
    assert_eq!(err.code, "EMERGENCY_STOP");

    // 3. HTTP fetch must be rejected
    let http_res = executor
        .network()
        .execute_http(
            HttpRequestDescriptor {
                method: "GET".to_string(),
                url: "http://example.com".to_string(),
                headers: std::collections::HashMap::new(),
                body: None,
                operation_class: kairo_protocol::network::NetworkOperationClass::Fetch,
                idempotency_key: None,
                policy: None,
            },
            None,
        )
        .await;
    assert!(http_res.is_err());
    assert_eq!(http_res.unwrap_err().code, "EMERGENCY_STOP");

    // 4. Reset Emergency Stop
    executor.network().set_emergency_stop(false);
    assert!(!executor.network().is_emergency_stopped());
}

#[tokio::test]
async fn test_network_health_report() {
    let executor = create_test_executor();
    let health = executor.network().get_health();
    assert_eq!(health.state, "HEALTHY");
    assert_eq!(health.active_requests, 0);
    assert_eq!(health.active_connections, 0);
    assert!(!health.circuit_breaker_open);
}

#[tokio::test]
async fn test_http_fetch_credentials_in_url_rejected() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-cred-1".to_string(),
        capability_id: "native.net.fetch".to_string(),
        arguments: vec!["http://user:secret@example.com/".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Standard,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({ "url": "http://user:secret@example.com/" }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::Failed);
    assert!(result.stderr.contains("CREDENTIALS_IN_URL_FORBIDDEN"));
}

#[tokio::test]
async fn test_http_fetch_unsupported_protocol() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-proto-1".to_string(),
        capability_id: "native.net.fetch".to_string(),
        arguments: vec!["ftp://example.com/file".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Standard,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({ "url": "ftp://example.com/file" }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::Failed);
    assert!(result.stderr.contains("UNSUPPORTED_PROTOCOL"));
}

#[tokio::test]
async fn test_http_fetch_ssrf_blocks_private_ip() {
    let executor = create_test_executor();
    let req = ExecutionRequest {
        request_id: "req-ssrf-1".to_string(),
        capability_id: "native.net.fetch".to_string(),
        arguments: vec!["http://127.0.0.1:80/secret".to_string()],
        working_directory: None,
        environment_policy: EnvironmentPolicy::default(),
        resource_budget: ResourceBudget::default(),
        output_limits: OutputLimits::default(),
        authorization_context: None,
        sandbox_policy: SandboxPolicy {
            profile: SandboxProfile::Standard,
            ..Default::default()
        },
        correlation_id: None,
        cancellation_id: None,
        payload: json!({ "url": "http://127.0.0.1:80/secret" }),
    };

    let result = executor.execute(req).await;
    assert_eq!(result.state, ExecutionState::Failed);
    assert!(result.stderr.contains("SSRF_BLOCKED") || result.stderr.contains("Loopback"));
}

# Kairo Native Network Execution & Connection Fabric (Task 85)

## 1. Overview & Architectural Boundaries

Kairo Subsystem 85 implements the **Native Network Execution & Connection Fabric**, establishing a high-performance, bounded, and hardened network transport substrate implemented in Rust, coordinated by Python governance.

### The Sacred Architectural Boundary
```
   ┌─────────────────────────────────────────────────────────────┐
   │                       PYTHON LAYER                          │
   │  • High-level reasoning, planning, and goal decomposition   │
   │  • URL selection and browser navigation semantics           │
   │  • SecurityCenter authorization & Governance approvals      │
   │  • EmergencyStop absolute authority                         │
   │  • Remote content is UNTRUSTED DATA (never instructions)    │
   └──────────────────────────────┬──────────────────────────────┘
                                  │ IPC Socket / Native Channel
   ┌──────────────────────────────▼──────────────────────────────┐
   │                     RUST RUNTIME DAEMON                     │
   │  • Connection pooling & persistent HTTP/1.1 & HTTP/2 pools  │
   │  • Bounded LRU DNS caching with anti-rebinding IP locking   │
   │  • Strict SSRF guard (RFC 1918, link-local, cloud metadata)  │
   │  • Streaming response limits & hard byte truncation         │
   │  • Token bucket rate limiting per host                      │
   │  • Circuit breaking (Closed -> Open -> HalfOpen)            │
   │  • Cooperative cancellation and deadline timeouts           │
   │  • Resource economy integration (native_network capacity)   │
   └─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Security Invariants

1. **Anti-DNS Rebinding (Pre-Validated Socket Resolution):**
   - Traditional HTTP clients resolve DNS and then pass the hostname to the socket connect function, allowing Time-of-Check to Time-of-Use (TOCTOU) DNS rebinding attacks where an attacker changes DNS records between resolution and connection.
   - Kairo's Rust substrate resolves the hostname via Tokio DNS, checks all resolved IP addresses against the SSRF guard, and injects the validated `SocketAddr` directly into `reqwest::ClientBuilder::resolve`. The socket connects strictly to the pre-validated IP.

2. **Strict SSRF Classification (`SsrfGuard`):**
   - Blocks IPv4 Loopback (`127.0.0.0/8`)
   - Blocks IPv4 Private Ranges (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
   - Blocks IPv4 Link-Local / AWS/GCP/Azure Cloud Metadata (`169.254.0.0/16`, explicitly `169.254.169.254`)
   - Blocks IPv4 Broadcast & Multicast (`224.0.0.0/4`, `255.255.255.255`, `0.0.0.0`)
   - Blocks IPv6 Loopback (`::1`), Unique Local (RFC 4193: `fc00::/7`), Link-Local (`fe80::/10`), Multicast (`ff00::/8`), and AWS IPv6 metadata (`fd00:ec2::254`)
   - Blocks Localhost and Internal Hostnames (`localhost`, `*.local`, `*.internal`, `*.lan`, `*.corp`, `*.home`, `*.arpa`)

3. **Untrusted Data Invariant:**
   - Any content retrieved over network protocols is strictly treated as untrusted data bytes.
   - Remote data is NEVER concatenated into system instructions or given prompt authority.

4. **EmergencyStop Authority:**
   - EmergencyStop is the supreme authority.
   - Activation instantly drops active sockets, cancels pending operations in the Tokio task registry, and rejects incoming requests fail-closed.

---

## 3. Substrate Capabilities

| Capability ID | Tool Name | Permission | Sandbox Profile | Description |
|---|---|---|---|---|
| `native.net.resolve` | `native_dns_resolve` | `READ` | `NETWORK_EGRESS` | Resolves hostnames to non-SSRF IP addresses with 60s LRU caching. |
| `native.net.fetch` | `native_http_fetch` | `READ` | `NETWORK_EGRESS` | Fast, pooled GET/HEAD requests with streaming response limits (10MB default). |
| `native.net.request` | `native_http_request` | `EXTERNAL` | `NETWORK_EGRESS` | Full HTTP verbs (POST, PUT, DELETE, PATCH) with governance approval and idempotency retries. |
| `native.net.health` | `system_telemetry` | `READ` | `STANDARD` | Live connection pool utilization, circuit breaker status, and SSRF defense metrics. |

---

## 4. Connection Pooling, Circuit Breaking & Rate Limiting

- **Connection Pool Tracker (`ConnectionPoolTracker`):**
  - Limits concurrent network requests via `tokio::sync::Semaphore` (default 64 concurrent).
  - Tracks active requests, active connections, total executed requests, total errors, and total blocked SSRF attempts.
- **Circuit Breaker (`CircuitBreaker`):**
  - Transitions from `Closed` to `Open` upon 5 consecutive connection/transport failures.
  - While `Open`, all requests to the target host fail fast with `CIRCUIT_BREAKER_OPEN`.
  - After a 30-second cooldown, transitions to `HalfOpen` to probe connectivity. A single successful probe closes the circuit.
- **Token Bucket Rate Limiter (`RateLimiter`):**
  - Per-host token bucket enforcing requests-per-minute (RPM) limits specified in `NetworkPolicy`.
  - Automatically refills tokens proportional to elapsed time.

---

## 5. Audit & Observability Lifecycle

The fabric emits structured events into Kairo's central `EventRegistry`:
- `network.request.accepted`
- `network.request.started`
- `network.dns.resolved`
- `network.connection.opened`
- `network.ssrf.blocked`
- `network.request.completed`
- `network.request.failed`
- `network.request.cancelled`
- `network.request.timed_out`
- `network.retry.attempted`
- `network.circuit_breaker.opened`
- `network.circuit_breaker.half_open`
- `network.circuit_breaker.closed`
- `network.rate_limit.exceeded`
- `network.body.truncated`
- `network.emergency_stop`

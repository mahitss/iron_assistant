# Kairo Resilience, Recovery, and Fault-Tolerant Runtime (Task 37)

The Resilience layer ensures Kairo remains robust, predictable, and secure when external dependencies, model providers, network connections, databases, or worker processes fail.

## Core Architectural Invariants

1. **Failure is Expected**: All external operations operate under explicit deadlines, bounded retries, and circuit breaker protection.
2. **Never Blindly Retry Side Effects**: Non-idempotent side effects with uncertain execution (`UNKNOWN_OUTCOME`) query the authoritative source state before taking further action.
3. **No Blind Resume**: Recovered tasks revalidate user authorization, target freshness, current policy version, device connectivity, and active approvals before continuing execution.
4. **Lease Fencing**: Distributed worker leases include monotonic fencing tokens. If a worker loses its lease, state mutations are strictly rejected.
5. **Fallback Security Invariance**: Fallbacks can never change the execution target (e.g., staging cannot fallback to production) and can never route `RESTRICTED` data to unauthorized providers.

## Key Modules

- `failures.py`: Deterministic failure categorization (`TRANSIENT`, `TIMEOUT`, `RATE_LIMITED`, `AUTHENTICATION`, `AUTHORIZATION`, `VALIDATION`, etc.) and secret sanitization.
- `backoff.py`: Exponential backoff with full jitter and HTTP `Retry-After` header parsing.
- `retry.py`: Bounded retries with per-operation, per-task, and per-provider budgets. Non-retryable guard for security and validation errors.
- `idempotency.py`: SHA256 idempotency key generation and execution deduplication.
- `reconciliation.py`: Authoritative state verification for `UNKNOWN_OUTCOME` operations.
- `leases.py`: Worker leases with heartbeats and monotonic fencing tokens to prevent split-brain execution.
- `watchdog.py`: Stuck task detection and quarantine management for poison tasks exceeding recovery limits.
- `circuit_breaker.py`: Scoped circuit breakers (`CLOSED`, `OPEN`, `HALF_OPEN`) per provider, service, or endpoint.
- `timeout.py`: Hierarchical deadline propagation and nested timeout budgets.
- `checkpoint.py`: Versioned, sanitized task checkpoints with corruption detection and fallback.
- `recovery.py`: Safe task recovery engine enforcing the *No Blind Resume* protocol.
- `fallback.py`: Multi-tier fallback hierarchy preserving data classification and scope boundaries.
- `degradation.py`: Read-only mode and non-critical feature shedding.
- `health.py`: Lightweight real probes (database, redis) distinguishing process liveness from operational readiness.
- `dedupe.py`: Sliding-window event deduplication and monotonic sequence ordering.
- `outbox.py`: Resilient bridge to transactional outbox for event durability.
- `manager.py`: Singleton coordinator `resilience_manager`.
- `router.py`: REST APIs for observability, circuit breaker management, and quarantine operations.

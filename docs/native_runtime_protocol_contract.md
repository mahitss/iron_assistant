# Kairo Native Runtime Protocol Hardening & Distributed Execution Contract (Task 87)

## 1. Architectural Overview & Boundaries

The **Kairo Native Runtime Protocol Contract** hardens the inter-process communication (IPC) boundary between the Python orchestration engine and the native Rust execution substrate. It formalizes a versioned, authenticated, typed, crash-safe, and replay-resistant distributed execution contract.

```
+-----------------------------------------------------------------------------------+
|                            PYTHON ORCHESTRATION LAYER (BRAIN)                     |
|  - Intent interpretation, planning, reasoning, policy governance, approvals       |
|  - Workflow orchestration, verification, continuous experience learning          |
|  - Decorates IPC requests with Authorization, Resource, and Target contexts       |
|  - Tracks pending requests and reconciles orphaned executions on disconnect       |
|  - Enforces at-most-once semantics for side-effects, idempotent read retries      |
+------------------------------------------^----------------------------------------+
                                           | Length-Prefixed Framing (4-byte BE)
                                           | Versioned Typed JSON Envelope
+------------------------------------------v----------------------------------------+
|                          NATIVE RUST SUBSTRATE (BODY)                             |
|  - Low-level execution substrate, process supervision, OS sandbox primitives      |
|  - Cryptographic capability attestation & configuration fingerprinting            |
|  - Session binding (sess_...) and SemVer protocol negotiation                     |
|  - Anti-TOCTOU target validation (hash revalidation before mutation)             |
|  - Bounded ReplayGuard (5,000 LRU deduplication, session freshness check)        |
|  - Unified deadline & timeout enforcement: min(rem_ms, req.deadline_ms)          |
|  - Emergency stop fast-path (sys.stop) with preemption and token draining         |
+-----------------------------------------------------------------------------------+
```

### Core Invariants & Boundaries

1. **Python is the Brain, Rust is the Body**:
   - Python owns all reasoning, workflow planning, policy evaluation, risk classification, user approvals, and causal attribution.
   - Rust owns native execution, sandbox boundaries, OS resource limits (Job Objects / cgroups), and low-level computer/network primitives.
2. **Strict Anti-Duplication Rule**:
   - Rust **NEVER** re-implements business logic, prompt engineering, policy engines, ethical rules, or approval workflows.
   - Rust strictly enforces structural invariants received in typed contract headers (`AuthorizationContext`, `ResourceAllocationContext`, `OperationTargetContext`).
3. **Execution Semantics**:
   - **Mutating Operations (EXTERNAL_MUTATION)**: Strict **at-most-once** execution. Re-dispatch is prohibited if execution status is unconfirmed.
   - **Safe Reads (SAFE_READ)**: Idempotent retry allowed on network glitch or timeout.
   - **Disconnect / Transport Drop**: If the transport drops while an external mutation is inflight, the status is irrevocably classified as **`UNKNOWN_OUTCOME`** until explicitly reconciled by Python.
4. **No Unauthenticated Execution**:
   - Every request must provide a valid session ID issued during the initial cryptographic handshake.

---

## 2. Protocol Versioning & SemVer Negotiation

The protocol adheres to Semantic Versioning (`MAJOR.MINOR.PATCH`):
- **Current Canonical Protocol Version**: `1.0.0` (with wire-compatibility alias `1.0`).

### Compatibility Matrix
- Protocol versions are compatible if and only if:
  1. `client.major == runtime.major`
  2. `client.minor <= runtime.minor` (the runtime supports backward-compatible minor extensions).
- If `client.major != runtime.major`, the handshake fails immediately with `ProtocolError::IncompatibleVersion`.

```rust
// Negotiation logic in kairo-protocol/src/contract.rs
impl ProtocolVersion {
    pub fn is_compatible_with(&self, runtime: &ProtocolVersion) -> bool {
        self.major == runtime.major && self.minor <= runtime.minor
    }
}
```

---

## 3. Cryptographic Attestation & Configuration Fingerprinting

Upon connection establishment and during `sys.contract` introspection, the native runtime generates deterministic cryptographic fingerprints:

1. **Capability Fingerprint (`cfp_...`)**:
   - Derived from the SHA-256 hash of sorted, canonical JSON descriptors of all registered capabilities (id, version, execution class, side-effect class, supported operations, enforcement levels).
   - Format: `cfp_<hex_16>` (e.g., `cfp_8b33a5101be4b8ad`).
   - Guarantees that Python and Rust share an identical understanding of the capability matrix without manual sync drift.

2. **Configuration Fingerprint (`cfg_...`)**:
   - Derived from the SHA-256 hash of runtime configuration parameters (max concurrent jobs, buffer capacities, log levels, replay window size, enforcement mode).
   - Format: `cfg_<hex_16>` (e.g., `cfg_bb70a6d2b86f0dc5`).
   - Any runtime reconfiguration immediately changes the fingerprint, signaling callers to re-verify runtime assumptions.

---

## 4. Distributed Execution Contract Envelopes

Every execution request (`RuntimeRequest`) sent over the IPC wire includes three strongly typed contract contexts:

### 1. AuthorizationContext
```rust
pub struct AuthorizationContext {
    pub decision_id: String,
    pub policy_id: Option<String>,
    pub security_level: String,
    pub approval_id: Option<String>,
    pub approved_tool: Option<String>,
    pub approved_target: Option<String>,
    pub granted_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
    pub signature_hash: Option<String>,
}
```
- **Rust Substrate Validation**:
  - Validates `expires_at > now`. If expired, rejects immediately with `RuntimeError::RequestExpired`.
  - Validates `approved_tool == req.operation` (if specified). Mismatches yield `RuntimeError::AuthorizationScopeMismatch`.
  - Validates `approved_target == target_context.target_identifier` (if specified).

### 2. ResourceAllocationContext
```rust
pub struct ResourceAllocationContext {
    pub allocation_id: String,
    pub request_id: String,
    pub capability_id: String,
    pub limits: ResourceBudget,
    pub remaining_budget: Option<ResourceBudget>,
    pub expires_at: DateTime<Utc>,
}
```
- **Rust Substrate Validation**:
  - Validates reservation expiry (`expires_at > now`).
  - Enforces `limits` against system Job Objects, memory thresholds, CPU shares, and file handle quotas.

### 3. OperationTargetContext & Anti-TOCTOU Revalidation
```rust
pub struct OperationTargetContext {
    pub target_type: String,
    pub target_identifier: String,
    pub expected_hash: Option<String>,
}
```
- **Time-Of-Check to Time-Of-Use (TOCTOU) Defense**:
  - Before modifying a file, system resource, or process, the runtime compares `expected_hash` with the payload's `target_hash` or the on-disk state.
  - If a discrepancy is detected (e.g., file modified by an external process after Python's approval), execution is aborted with `TARGET_CHANGED` (`RuntimeError::TargetChanged`).

---

## 5. Bounded ReplayGuard & Deduplication

To prevent replay attacks, retransmitted packets, or duplicate tool executions, `kairo-runtime` implements an in-memory, session-bound `ReplayGuard`:

1. **Window Size**: Fixed capacity of **5,000 requests** managed via an LRU eviction policy.
2. **Freshness Invariant**:
   - Rejects any request where `now - created_at > 300,000 ms` (5 minutes) with `RuntimeError::RequestExpired`.
   - Rejects any request where `deadline < now` with `RuntimeError::RequestExpired`.
3. **Duplicate Detection & Cache Serving**:
   - When a duplicate `(session_id, message_id)` is observed:
     - If the initial execution completed, `ReplayGuard` returns `ReplayDecision::Cached(Box<RuntimeResponse>)`.
     - The runtime returns the previously computed response immediately without re-executing side effects.
     - If the initial execution is currently inflight, the runtime returns `RuntimeError::RequestDuplicate`.

---

## 6. Disconnect Handling & UNKNOWN_OUTCOME Semantics

In a distributed agent architecture, connection loss between Brain and Body during an external mutation is a critical failure mode:

```
[Python Brain] ------------------- (req: mutate file) -------------------> [Rust Body]
                       [Connection Drops / TCP Reset]
[Python Brain] <------------------ [Result Lost] ----------------------- [Rust Body]
```

1. **Client Disconnect Detection**:
   - If the IPC transport disconnects while a request is in-flight:
     - If the operation is a `SAFE_READ`, the client marks it retryable.
     - If the operation is an `EXTERNAL_MUTATION`, the client immediately wraps the failure in a `RuntimeResponse` with `ResponseStatus::UNKNOWN_OUTCOME` and records it in `service._orphans`.
2. **Orphan Tracking & Reconciliation**:
   - `NativeRuntimeService` maintains an in-memory orphan registry (`_orphans`).
   - Operators or background reconciliation tasks call `POST /api/v1/native/orphans/reconcile` (or `service.reconcile_orphans()`).
   - The reconciliation procedure logs audit events (`protocol.orphan.detected`), releases associated resource reservations in `ResourceAllocationRegistry`, and transitions execution states to `ORPHAN_ABORTED`.

---

## 7. Emergency Stop Fast-Path (`sys.stop`)

When a safety policy is breached, or an operator triggers emergency halt:

1. **Preemption Priority**:
   - `sys.stop` operates on a dedicated priority channel bypassing normal job queues.
2. **Token Draining**:
   - Cancels all active cancellation tokens across all worker threads.
   - Clears pending dispatch queues and transitions `RuntimeState` to `STOPPING` -> `DRAINED`.
3. **Execution Rejection**:
   - Once draining begins, subsequent requests are rejected immediately with `RuntimeError::EmergencyStopped`.

---

## 8. State Transition Models

### Message Lifecycle States (14 States)
`RECEIVED` -> `VALIDATING` -> `SESSION_BOUND` -> `AUTHORIZED` -> `RESERVED` -> `SCHEDULED` -> `EXECUTING` -> `SUCCEEDED` / `FAILED` / `REJECTED` / `CANCELLED` / `TIMED_OUT` / `UNKNOWN_OUTCOME` / `ORPHAN_ABORTED`.

### Runtime States (11 States)
`UNINITIALIZED` -> `INITIALIZING` -> `READY` -> `DEGRADED` -> `DRAINING` -> `STOPPING` -> `STOPPED` -> `DISCONNECTED` -> `RECONNECTING` -> `RECOVERING` -> `TERMINATED`.

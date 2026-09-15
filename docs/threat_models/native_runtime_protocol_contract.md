# Kairo Native Runtime Protocol Contract Threat Model (Task 87)

This document analyzes the security threats, adversarial vectors, defenses, and platform guarantees governing the **Native Runtime Protocol & Distributed Execution Contract**.

---

## 1. Threat Matrix Overview

| Threat ID | Threat Name | Severity | Primary Defense Mechanism | Residual Risk / Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **NRPC-01** | Protocol Downgrade & Version Confusion | **High** | Strict SemVer major compatibility check (`client.major == runtime.major`); rejected immediately if incompatible. | Zero-day vulnerabilities within accepted backward-compatible minor versions. |
| **NRPC-02** | Session Hijacking & Cross-Session Spoofing | **Critical** | Cryptographic random `session_id` (`sess_<hex32>`) tied to initial handshake; every subsequent frame verified against session cache. | Compromise of host memory where session secret is resident. |
| **NRPC-03** | Replay Attack on Mutating Operations | **Critical** | In-memory `ReplayGuard` (5,000 LRU window), 5-minute freshness check, and cached response return for duplicate message IDs. | Eviction from LRU window after 5,000 intervening requests outside 5-minute freshness threshold. |
| **NRPC-04** | Time-Of-Check to Time-Of-Use (TOCTOU) State Drift | **Critical** | Mandatory `expected_hash` verification in `OperationTargetContext` immediately before native execution; returns `TARGET_CHANGED` on mismatch. | Workloads operating on unhashable streaming sources. |
| **NRPC-05** | Authorization Scope Confusion / Scope Escape | **Critical** | Dual-layer binding in Rust dispatcher: `approved_tool == req.operation` and `approved_target == target_context.target_identifier`. | Overly broad approvals granted by Python brain policy engine. |
| **NRPC-06** | Resource Exhaustion via Long-Running Operations | **High** | Unified deadline enforcement: `effective_timeout = min(remaining_ms, req.deadline_ms)`; cooperative cancellation tokens and OS Job Object bounds. | OS kernel delays during process kill operations. |
| **NRPC-07** | In-Flight Disconnect Drift (Zombie / Orphan Mutations) | **Critical** | `UNKNOWN_OUTCOME` classification for mutating operations on disconnect; Python orphan tracker with resource release reconciliation. | Manual forensic verification required if external system has no queryable state. |
| **NRPC-08** | Emergency Stop Starvation under Task Load | **Critical** | Priority channel for `sys.stop` bypassing execution queue; atomic cancellation token broadcast; immediate drain and execution rejection. | Synchronous native C/Win32 calls that do not check cancellation tokens. |
| **NRPC-09** | Length-Prefixed Framing Buffer Overflows & Framing Attacks | **High** | 4-byte big-endian length prefix with hard max frame limit (16MB); malformed payloads trigger graceful frame drop and error envelope. | Malformed frame causing TCP stream de-synchronization (mitigated by closing connection). |
| **NRPC-10** | Capability Matrix Drift & Covert Native Primitives | **High** | Cryptographic SHA-256 capability fingerprint (`cfp_...`) verified at handshake and queryable via `sys.contract`. | Binary tampering post-compilation (mitigated by signed binaries and OS file integrity). |

---

## 2. In-Depth Threat Analysis

### NRPC-01: Protocol Downgrade & Version Confusion
- **Attack Vector:** An attacker sends an outdated protocol version (`0.1`) with deprecated lax security constraints or malformed headers to bypass Task 87 contract requirements.
- **Architectural Defense:**
  1. The Rust runtime parses the client version using `ProtocolVersion::parse`.
  2. Compatibility requires `client.major == runtime.major` and `client.minor <= runtime.minor`.
  3. Version mismatches produce `ProtocolError::IncompatibleVersion` and terminate the connection before any operations can be dispatched.

### NRPC-02: Session Hijacking & Cross-Session Spoofing
- **Attack Vector:** An adversary injects IPC packets on port 8798 claiming to be an already authenticated session, executing arbitrary system calls.
- **Architectural Defense:**
  1. Handshake requires HMAC-SHA256 authentication with a pre-shared secret known only to the Python parent process and the spawned Rust daemon.
  2. The runtime generates a cryptographically random `session_id` (`sess_<32 hex chars>`).
  3. Every incoming `RuntimeRequest` must supply the matching `session_id`. Requests with mismatched or absent session IDs are dropped with `RuntimeError::SessionInvalid`.

### NRPC-03: Replay Attack on Mutating Operations
- **Attack Vector:** A network glitch causes retransmission, or an attacker captures and replays a signed mutating request (e.g. `native.clipboard.write` or `native.tool.execute`).
- **Architectural Defense:**
  1. The `ReplayGuard` maintains an LRU cache of `(session_id, message_id)`.
  2. If the request was already processed, the runtime returns `ReplayDecision::Cached` containing the previous response. **No re-execution occurs.**
  3. Requests with `timestamp` older than 5 minutes or past their `deadline` are discarded with `RuntimeError::RequestExpired`.

### NRPC-04: Time-Of-Check to Time-Of-Use (TOCTOU) State Drift
- **Attack Vector:** Python approves a file edit based on content hash `H1`. Between the approval check and the native execution, another process alters the file to `H2`. The native tool executes against modified content, leading to data corruption or code execution.
- **Architectural Defense:**
  1. `OperationTargetContext` conveys `expected_hash`.
  2. The native dispatcher computes the current hash of the target prior to calling the underlying primitive.
  3. If current hash != `expected_hash`, execution aborts with `TARGET_CHANGED` and status `ERROR`.

### NRPC-05: Authorization Scope Confusion / Scope Escape
- **Attack Vector:** A request carries a valid `AuthorizationContext` granted for `sys.ping`, but specifies `native.tool.execute` in the operation field.
- **Architectural Defense:**
  1. The Rust dispatcher verifies `auth_ctx.approved_tool == req.operation`.
  2. If the context restricts targets (`auth_ctx.approved_target`), it is verified against `target_context.target_identifier`.
  3. Violations trigger `RuntimeError::AuthorizationScopeMismatch`.

### NRPC-06: Resource Quota Exhaustion & Denial of Service
- **Attack Vector:** A malicious or buggy task requests unbounded memory or loops infinitely, exhausting host CPU and memory.
- **Architectural Defense:**
  1. `ResourceAllocationContext` specifies strict `ResourceBudget` limits.
  2. The runtime binds the process to a Windows Job Object or Linux cgroup restricting peak commit charge and CPU rate.
  3. Deadlines are unified via `min(now + remaining_ms, req.deadline_ms)` and actively monitored.

### NRPC-07: In-Flight Disconnect Drift (Zombie / Orphan Mutations)
- **Attack Vector:** An IPC disconnection occurs while a mutation is running. Python cannot tell whether the mutation occurred and assumes failure, triggering an unsafe duplicate retry.
- **Architectural Defense:**
  1. The client flags all unconfirmed mutating operations as `UNKNOWN_OUTCOME` and forbids automatic retry.
  2. In-flight requests are spooled into `NativeRuntimeService._orphans`.
  3. The `reconcile_orphans()` endpoint frees reservations and flags downstream workflows to initiate forensic validation.

### NRPC-08: Emergency Stop Starvation under Task Load
- **Attack Vector:** A runaway workload floods the dispatch queue, delaying the processing of an emergency stop command.
- **Architectural Defense:**
  1. `sys.stop` bypasses worker thread dispatch queues and is processed immediately on the control plane listener.
  2. Signals an atomic `CancellationToken` shared by all active workers.
  3. Immediately rejects subsequent incoming requests with `RuntimeError::EmergencyStopped`.

### NRPC-09: Length-Prefixed Framing Buffer Overflows
- **Attack Vector:** An attacker sends a 4-byte prefix claiming a 2GB payload, causing an out-of-memory crash.
- **Architectural Defense:**
  1. The transport layer limits maximum frame size to 16MB.
  2. Any frame header indicating >16MB causes immediate disconnection and connection state transition to `ERROR`.

### NRPC-10: Capability Matrix Drift & Covert Native Primitives
- **Attack Vector:** An attacker replaces the native runtime binary with one exposing unauthorized capabilities.
- **Architectural Defense:**
  1. The runtime calculates `capability_fingerprint` by hashing all registered capability metadata.
  2. Python verifies `capability_fingerprint` during handshake. Any drift from known manifests triggers an attestation alert.

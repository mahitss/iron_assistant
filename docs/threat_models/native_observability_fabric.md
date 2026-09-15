# Kairo Native Observability Fabric Threat Model (Task 86)

This document analyzes the specific security threats, attack surfaces, defenses, and platform guarantees governing the **Native Event, Telemetry & Observability Fabric**.

---

## 1. Threat Matrix Overview

| Threat ID | Threat Name | Severity | Primary Defense Mechanism | Residual Risk / Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **NOF-01** | Secret & Credential Exfiltration via Telemetry | **Critical** | Dual-layer regex sanitization (`TelemetrySanitizer` in Python, `NativeRedactor` in Rust) masking keys, tokens, URIs, and basic auth headers. | Novel proprietary secret formats not matching regex patterns (mitigated by key-name heuristic masking). |
| **NOF-02** | Private Chain-of-Thought (CoT) Persistence | **Critical** | Strict schema validation; stripping of `<thought>` tags and `reasoning_content` before event dispatch. | Downstream log forwarder misconfiguration (mitigated at source emission layer). |
| **NOF-03** | Telemetry Flooding Denial of Service (DoS) | **High** | Fixed-capacity ring-buffers (5,000 native, 2,000 Python) with priority-aware backpressure shedding P3/P2. | High CPU consumption under continuous flood (mitigated by atomic dropped counters). |
| **NOF-04** | Critical Audit Log Eviction via Event Flooding | **Critical** | Priority-tier enforcement: P0 (Critical) and P1 (Security/Error) events are **NEVER DROPPED**; lower-tier events are evicted first. | Long-term cold storage disk saturation (handled by log rotation). |
| **NOF-05** | Replay-Triggered Side-Effect Execution | **Critical** | Strict data-only replay invariance: replay endpoints return read-only JSON projections and are physically decoupled from execution dispatchers. | None; replay components have no reference or binding to runtime dispatchers. |
| **NOF-06** | Observability Outcome Authorization Spoofing | **Critical** | Architectural separation: Observability reports outcomes (`ALLOW`, `DENY`, `FAIL`) for visibility only; SecurityCenter evaluates policy independently. | Developer confusion between observability events and security gating (enforced by code linting & architecture boundaries). |
| **NOF-07** | Timeline Forgery & Clock Skew Manipulation | **High** | Monotonic nanosecond sequencing via `std::time::Instant`; timelines ordered deterministically by monotonic timestamps. | System reboot resetting process start instant (mitigated by correlation ID binding). |
| **NOF-08** | Deep Recursion Serialization Bombs | **High** | Maximum recursion depth limits (10 levels) and 64KB payload bounds with attribute count limits (100 per level). | Truncation of legitimately large debug data (hash preserved). |
| **NOF-09** | Cross-Tenant Telemetry Data Leakage | **High** | Project and tenant context filtering on `/api/v1/observability/traces` and execution endpoints. | Shared correlation IDs across tenants (mitigated by UUIDv4 generation). |
| **NOF-10** | Telemetry Failure Crashing Core Workload | **Critical** | Fail-safe telemetry design: panic containment around telemetry capture; failures logged and dropped without interrupting core execution. | Missing telemetry during catastrophic out-of-memory events. |

---

## 2. In-Depth Threat Analysis

### NOF-01: Secret & Credential Exfiltration via Telemetry Payloads
- **Attack Vector:** An agent interacts with an external API containing secret API keys (`sk-ant-...`, `Bearer ey...`) or connects to a database (`postgres://user:pass@host/db`). The raw response or connection parameters are emitted in an event payload.
- **Architectural Defense:**
  1. All events must pass through `NativeRedactor::redact_json` in Rust or `TelemetrySanitizer.sanitize_event_payload` in Python prior to buffer insertion, dispatch, or logging.
  2. Redaction patterns cover PEM private keys, database URIs with passwords, HTTP Basic auth headers, embedded URL credentials, sensitive query parameters (`?api_key=`, `?secret=`, etc.), and known vendor tokens (OpenAI, Anthropic, AWS, GitHub, Slack).
  3. Negative lookahead regex patterns `(?!\[REDACTED)` prevent recursive re-redaction corruption.

### NOF-02: Private Chain-of-Thought (CoT) Persistence
- **Attack Vector:** An LLM generates internal reasoning steps containing proprietary prompts, speculative safety checks, or unverified intermediate steps. Storing these creates legal, privacy, and intellectual property exposure.
- **Architectural Defense:**
  1. The canonical event registry in `backend/app/events/registry.py` strictly excludes raw reasoning fields.
  2. Event schemas enforce bounded `payload` dictionaries that reject `<thought>` and `reasoning_content` keys.
  3. Pre-dispatch sanitization scrubs chain-of-thought blocks before events enter the dispatcher queue.

### NOF-03 & NOF-04: Telemetry Flooding & Critical Audit Log Eviction
- **Attack Vector:** A compromised sandbox or runaway process emits millions of debug-level events (`runtime.debug`, `network.packet`) in an attempt to exhaust host memory or evict critical security events (`security.policy_denied`, `governance.violation`).
- **Architectural Defense:**
  1. Both the Rust substrate (`NativeEventBuffer`) and Python dispatcher implement **priority-aware backpressure**:
     - **P0 (Critical)**: Panics, crash alerts, security breaches. **Drop probability = 0%**.
     - **P1 (Security / Error)**: Action blocks, policy rejections, task errors. **Drop probability = 0%**.
     - **P2 (Info / Lifecycle)**: Regular task completions, lifecycle transitions. Shed when buffer reaches capacity.
     - **P3 (Debug)**: High-volume traces. First to be shed immediately under buffer pressure.
  2. If the buffer is full when a P0/P1 event arrives, the buffer evicts older P3 or P2 entries to make room. If all entries are high priority, the Python dispatcher falls back to synchronous direct dispatch.
  3. Atomic drop counters (`dropped_p3`, `dropped_p2`) track shed volumes for audit reporting.

### NOF-05: Replay-Triggered Side-Effect Execution
- **Attack Vector:** An operator or forensic investigator requests `/api/v1/observability/replay/{correlation_id}`. A flawed implementation treats "replay" as "re-execution", re-issuing tool calls, file writes, or IPC commands.
- **Architectural Defense:**
  1. Section 26 Invariance: **Data-Only Replay**.
  2. `timeline_reconstructor.replay_events(correlation_id)` is a pure read query on the in-memory timeline store.
  3. Replay components have zero dependency on `ToolExecutor`, `NativeRuntimeClient`, or the action execution engine. Replay returns serialized event dictionaries strictly for forensic visualization.

### NOF-06: Observability Outcome Authorization Spoofing
- **Attack Vector:** An attacker constructs a synthetic telemetry event with `outcome: "ALLOW"` or `outcome: "SUCCESS"` and injects it to bypass a security policy checkpoint.
- **Architectural Defense:**
  1. **Strict Non-Authoritative Boundary**: The security engine (`SecurityCenter`, `PolicyEngine`) is completely separate from observability. Policy engines evaluate security context, credentials, and rule sets directly.
  2. Observability consumes outcomes as passive historical data. No system authorization, gating, or capability access decision ever inspects telemetry event history or outcomes.

### NOF-07: Timeline Forgery & Clock Skew Manipulation
- **Attack Vector:** An attacker alters system time (via NTP or OS clock tampering) to re-order execution events, obscuring the causal sequence of an exploit.
- **Architectural Defense:**
  1. Timelines are reconstructed using `monotonic_timestamp_ns`, captured via `std::time::Instant` in Rust.
  2. `Instant` measurements are based on hardware performance counters (e.g. TSC / QPC on Windows) and are completely immune to wall-clock time modifications or NTP adjustments.
  3. Causal DAG relationships (`causation_id`, `parent_event_id`) preserve the logical execution sequence independently of timestamps.

### NOF-08: Deep Recursion Serialization Bombs
- **Attack Vector:** An attacker passes a self-referential or 1,000-level nested dictionary in an operation parameter to cause a Python `RecursionError` or Rust stack overflow during telemetry serialization.
- **Architectural Defense:**
  1. `TelemetrySanitizer` enforces a maximum recursion depth of 10. Once exceeded, deeper levels are pruned and replaced with `{"_depth_exceeded": true}`.
  2. Payload size is capped at 64 KB, and attribute count per level is capped at 100 attributes.

### NOF-10: Telemetry Failure Crashing Core Workload
- **Attack Vector:** An unexpected exception in a telemetry listener or metric counter crashes an active workflow.
- **Architectural Defense:**
  1. Telemetry emission is strictly fail-safe. In Rust, dispatcher telemetry is wrapped in non-panicking constructs; in Python, the event dispatcher wraps handler invocations in isolated try/except blocks.
  2. Telemetry failures are logged to stderr or increment error counters without propagating exceptions to caller business logic.

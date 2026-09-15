# Kairo Native Event, Telemetry & Observability Fabric (Task 86)

## 1. Architectural Overview & Boundaries

The **Kairo Native Event, Telemetry & Observability Fabric** establishes a unified, strongly typed, low-overhead nervous system that spans the Python orchestration layer and the native Rust execution substrate.

```
+-----------------------------------------------------------------------------------+
|                            PYTHON ORCHESTRATION LAYER                             |
|  - Semantic event interpretation & governance (Policy, SecurityCenter, Ethics)    |
|  - Forensic execution timeline reconstruction & causal failure diagnosis          |
|  - Deterministic error fingerprinting (normalized hashes, no jitter)              |
|  - Dependency-aware subsystem health aggregation across 11 core subsystems        |
|  - Data-only replay projections (strictly free of execution side-effects)         |
+------------------------------------------^----------------------------------------+
                                           | IPC Frame Bridge
                                           | (Correlation / Trace Propagation)
+------------------------------------------v----------------------------------------+
|                          NATIVE RUST SUBSTRATE (kairo-runtime)                    |
|  - Low-level factual event emission (deterministic, unopinionated facts)          |
|  - Monotonic nanosecond duration measurement (std::time::Instant)                 |
|  - Bounded ring-buffer storage (5,000 capacity) with priority-aware drop          |
|  - NativeRedactor: zero private CoT, centralized secret & key token masking       |
|  - Distributed correlation draining via RuntimeResponse envelope                  |
+-----------------------------------------------------------------------------------+
```

### Core Invariants & Boundaries

1. **Single Unified System**:
   - There is only **one** event bus, **one** audit system, **one** logging pipeline, **one** metrics collector, and **one** tracing system in Kairo. Task 86 strictly unifies and hardens `backend/app/events/` and `backend/app/observability/` with `native/crates/kairo-protocol` and `native/crates/kairo-runtime`.
2. **Strict Division of Responsibilities**:
   - **Python** owns reasoning, intent interpretation, governance enforcement, forensic reconstruction, error deduplication, and dependency health analysis.
   - **Rust** owns factual event emission, microsecond/nanosecond interval capture (`Instant`), ring-buffered local event spooling, and IPC correlation metadata propagation.
3. **Observability Reports Outcomes, Never Authorizes**:
   - Telemetry tracks status (`ALLOW`, `DENY`, `BLOCK`, `FAIL`, `CANCEL`, `TIMEOUT`, `UNKNOWN`, `SUCCESS`), but **NEVER** decides authorization, gating, or security permissions.
4. **Fail-Safe Telemetry vs Fail-Closed Security**:
   - Failures within the telemetry collection layer must never crash the core runtime.
   - Mandatory security audit invariants adhere to strict fail-closed requirements.
5. **Zero Private Chain-of-Thought (CoT) Persisted or Logged**:
   - Telemetry payloads, event envelopes, and audit logs are strictly barred from storing internal model reasoning tokens, thinking blocks, or scratchpad text.
6. **Data-Only Replay Invariance**:
   - Execution replays produce read-only forensic projections. They are physically barred from re-invoking tools, re-issuing IPC requests, or triggering external mutations.

---

## 2. Canonical Event & Telemetry Schemas

### Envelope Schema

Every event emitted across Python and Rust conforms to the canonical envelope schema:

| Field | Type | Description |
| :--- | :--- | :--- |
| `event_id` | `str` / `String` | Globally unique event identifier (`evt_...`). |
| `event_type` | `str` / `String` | Canonical dot-delimited type (e.g. `runtime.request.received`). |
| `monotonic_timestamp_ns` | `u64` / `int` | Monotonic nanoseconds from process/boot start (`Instant`). |
| `wall_timestamp_utc` | `DateTime<Utc>` / `datetime` | UTC wall clock time for historical indexing. |
| `correlation_id` | `Optional[str]` | Unique distributed execution correlation ID. |
| `causation_id` | `Optional[str]` | ID of the event or operation directly causing this event. |
| `trace_id` | `Optional[str]` | Distributed tracing context trace ID. |
| `span_id` | `Optional[str]` | Identifier of the active execution span. |
| `parent_event_id` | `Optional[str]` | Explicit parent event in the causal DAG. |
| `execution_domain` | `str` / `Enum` | Domain (`RUNTIME`, `EXECUTION`, `RESOURCE`, `SECURITY`, `COMPUTER`, `NETWORK`, `TOOL`, `HEALTH`). |
| `severity` | `str` / `Enum` | Severity level (`DEBUG`, `INFO`, `NOTICE`, `WARN`, `ERROR`, `CRITICAL`). |
| `privacy_class` | `str` / `Enum` | Classification (`PUBLIC`, `INTERNAL`, `RESTRICTED`, `CONFIDENTIAL`). |
| `outcome` | `str` / `Enum` | Observational outcome (`SUCCESS`, `FAIL`, `BLOCK`, `DENY`, `CANCEL`, `TIMEOUT`, `UNKNOWN`). |
| `component` | `str` / `String` | Originating component / subsystem name. |
| `payload` | `Dict[str, Any]` / `Value` | Sanitized, bounded structured event payload. |

### Priority Tiers & Backpressure Shedding

Every event is categorized into a priority tier governing retention under resource pressure:

- **P0 (Tier 0 - Critical)**: System panics, security violations, unrecoverable crashes, audit trail integrity failures. **NEVER DROPPED**.
- **P1 (Tier 1 - Security / Error)**: Action blocks, policy denials, operation errors, rate-limit thresholds. **NEVER DROPPED**.
- **P2 (Tier 2 - Info / Lifecycle)**: State transitions, normal completions, health reports, standard audits. Shed under severe backpressure.
- **P3 (Tier 3 - Debug)**: Verbose diagnostics, high-frequency internal traces. First to be shed under queue pressure.

### Bounded Payloads

Payload bounding guarantees deterministic memory overhead:
- **Maximum Payload Size**: 64 KB per event. Excess strings are truncated with `...[TRUNCATED]` while maintaining SHA-256 hash validation.
- **Maximum Attributes**: 100 attributes per dictionary level.
- **Maximum Recursion Depth**: 10 nested levels. Exceeded depths are safely terminated with `{"_depth_exceeded": true}`.

---

## 3. Distributed Correlation & Monotonic Span Timing

Distributed tracing without external dependencies relies on the native substrate's `NativeTracer`:

1. **Monotonic Nanoseconds**:
   - Durations are measured using `std::time::Instant::now()`, completely immune to NTP adjustments, daylight savings shifts, or system clock skew.
2. **Context Propagation**:
   - Python's `NativeRuntimeClient` injects `correlation_id`, `trace_id`, `span_id`, and `causation_id` into every `RuntimeRequest`.
   - The native runtime dispatcher initializes a native span, emits `runtime.request.received`, performs execution, emits `runtime.request.completed` or `runtime.request.failed`, and attaches drained correlation events into `RuntimeResponse.native_events`.
3. **Bridge Ingestion**:
   - Upon receiving a `RuntimeResponse`, the client automatically bridges returned `native_events` into the Python `event_bus` and indexes them into the `timeline_reconstructor`.

---

## 4. Secret Sanitization & Privacy Shield

Both Python (`TelemetrySanitizer`) and Rust (`NativeRedactor`) enforce identical redaction rules before any event is logged, dispatched, or serialized:

- **Secret Patterns Redacted**:
  - Private Key Blocks (`-----BEGIN RSA PRIVATE KEY-----`, etc.)
  - Database Connection Strings (`postgres://`, `mysql://`, `mongodb://`, `sqlite://` with passwords)
  - HTTP Basic Authorization headers (`Basic [base64]`)
  - URLs with embedded credentials (`https://user:pass@host/`)
  - Sensitive Query Parameters (`?api_key=...`, `&token=...`, `&secret=...`)
  - OpenAI, Anthropic, AWS, GitHub, Slack tokens, and JWT strings (`Bearer ey...`, `sk-...`, `AKIA...`)
- **Negative Lookahead Safety**:
  - Regexes employ `(?!\[REDACTED)` to ensure already-redacted text is not repeatedly mangled or expanded.
- **Strict Prohibition on CoT**:
  - Chain-of-thought blocks (`<thought>`, `reasoning_content`) are scrubbed before reaching the event bus.

---

## 5. Forensic Execution Timeline Reconstruction

The `TimelineReconstructor` provides deterministic execution analysis:

```python
timeline = timeline_reconstructor.reconstruct_timeline(correlation_id)
# Returns:
# - correlation_id: str
# - start_time / end_time: datetime
# - duration_ms: float
# - overall_status: "COMPLETED" | "FAILED" | "IN_PROGRESS"
# - entries: List[TimelineEntry] (sorted deterministically by monotonic timestamp)
# - primary_failure_cause: Optional[str] (pinpoints root cause in causal DAG)
# - error_fingerprint: Optional[str] (stable error classification hash)
```

### Deterministic Error Fingerprinting

To eliminate alert fatigue and deduplicate failure diagnostics, errors are fingerprinted using a stable SHA-256 hash:
- Evaluates: `error_type`, normalized error message (UUIDs, timestamps, hex addresses, and file paths stripped), and `component`.
- Identical failures produce identical 16-character hex fingerprints (`fp_...`), allowing automatic grouping and regression detection.

### Data-Only Replay

```python
replay_events = timeline_reconstructor.replay_events(correlation_id)
```
- Replays retrieve the exact sequence of historical events for a given correlation ID.
- Replays return immutable event data projections. No side effects, network calls, tool executions, or state mutations can occur during replay.

---

## 6. Dependency-Aware Subsystem Health Aggregation

The `SubsystemHealthAggregator` tracks and evaluates 11 core subsystems:

```
  python_core (CRITICAL)
  database (CRITICAL)
  redis (NON-CRITICAL)
  event_fabric (CRITICAL)
  rust_runtime (CRITICAL)
  sandbox (NON-CRITICAL)
  resource_enforcement (NON-CRITICAL)
  native_tools (NON-CRITICAL)
  computer_interaction (NON-CRITICAL)
  network_fabric (NON-CRITICAL)
  workflow_engine (NON-CRITICAL)
```

### Health Computation Matrix

- **HEALTHY (100% Score)**: All subsystems operational.
- **DEGRADED**: Any non-critical subsystem (e.g. `redis`, `sandbox`) is in `DEGRADED` or `UNHEALTHY` state, while all critical subsystems are operational.
- **FAILED / UNHEALTHY (0% Score)**: Any **critical** subsystem (`python_core`, `database`, `event_fabric`, `rust_runtime`) is in `UNHEALTHY` or `FAILED` state.
- **Aggregated Health Score**: Proportional to operational weights across all 11 subsystems, with zero score override if any critical subsystem fails.

---

## 7. Operational REST Endpoints & UI

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/observability/traces` | `GET` | Paginated distributed trace list with tenant & project isolation. |
| `/api/v1/observability/events` | `GET` | Paginated live telemetry event stream with domain/severity filters. |
| `/api/v1/observability/executions/{correlation_id}` | `GET` | Detailed execution context for a correlation ID. |
| `/api/v1/observability/timeline/{correlation_id}` | `GET` | Reconstructed forensic execution timeline with root-cause identification. |
| `/api/v1/observability/replay/{correlation_id}` | `GET` | Pure data replay projection of historical execution events. |
| `/api/v1/observability/subsystems` | `GET` | Unified 11-subsystem health report with health score and safety checks. |
| `/health/components` | `GET` | Component health endpoint for load balancers and orchestrators. |

### Frontend UI

The Observability Fabric is integrated into the Resource Center as **Subtab 11: "11. Observability Fabric (Task 86)"**:
- **Unified Health KPI Header**: Displays overall status (`HEALTHY`, `DEGRADED`, `FAILED`), safety status, and composite health score.
- **Subsystem Grid**: Status badges, latency, uptime, and failure reasons for all 11 subsystems.
- **Forensic Timeline Reconstructor**: Search by correlation ID, step-by-step causal execution trace, duration, and error fingerprint.
- **Live Telemetry Stream**: Ring buffer viewer with real-time domain, severity, and outcome tags.

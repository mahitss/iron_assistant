# Kairo Native Tool Execution Fabric (Task 83)

## 1. Architectural Overview

The **Kairo Native Tool Execution Fabric** provides a typed, sandboxed, policy-enforced execution pipeline connecting high-level AI tool intent to low-level Rust native capabilities.

```
USER / AGENT INTENT
        ↓
    TOOLREGISTRY   (Application-level definitions, schemas, execution metadata)
        ↓
    TOOLEXECUTOR   (Orchestration, routing, fallback handling, provenance)
        ↓
   SECURITYCENTER  (Authoritative access control: ALLOWED / DENIED / APPROVAL_REQUIRED)
        ↓
     GOVERNANCE    (Policy engine, constitutional limits, human review)
        ↓
  APPROVALREGISTRY (Cryptographic/stateful approval token binding)
        ↓
 RESOURCE ECONOMY  (Capacity allocation, budget reservation, backpressure)
        ↓
NATIVE RUNTIME CLIENT (Async frame-based IPC, circuit breaker, heartbeats)
        ↓
    RUST RUNTIME   (kairo-runtime daemon, low-level validation, lifecycle)
        ↓
    RUST SANDBOX   (Win32 Job Object isolation, isolated workspace directory)
        ↓
RESOURCE ENFORCEMENT (Hardware MMU bounds, Tokio deadline timers, stream bounds)
        ↓
 NATIVE CAPABILITY (Deterministic, registered native capability)
        ↓
    VERIFICATION   (Process tree termination verification, workspace RAII cleanup)
        ↓
   RESULT RETURN   (Structured output normalization, error categorization)
        ↓
AUDIT / TELEMETRY  (Event registry emission, tool health metrics update)
```

---

## 2. Core Architectural Principles

1. **Python / Rust Division of Responsibilities**:
   - **Python** is responsible for tool discovery, selection, intent interpretation, governance, authorization, approval, orchestration, high-level schema validation, and workflow logic.
   - **Rust** is responsible for low-level capability execution, execution-boundary validation, sandboxing, process tree isolation, hard resource enforcement, cancellation, deadlines, output stream control, and execution lifecycle containment.
2. **Capability ≠ Tool**:
   - **Capability**: What the native runtime can technically perform (e.g., `native.file.inspect`, `native.sysinfo`, `sandbox.hash`).
   - **Tool**: The user/system-facing application interface in Kairo (e.g., `native_workspace_inspect`, `native_system_info`, `native_hash`).
   - A tool binds to a capability ID; capability identities are stable strings, not arbitrary binary paths.
3. **No Arbitrary Executable Paths**:
   - Invocations never accept arbitrary executable paths from users or model payloads.
   - Capabilities are registered statically in trusted runtime metadata.
4. **No Shell Strings**:
   - No `run(command_string)` or `sh -c` / `cmd.exe /c` execution exists.
   - Native capabilities use direct internal native functions or isolated process spawns with discrete argument vectors.
5. **EmergencyStop Always Wins**:
   - Active emergency stops immediately halt all native tool dispatches, kill active process trees, and release allocated resource reservations.

---

## 3. Tool Classification & Preferences

### Execution Classification (`ToolExecutionClass`)
- `PYTHON`: Executed entirely in the Python runtime.
- `NATIVE_RUST`: Executed within the Rust native sandbox substrate.
- `REMOTE`: Executed via an external RPC/API service.
- `COMPOSITE`: Workflow tool composing multiple subordinate tools.

### Execution Preference (`ToolExecutionPreference`)
- `NATIVE_REQUIRED`: Must execute in native Rust substrate. If runtime is unavailable, degraded, or disabled, execution fails closed immediately.
- `NATIVE_PREFERRED`: Prefers native Rust substrate for speed/containment. If runtime is unavailable, gracefully falls back to verified Python implementation.
- `PYTHON_PREFERRED`: Prefers Python runtime, with native offload if requested.
- `PYTHON_REQUIRED`: Must execute exclusively in Python.

### Operational Availability (`ToolAvailability`)
- `AVAILABLE`: Tool and native runtime are operational.
- `DEGRADED`: Native substrate is offline or degraded, but safe Python fallback is available.
- `UNAVAILABLE`: Tool or native substrate is offline with no fallback possible.
- `DISABLED`: Substrate is disabled by configuration.
- `INCOMPATIBLE`: Substrate or capability version is incompatible.

---

## 4. Built-in Native Tools Catalog

| Tool Name | Version | Permission | Execution Class | Preference | Capability ID | Sandbox Profile | Side Effects |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `native_hash` | 1.0.0 | READ | `NATIVE_RUST` | `NATIVE_PREFERRED` | `sandbox.hash` | `STANDARD` | READ_ONLY |
| `native_system_info` | 1.0.0 | READ | `NATIVE_RUST` | `NATIVE_PREFERRED` | `native.sysinfo` | `STANDARD` | READ_ONLY |
| `native_workspace_inspect` | 1.0.0 | READ | `NATIVE_RUST` | `NATIVE_REQUIRED` | `native.file.inspect` | `ISOLATED_READ` | STATEFUL_LOCAL |
| `native_probe` | 1.0.0 | EXECUTE | `NATIVE_RUST` | `NATIVE_REQUIRED` | `sandbox.probe` | `RESTRICTED_COMPUTE` | STATEFUL_LOCAL |

---

## 5. End-to-End Execution Lifecycle

1. **Pre-flight & Discovery**:
   - `ToolRegistry` resolves tool definition by name.
   - Pydantic models validate input arguments before crossing any boundaries.
2. **Authoritative Security Evaluation**:
   - `SecurityCenter.authorize()` evaluates user permissions, tool permission level, and arguments.
   - If `DENIED`, halts immediately with reason.
   - If `APPROVAL_REQUIRED` and valid `approval_id` is missing, halts pending explicit human authorization.
3. **Availability & Routing**:
   - `ToolExecutor` inspects native runtime health via `NativeRuntimeService.get_health()`.
   - If unavailable and `NATIVE_REQUIRED`, returns structured error.
   - If unavailable and `NATIVE_PREFERRED`, routes to safe Python fallback.
4. **Emergency Stop Check**:
   - `EmergencyStopService.is_stopped()` is checked. If stopped, halts immediately with `Execution blocked by active EmergencyStop`.
5. **Resource Budgeting & Reservation**:
   - `ResourceBudget` is mapped from tool metadata and bounded by effective policy.
   - `ResourceEconomyCoordinator` reserves required memory, CPU, and storage units atomically.
6. **Native Sandbox Dispatch**:
   - `ExecutionRequest` is sent across IPC to `kairo-runtime.exe`.
   - Rust runtime validates request signature, capability existence, and budget limits.
   - Rust creates a Win32 Job Object and isolated temporary workspace directory.
7. **Execution & Confinement**:
   - Native capability runs bounded by wall-clock timeout and hardware limits.
   - Output streams are truncated at `max_stdout_bytes` (default 2 MiB) to prevent memory exhaustion.
8. **Result Normalization & Audit**:
   - `ToolResult` is populated with `execution_class="NATIVE_RUST"`, `capability_id`, `duration_ms`, `resource_telemetry`, and `provenance`.
   - Tool metrics (invocations, success rate, latency, failures, fallbacks) update in `ToolRegistry`.
   - Audit event (`tool.native.completed` or `tool.native.fallback`) is emitted to `EventRegistry`.

---

## 6. Failure Modes & Recovery

| Failure Scenario | System Behavior | Guarantees |
| :--- | :--- | :--- |
| **Daemon Process Crash / Offline** | `NATIVE_PREFERRED` routes to Python fallback; `NATIVE_REQUIRED` fails closed. | Zero false successes; no uncontained execution. |
| **Resource Violation (Memory/Disk/Time)** | Win32 Job Object terminates process tree; returns `RESOURCE_EXCEEDED`. | Zero leaked memory leases; reservations cleaned up. |
| **Path Traversal Attack (`../../etc`)** | Sandbox path validator catches traversal; returns `PATH_TRAVERSAL_DETECTED`. | No reads outside isolated workspace. |
| **Shell Injection (`cmd; rm -rf /`)** | Invocations pass discrete argument vectors; no shell interpreter is spawned. | Metacharacters treated purely as string literals. |
| **Emergency Stop Active** | Substrate blocks execution prior to process creation; active runs killed. | Immediate halting of all side-effects. |

---

## 7. Troubleshooting

- **Check Runtime Health**:
  ```bash
  curl http://localhost:8000/api/v1/native/tools/health
  ```
- **List Native Catalog**:
  ```bash
  curl http://localhost:8000/api/v1/native/tools
  ```
- **Inspect Specific Tool**:
  ```bash
  curl http://localhost:8000/api/v1/native/tools/native_hash
  ```
- **Daemon Logs**:
  Native runtime outputs structured JSON logs to stdout or `backend/native_tool_daemon_e2e.log`. Look for `target="kairo_runtime::sandbox"`.

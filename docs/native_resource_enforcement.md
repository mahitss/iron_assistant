# Kairo Native Resource Enforcement & Execution Economy (Task 82)

## Architectural Overview

Task 82 establishes the definitive bridge between **Task 77 (Kairo Resource Economy / Capability Allocation)** and **Tasks 80 & 81 (Rust Native Substrate & Secure Execution Sandbox)**.

```
┌────────────────────────────────────────────────────────────────────────┐
│               Task 77: Policy & Capacity Decision Layer                │
│    (Decides WHAT resources Kairo MAY allocate based on quota & credit)  │
│                                                                        │
│       ResourceRegistry ────► ResourceEconomyCoordinator                │
│                │                         ▲                             │
│       atomic reservation                 │ reconciliation & learning   │
│                ▼                         │                             │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │         NativeRuntimeService (Python Bridge Layer)          │      │
│   └──────────────────────────────┬──────────────────────────────┘      │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │ IPC Frame (Budget + Policy)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Task 82: Native Enforcement Substrate (Rust)             │
│    (Enforces WHAT the native process execution layer ACTUALLY receives)│
│                                                                        │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  │
│   │ Win32 Job Object  │  │  Tokio Hard Timer │  │ Stream Bounded    │  │
│   │ Memory & Process  │  │  Wall-Clock Limit │  │ Stdout/Stderr     │  │
│   │ Limits (Hardware) │  │  (Cancellation)   │  │ (2 MiB Max Bnd)   │  │
│   └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘  │
│             │                      │                      │            │
│             └──────────────────────┼──────────────────────┘            │
│                                    ▼                                   │
│                        Deterministic Probe / Workload                  │
│                                    │                                   │
│                                    ▼                                   │
│                     Workspace Metric & Telemetry Capture               │
│                                    │                                   │
│                                    ▼                                   │
│                 Telemetry + Violation Classification                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## The 4 Tiers of Real Resource Enforcement

In accordance with Kairo's **Zero Fake Enforcement Invariant**, all limits are explicitly categorized by their hardware/OS enforcement authority:

| Resource Dimension | Target Limit | Enforcement Mechanism | Platform Authority | Measurement Quality |
| :--- | :--- | :--- | :--- | :--- |
| **Physical Memory** | `max_memory_bytes` | Win32 Job Object `JOB_OBJECT_LIMIT_JOB_MEMORY` | Hardware / Kernel MMU | Exact (Job Object counters) |
| **Wall-Clock Time** | `max_execution_seconds` | Tokio async timeout (`tokio::time::timeout`) | OS Kernel Timer / Async | Exact (Monotonic clock) |
| **Process Count** | `max_processes` | Win32 Job Object `JOB_OBJECT_LIMIT_ACTIVE_PROCESS` | OS Kernel Process Table | Exact (Active process limit) |
| **Output Bounds** | `max_output_bytes` | Bounded async stream buffer (`take(limit)`) | Runtime stream reader | Exact (Byte counting) |
| **Workspace Disk** | `max_disk_bytes` | Pre & post execution recursive walk | File system metadata | Approximate (Sampled post-exec) |
| **Workspace Files**| `max_file_count` | Recursive directory walk counter | File system metadata | Approximate (Sampled post-exec) |
| **CPU Time** | `max_cpu_seconds` | Kernel + User CPU time via `GetJobObjectInformation` | OS Kernel Scheduler | Exact (Telemetry only on Windows) |
| **LLM Tokens** | `max_tokens` | Model context / tokenizer accounting | Application level | Inapplicable (Native substrate) |

---

## Cross-Platform Enforcement Matrix

The system provides honest cross-platform reporting via `GET /api/v1/native/economy/matrix`:

```json
{
  "matrix": [
    {
      "resource": "memory_bytes",
      "windows": "Job Object (Hard OOM Kill)",
      "linux": "cgroups v2 memory.max (OOM Killer)",
      "macos": "setrlimit RLIMIT_AS / Process Group",
      "is_hard_limit": true
    },
    {
      "resource": "cpu_seconds",
      "windows": "Job Object Accounting (Observable Metric)",
      "linux": "cgroups v2 cpu.max (Hard CFS Throttling)",
      "macos": "setrlimit RLIMIT_CPU (SIGXCPU Hard Kill)",
      "is_hard_limit": false
    },
    {
      "resource": "active_processes",
      "windows": "Job Object ActiveProcessLimit (Hard Process Deny)",
      "linux": "cgroups v2 pids.max (Hard Deny)",
      "macos": "setrlimit RLIMIT_NPROC (Soft/Hard Limit)",
      "is_hard_limit": true
    },
    {
      "resource": "execution_seconds",
      "windows": "Tokio Async Deadline / TerminateJobObject",
      "linux": "Tokio Async Deadline / SIGKILL Process Group",
      "macos": "Tokio Async Deadline / SIGKILL Process Group",
      "is_hard_limit": true
    },
    {
      "resource": "output_bytes",
      "windows": "Bounded Stream Reader (Hard Stream Truncation)",
      "linux": "Bounded Stream Reader (Hard Stream Truncation)",
      "macos": "Bounded Stream Reader (Hard Stream Truncation)",
      "is_hard_limit": true
    },
    {
      "resource": "workspace_storage",
      "windows": "Post-exec Recursive Metric Check",
      "linux": "cgroups v2 / Disk Quotas / Post-exec Check",
      "macos": "Post-exec Recursive Metric Check",
      "is_hard_limit": false
    }
  ]
}
```

---

## Execution Economy Lifecycle: Reservation & Reconciliation

1. **Atomic Pre-Execution Reservation**:
   - Before IPC dispatch, `NativeRuntimeService` reserves memory (`native_memory`), CPU (`native_cpu`), and workspace disk (`native_workspace`) through `ResourceRegistry.reserve()`.
   - If host capacity is exhausted or saturation exceeds thresholds, `ResourceReservationError` is raised, triggering immediate **Backpressure**.
2. **Deterministic Native Execution**:
   - The Rust daemon configures the Win32 Job Object with exact memory limits and active process limits.
   - If a process breaches memory limits, the Windows kernel terminates it immediately (`0xC0000017` / OOM), and `kairo-runtime` classifies it as `MEMORY_EXCEEDED`.
   - Output streams are read up to `max_output_bytes` (default 2 MiB) with truncation flags.
   - Sandboxed workspaces are validated before and after execution.
3. **Guaranteed Zero-Leak Release**:
   - Every execution reservation has a corresponding release block in Python's `finally:` clause.
   - Releases occur without fail across:
     - Successful executions.
     - Timeout terminations.
     - Hard memory terminations.
     - IPC connection drops.
     - Global Emergency Stop triggers.
4. **Estimation Learning**:
   - Telemetry from the completed execution (`actual_memory_bytes`, `duration_ms`) is reconciled against the initial reservation.
   - The variance is fed into `ResourceEconomyEngine._historical_demands[capability_id]` to dynamically calibrate future reservation estimates.

---

## Emergency Stop Supremacy

The **Global Emergency Stop** (`EmergencyStopManager`) maintains supreme authority:
- When active, all incoming native execution requests are rejected immediately with status `BLOCKED_BY_EMERGENCY_STOP`.
- No reservations are allocated.
- Any in-flight reservations are instantly released.
- Zero resources remain reserved or leaked.

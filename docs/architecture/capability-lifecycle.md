# Architectural Audit & Specification: Capability Lifecycle, Versioning & Safe Evolution Engine (Task 91)

## 1. Executive Summary & Existing Capability Architecture

Kairo currently possesses rich, multi-tiered capability infrastructure spanning Python and native Rust substrates. However, before Task 91, capability definition, tool execution, security gating, and runtime protocols operated without a unified **application-level capability lifecycle, versioning, compatibility, and safe evolution authority**.

### 1.1 Existing Subsystems Audited & Integration Map

```
+---------------------------------------------------------------------------------------------------------+
|                                    EXISTING AUTHORITATIVE PLATFORM                                      |
|                                                                                                         |
|   +--------------------------+    +--------------------------+    +---------------------------------+   |
|   | SecurityCenter (Task 78) |    | Governance/Constitution  |    | ApprovalRegistry (Task 78)      |   |
|   | Single Auth Authority    |    | Policy Authority         |    | Human/Dual-Control Authority    |   |
|   +--------------------------+    +--------------------------+    +---------------------------------+   |
|   +--------------------------+    +--------------------------+    +---------------------------------+   |
|   | Resource Economy (T77)   |    | EmergencyStop Service    |    | ToolRegistry / Executor         |   |
|   | Budget & Active Work     |    | Absolute Kill-Switch     |    | Executable Tool Source of Truth |   |
|   +--------------------------+    +--------------------------+    +---------------------------------+   |
|   +--------------------------+    +--------------------------+    +---------------------------------+   |
|   | ModelRouter (Models)     |    | Observability Fabric(T86)|    | Recovery Twin & Sim (Task 89)   |   |
|   | Provider & Model Routing |    | Telemetry Ring-Buffer    |    | Blast Radius & Twin Sandbox     |   |
|   +--------------------------+    +--------------------------+    +---------------------------------+   |
|   +--------------------------+    +--------------------------+                                          |
|   | Self-Healing (Task 88)   |    | Reliability Intel (T90)  |                                          |
|   | Subsystem Recovery       |    | Precursors & Baselines   |                                          |
|   +--------------------------+    +--------------------------+                                          |
+---------------------------------------------------|-----------------------------------------------------+
                                                    |
                                                    v
+---------------------------------------------------------------------------------------------------------+
|                      TASK 91: CAPABILITY LIFECYCLE, VERSIONING & EVOLUTION ENGINE                       |
|                                                                                                         |
|   - Application-Level Capabilities (Tools, Native Capabilities, Model Providers, Workflows)             |
|   - 12-State Explicit Lifecycle State Machine (DISCOVERED -> VALIDATED -> CANARY -> ACTIVE -> RETIRED) |
|   - Cryptographic Capability Fingerprinting (Contract, Implementation, Dependency Hashes)               |
|   - 6-Class Compatibility Evaluator & Dependency Graph Impact Analysis                                  |
|   - Conformance Test Pipeline with Deterministic Test Vectors                                            |
|   - Simulation Gating (Twin Impact & Stale Simulation Drift Rejection)                                  |
|   - Progressive Canary Rollout with Automated Anomaly Rollback                                          |
|   - 11-Gate Promotion Verification (Zero Security/Governance Bypass)                                    |
|   - Safe Verified Rollback & Orderly Deprecation / Sunset Sunsetting                                    |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Existing Component Roles & Authority Boundaries

### What Existing Systems Own (Strictly NOT Owned by Task 91):
1. **ToolRegistry (`app.tools.registry.py`)**: Remains the **exclusive source of truth** for executable Python tools and OpenAI/OpenRouter-compatible function schemas. Task 91 does *not* execute tools or replace tool registrations.
2. **ToolExecutor (`app.tools.executor.py`)**: Remains the **exclusive executor** of tools, enforcing timeouts, sandbox profiles, and argument sanitization.
3. **ModelRouter (`app.models.router.py`)**: Remains the **exclusive selector** of LLM models and provider routing based on requested task capabilities.
4. **Native Rust Capability Registry (`native/crates/kairo-runtime/src/capabilities.rs`)**: Remains the **exclusive low-level host execution substrate** for OS processes, screen capture, raw sockets, and window inspection.
5. **SecurityCenter (`app.security.center.py`)**: The **SINGLE authorization authority**. Task 91 never grants permissions, evaluates ACLs, or bypasses security checks.
6. **Governance & Constitution (`app.policy.governance_coordinator.py`)**: The **SINGLE policy authority**. Task 91 requests policy compliance reviews; it does not invent policy.
7. **ApprovalRegistry (`app.security.approvals.py`)**: The **SINGLE human signoff authority** for high-risk operations.
8. **Resource Economy (`app.orchestration.py` / Task 77)**: The **SINGLE resource budgeting authority**. Task 91 requests budget tokens for canary and validation.
9. **EmergencyStop (`app.security.emergency_stop.py`)**: The **absolute kill-switch override**. When active, all capability promotions, rollouts, canaries, and executions are halted fail-closed.
10. **Observability Fabric (`app.observability.py` / Task 86)**: The **telemetry event bus**. Task 91 emits canonical `capability.*` events into it.
11. **Digital Twin & Recovery Simulation (`app.simulation/` / Task 89)**: The **simulation sandbox**. Task 91 delegates rollout consequence and blast radius simulation to it.
12. **Reliability Intelligence (`app.reliability_intelligence/` / Task 90)**: The **precursor detection and strategy health authority**. Task 91 consumes reliability scorecards and stability windows.

---

## 3. What the Capability Lifecycle Engine Owns

Task 91 establishes the **orchestration, metadata, versioning, compatibility, and evolution lifecycle** across Kairo's capabilities:

1. **Higher-Order Capability Domain**: Represents application-level capabilities (`TOOL`, `NATIVE_RUNTIME`, `MODEL_PROVIDER`, `WORKFLOW`, `INTEGRATION`, `COMPOSITE`).
2. **Explicit 12-State Machine**:
   `DISCOVERED` $\to$ `VALIDATING` $\to$ `VALIDATED` $\to$ `SIMULATING` $\to$ `CANARY` $\to$ `ACTIVE` $\to$ `DEGRADED` $\to$ `BLOCKED` $\to$ `DEPRECATED` $\to$ `RETIRING` $\to$ `RETIRED` (with terminal `FAILED`).
3. **Cryptographic Fingerprinting**:
   - Contract schema hash (SHA-256).
   - Implementation artifact hash.
   - Dependency set hash.
   - Composite capability identity fingerprint (tamper & drift detection).
4. **Compatibility Engine**:
   - Analyzes compatibility between versions across schemas, dependencies, resource profiles, and security levels.
   - Classifies as `FULLY_COMPATIBLE`, `BACKWARD_COMPATIBLE`, `FORWARD_COMPATIBLE`, `PARTIALLY_COMPATIBLE`, `INCOMPATIBLE`, `UNKNOWN`.
5. **Dependency Graph & Impact Analysis**:
   - Models relationships between capabilities, tools, native daemons, model providers, and workflows.
   - Propagates dependency health degradations to affected downstream consumers.
6. **Validation & Conformance Pipeline**:
   - Validates schema, metadata, permissions, and runs deterministic test vectors.
7. **Simulation & Canary Promotion Gates**:
   - Enforces 11 explicit gates before an immutable version can become `ACTIVE`.
8. **Safe Rollback & Verified Deprecation**:
   - Reverts safely to previous stable versions with non-LLM health checks and manages sunset schedules.

---

## 4. Security & Safety Boundaries

1. **Autonomous Evolution $\neq$ Autonomous Authorization**:
   - Kairo may autonomously discover, analyze, validate, simulate, test, observe, and recommend evolution.
   - Actual authorization remains strictly with **SecurityCenter**.
   - Actual policy compliance remains strictly with **Governance**.
   - Actual approval remains strictly with **ApprovalRegistry**.
2. **Immutable Active Versions**:
   - Once a version reaches `ACTIVE`, it is frozen. Any subsequent change requires registering a new SemVer version.
3. **Emergency Stop Primacy**:
   - If `EmergencyStopService::is_stopped()` is True, all lifecycle mutations (promotion, canary, validation) abort fail-closed.
4. **Untrusted Data Invariant**:
   - External manifests, tool definitions, model metadata, and network inputs are treated as untrusted data and validated against strict schemas before ingestion.

# KAIRO Autonomous Self-Model, Capability Awareness & Internal State Intelligence (Task 101)

## Executive Summary

Task 101 establishes the **Autonomous Self-Model, Capability Awareness & Internal State Intelligence** layer of KAIRO.
The objective of this layer is to give Kairo a durable, evidence-backed model of its own operational state, strictly grounded in observed telemetry without fictional self-awareness or duplicate authorities.

```
CAPABILITY LIFECYCLE
        ↓
RUNTIME OBSERVATION
        ↓
TOOL / EXECUTION STATE
        ↓
RESOURCE STATE
        ↓
SECURITY / GOVERNANCE STATE
        ↓
DEPENDENCY HEALTH
        ↓
RELIABILITY SIGNALS
        ↓
WORLD-STATE RECONCILIATION
        ↓
SELF-MODEL (Task 101)
        ↓
METACOGNITIVE ASSESSMENT
        ↓
MISSION / DECISION / CONTEXT
```

---

## 1. The 15 Canonical Introspective Questions

The Self-Model provides typed, deterministic resolution of the 15 canonical operational questions:

1. **What capabilities do I have?**
   - Derived from `CapabilityLifecycleService.list_capabilities()`.
2. **Which versions are available?**
   - Precise SemVer version string mapped per registered capability.
3. **Which capabilities are actually ready?**
   - Filtered by multi-dimensional readiness (`readiness_state == READY`).
4. **Which are degraded?**
   - Filtered by `readiness_state == DEGRADED` (consecutive failures, unstable health, degraded upstream dependencies).
5. **Which are temporarily unavailable?**
   - Capabilities in `UNAVAILABLE`, `BLOCKED`, or `FAILED` states.
6. **What resources do I currently have?**
   - Saturation percentage, capacity degradation tier, and allocated vs. available capacity across CPU, memory, tokens, and execution budgets from `ResourceEconomyEngine`.
7. **What tools can I use?**
   - Authoritative list of active tools from `ToolRegistry` that are unrestricted and permitted under active security modes.
8. **What access is currently authorized?**
   - Active security policies, least-privilege perimeter, and authorized operational scopes from `SecurityCenter`.
9. **Which actions require approval?**
   - Explicit human-in-the-loop approval actions bound in `ApprovalRegistry` and `SecurityCenter`.
10. **Which dependencies are failing?**
    - Underperforming or offline services (`PostgreSQL`, `Redis`, `Rust runtime`, `model_provider`, `browser_engine`, `network_egress`).
11. **Which capabilities have recently failed?**
    - Capabilities exhibiting consecutive failures or recent telemetry errors.
12. **How reliable is each capability?**
    - Calibrated empirical success rates and reliability scores from `ReliabilityIntelligenceService`.
13. **What has changed since the last check?**
    - Structured delta (`SelfModelDelta`) between consecutive immutable snapshots recording `CAPABILITY_STATE_CHANGED`, `EMERGENCY_STOP_CHANGED`, etc.
14. **What do I know about my own limitations?**
    - Evidence-backed, factual boundaries (e.g. "External actions blocked by EmergencyStop", "Resource saturation throttles background throughput").
15. **What am I uncertain about?**
    - Explicit epistemic uncertainties with designated revalidation policies (e.g., intermittent failures, unverified telemetry).

---

## 2. Mandatory Architectural Distinctions

$$\mathbf{AVAILABLE \neq READY \quad\mid\quad READY \neq AUTHORIZED}$$
$$\mathbf{AUTHORIZED \neq SAFE \quad\mid\quad SAFE \neq RELIABLE}$$
$$\mathbf{RELIABLE \neq ALWAYS\ AVAILABLE \quad\mid\quad CAPABLE \neq CURRENTLY\ CAPABLE}$$
$$\mathbf{INSTALLED \neq USABLE \quad\mid\quad CONFIGURED \neq VERIFIED}$$
$$\mathbf{VERIFIED \neq PERMANENT \quad\mid\quad PREDICTED \neq OBSERVED}$$
$$\mathbf{AGENT\ CLAIM \neq FACT \quad\mid\quad MODEL\ CLAIM \neq FACT}$$
$$\mathbf{TOOL\ SUCCESS \neq WORLD\ STATE\ SUCCESS \quad\mid\quad NO\ DATA \neq HEALTHY}$$
$$\mathbf{STALE\ DATA \neq CURRENT\ STATE \quad\mid\quad UNKNOWN \neq FALSE}$$

---

## 3. Multi-Dimensional Readiness Model

A capability is never evaluated via an unexplained magic score. It is assessed across 6 distinct dimensions:

| Dimension | Verification Source | Failure Condition |
| :--- | :--- | :--- |
| **CONFIGURATION** | Cryptographic contract fingerprinting | Schema mismatch, missing parameters |
| **DEPENDENCIES** | Core dependency availability probes | Required database, runtime, or network offline |
| **HEALTH** | Lifecycle health status telemetry | Health marked `DEGRADED`, `UNSTABLE`, or `UNSAFE` |
| **SECURITY** | EmergencyStop & SecurityCenter | Kill-switch engaged or policy violation |
| **GOVERNANCE** | ApprovalRegistry policy | Unapproved high-risk operation |
| **RECENT FAILURES** | Reliability consecutive failure counters | Consecutive failures $\ge 1$ (degraded), $\ge 3$ (failed) |

---

## 4. Property Invariants

1. **No Self-Modifying Authority**: Kairo can never use its self-model to grant itself new permissions, bypass security policies, or disable EmergencyStop.
2. **Fail-Closed EmergencyStop**: When `EmergencyStopService.is_stopped()` is true, all external execution capabilities transition immediately to `BLOCKED`.
3. **No Automatic Post-Stop Restoration**: When EmergencyStop is cleared, capabilities are not assumed to be `READY`; bounded revalidation is strictly required.
4. **Scoped Blast Radius**: Degradation in one capability (e.g., `browser_engine`) never invalidates unrelated capabilities (e.g., `code_execution`).
5. **No Fictional Awareness**: 100% of claims are verified against empirical telemetry via `verify_grounding()`.

---

## 5. API and CLI Reference

### REST Endpoints (`/api/v1/self-model`)
- `GET /snapshot`: Fetch current immutable self-state snapshot.
- `POST /reconcile`: Trigger empirical reconciliation and snapshot emission.
- `GET /answers`: Retrieve answers to all 15 introspective questions.
- `GET /capabilities`: Retrieve capability awareness matrix with readiness dimensions.
- `GET /limitations`: Retrieve active factual boundaries.
- `GET /uncertainties`: Retrieve active epistemic uncertainties.
- `GET /deltas`: Retrieve snapshot diffs.
- `GET /verify-grounding`: Audit telemetry backing and invariant compliance.
- `GET /summary`: Compact operational status for model context injection.

### CLI Commands (`kairo self-model`)
- `kairo self-model status`: High-level operational mode and kill-switch status.
- `kairo self-model capabilities`: Formatted capability readiness matrix.
- `kairo self-model limitations`: Active operational limitations.
- `kairo self-model uncertainties`: Epistemic uncertainties requiring probe.
- `kairo self-model answers`: Formatted display of the 15 canonical answers.
- `kairo self-model reconcile`: Force empirical reconciliation pass.

# KAIRO Autonomous System State Graph, Self-Modeling & Operational Digital Twin

## Phase 0: Repository-First Audit & System State Architecture

### 1. Executive Summary & Non-Negotiable Cognitive Principles
The **KAIRO System State Graph** is the continuously updated operational self-model of the autonomous assistant. It bridges goals, active work, runtime components, capabilities, resources, incidents, and security constraints into a coherent operational topology.

$$\mathbf{OBSERVED \neq INFERRED \quad\mid\quad INFERRED \neq PREDICTED \quad\mid\quad PREDICTED \neq ACTUAL}$$
$$\mathbf{UNKNOWN \neq FAILED \quad\mid\quad STATE\ GRAPH \neq SOURCE\ OF\ AUTHORITY}$$

The System State Graph is **NOT** an authority engine. It connects authoritative realities:
- **SecurityCenter** authorizes.
- **Governance** governs.
- **ApprovalRegistry** approves.
- **Resource Economy** allocates.
- **Capability Lifecycle** manages evolution.
- **Reliability Intelligence** manages failure detection and health.
- **Forecasting** predicts.
- **Knowledge Consolidation** manages persistent knowledge.
- **System State Graph** connects these subsystems to explain: *What is Kairo doing? Why? What depends on what? What is broken? What is predicted? What is unknown?*

---

### 2. Audit of Existing Subsystems & Integration Strategy

| Subsystem | Existing Repository Component | Integration Strategy (Task 93) | Non-Duplication Guarantee |
| :--- | :--- | :--- | :--- |
| **Knowledge Graph** | `backend/app/knowledge_graph/` (`kg_nodes`, `kg_edges`) | Operational state vertices and directed edges are projected to unified graph structures. | **No 2nd Graph DB**: All graph relationships use existing graph models. |
| **Digital Twin / Simulation** | `backend/app/simulation/` (`RuntimeDigitalTwin`, `RuntimeSnapshot`) | Operational state graph provides live snapshot inputs to digital twin. Simulation results are marked strictly as `PREDICTED_STATE`. | **No 2nd Digital Twin**: Live state feeds directly into existing recovery simulation. |
| **Forecasting & Early Warning** | `backend/app/foresight/`, `backend/app/reliability_intelligence/` | State graph exposes predicted degradation as `PREDICTED` epistemological status. | **No 2nd Forecasting Engine**: Reuses existing forecasts. |
| **Capability Lifecycle** | `backend/app/capability_lifecycle/` (Task 91) | Ingests capability states (`DISCOVERED` to `RETIRED`), fingerprints, and compatibility edges. | **No 2nd Capability Registry**: Capability lifecycle remains authoritative. |
| **Reliability & Incidents** | `backend/app/reliability/`, `backend/app/incident_response/` | Incident vertices link to affected components, workflows, and goals. | **No 2nd Incident System**: Reuses existing failure taxonomy and incident records. |
| **Goal & Strategic Executive** | `backend/app/missions/` (`goals.py`, `service.py`) | Ingests goal hierarchy, priorities, progress, and blockers. | **No 2nd Goal Manager**: Missions/Strategic Executive remains authoritative. |
| **Tasks & Workflows** | `backend/app/tasks/`, `backend/app/automation/` | Maps active tasks, workflow runs, steps, and tool executions. | **No 2nd Task Scheduler**: State graph only reflects execution status. |
| **Resource Economy** | `backend/app/optimization/` (`resource_economy.py`, Task 77) | Ingests CPU, memory, storage, concurrency, and token budget allocations. | **No 2nd Resource Allocator**: Resource Economy owns budgeting. |
| **Security & Emergency Stop** | `backend/app/security/center.py`, `backend/app/security/emergency_stop.py` | State graph reflects active restrictions, blocked tools, and emergency stop state. | **Sole Security Authority**: SecurityCenter remains authoritative. |
| **Knowledge Consolidation** | `backend/app/knowledge_consolidation/` (Task 92) | Reflects knowledge freshness and unresolved contradictions; emits operational summaries. | **Sole Knowledge Authority**: Task 92 manages memories. |
| **Native Rust Runtime** | `native/crates/kairo-runtime/`, `backend/app/native/` | Ingests process supervisor health, IPC protocol status, and active native executions. | **Single Runtime**: Protocol contract preserved. |

---

### 3. Epistemological Classification: Grounding Truth

| Classification | Definition | Example in State Graph |
| :--- | :--- | :--- |
| **OBSERVED** | Grounded in direct, timestamped empirical telemetry, socket probe, or event. | Native runtime process PID 4102 is active; heartbeats received. |
| **DERIVED** | Deterministically calculated via strict dependency propagation or causal logic. | Tool capability `local_file_read` is available because runtime is healthy. |
| **INFERRED** | Estimated via probabilistic model or operational assumption under incomplete data. | Worker queue latency implies task X may experience moderate queue delay. |
| **PREDICTED** | Output from forecasting, digital twin, or simulation models regarding future state. | Memory RSS projected to cross 80% threshold in 15 minutes. |
| **UNKNOWN** | State cannot be verified due to missing heartbeat, network partition, or unmonitored component. | Remote companion device state is unknown; heartbeat timed out. |

---

### 4. Operational State Graph Topology

```
                  [ GOAL: Complete Task 93 ]
                             │
                             ▼ (SERVES)
                 [ TASK: Implement State Graph ]
                             │
                             ▼ (EXECUTES)
               [ WORKFLOW: Verify & Build Subsystem ]
                             │
                             ▼ (INVOKES)
             [ CAPABILITY: system_state_engine (v1.0.0) ]
                             │
                             ▼ (DEPENDS_ON)
             ┌───────────────┴───────────────┐
             ▼                               ▼
  [ RUNTIME: Python Core ]       [ RUNTIME: Native Rust Daemon ]
             │                               │
             ▼ (CONSUMES)                    ▼ (CONSUMES)
  [ RESOURCE: CPU 12% ]           [ RESOURCE: Memory RSS 48MB ]
             │                               │
             └───────────────┬───────────────┘
                             ▼ (CONSTRAINED_BY)
             [ SECURITY: EmergencyStop = INACTIVE ]
             [ GOVERNANCE: Policy = AUTHORIZED ]
```

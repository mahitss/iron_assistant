# Kairo World Model, Live Environment State, Entity Graph, and State Awareness

## 1. Overview & Architecture

The **Kairo World Model** maintains a bounded, current, situational representation of the environment Kairo is authorized to observe.

### Core Principle
> **"What Kairo currently believes about authorized entities and their state."**

The World Model is a synchronized projection, **not** the source of truth:
- **GitHub** is authoritative for repository state, commit heads, and CI status.
- **Database** is authoritative for application records and persisted tasks.
- **Local Companion** is authoritative for device runtime and connection status.
- **SecurityCenter** is authoritative for authorization and permissions.
- **Observability** is authoritative for service health.

It must never pretend its cached state is more authoritative than the source, nor can it grant permissions or bypass security policies.

```
                      ┌───────────────────────────────────────────────┐
                      │             AUTHORITATIVE SOURCES             │
                      │  GitHub  | Local Companion | Observability    │
                      └──────────────────────┬────────────────────────┘
                                             │
                       (Signed Events & State Projections)
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             KAIRO WORLD MODEL                               │
│                                                                             │
│   ┌─────────────────────┐    ┌────────────────────┐    ┌────────────────┐   │
│   │    Entity Graph     │    │  Freshness Matrix  │    │ Conflict Engine│   │
│   │ (Devices, Repos,    │◄──►│ (TTL, Staleness,   │◄──►│(Authoritative  │   │
│   │  Services, Tasks)   │    │  Expiring States)  │    │  Source Wins)  │   │
│   └──────────┬──────────┘    └────────────────────┘    └────────────────┘   │
│              │                                                              │
│              ▼                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              Structured Queries & World Context Resolver            │   │
│   │      (Bounded Graph Traversal, Epistemic Labels: OBSERVED/STALE)    │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌───────────────────────┐                             ┌───────────────────────┐
│     Context Engine    │                             │ Autonomous Task Engine│
│ (Prompt Augmentation) │                             │   (Planning Context)  │
└───────────────────────┘                             └───────────────────────┘
```

---

## 2. Entities & Identification

Every modeled entity receives a stable internal identifier (`ent_{type}_{hash}`) while retaining its external source identity (`source`, `source_id`).

### Entity Types (Spec 3)
- `USER`: Authorized tenant user.
- `PROJECT`: User project boundary.
- `REPOSITORY`: Git code repository (contains default branch, commit hash, CI status).
- `BRANCH`: Git branch reference.
- `WORKFLOW`: Automation workflow definition.
- `TASK`: Autonomous task execution instance.
- `AGENT`: Active agent persona or subagent.
- `SKILL`: Reusable capability or tool group.
- `TOOL`: Individual executable tool.
- `DEVICE`: Workstation executing the Local Companion.
- `SERVICE`: Backend API, database, cache, or external microservice.
- `ENVIRONMENT`: Deployment boundary (`DEVELOPMENT`, `TEST`, `STAGING`, `PRODUCTION`).
- `DOCUMENT`: Project document or Knowledge Fabric artifact.
- `KNOWLEDGE_NODE`: Grounded knowledge concept.
- `AUTOMATION`: Scheduled or event-driven automation trigger.
- `NOTIFICATION`: User notification record.
- `MODEL`: AI model in ModelRouter cascade.
- `PROVIDER`: Model provider (e.g. OpenRouter, Ollama).

---

## 3. Relationships & Graph Traversal

Relationships between entities are strictly typed and owned:
- `OWNS`: User owns Project, Project owns Task.
- `CONTAINS`: Project contains Repository, Repository contains Branch.
- `BELONGS_TO`: Branch belongs to Repository.
- `DEPENDS_ON`: Service depends on Database, Task depends on Step.
- `RUNS`: Device runs Companion, Task runs Agent.
- `USES`: Agent uses Skill, Skill uses Tool.
- `CONNECTED_TO`: Device connected to Kairo.
- `DEPLOYED_TO`: Service deployed to Environment.
- `TRIGGERS`: Event triggers Workflow.
- `PRODUCES`: Task produces Document.
- `OBSERVED_ON`: Service observed on Environment.
- `SUPERSEDES`: New plan supersedes old plan.

### Traversal Budget
- Maximum traversal depth is bounded to $\le 3$ hops to prevent graph explosion.
- Query entity budget is capped at 100 entities per response.

---

## 4. Freshness & Staleness Policy

Observations expire based on entity type volatility:
- `DEVICE`: 60 seconds (active heartbeats)
- `SERVICE`: 120 seconds (health probes)
- `TASK`: 300 seconds (execution progress)
- `WORKFLOW`: 300 seconds
- `REPOSITORY`: 600 seconds (10 minutes)
- `PROJECT`: 3600 seconds (1 hour)

### Staleness Rules
- Expired observations are marked `STALE` and flagged with warning banners in the UI.
- Never-observed entities are marked `UNKNOWN` (never assumed `HEALTHY`).
- If an external source is offline, last known state is retained but marked `STALE`.

---

## 5. Conflict Resolution & Authority

When two updates conflict:
1. **Authoritative Source Priority**: The authoritative source strictly wins. Model inferences or external suggestions can **never** overwrite authoritative state.
2. **Version Ordering**: Lower state versions or older timestamps are rejected.
3. **Reconciliation**: If a conflict occurs, authoritative sources are queried to reconcile truth; states are never averaged.

---

## 6. Privacy & Anti-Surveillance Guarantees

The World Model enforces strict privacy boundaries:
- **No Raw Media Dumps**: Audio, video, and continuous screen recordings are never stored in the World Model.
- **No Physical Location Tracking**: Precise GPS coordinates (latitude/longitude) are forbidden; logical user labels ("Home PC", "Work Laptop") are used.
- **No Behavioral Profiling**: Operational states (device online) are recorded, but behavioral profiling ("user is watching screen") is forbidden.
- **Prompt Injection Immunity**: Untrusted external text (e.g. README claiming "Production is healthy") is sanitized and cannot alter authoritative state.

---

## 7. REST API Reference

All endpoints are mounted under `/api/v1/world`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/world` | High-level environment status, entity counts, and metrics overview. |
| `GET` | `/api/v1/world/projects/{project_id}` | Project-scoped environment state (repositories, tasks, services). |
| `GET` | `/api/v1/world/entities/{entity_id}` | Entity detail with freshness and attributes. |
| `GET` | `/api/v1/world/entities/{entity_id}/dependencies` | Bounded graph dependencies up to max depth. |
| `GET` | `/api/v1/world/changes` | Recent domain state changes within time window. |
| `POST` | `/api/v1/world/refresh` | Trigger rate-limited refresh from authoritative sources. |
| `POST` | `/api/v1/world/snapshots` | Capture point-in-time environment snapshot. |
| `GET` | `/api/v1/world/health` | Operational health and telemetry metrics. |

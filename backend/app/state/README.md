# Kairo Unified Data & State Fabric (Task 39)

The **Unified Data & State Fabric** provides a coherent, durable, versioned, consistent, and auditable state architecture across all Kairo subsystems.

## Core Architectural Invariants

1. **One Authoritative Owner**: Every entity domain (`tasks`, `approvals`, `policies`, `identity`, `notifications`, `memory`, `audit`, `projects`) has exactly ONE authoritative owning subsystem. No arbitrary component may mutate another subsystem's authoritative state directly.
2. **State Classification**: Every state object is strictly classified as `AUTHORITATIVE`, `DERIVED`, `CACHE`, `EPHEMERAL`, or `ARCHIVAL`.
3. **No Blind Overwrites / Concurrency Safety**: Monotonic integer versions with optimistic concurrency check (`expected_version == actual_version`). Mismatches raise `StateConflictError`.
4. **Cache Security & Non-Authoritativeness**: Caches are never the source of truth. All cache keys include security scopes (`user_id`, `project_id`). Cache misses or failures seamlessly fallback to authoritative stores.
5. **Durable Secret-Scrubbed Changelog**: All state transitions record an append-only change stream with actor, service, and correlation IDs. Sensitive credentials and tokens are scrubbed.
6. **Side-Effect-Free Projection Rebuild**: Rebuilding derived projections (e.g. World Model) strictly suppresses external side effects (no notifications, tools, deployments, or emails).
7. **Explicit State Machines**: Rigid validation of allowed state transitions across Tasks, Approvals, Notifications, Devices, and Sessions. Impossible states are detected and quarantined.
8. **Drift Detection Without Blind Remediation**: External systems (GitHub, cloud, device OS) are authoritative for their own state. Drift is detected and reported, but remediation is strictly routed through Intent, Policy, and Approvals.
9. **Zero Blind State Recovery**: Restored state revalidates policy, ownership, device trust, and freshness before resuming.

## API Endpoints (`/api/v1/state`)

- `GET /health`: Overall state fabric status, active record count, and quarantine count.
- `GET /records/{domain}/{resource_type}/{resource_id}`: Read state record under specified read consistency (`STRONG`, `READ_YOUR_WRITES`, `EVENTUAL`).
- `GET /changelog`: Query durable change stream.
- `POST /reconcile`: Run state reconciliation (`CHECK`, `REPORT`, `SAFE_REPAIR`, `FULL_REBUILD`).
- `GET /reconcile/last`: Get last reconciliation report.
- `GET /quarantine`: List actively quarantined records.
- `POST /quarantine/{resource_id}/release`: Release record from quarantine.

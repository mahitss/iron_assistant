# Kairo Perception, Environmental Awareness, Multi-Source Observation, and Situational Awareness Engine (Task 46)

## Overview

The **Kairo Perception & Environmental Awareness Engine** enables continuous, privacy-aware, bounded observation of authorized external environments. It transforms raw, heterogeneous telemetry into structured environmental awareness without directly executing consequential mutations.

---

## Core Principle

```
RAW EVENT
    ↓
 INGEST (Source verification & secret redaction)
    ↓
NORMALIZE (Heterogeneous sources converted to PerceptionEvent)
    ↓
VALIDATE (Structure, payload size limits, and cryptographic signatures)
    ↓
CLASSIFY (Source trust weighting & privacy level gating)
    ↓
CORRELATE (Trace linking & cross-system event graph)
    ↓
UPDATE WORLD MODEL (Reconciliation with authoritative state)
    ↓
DETECT CHANGE (Structural diffing & burst aggregation)
    ↓
DETERMINE SIGNIFICANCE (TRIVIAL, LOW, MEDIUM, HIGH, CRITICAL)
    ↓
OPTIONAL RESPONSE (Alerts & Proactive suggestions; never unapproved mutations)
```

**Canonical Rule**: Perception describes *what was observed*, not *why it happened*. High confidence is not verification. Perception does NOT directly execute consequential actions.

---

## Architecture

The perception subsystem is modularized in `backend/app/perception/`:

| Module | Purpose |
|---|---|
| `service.py` | Master `PerceptionService` coordinating ingestion, normalization, reconciliation, and awareness |
| `sources.py` | `SourceRegistry`, `PerceptionSource`, 22 `SourceType` categories, and explicit scope authorization |
| `adapters.py` | Source-specific adapters converting device, browser, git, fs, and service events to normalized format |
| `normalizer.py` | Dispatches events to adapters and enforces standard `PerceptionEvent` contracts |
| `events.py` | `PerceptionEvent`, 27 `EventType` enums, authenticity verification, and payload size bounds |
| `observations.py` | `Observation` empirical facts with confidence, latency, and freshness scoring |
| `deduplication.py` | `EventDeduplicator` hash and ID-based deduplication for idempotency guarantees |
| `ordering.py` | `EventOrderManager` sequence validation and out-of-order event handling |
| `freshness.py` | `FreshnessTracker` clock skew compensation and stale update overwrite protection |
| `correlator.py` | `EventCorrelator` linking multi-source chains with strict observation vs causation separation |
| `provenance.py` | `ProvenanceTracker` tracking transformation lineage and signature audits |
| `changes.py` | `ChangeDetector` structural diffing, change types, and burst aggregation |
| `significance.py` | `SignificanceClassifier` deterministic 5-tier change consequence evaluation |
| `environment.py` | `EnvironmentBoundaryGuard` enforcing strict isolation across 6 environments |
| `snapshots.py` | `SnapshotManager` versioned environmental state snapshots with missing data marked UNKNOWN |
| `reconciliation.py` | `StateReconciler` authoritative source preference and `EntityResolver` |
| `redaction.py` | `SecretRedactor` recursive credential, token, and password sanitization |
| `privacy.py` | `PerceptionPrivacyGuard` anti-surveillance defense and cross-tenant isolation |
| `context.py` | `PerceptionContext` and `RelevanceEngine` ranking observations for model context |
| `situation.py` | `SituationalAwarenessManager` fact/inference synthesis and live `Anomaly` detection |
| `sensors.py` | Multi-modal probes for device, browser, file, git, and service health telemetry |
| `health.py` | `PerceptionHealthMetrics` real-time ingestion observability |
| `models.py` | SQLAlchemy database models for sources, observations, changes, snapshots, and situations |
| `schemas.py` | Pydantic request and response schemas |
| `router.py` | FastAPI REST API endpoints mounted under `/api/v1/perception` |

---

## 22 Supported Source Types

1. `DEVICE`: System telemetry, power, network connectivity.
2. `DESKTOP`: Window focus and desktop notifications.
3. `APPLICATION`: Process and application lifecycle.
4. `BROWSER`: Navigation, page title, DOM errors (excluding credentials).
5. `FILE_SYSTEM`: Scoped file modifications (metadata only, no content auto-read).
6. `GIT`: Local commits, branches, and working tree hashes.
7. `GITHUB`: Issues, PRs, workflow checks, and release milestones.
8. `DEPLOYMENT`: Rollout status, container versions, and health checks.
9. `SERVICE`: Endpoint availability, latency, and error rates.
10. `DATABASE`: Connection status and schema migration signals.
11. `API`: Third-party webhook callbacks and polling feeds.
12. `NETWORK`: Connectivity and DNS resolution telemetry.
13. `NOTIFICATION`: System and application alert streams.
14. `VOICE`: Voice activity events (transcriptions only; no raw audio retention).
15. `VISION`: Visual object detections (bounding boxes only; no raw video retention).
16. `CALENDAR`: Scheduled events and upcoming maintenance windows.
17. `AUTOMATION`: Scheduled workflows and cron job executions.
18. `AGENT`: Multi-agent subtask lifecycle and contract status.
19. `TASK_ENGINE`: Long-running autonomous task updates.
20. `WORLD_MODEL`: Authoritative entity synchronization.
21. `USER_INPUT`: Explicit commands and prompts.
22. `SYSTEM`: Kernel and host operating system signals.

---

## Security & Invariant Checklist (Spec 198)

- **Can an unauthorized source inject state?** NO. `PerceptionSourceScope` validates caller user, project, and device boundaries.
- **Can an event overwrite authoritative state?** NO. `StateReconciler` rejects weaker observations that contradict authoritative state.
- **Can stale events overwrite fresh state?** NO. `FreshnessTracker` blocks updates where event timestamp is older than current state.
- **Can one user see another user's environment?** NO. `PerceptionPrivacyGuard` enforces cross-user isolation (`CrossTenantPerceptionError`).
- **Can one project see another project's state?** NO. Cross-project isolation is enforced at source and query level.
- **Can screen, camera, or mic capture happen without authorization?** NO. Explicit consent is mandatory; continuous surveillance is strictly blocked (`PrivacyViolationError`).
- **Can credentials enter event storage?** NO. `SecretRedactor` redacts passwords, tokens, and keys before normalization and persistence.
- **Can external page content become system instructions?** NO. Payloads are strictly treated as data, never prompt instructions.
- **Can duplicate events corrupt state?** NO. `EventDeduplicator` enforces idempotency.
- **Can out-of-order events corrupt state?** NO. `EventOrderManager` buffers and detects sequential gaps.
- **Can an unknown source state become healthy?** NO. Missing telemetry becomes `UNKNOWN`, never `HEALTHY`.
- **Can anomaly detection trigger automatic destructive actions?** NO. Perception signals anomalies for human/governed review; it never executes mutations directly.
- **Can perception bypass Policy or SecurityCenter?** NO. All consequential workflows remain governed by PolicyEngine and SecurityCenter.
- **Can replay trigger real side effects?** NO. Replay deterministically reconstructs in-memory observations without invoking side effects.
- **Can disabling a source falsely preserve old state as current?** NO. Disabling a source immediately marks its state `UNKNOWN/UNAVAILABLE`.

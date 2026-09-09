# Kairo Unified Event Bus & Event-Driven Runtime Architecture

## Overview

The Kairo Unified Event Bus is the central asynchronous nervous system of Kairo. It enables cross-subsystem coordination, decoupled reactive workflows, proactive intelligence, audit trails, and user notifications without tightly coupling source components to side-effecting handlers.

```
SOURCE (e.g. GitHub CI, Chat, Security Center, Device, Evaluation)
  │
  ▼
EVENT BUS (Authority Validation + Trace/Secret Redaction + Lineage Tracking)
  │
  ├── Deduplication Guard (Sliding window on event_id / idempotency_key)
  │
  ├── Transactional Outbox (Atomic database state & event staging)
  │
  ▼
SUBSCRIBERS (Priority-ordered, Tenant/User Isolation, Pattern Matching)
  │
  ├── Failure Isolation (gather return_exceptions=True; individual handler crash never breaks others)
  ├── Exponential Backoff Retry (Transient vs Permanent failure classification)
  └── Dead Letter Queue (Sanitized trace logging, guarded replay policy)
  │
  ▼
SIDE EFFECTS
  ├── Knowledge & Memory Ingestion (Automatic indexing of completed actions)
  ├── Proactive Intelligence (Automated remediation suggestions)
  ├── User Alerts & Notifications (Web/companion delivery)
  ├── Tamper-Evident Audit Logging (Authoritative SecurityCenter records)
  └── User Activity Feed (/api/v1/events/activity)
```

---

## Core Principles & Security Constraints

1. **The Event Bus is NOT a Security Authority**:
   - An event such as `security.allowed` or `approval.granted` communicates decisions that occurred.
   - `SecurityCenter` and `ApprovalManager` remain authoritative.
   - High-privilege actions NEVER execute solely on historical event logs.
2. **Prompt Injection & Event Forgery Immunity**:
   - Model outputs, chat users, and autonomous LLM agents can NEVER publish privileged security events (`security.allowed`, `approval.granted`, `device.authorized`).
   - Publication authority is strictly enforced at the bus boundary (`EventSecurityGuard.validate_publication_authority`).
3. **Tenant & User Isolation**:
   - Subscribers scoped to User A will NEVER receive events belonging to User B.
   - System-wide subscribers (e.g., AuditLogger, Global Metrics) must be explicitly flagged with `system_wide=True`.
4. **Zero Secret Leakage**:
   - All event payloads, logs, error traces, and dead-letter records pass through automated secret redaction (`EventSecurityGuard.sanitize_event`), stripping API keys, tokens, and credentials.
5. **Replay Safety**:
   - Replay safety is classified per event type:
     - `REPLAY_SAFE`: Idempotent operations (e.g. `knowledge.index.requested`, `notification.read`).
     - `REPLAY_REQUIRES_REVIEW`: Requires explicit human confirmation/review before replaying from Dead Letter Queue.
     - `NON_REPLAYABLE`: Side-effecting operations (e.g. `github.write`, `computer.action`, `device.revoked`). Replay is strictly forbidden.

---

## Canonical Event Schema

Every event passing through the bus conforms to the canonical `Event` schema:

```json
{
  "event_id": "uuid-v4",
  "event_type": "github.ci.failed",
  "event_version": "1.0.0",
  "timestamp": "2026-09-09T12:00:00Z",
  "source": "github_webhook",
  "user_id": "user_123",
  "project_id": "proj_456",
  "correlation_id": "corr_abc",
  "causation_id": "caus_def",
  "payload": {
    "repo": "kairo-assistant/core",
    "workflow_name": "CI",
    "run_id": "987654",
    "failure_summary": "Tests failed in tests/test_event_bus.py"
  },
  "metadata": {
    "idempotency_key": "gh_run_987654"
  }
}
```

---

## 18 Registered Namespaces

| Namespace | Description | Sample Event Types | Default Replay Safety |
|---|---|---|---|
| `chat.*` | Conversational interactions | `chat.message.created`, `chat.response.completed` | `REPLAY_SAFE` |
| `github.*` | Repository & CI/CD signals | `github.ci.failed`, `github.pr.merged`, `github.issue.created` | `REPLAY_REQUIRES_REVIEW` |
| `security.*` | Violations & guard decisions | `security.blocked`, `security.allowed`, `security.violation` | `NON_REPLAYABLE` |
| `approval.*` | Human-in-the-loop approvals | `approval.requested`, `approval.granted`, `approval.denied` | `NON_REPLAYABLE` |
| `emergency_stop.*` | Emergency shutdown triggers | `emergency_stop.activated`, `emergency_stop.cleared` | `NON_REPLAYABLE` |
| `knowledge.*` | Knowledge fabric updates | `knowledge.index.requested`, `knowledge.indexed` | `REPLAY_SAFE` |
| `memory.*` | Long-term memory storage | `memory.stored`, `memory.pruned` | `REPLAY_SAFE` |
| `project.*` | Project management updates | `project.created`, `project.updated`, `project.archived` | `REPLAY_REQUIRES_REVIEW` |
| `device.*` | Companion device lifecycle | `device.registered`, `device.connected`, `device.revoked` | `NON_REPLAYABLE` |
| `notification.*` | User alert dispatches | `notification.created`, `notification.read` | `REPLAY_SAFE` |
| `evaluation.*` | Benchmarking & evaluations | `evaluation.started`, `evaluation.completed` | `REPLAY_SAFE` |
| `voice.*` | Audio streaming sessions | `voice.session.started`, `voice.session.ended` | `NON_REPLAYABLE` |
| `vision.*` | Image & visual inspection | `vision.requested`, `vision.processed` | `REPLAY_SAFE` |
| `computer.*` | OS / desktop automation | `computer.action.requested`, `computer.action.blocked` | `NON_REPLAYABLE` |
| `web_monitor.*` | Web polling & page alerts | `web_monitor.changed`, `web_monitor.error` | `REPLAY_SAFE` |
| `agent.*` | Multi-agent task execution | `agent.task.started`, `agent.task.completed` | `REPLAY_REQUIRES_REVIEW` |
| `automation.*` | Workflow triggers & steps | `automation.triggered`, `automation.step.completed` | `REPLAY_REQUIRES_REVIEW` |
| `system.*` | Host & provider telemetry | `service.started`, `provider.degraded`, `provider.recovered` | `NON_REPLAYABLE` |

---

## API Endpoints

- `GET /api/v1/events/registry`: Full catalog of registered events and contracts.
- `GET /api/v1/events/metrics`: Bus throughput, p95 latency, retry counts, queue depth.
- `GET /api/v1/events/dead-letters`: List failed/dead-lettered events with pagination and filters.
- `POST /api/v1/events/dead-letters/{id}/replay`: Replay dead letter with replay safety validation.
- `POST /api/v1/events/dead-letters/{id}/discard`: Discard dead letter.
- `GET /api/v1/events/activity`: User-scoped activity feed timeline.
- `POST /api/v1/events/publish`: Publish client-origin event with authority enforcement.

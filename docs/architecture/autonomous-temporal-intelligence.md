# Kairo Autonomous Temporal Intelligence, Event History, Change Reconstruction & "What Changed?" Engine

## 1. Overview & Conceptual Architecture

Kairo Autonomous Temporal Intelligence (Task 111) provides a unified, production-grade temporal intelligence layer across all Kairo events, states, observations, decisions, actions, missions, multi-agent activities, memory, and beliefs.

Rather than creating duplicate event buses, second world models, or redundant causal engines, Task 111 establishes an authoritative projection and query interface over the existing event store (`events`), causal engine (`app.causal.temporal_engine`), Task 110 Cognitive Working Set, Task 109 Attention, Task 100 Mission Control, Task 99 Situation Awareness, and Task 95 ActionTransactions.

```
                    HETEROGENEOUS KAIRO EVENTS
                    (Action, Telemetry, Mission,
                     WorldState, Decision, Chat)
                                │
                                ▼
                   TEMPORAL NORMALIZATION LAYER
                     (NormalizationEngine)
        - Multi-clock separation (Event, Observed, Ingested, Effective)
        - Payload disarming & untrusted content sanitization
        - Deterministic category mapping
                                │
                                ▼
                   ORDERING & WATERMARK ENGINE
                      (OrderingEngine)
        - Deterministic sequence & monotonic sorting
        - Out-of-order and late event tagging
        - Deduplication without state distortion
        - Subsystem watermark tracking (source, ingestion, processing)
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
  TIMELINE ENGINE       "WHAT CHANGED?"         ATTRIBUTION ENGINE
 (TimelineEngine)         DIFF ENGINE          (AttributionEngine)
- Entity & Global      (DiffEngine)            - Strictly non-fabricating
  Timelines           - Deep structural diff   - Reuses TemporalCausalityEngine
- StateTransitions     - Semantic categories:   - Expected vs Actual analysis
- Bounded segments       ADDED, REMOVED,       - Deterministic action linkage
                         MODIFIED, DEGRADED,   - Certainty levels:
                         RECOVERED, STALE        DIRECT, STRONG, POSSIBLE,
                                                 CORRELATED, UNATTRIBUTED
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                 RECONSTRUCTION & QUERY ENGINE
              (ReconstructionEngine, QueryEngine)
        - Bounded temporal queries (limit <= 1000)
        - Point-in-time historical "state_as_of" (flagged historical_only)
        - Temporal anomaly detection (Rapid oscillation, future-dated events)
        - Silent telemetry gap detection
        - Offline reconnection catch-up reconciliation
                                │
                                ▼
                   DOWNSTREAM COGNITIVE BRIDGES
                    (DownstreamTemporalBridges)
        - Task 110: Bounded context working set injection
        - Task 109: Salience boosts without priority usurpation
        - EmergencyStop fail-closed action suppression
        - NO_ACTION recommendation evaluation
```

---

## 2. Core Architectural Invariants

1. **`EVENT != STATE != CAUSE`**: An event records that a signal arrived. A state describes an entity's condition. A cause is a verified relationship requiring evidence and precedence.
2. **`TEMPORAL ORDER != CAUSATION` & `CORRELATION != CAUSATION`**: An event occurring before a state mutation does not prove it caused the mutation. Without deterministic links (transaction ID, correlation ID) or entity alignment, attribution remains `UNATTRIBUTED` or `CORRELATED`.
3. **Multi-Clock Timestamps**: Distinct clocks are preserved:
   - `event_time`: When the occurrence physically happened.
   - `observed_time`: When a sensor or agent detected it.
   - `ingested_time`: When stored in Kairo persistence.
   - `processed_time`: When normalized by the temporal engine.
   - `effective_time`: When state became operationally active.
4. **Historical Isolation**: Historical queries (`state_as_of`) explicitly return `"is_historical_reconstruction": True` and `"historical_only": True`. Historical state can **never** masquerade as current state or authorize current actions.
5. **Fail-Closed Safety**: EmergencyStop overrides all cognition. Temporal intelligence cannot directly execute actions (`hasattr(service, "execute_action") == False`).
6. **No Raw CoT Persistence**: Sensitive thought processes and unvetted chain-of-thought instructions are filtered and never stored in temporal event summaries or state diffs.

---

## 3. Multi-Clock Semantics & Normalization

The `NormalizationEngine` maps heterogenous events into a normalized `TemporalEvent`:

```python
from app.temporal.normalization_engine import NormalizationEngine

raw_event = {
    "event_id": "evt_action_99",
    "event_type": "action.executed",
    "event_time": "2026-09-18T05:00:00Z",
    "observed_time": "2026-09-18T05:00:02Z",
    "source": "action_executor",
    "entity_id": "service_db",
    "payload": {"status": "SUCCESS"}
}

temporal_event = NormalizationEngine.normalize(raw_event)
assert temporal_event.clocks.event_time != temporal_event.clocks.ingested_time
assert temporal_event.clocks.ingestion_lag_seconds >= 0.0
```

### Untrusted Content Disarming
If an event arrives from untrusted sources (`untrusted_web`, `external_api`, `user_file`) or contains instruction smuggling patterns (`"ignore previous"`, `"system override"`), `is_untrusted` is flagged `True` and confidence is curtailed to `<= 0.8`.

---

## 4. "What Changed?" Diff Engine

The `DiffEngine` computes semantic diffs between two state dictionaries, snapshot models, or checkpoint hashes:

```python
from app.temporal.diff_engine import DiffEngine

state_a = {"cluster_nodes": 5, "service_status": "READY"}
state_b = {"cluster_nodes": 3, "service_status": "DEGRADED", "new_feature_flag": True}

changeset = DiffEngine.compute_diff(
    state_a=state_a,
    state_b=state_b,
    from_reference="snapshot_v1",
    to_reference="snapshot_v2",
    entity_id="cluster_prod"
)

# Output ChangeCategories:
# - cluster_nodes: MODIFIED (5 -> 3)
# - service_status: DEGRADED (READY -> DEGRADED)
# - new_feature_flag: ADDED (None -> True)
```

Categories include: `ADDED`, `REMOVED`, `MODIFIED`, `REORDERED`, `SUPERSEDED`, `EXPIRED`, `STALE`, `RECOVERED`, `DEGRADED`, and `UNKNOWN`.

---

## 5. Non-Fabricating Causal Attribution

The `AttributionEngine` reuses `app.causal.temporal_engine.TemporalCausalityEngine.validate_temporal_precedence` to enforce strict cause-before-effect ordering.

```
Attribution Certainty Hierarchy:
├── DIRECTLY_ATTRIBUTED: ActionTransaction ID, trigger ID, or matching correlation ID
├── STRONGLY_LINKED: Same entity, verified lag < 5.0s, high confidence
├── POSSIBLY_LINKED: Same entity, verified lag < 60.0s
├── CORRELATED: Proximity within 60.0s but disparate entities or unverified link
└── UNATTRIBUTED: No candidate causes or external mutation (never fabricated)
```

---

## 6. Expected vs Actual Analysis

Tracks whether actions, milestones, or simulations achieved their expected outcomes:

```python
from app.temporal.attribution_engine import AttributionEngine

eva = AttributionEngine.evaluate_expected_vs_actual(
    subject_entity_id="action_restart",
    expected_state="RUNNING",
    observed_state="RUNNING",
    expected_by=deadline,
    observed_at=observation_time
)
# Status: VERIFIED (or CONTRADICTED if observed != expected, UNVERIFIED if deadline passed without observation)
```

---

## 7. Offline Disconnection Catch-Up Reconstruction

When Kairo reconnects after being offline:
1. Surfaces unobserved telemetry gaps (`TemporalGap`).
2. Computes the diff between pre-disconnection state and current state (`DiffEngine`).
3. Reconciles state transitions without blindly replaying high-frequency noise.
4. Advances subsystem watermarks to current time.

```python
changeset, gaps = service.reconcile_offline(
    subsystem="cluster_prod",
    prior_state=pre_offline_state,
    observed_current_state=post_offline_state,
    reconnect_time=utc_now()
)
```

---

## 8. REST API & CLI Interface

### REST Endpoints
- `POST /api/v1/temporal/query`: Bounded temporal query.
- `GET /api/v1/temporal/timeline/{entity_id}`: Chronological timeline for entity.
- `GET /api/v1/temporal/changes`: List recent changesets.
- `GET /api/v1/temporal/state/{entity_id}`: Current entity state.
- `GET /api/v1/temporal/state/{entity_id}/as-of?as_of_time=...`: Point-in-time historical reconstruction.
- `POST /api/v1/temporal/diff`: Semantic diff between two state dictionaries or checkpoints.
- `GET /api/v1/temporal/gaps`: Surface unobserved telemetry gaps.
- `GET /api/v1/temporal/anomalies`: List temporal anomalies (oscillation, future timestamps).
- `GET /api/v1/temporal/watermarks`: List subsystem watermarks and processing lag.
- `POST /api/v1/temporal/checkpoint`: Capture a new named temporal checkpoint.
- `POST /api/v1/temporal/reconstruct`: Trigger offline catch-up reconstruction.

### CLI Commands
```bash
# Timeline inspection
python -m app.temporal.cli timeline cluster_prod --limit 20

# Recent changes
python -m app.temporal.cli changes cluster_prod

# State as-of specific timestamp
python -m app.temporal.cli state-at cluster_prod 2026-09-18T00:00:00Z

# Semantic diff between two checkpoints or JSON objects
python -m app.temporal.cli diff chkp_1 chkp_2
python -m app.temporal.cli diff '{"nodes": 3}' '{"nodes": 5}'

# Diagnostics
python -m app.temporal.cli gaps
python -m app.temporal.cli anomalies
python -m app.temporal.cli watermarks

# Create checkpoint
python -m app.temporal.cli checkpoint pre_deployment_v2

# Reconcile offline period
python -m app.temporal.cli reconstruct
```

---

## 9. Frontend Temporal Intelligence UI

Located in `frontend/components/temporal/temporalIntelligenceView.js`, the view provides:
- **Global & Entity Timeline Explorer**: Chronological event segments, transition badges, and evidence traces.
- **"What Changed?" Diff Viewer**: Semantic colored diffs (`ADDED`, `REMOVED`, `MODIFIED`, `DEGRADED`, `RECOVERED`).
- **As-Of Point-in-Time Inspector**: Historical state query interface with mandatory `HISTORICAL RECONSTRUCTION` badge.
- **Telemetry Gaps & Anomalies**: Card list of detected oscillations, clock skews, and silent telemetry gaps.
- **Watermark Lag Meters**: Visual gauge showing ingestion vs processing vs reconciliation lag.

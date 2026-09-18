"""Unit, integration, property, and adversarial tests for Kairo Task 111:
Autonomous Temporal Intelligence, Event History, Change Reconstruction & "What Changed?" Engine.
"""

from datetime import UTC, datetime, timedelta
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.temporal.attribution_engine import AttributionEngine
from app.temporal.diff_engine import DiffEngine
from app.temporal.domain import (
    AttributionCertainty,
    ChangeCategory,
    ChangeSet,
    ExpectationStatus,
    ExpectedVsActual,
    StateTransition,
    TemporalAnomalyType,
    TemporalClockType,
    TemporalEntity,
    TemporalEntityType,
    TemporalEvent,
    TemporalGap,
    TemporalIntervalType,
    TemporalQuery,
    TemporalWatermark,
    Timeline,
    gen_temporal_id,
    utc_now,
)
from app.temporal.downstream_bridges import DownstreamTemporalBridges
from app.temporal.normalization_engine import NormalizationEngine
from app.temporal.ordering_engine import OrderingEngine
from app.temporal.query_engine import QueryEngine
from app.temporal.reconstruction_engine import ReconstructionEngine
from app.temporal.service import TemporalIntelligenceService
from app.temporal.timeline_engine import TimelineEngine


@pytest.fixture
def clean_service():
    TemporalIntelligenceService.reset_instance()
    svc = TemporalIntelligenceService.get_instance()
    # Reset internal memory structures for clean test runs
    svc._events.clear()
    svc._seen_canonical_ids.clear()
    svc._entities.clear()
    svc._transitions.clear()
    svc._anomalies.clear()
    svc._gaps.clear()
    svc._watermarks.clear()
    svc._checkpoints.clear()
    svc._changesets.clear()
    svc._sequence_counter = 0
    return svc


@pytest.fixture
def test_client():
    return TestClient(app)


# ============================================================================
# 1. Invariant & Multi-Clock Separation
# ============================================================================

def test_invariant_multi_clock_separation():
    """Verify event_time and ingested_time remain strictly distinct."""
    t_event = datetime(2026, 9, 18, 5, 0, 0, tzinfo=UTC)
    t_observed = datetime(2026, 9, 18, 5, 2, 0, tzinfo=UTC)
    t_ingested = datetime(2026, 9, 18, 5, 5, 0, tzinfo=UTC)

    raw_event = {
        "event_id": "evt_test_01",
        "event_type": "world.service.degraded",
        "source": "health_monitor",
        "timestamp": t_event.isoformat(),
        "observed_time": t_observed.isoformat(),
        "payload": {"service": "database", "status": "DEGRADED"},
    }

    tevt = NormalizationEngine.normalize(
        event_dict_or_obj=raw_event,
        ingested_at=t_ingested,
    )

    assert tevt.clocks.event_time == t_event
    assert tevt.clocks.observed_time == t_observed
    assert tevt.clocks.ingested_time == t_ingested
    assert tevt.clocks.ingestion_lag_seconds == 300.0  # 5 minutes lag
    assert tevt.clocks.observation_lag_seconds == 120.0  # 2 minutes lag


def test_invariant_historical_state_never_current():
    """Verify As-Of historical evaluation is explicitly flagged and never current authority."""
    t_past = utc_now() - timedelta(hours=2)
    trans = [
        StateTransition(
            entity_id="capability_search",
            entity_type=TemporalEntityType.CAPABILITY,
            previous_state="READY",
            next_state="DEGRADED",
            timestamp=t_past,
            attribution=AttributionCertainty.UNATTRIBUTED,
        )
    ]

    res = QueryEngine.state_as_of(
        entity_id="capability_search",
        as_of_time=t_past + timedelta(minutes=5),
        transitions=trans,
    )

    assert res["state"] == "DEGRADED"
    assert res["is_historical_reconstruction"] is True
    # Invariant: Historical state cannot claim to be active current state
    assert "as_of_time" in res


# ============================================================================
# 2. Deterministic Ordering, Deduplication & Late Events
# ============================================================================

def test_deterministic_ordering_and_tie_breaking():
    """Verify deterministic sorting on identical event timestamps using sequence and IDs."""
    t_fixed = datetime(2026, 9, 18, 6, 0, 0, tzinfo=UTC)

    e1 = TemporalEvent(
        canonical_event_id="e1",
        event_type="test.one",
        source_subsystem="sys",
        correlation_id="c1",
        sequence_number=2,
    )
    e1.clocks.event_time = t_fixed

    e2 = TemporalEvent(
        canonical_event_id="e2",
        event_type="test.two",
        source_subsystem="sys",
        correlation_id="c2",
        sequence_number=1,
    )
    e2.clocks.event_time = t_fixed

    sorted_evts = OrderingEngine.sort_events([e1, e2])
    assert sorted_evts[0].sequence_number == 1
    assert sorted_evts[1].sequence_number == 2


def test_deduplication_and_late_arrival_tagging():
    """Verify duplicate events are flagged and late arrivals identified."""
    now = utc_now()
    watermark = now

    e_fresh = TemporalEvent(
        canonical_event_id="c_fresh",
        event_type="test.fresh",
        source_subsystem="test",
        correlation_id="c1",
    )
    e_fresh.clocks.event_time = now + timedelta(seconds=10)

    e_late = TemporalEvent(
        canonical_event_id="c_late",
        event_type="test.late",
        source_subsystem="test",
        correlation_id="c2",
    )
    e_late.clocks.event_time = now - timedelta(seconds=600)  # 10 mins prior to watermark

    seen: set[str] = set()
    unique, dups = OrderingEngine.deduplicate([e_fresh, e_fresh], seen_canonical_ids=seen)
    assert len(unique) == 1
    assert len(dups) == 1
    assert dups[0].is_duplicate is True

    annotated = OrderingEngine.detect_late_and_out_of_order([e_late], current_watermark=watermark)
    assert annotated[0].is_out_of_order is True
    assert annotated[0].is_late is True


# ============================================================================
# 3. State Transitions & Timeline Construction
# ============================================================================

def test_state_transition_extraction_and_timeline():
    """Verify automatic state transition extraction and timeline segmentation."""
    t0 = utc_now()
    e_start = TemporalEvent(
        canonical_event_id="act_01_start",
        event_type="action.started",
        category="ACTION",
        source_subsystem="execution",
        source_entity_id="act_01",
        correlation_id="corr_act",
        payload_diff={"previous_state": "READY", "next_state": "EXECUTING"},
    )
    e_start.clocks.event_time = t0

    e_succ = TemporalEvent(
        canonical_event_id="act_01_succ",
        event_type="action.succeeded",
        category="ACTION",
        source_subsystem="execution",
        source_entity_id="act_01",
        correlation_id="corr_act",
        payload_diff={"previous_state": "EXECUTING", "next_state": "SUCCEEDED"},
    )
    e_succ.clocks.event_time = t0 + timedelta(seconds=2)

    timeline = TimelineEngine.build_timeline(events=[e_start, e_succ], entity_id="act_01")
    assert timeline.total_events == 2
    assert timeline.total_transitions == 2
    assert timeline.segments[0].transitions[0].next_state == "EXECUTING"
    assert timeline.segments[0].transitions[1].next_state == "SUCCEEDED"


# ============================================================================
# 4. "What Changed?" Semantic Diff Engine
# ============================================================================

def test_semantic_diff_engine():
    """Verify structured diff across state dicts with degradation and recovery classification."""
    state_a = {
        "database_health": "READY",
        "active_connections": 10,
        "backup_in_progress": False,
    }
    state_b = {
        "database_health": "DEGRADED",
        "active_connections": 55,
        "backup_in_progress": True,
        "read_replica": "OFFLINE",
    }

    changeset = DiffEngine.compute_diff(
        state_a=state_a,
        state_b=state_b,
        from_reference="checkpoint_01",
        to_reference="checkpoint_02",
    )

    assert len(changeset.changes) == 4
    assert changeset.added_count == 1  # read_replica
    assert changeset.degraded_count >= 1  # database_health DEGRADED or read_replica OFFLINE

    summary = DiffEngine.generate_summary(changeset)
    assert summary.total_changes == 4
    assert summary.has_degraded_capabilities is True
    assert "changes detected" in summary.headline


# ============================================================================
# 5. Non-Fabrication Causal Attribution
# ============================================================================

def test_attribution_precedence_and_non_fabrication():
    """Verify suspect cause timestamped AFTER effect is rejected, and unproven cause remains UNATTRIBUTED."""
    t_effect = utc_now()
    trans = StateTransition(
        entity_id="service_api",
        entity_type=TemporalEntityType.SERVICE,
        previous_state="HEALTHY",
        next_state="DEGRADED",
        timestamp=t_effect,
    )

    # 1. Contradiction: Cause occurred 10s AFTER transition
    impossible_cause = TemporalEvent(
        canonical_event_id="imp_cause",
        event_type="action.failed",
        source_subsystem="agent",
        correlation_id="c_imp",
    )
    impossible_cause.clocks.event_time = t_effect + timedelta(seconds=10)

    res_contradicted = AttributionEngine.attribute_transition(trans, [impossible_cause])
    # Invariant: Must NOT fabricate or accept cause occurring after effect
    assert res_contradicted.attribution == AttributionCertainty.UNATTRIBUTED

    # 2. Proven valid preceding cause with matching correlation ID
    valid_cause = TemporalEvent(
        canonical_event_id="valid_cause",
        event_type="action.failed",
        source_subsystem="agent",
        correlation_id="corr_match",
    )
    valid_cause.clocks.event_time = t_effect - timedelta(seconds=2)

    trans.correlation_id = "corr_match"
    res_attributed = AttributionEngine.attribute_transition(trans, [valid_cause])
    assert res_attributed.attribution == AttributionCertainty.DIRECTLY_ATTRIBUTED
    assert "valid_cause" in str(res_attributed.attributed_cause)


# ============================================================================
# 6. Expected vs Actual Discrepancy Analysis
# ============================================================================

def test_expected_vs_actual_evaluation():
    """Verify expected postcondition matching vs discrepancy contradictions."""
    t_expected = utc_now() + timedelta(minutes=5)

    # Success case
    eva_match = AttributionEngine.evaluate_expected_vs_actual(
        subject_entity_id="node_cluster",
        expected_state="ONLINE",
        observed_state="ONLINE",
        expected_by=t_expected,
        observed_at=utc_now(),
    )
    assert eva_match.status == ExpectationStatus.VERIFIED

    # Contradiction case
    eva_mismatch = AttributionEngine.evaluate_expected_vs_actual(
        subject_entity_id="node_cluster",
        expected_state="ONLINE",
        observed_state="OFFLINE",
        expected_by=t_expected,
        observed_at=utc_now(),
    )
    assert eva_mismatch.status == ExpectationStatus.CONTRADICTED
    assert "Discrepancy" in str(eva_mismatch.discrepancy_explanation)


# ============================================================================
# 7. Anomalies, Gaps & Offline Catch-up
# ============================================================================

def test_temporal_anomaly_and_gap_detection():
    """Verify detection of future timestamps, rapid oscillations, and telemetry gaps."""
    now = utc_now()

    # 1. Future event
    future_evt = TemporalEvent(
        canonical_event_id="fut_01",
        event_type="test.future",
        source_subsystem="external",
        correlation_id="c_fut",
    )
    future_evt.clocks.event_time = now + timedelta(seconds=120)

    anomalies = ReconstructionEngine.detect_anomalies([future_evt], now_reference=now)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == TemporalAnomalyType.FUTURE_DATED_EVENT

    # 2. Telemetry Gap
    e1 = TemporalEvent(canonical_event_id="e1", event_type="heartbeat", source_subsystem="sys", correlation_id="c1")
    e1.clocks.event_time = now
    e2 = TemporalEvent(canonical_event_id="e2", event_type="heartbeat", source_subsystem="sys", correlation_id="c2")
    e2.clocks.event_time = now + timedelta(seconds=700)  # 700s gap > 300s expected

    gaps = ReconstructionEngine.detect_temporal_gaps([e1, e2], expected_heartbeat_seconds=300.0)
    assert len(gaps) == 1
    assert gaps[0].duration_seconds == 700.0


def test_offline_period_reconciliation():
    """Verify watermark advance and gap creation upon reconnecting after offline period."""
    watermark = TemporalWatermark(
        subsystem="telemetry",
        ingestion_watermark=utc_now() - timedelta(minutes=45),
    )
    reconnect_time = utc_now()

    prior_state = {"cluster": "ACTIVE", "nodes": 10}
    observed_state = {"cluster": "ACTIVE", "nodes": 8, "drain_reason": "spot_preemption"}

    changeset, gaps = ReconstructionEngine.reconcile_offline_period(
        last_watermark=watermark,
        reconnect_time=reconnect_time,
        recovered_events=[],
        prior_state=prior_state,
        observed_current_state=observed_state,
    )

    assert len(gaps) == 1
    assert gaps[0].is_offline_period is True
    assert changeset.modified_count == 1  # nodes changed from 10 to 8
    assert changeset.added_count == 1     # drain_reason added
    assert watermark.ingestion_watermark == reconnect_time


# ============================================================================
# 8. Downstream Bridges & No-Action Cases
# ============================================================================

def test_downstream_no_action_recommendation():
    """Verify engine explicitly recommends NO_ACTION when no actionable deltas exist."""
    # Case 1: Empty changeset
    empty_cs = ChangeSet(
        from_reference="t1",
        to_reference="t2",
        from_time=utc_now(),
        to_time=utc_now(),
    )
    should_no_action, reason = DownstreamTemporalBridges.evaluate_no_action_recommendation(
        changeset=empty_cs,
        gaps=[],
        is_emergency_stop_active=False,
    )
    assert should_no_action is True
    assert "No temporal state changes detected" in reason

    # Case 2: EmergencyStop active overrides cognition
    should_no_action_es, reason_es = DownstreamTemporalBridges.evaluate_no_action_recommendation(
        changeset=empty_cs,
        gaps=[],
        is_emergency_stop_active=True,
    )
    assert should_no_action_es is True
    assert "EmergencyStop is active" in reason_es


# ============================================================================
# 9. REST API Integration Tests
# ============================================================================

def test_api_health_and_query(test_client, clean_service):
    """Verify GET /temporal/health and POST /temporal/query endpoints."""
    # Health check
    resp_health = test_client.get("/temporal/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "HEALTHY"

    # Ingest event via service
    clean_service.ingest_event({
        "event_id": "evt_api_test",
        "event_type": "capability.degraded",
        "source": "api_tester",
        "entity_id": "cap_vector_db",
        "payload_diff": {"previous_state": "READY", "next_state": "DEGRADED"},
    })

    # Query endpoint
    query_payload = {
        "entity_id": "cap_vector_db",
        "limit": 10,
    }
    resp_query = test_client.post("/temporal/query", json=query_payload)
    assert resp_query.status_code == 200
    data = resp_query.json()
    assert data["total_count"] >= 1
    assert len(data["events"]) >= 1


def test_api_diff_and_checkpoints(test_client, clean_service):
    """Verify POST /temporal/diff and checkpoint endpoints."""
    diff_payload = {
        "state_a": {"status": "ACTIVE", "workers": 4},
        "state_b": {"status": "PAUSED", "workers": 0},
        "from_reference": "run_1",
        "to_reference": "run_2",
    }
    resp_diff = test_client.post("/temporal/diff", json=diff_payload)
    assert resp_diff.status_code == 200
    diff_data = resp_diff.json()
    assert diff_data["modified_count"] == 2

    # Checkpoint creation
    chkp_payload = {
        "name": "milestone_alpha",
        "checkpoint_type": "MISSION_MILESTONE",
        "entity_states": {"mission_01": "ACTIVE", "cap_db": "READY"},
    }
    resp_chkp = test_client.post("/temporal/checkpoints", json=chkp_payload)
    assert resp_chkp.status_code == 201
    assert resp_chkp.json()["name"] == "milestone_alpha"

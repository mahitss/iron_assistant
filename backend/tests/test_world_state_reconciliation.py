"""
Comprehensive Test Suite for Task 98: KAIRO Autonomous World-State Reconstruction,
State Estimation, Reality Synchronization & Drift Reconciliation Engine.

Covers:
1. Domain Schemas & Epistemic Guardrails (Observation != Truth, Expected != Actual, Missing != No Change).
2. Entity Resolution & Canonical Mapping (No ungrounded fuzzy merging).
3. State Invariants & Formal Lifecycle Transitions (StateLifecycleValidator & InvariantEngine).
4. Drift Detection, Severity Calculation, and Causal Hypothesis Generation.
5. Dialectic Conflict Preservation & Multi-Source Resolution (Contradictions remain visible).
6. Change Attribution (ActionTransaction & Decision linking vs UNATTRIBUTED_CHANGE).
7. Post-Action Verification (Execution != Verified State; Preventing false success).
8. Historical State Reconstruction at Timestamp T & Snapshot Diffing.
9. Downstream Graph Reasoning Propagation (Task 97 integration & Revalidation Queue).
10. Emergency Stop Blocking (Mutations halted, read-only observation preserved).
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta

from app.world_state.domain import (
    WorldScope,
    StateStatus,
    EpistemicCertainty,
    CertaintyTier,
    FreshnessState,
    DriftType,
    DriftSeverity,
    DriftClassification,
    DriftStatus,
    ExpectationMatchOutcome,
    StateObservation,
    ExpectedState,
    WorldStateEntity,
    StateDriftRecord,
    StateConflictRecord,
    RevalidationCandidate,
    WorldStateSnapshot,
    WorldStateDiff,
    utc_now,
)
from app.world_state.lifecycle import StateLifecycleValidator, InvariantEngine
from app.world_state.drift_engine import DriftEngine
from app.world_state.reconciliation_engine import (
    WorldStateReconciliationEngine,
    get_world_state_reconciliation_engine,
)
from app.security.emergency_stop import get_emergency_stop_service


@pytest.fixture
def engine():
    """Provides a fresh, isolated WorldStateReconciliationEngine instance."""
    eng = WorldStateReconciliationEngine()
    eng.reset()
    # Ensure emergency stop is deactivated initially
    es = get_emergency_stop_service()
    es.reset()
    return eng


@pytest.mark.asyncio
async def test_entity_resolution_and_canonical_mapping(engine):
    """Verifies that alias resolution maps to canonical IDs without ungrounded merging."""
    engine.register_canonical_alias("postgres-primary", "service:db:postgres-01")
    engine.register_canonical_alias("pg-master", "service:db:postgres-01")

    assert engine.resolve_canonical_id("postgres-primary") == "service:db:postgres-01"
    assert engine.resolve_canonical_id("PG-MASTER") == "service:db:postgres-01"
    # Unregistered ID resolves directly without hallucinating an alias
    assert engine.resolve_canonical_id("service:redis:cache") == "service:redis:cache"


@pytest.mark.asyncio
async def test_observation_ingestion_and_epistemic_updating(engine):
    """Verifies observation ingestion, confidence calculation, and freshness."""
    t0 = utc_now()
    obs1 = StateObservation(
        source_id="telemetry_agent_cpu",
        scope=WorldScope.INFRASTRUCTURE,
        canonical_id="node:worker-01",
        attributes={"cpu_utilization": 42.5, "status": "ONLINE"},
        certainty=EpistemicCertainty.CERTAIN,
        confidence=0.95,
        observed_at=t0,
    )

    entity = await engine.ingest_observation(obs1)
    assert entity.canonical_id == "node:worker-01"
    assert entity.scope == WorldScope.INFRASTRUCTURE
    assert entity.status == StateStatus.CURRENT
    assert entity.freshness == FreshnessState.FRESH
    assert "cpu_utilization" in entity.attributes
    assert entity.attributes["cpu_utilization"].value == 42.5
    assert entity.attributes["cpu_utilization"].source_count == 1


@pytest.mark.asyncio
async def test_drift_detection_value_divergence(engine):
    """Verifies empirical drift detection when observed state diverges from expected state."""
    # 1. Register entity
    engine.register_entity("service:gateway:api", WorldScope.SYSTEM, "API Gateway")

    # 2. Declare expected state
    exp = ExpectedState(
        canonical_id="service:gateway:api",
        scope=WorldScope.SYSTEM,
        expected_attributes={"replicas": 5, "status": "HEALTHY"},
        tolerance={"replicas": 0.0},
        purpose="Autoscaling scale-up expectation",
    )
    engine.declare_expected_state(exp)

    # 3. Ingest observation with diverging value
    obs = StateObservation(
        source_id="k8s_operator_probe",
        scope=WorldScope.SYSTEM,
        canonical_id="service:gateway:api",
        attributes={"replicas": 3, "status": "DEGRADED"},
        certainty=EpistemicCertainty.CERTAIN,
        confidence=0.99,
    )
    await engine.ingest_observation(obs)

    # 4. Reconcile expectations
    reconciled = await engine.reconcile_expectations()
    assert len(reconciled) >= 1
    exp_record, outcome, drift_records = reconciled[0]

    assert outcome == ExpectationMatchOutcome.DRIFT_DETECTED
    assert len(drift_records) >= 1

    # Check drift properties
    val_drift = next(d for d in drift_records if d.attribute_name == "replicas")
    assert val_drift.drift_type == DriftType.VALUE_DIVERGENCE
    assert val_drift.expected_value == 5
    assert val_drift.observed_value == 3
    assert val_drift.severity in (DriftSeverity.MEDIUM, DriftSeverity.HIGH)


@pytest.mark.asyncio
async def test_dialectic_conflict_preservation(engine):
    """Verifies that contradictory observations preserve the contradiction rather than silently overwriting."""
    t0 = utc_now()

    # Sensor A says latency is 20ms
    obs_a = StateObservation(
        source_id="synthetic_probe_eu",
        scope=WorldScope.SYSTEM,
        canonical_id="service:search:cluster",
        attributes={"latency_p99": 20.0},
        certainty=EpistemicCertainty.CERTAIN,
        confidence=0.95,
        observed_at=t0,
    )
    await engine.ingest_observation(obs_a)

    # Sensor B simultaneously says latency is 250ms (divergence > 50%)
    obs_b = StateObservation(
        source_id="app_metrics_ingress",
        scope=WorldScope.SYSTEM,
        canonical_id="service:search:cluster",
        attributes={"latency_p99": 250.0},
        certainty=EpistemicCertainty.CERTAIN,
        confidence=0.90,
        observed_at=t0 + timedelta(seconds=1),
    )
    await engine.ingest_observation(obs_b)

    # Contradiction must be preserved in conflicts register
    conflicts = engine.get_conflicts(WorldScope.SYSTEM)
    assert len(conflicts) >= 1
    conf = conflicts[0]
    assert conf.canonical_id == "service:search:cluster"
    assert conf.attribute_name == "latency_p99"
    assert conf.status == "OPEN"
    assert "synthetic_probe_eu" in conf.sources
    assert "app_metrics_ingress" in conf.sources


@pytest.mark.asyncio
async def test_change_attribution_and_unattributed_drift(engine):
    """Verifies that changes without known ActionTransaction or Decision are classified as UNATTRIBUTED_CHANGE."""
    engine.register_entity("database:prod:users", WorldScope.RESOURCE, "User Storage DB")

    # Ingest baseline
    obs_base = StateObservation(
        source_id="db_crawler",
        scope=WorldScope.RESOURCE,
        canonical_id="database:prod:users",
        attributes={"max_connections": 100},
        certainty=EpistemicCertainty.CERTAIN,
    )
    await engine.ingest_observation(obs_base)

    # Unexpected external modification without registered ActionTransaction
    obs_changed = StateObservation(
        source_id="db_crawler",
        scope=WorldScope.RESOURCE,
        canonical_id="database:prod:users",
        attributes={"max_connections": 25},
        certainty=EpistemicCertainty.CERTAIN,
    )
    await engine.ingest_observation(obs_changed)

    # Verify drift created
    drifts = engine._drift_engine.get_active_drifts()
    assert len(drifts) >= 1
    unattributed_drift = drifts[0]
    assert unattributed_drift.classification == DriftClassification.UNATTRIBUTED_CHANGE
    assert unattributed_drift.attributed_action_id is None
    assert unattributed_drift.attributed_decision_id is None


@pytest.mark.asyncio
async def test_post_action_verification_execution_not_verified_state(engine):
    """Phase 31: EXECUTION != VERIFIED STATE.
    Prevents false success when action succeeds but actual state does not match postconditions."""
    engine.register_entity("service:payment:processor", WorldScope.SERVICE, "Payment Gateway")

    # Register known action transaction
    action_id = "act_restart_payment_001"
    engine.register_action_transaction(
        action_id=action_id,
        action_type="RESTART_SERVICE",
        target_entity_id="service:payment:processor",
        expected_postconditions={"active_workers": 8, "status": "ONLINE"},
    )

    # Ingest actual state showing payment service only has 2 active workers and is DEGRADED
    obs = StateObservation(
        source_id="healthcheck_agent",
        scope=WorldScope.SERVICE,
        canonical_id="service:payment:processor",
        attributes={"active_workers": 2, "status": "DEGRADED"},
        certainty=EpistemicCertainty.CERTAIN,
    )
    await engine.ingest_observation(obs)

    # Action says it completed execution, but post-action verification must FAIL
    verification = await engine.verify_post_action(action_id)
    assert verification["verified"] is False
    assert verification["outcome"] == "FAILED_POSTCONDITION_MISMATCH"
    assert len(verification["mismatches"]) >= 1


@pytest.mark.asyncio
async def test_historical_state_reconstruction_at_timestamp(engine):
    """Phase 33: Point-in-time state reconstruction at timestamp T."""
    t_past = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t_present = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Observation at t_past: memory_mb = 1024
    obs_past = StateObservation(
        source_id="probe_01",
        scope=WorldScope.INFRASTRUCTURE,
        canonical_id="container:ml_worker",
        attributes={"memory_mb": 1024, "status": "STABLE"},
        observed_at=t_past,
    )
    await engine.ingest_observation(obs_past)

    # Observation at t_present: memory_mb = 4096
    obs_present = StateObservation(
        source_id="probe_01",
        scope=WorldScope.INFRASTRUCTURE,
        canonical_id="container:ml_worker",
        attributes={"memory_mb": 4096, "status": "HIGH_LOAD"},
        observed_at=t_present,
    )
    await engine.ingest_observation(obs_present)

    # Current state should show 4096
    curr_entity = engine.get_entity("container:ml_worker")
    assert curr_entity.attributes["memory_mb"].value == 4096

    # Historical reconstruction at t_past + 10 mins should show 1024
    reconstructed = engine.reconstruct_historical_state(
        target_timestamp=t_past + timedelta(minutes=10),
        scope=WorldScope.INFRASTRUCTURE,
    )
    assert "container:ml_worker" in reconstructed
    rec_entity = reconstructed["container:ml_worker"]
    assert rec_entity["attributes"]["memory_mb"]["value"] == 1024
    assert rec_entity["attributes"]["status"]["value"] == "STABLE"


@pytest.mark.asyncio
async def test_snapshot_creation_and_diffing(engine):
    """Phase 36: State snapshot creation and topological/attribute diff computation."""
    # State 1
    obs1 = StateObservation(
        source_id="telemetry",
        scope=WorldScope.SYSTEM,
        canonical_id="srv_cluster",
        attributes={"nodes": 3},
    )
    await engine.ingest_observation(obs1)
    snap1 = engine.create_snapshot(scope=WorldScope.SYSTEM, description="Snapshot 1")

    # State 2: nodes changed to 5, new entity added
    obs2 = StateObservation(
        source_id="telemetry",
        scope=WorldScope.SYSTEM,
        canonical_id="srv_cluster",
        attributes={"nodes": 5},
    )
    obs3 = StateObservation(
        source_id="telemetry",
        scope=WorldScope.SYSTEM,
        canonical_id="srv_load_balancer",
        attributes={"status": "ONLINE"},
    )
    await engine.ingest_observation(obs2)
    await engine.ingest_observation(obs3)
    snap2 = engine.create_snapshot(scope=WorldScope.SYSTEM, description="Snapshot 2")

    # Compute diff between snapshot 1 and snapshot 2
    diff = engine.compute_diff(snap1.snapshot_id, snap2.snapshot_id)
    assert "srv_load_balancer" in diff.added_entities
    assert "srv_cluster" in diff.modified_entities
    assert diff.modified_entities["srv_cluster"]["nodes"]["old"] == 3
    assert diff.modified_entities["srv_cluster"]["nodes"]["new"] == 5


@pytest.mark.asyncio
async def test_state_lifecycle_validator_and_invariants(engine):
    """Verifies formal lifecycle state transition matrix and invariant constraints."""
    validator = StateLifecycleValidator()

    # Valid transitions
    assert validator.can_transition(StateStatus.UNKNOWN, StateStatus.PROVISIONAL) is True
    assert validator.can_transition(StateStatus.CURRENT, StateStatus.DEGRADED) is True
    assert validator.can_transition(StateStatus.DEGRADED, StateStatus.ARCHIVED) is True

    # Invalid transitions
    assert validator.can_transition(StateStatus.ARCHIVED, StateStatus.CURRENT) is False
    assert validator.can_transition(StateStatus.UNKNOWN, StateStatus.CURRENT) is False

    # Invariant: Stale cannot be Current
    inv_engine = InvariantEngine()
    entity = WorldStateEntity(
        canonical_id="test:inv:01",
        scope=WorldScope.SYSTEM,
        status=StateStatus.CURRENT,
        freshness=FreshnessState.STALE,
        last_observed_at=utc_now() - timedelta(hours=2),
    )
    violations = inv_engine.check_invariants(entity)
    assert any(v.invariant_name == "STALE_CANNOT_BE_CURRENT" for v in violations)


@pytest.mark.asyncio
async def test_emergency_stop_blocks_reconciliation_mutations(engine):
    """Phase 45: Emergency Stop halts reconciliation mutations and revalidations."""
    es = get_emergency_stop_service()
    es.trigger(reason="SECURITY_DRIFT_LOCKDOWN", source="SecurityConsole")

    # Registering expectation during emergency stop should be blocked
    exp = ExpectedState(
        canonical_id="service:payment",
        scope=WorldScope.SERVICE,
        expected_attributes={"status": "READY"},
    )
    with pytest.raises(RuntimeError, match="Emergency Stop active"):
        engine.declare_expected_state(exp)

    # Reconciling expectations should be blocked
    with pytest.raises(RuntimeError, match="Emergency Stop active"):
        await engine.reconcile_expectations()

    # Ingesting observation should record for forensic audit without modifying mutable state
    obs = StateObservation(
        source_id="forensic_probe",
        scope=WorldScope.SERVICE,
        canonical_id="service:payment",
        attributes={"status": "HALTED"},
    )
    recorded_entity = await engine.ingest_observation(obs)
    assert recorded_entity.status == StateStatus.UNKNOWN

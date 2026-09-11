"""Unit tests for Memory Capture Pipeline and Lifecycle State Machine (Task 68)."""

from datetime import UTC, datetime

import pytest

from app.memory_consolidation.capture import MemoryCapturePipeline
from app.memory_consolidation.lifecycle import (
    InvalidLifecycleTransitionError,
    MemoryLifecycleStateMachine,
)
from app.memory_consolidation.schemas import (
    CognitiveClassification,
    DurableMemory,
    MemoryCaptureRequest,
    MemoryLifecycleState,
    MemoryType,
    TrustLevel,
)


def test_memory_capture_basic_observation():
    """Verify capture of normal operational observation with clean metadata and provenance."""
    req = MemoryCaptureRequest(
        content="Service ingress latency averaged 42ms during morning peak.",
        cognitive_type=CognitiveClassification.OBSERVATION,
        memory_type=MemoryType.EPISODIC_MEMORY,
        source_type="telemetry_collector",
        source_id="telem_01",
        confidence=0.88,
        importance=0.6,
        tenant_id="tenant_cap_1",
    )
    memory, provenance, audits = MemoryCapturePipeline.process_capture(req)

    assert memory.memory_id.startswith("mem_")
    assert memory.cognitive_type == CognitiveClassification.OBSERVATION
    assert memory.memory_type == MemoryType.EPISODIC_MEMORY
    assert memory.status == MemoryLifecycleState.ACTIVE
    assert memory.trust_level in {TrustLevel.UNVERIFIED, TrustLevel.TRUSTED}
    assert provenance.source_id == "telem_01"
    assert provenance.is_independent_source is True
    assert len(audits) >= 1
    assert audits[0]["event_type"] == "MEMORY_CAPTURED"


def test_memory_capture_simulation_invariant():
    """INVARIANT: Simulation results cannot be captured as EPISODIC_MEMORY (Spec 2, 32)."""
    req = MemoryCaptureRequest(
        content="Simulated high-load failure: server cluster will collapse at 100k req/s.",
        cognitive_type=CognitiveClassification.SIMULATION,
        memory_type=MemoryType.EPISODIC_MEMORY,  # Illegal pairing
        source_type="counterfactual_simulator",
        confidence=0.75,
        tenant_id="tenant_sim",
    )
    memory, _, _ = MemoryCapturePipeline.process_capture(req)

    assert memory.cognitive_type == CognitiveClassification.SIMULATION
    # System must correct memory_type to prevent recording simulation as real episodic event
    assert memory.memory_type != MemoryType.EPISODIC_MEMORY
    assert memory.memory_type == MemoryType.WORKING_MEMORY


def test_memory_capture_prediction_invariant():
    """INVARIANT: Predictions cannot be captured as observed EPISODIC_MEMORY events."""
    req = MemoryCaptureRequest(
        content="Forecast: Storage volume /data will reach 90% capacity by next Tuesday.",
        cognitive_type=CognitiveClassification.PREDICTION,
        memory_type=MemoryType.EPISODIC_MEMORY,  # Illegal pairing
        source_type="predictive_engine",
        confidence=0.82,
        tenant_id="tenant_pred",
    )
    memory, _, _ = MemoryCapturePipeline.process_capture(req)

    assert memory.cognitive_type == CognitiveClassification.PREDICTION
    assert memory.memory_type != MemoryType.EPISODIC_MEMORY
    assert memory.memory_type == MemoryType.PROSPECTIVE_MEMORY


def test_lifecycle_allowed_transitions():
    """Verify deterministic state transitions across valid lifecycle paths."""
    now = datetime.now(UTC)
    mem = DurableMemory(
        content="Ephemeral debug observation",
        status=MemoryLifecycleState.CAPTURED,
        tenant_id="tenant_lc",
        observed_at=now,
    )

    # CAPTURED -> CLASSIFIED
    audit1 = MemoryLifecycleStateMachine.transition(mem, MemoryLifecycleState.CLASSIFIED, actor="classifier")
    assert mem.status == MemoryLifecycleState.CLASSIFIED.value
    assert audit1["new_state"] == MemoryLifecycleState.CLASSIFIED.value

    # CLASSIFIED -> VALIDATING
    MemoryLifecycleStateMachine.transition(mem, MemoryLifecycleState.VALIDATING, actor="verifier")
    assert mem.status == MemoryLifecycleState.VALIDATING.value

    # VALIDATING -> ACTIVE
    MemoryLifecycleStateMachine.transition(mem, MemoryLifecycleState.ACTIVE, actor="validator")
    assert mem.status == MemoryLifecycleState.ACTIVE.value

    # ACTIVE -> CONSOLIDATING
    MemoryLifecycleStateMachine.transition(mem, MemoryLifecycleState.CONSOLIDATING, actor="worker")
    assert mem.status == MemoryLifecycleState.CONSOLIDATING.value

    # CONSOLIDATING -> CONSOLIDATED
    MemoryLifecycleStateMachine.transition(mem, MemoryLifecycleState.CONSOLIDATED, actor="worker")
    assert mem.status == MemoryLifecycleState.CONSOLIDATED.value

    # CONSOLIDATED -> PROMOTED
    MemoryLifecycleStateMachine.transition(mem, MemoryLifecycleState.PROMOTED, actor="promoter")
    assert mem.status == MemoryLifecycleState.PROMOTED.value


def test_lifecycle_rejects_illegal_transition():
    """Verify state machine strictly rejects illegal transitions (e.g. DELETED -> ACTIVE)."""
    now = datetime.now(UTC)
    mem = DurableMemory(
        content="Compliance scrubbed record",
        status=MemoryLifecycleState.DELETED,
        tenant_id="tenant_lc_err",
        observed_at=now,
    )

    # Attempt illegal transition DELETED -> ACTIVE
    with pytest.raises(InvalidLifecycleTransitionError) as exc_info:
        MemoryLifecycleStateMachine.transition(mem, MemoryLifecycleState.ACTIVE, actor="adversary")

    assert "INVALID_LIFECYCLE_TRANSITION" in str(exc_info.value)
    assert mem.status == MemoryLifecycleState.DELETED


def test_lifecycle_terminal_deleted_state():
    """Verify terminal state DELETED cannot transition to any state."""
    assert MemoryLifecycleStateMachine.ALLOWED_TRANSITIONS[MemoryLifecycleState.DELETED] == set()

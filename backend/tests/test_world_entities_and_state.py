"""Tests for World Entity schemas, identity, structured states, and transition rules (Task 32, Spec 2-4, 25-27, 81-88)."""

from datetime import UTC, datetime
import pytest

from app.world.entities import (
    ConfidenceLevel,
    EntityType,
    ObservationType,
    WorldEntityCreateRequest,
    WorldEntitySchema,
    generate_entity_id,
)
from app.world.state import (
    DeviceState,
    EnvironmentType,
    RepositoryState,
    ServiceState,
    StateTransitionValidator,
    TaskOperationalState,
)


def test_entity_identity_generation():
    """Verify deterministic, collision-safe entity ID generation (Spec 4)."""
    id1 = generate_entity_id(EntityType.REPOSITORY, "user_1", "github", "12345")
    id2 = generate_entity_id(EntityType.REPOSITORY, "user_1", "github", "12345")
    id_diff_user = generate_entity_id(EntityType.REPOSITORY, "user_2", "github", "12345")

    assert id1 == id2
    assert id1.startswith("ent_repository_")
    assert id1 != id_diff_user


def test_entity_schema_validation():
    """Verify WorldEntitySchema accepts valid attributes and serializes properly (Spec 2)."""
    now = datetime.now(UTC)
    entity = WorldEntitySchema(
        id="ent_dev_1",
        type=EntityType.DEVICE,
        name="MacBook Pro",
        owner_id="user_1",
        project_id="proj_alpha",
        source="local_companion",
        source_id="mac_01",
        state=DeviceState.CONNECTED.value,
        state_version=1,
        observation_type=ObservationType.OBSERVED,
        confidence=ConfidenceLevel.HIGH,
        observed_at=now,
        metadata={"platform": "darwin"},
    )

    assert entity.id == "ent_dev_1"
    assert entity.type == EntityType.DEVICE
    assert entity.state == "CONNECTED"
    assert entity.metadata["platform"] == "darwin"
    assert entity.is_stale is False


def test_valid_device_state_transitions():
    """Verify legal device state transitions (Spec 82)."""
    assert StateTransitionValidator.can_transition_device(DeviceState.UNKNOWN, DeviceState.CONNECTED) is True
    assert StateTransitionValidator.can_transition_device(DeviceState.CONNECTED, DeviceState.DISCONNECTED) is True
    assert StateTransitionValidator.can_transition_device(DeviceState.DISCONNECTED, DeviceState.CONNECTED) is True
    assert StateTransitionValidator.can_transition_device(DeviceState.CONNECTED, DeviceState.REVOKED) is True


def test_revoked_device_cannot_reconnect_via_stale_event():
    """Security Invariant: A REVOKED device must NEVER transition to CONNECTED (Spec 82, 131)."""
    # Once revoked, device cannot be un-revoked by an incoming event
    assert StateTransitionValidator.can_transition_device(DeviceState.REVOKED, DeviceState.CONNECTED) is False
    assert StateTransitionValidator.can_transition_device(DeviceState.REVOKED, DeviceState.DISCONNECTED) is False
    assert StateTransitionValidator.can_transition_device(DeviceState.REVOKED, DeviceState.UNKNOWN) is False


def test_service_state_transitions():
    """Verify service health transitions (Spec 81)."""
    assert StateTransitionValidator.can_transition_service(ServiceState.UNKNOWN, ServiceState.HEALTHY) is True
    assert StateTransitionValidator.can_transition_service(ServiceState.HEALTHY, ServiceState.DEGRADED) is True
    assert StateTransitionValidator.can_transition_service(ServiceState.DEGRADED, ServiceState.UNHEALTHY) is True
    assert StateTransitionValidator.can_transition_service(ServiceState.UNHEALTHY, ServiceState.HEALTHY) is True


def test_state_version_monotonicity():
    """Verify state version regression is rejected (Spec 87)."""
    assert StateTransitionValidator.validate_state_version(current_version=2, new_version=3) is True
    assert StateTransitionValidator.validate_state_version(current_version=3, new_version=3) is True
    assert StateTransitionValidator.validate_state_version(current_version=4, new_version=2) is False

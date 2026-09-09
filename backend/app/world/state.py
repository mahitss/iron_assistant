"""Structured state models, versioning, and transition rules for Kairo World Model (Task 32, Spec 25-27, 81-88)."""

from enum import Enum
import logging
from typing import Dict, Set

logger = logging.getLogger("kairo.world.state")


class DeviceState(str, Enum):
    """Structured lifecycle state of a registered user device (Spec 82)."""

    UNKNOWN = "UNKNOWN"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    REVOKED = "REVOKED"


class RepositoryState(str, Enum):
    """Structured operational state of a project repository (Spec 83)."""

    UNKNOWN = "UNKNOWN"
    SYNCING = "SYNCING"
    SYNCED = "SYNCED"
    STALE = "STALE"
    ERROR = "ERROR"


class ServiceState(str, Enum):
    """Structured operational state of a system service or microservice (Spec 81)."""

    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class TaskOperationalState(str, Enum):
    """Structured operational status of an autonomous task (Spec 84)."""

    UNKNOWN = "UNKNOWN"
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    WAITING_USER = "WAITING_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowOperationalState(str, Enum):
    """Structured operational status of an automation workflow (Spec 85)."""

    UNKNOWN = "UNKNOWN"
    ACTIVE = "ACTIVE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class EnvironmentType(str, Enum):
    """Explicit deployment environment boundaries (Spec 14, 15)."""

    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class ProviderHealthState(str, Enum):
    """Operational status of an AI inference model or external provider (Spec 53)."""

    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


# --- Valid Transition Rules (Spec 81-82, 87) ---

VALID_DEVICE_TRANSITIONS: dict[DeviceState, set[DeviceState]] = {
    DeviceState.UNKNOWN: {DeviceState.CONNECTED, DeviceState.DISCONNECTED, DeviceState.REVOKED},
    DeviceState.CONNECTED: {DeviceState.DISCONNECTED, DeviceState.REVOKED},
    DeviceState.DISCONNECTED: {DeviceState.CONNECTED, DeviceState.REVOKED},
    DeviceState.REVOKED: set(),  # Terminal state: REVOKED devices cannot reconnect via stale events (Spec 82, 131)
}

VALID_SERVICE_TRANSITIONS: dict[ServiceState, set[ServiceState]] = {
    ServiceState.UNKNOWN: {ServiceState.HEALTHY, ServiceState.DEGRADED, ServiceState.UNHEALTHY},
    ServiceState.HEALTHY: {ServiceState.DEGRADED, ServiceState.UNHEALTHY, ServiceState.UNKNOWN},
    ServiceState.DEGRADED: {ServiceState.HEALTHY, ServiceState.UNHEALTHY, ServiceState.UNKNOWN},
    ServiceState.UNHEALTHY: {ServiceState.HEALTHY, ServiceState.DEGRADED, ServiceState.UNKNOWN},
}

VALID_REPO_TRANSITIONS: dict[RepositoryState, set[RepositoryState]] = {
    RepositoryState.UNKNOWN: {RepositoryState.SYNCING, RepositoryState.SYNCED, RepositoryState.ERROR},
    RepositoryState.SYNCING: {RepositoryState.SYNCED, RepositoryState.ERROR, RepositoryState.STALE},
    RepositoryState.SYNCED: {RepositoryState.SYNCING, RepositoryState.STALE, RepositoryState.ERROR},
    RepositoryState.STALE: {RepositoryState.SYNCING, RepositoryState.SYNCED, RepositoryState.ERROR},
    RepositoryState.ERROR: {RepositoryState.SYNCING, RepositoryState.SYNCED, RepositoryState.STALE},
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state transition is attempted (e.g., REVOKED -> CONNECTED)."""
    pass


class StateTransitionValidator:
    """Enforces strict, validated state transitions across all entity types."""

    @classmethod
    def can_transition_device(cls, current_state: str | DeviceState, new_state: str | DeviceState) -> bool:
        cur = DeviceState(current_state) if isinstance(current_state, str) else current_state
        target = DeviceState(new_state) if isinstance(new_state, str) else new_state

        if cur == target:
            return True

        # Special security rule: REVOKED devices can never be made CONNECTED by events (Spec 82, 131)
        if cur == DeviceState.REVOKED and target != DeviceState.REVOKED:
            return False

        allowed = VALID_DEVICE_TRANSITIONS.get(cur, set())
        return target in allowed

    @classmethod
    def can_transition_service(cls, current_state: str | ServiceState, new_state: str | ServiceState) -> bool:
        cur = ServiceState(current_state) if isinstance(current_state, str) else current_state
        target = ServiceState(new_state) if isinstance(new_state, str) else new_state
        if cur == target:
            return True
        allowed = VALID_SERVICE_TRANSITIONS.get(cur, set())
        return target in allowed

    @classmethod
    def can_transition_repository(cls, current_state: str | RepositoryState, new_state: str | RepositoryState) -> bool:
        cur = RepositoryState(current_state) if isinstance(current_state, str) else current_state
        target = RepositoryState(new_state) if isinstance(new_state, str) else new_state
        if cur == target:
            return True
        allowed = VALID_REPO_TRANSITIONS.get(cur, set())
        return target in allowed

    @classmethod
    def validate_state_version(cls, current_version: int | None, new_version: int | None) -> bool:
        """Reject updates with older version numbers (Spec 87, 88)."""
        if current_version is not None and new_version is not None:
            return new_version >= current_version
        return True

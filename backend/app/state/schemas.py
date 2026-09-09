"""Pydantic schemas and enums for Kairo Unified Data & State Fabric (Task 39)."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class StateClassification(str, Enum):
    """Classification of state records and objects (Spec 2)."""
    AUTHORITATIVE = "AUTHORITATIVE"
    DERIVED = "DERIVED"
    CACHE = "CACHE"
    EPHEMERAL = "EPHEMERAL"
    ARCHIVAL = "ARCHIVAL"


class StateDomain(str, Enum):
    """Subsystem domains with authoritative ownership boundaries (Spec 8)."""
    TASKS = "tasks"
    APPROVALS = "approvals"
    POLICIES = "policies"
    IDENTITY = "identity"
    DEVICES = "devices"
    PROJECTS = "projects"
    NOTIFICATIONS = "notifications"
    MEMORY = "memory"
    WORLD = "world"
    AUDIT = "audit"


class ReadConsistency(str, Enum):
    """Read consistency levels supported by the fabric (Spec 119-122)."""
    STRONG = "STRONG"
    READ_YOUR_WRITES = "READ_YOUR_WRITES"
    EVENTUAL = "EVENTUAL"


class ReconciliationMode(str, Enum):
    """Modes for state reconciliation runs (Spec 63)."""
    CHECK = "CHECK"
    REPORT = "REPORT"
    SAFE_REPAIR = "SAFE_REPAIR"
    FULL_REBUILD = "FULL_REBUILD"


class DriftSeverity(str, Enum):
    """Severity of state drift between desired and observed reality (Spec 127)."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OperationType(str, Enum):
    """Operations recorded in durable change streams (Spec 22)."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    TRANSITION = "TRANSITION"
    DELETE = "DELETE"
    RECONCILE = "RECONCILE"


class ObservationFreshness(str, Enum):
    """Freshness status of observed external reality (Spec 181-183)."""
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class StateRecord(BaseModel):
    """Authoritative or derived state record (Spec 10)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain: StateDomain
    resource_type: str
    resource_id: str
    version: int = Field(default=1, ge=1)
    classification: StateClassification = StateClassification.AUTHORITATIVE
    status: str = "ACTIVE"
    data: dict[str, Any] = Field(default_factory=dict)
    checksum: str
    owner_domain: StateDomain
    user_id: str | None = None
    project_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StateConflict(BaseModel):
    """Details of an optimistic concurrency conflict (Spec 14)."""
    resource: str
    expected_version: int
    actual_version: int
    operation: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: str | None = None


class StateDrift(BaseModel):
    """Drift between desired state and observed real-world state (Spec 127)."""
    resource: str
    desired: Any
    observed: Any
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    severity: DriftSeverity = DriftSeverity.MEDIUM
    classification: str = "TEMPORARY"  # EXPECTED, TEMPORARY, ERRONEOUS


class StateSnapshot(BaseModel):
    """Snapshot of derived projection for fast recovery (Spec 30)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    projection_identifier: str
    state_version: int
    schema_version: int = 1
    checksum: str
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChangelogEntry(BaseModel):
    """Durable record of state change with actor and correlation (Spec 22)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain: StateDomain
    resource_type: str
    resource_id: str
    version: int
    operation: OperationType
    actor: str
    service: str
    correlation_id: str | None = None
    changes: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReconciliationIssue(BaseModel):
    """An issue detected during state reconciliation (Spec 65)."""
    resource: str
    issue: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    severity: str = "MEDIUM"
    recommended_repair: str


class ReconciliationReport(BaseModel):
    """Complete summary of a reconciliation run (Spec 65)."""
    mode: ReconciliationMode
    issues: list[ReconciliationIssue] = Field(default_factory=list)
    repaired_count: int = 0
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

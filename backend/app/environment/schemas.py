"""Pydantic v2 schemas and enums for Kairo Environmental Intelligence & Digital Twin Engine (Task 54)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScopeType(str, Enum):
    DEVICE = "DEVICE"
    HOST = "HOST"
    APPLICATION = "APPLICATION"
    PROJECT = "PROJECT"
    ENVIRONMENT = "ENVIRONMENT"
    ORGANIZATION = "ORGANIZATION"
    CLOUD = "CLOUD"
    NETWORK = "NETWORK"
    SYSTEM = "SYSTEM"


class NodeType(str, Enum):
    DEVICE = "DEVICE"
    HOST = "HOST"
    VM = "VM"
    CONTAINER = "CONTAINER"
    CLUSTER = "CLUSTER"
    PROCESS = "PROCESS"
    APPLICATION = "APPLICATION"
    SERVICE = "SERVICE"
    DATABASE = "DATABASE"
    CACHE = "CACHE"
    QUEUE = "QUEUE"
    REPOSITORY = "REPOSITORY"
    API = "API"
    ENDPOINT = "ENDPOINT"
    NETWORK = "NETWORK"
    LOAD_BALANCER = "LOAD_BALANCER"
    STORAGE = "STORAGE"
    BUCKET = "BUCKET"
    ENVIRONMENT = "ENVIRONMENT"
    DEPLOYMENT = "DEPLOYMENT"
    SECRET_REFERENCE = "SECRET_REFERENCE"
    CONFIGURATION = "CONFIGURATION"
    RESOURCE = "RESOURCE"


class RelationshipType(str, Enum):
    RUNS_ON = "RUNS_ON"
    HOSTS = "HOSTS"
    DEPENDS_ON = "DEPENDS_ON"
    CONNECTS_TO = "CONNECTS_TO"
    CALLS = "CALLS"
    EXPOSES = "EXPOSES"
    DEPLOYS_TO = "DEPLOYS_TO"
    CONTAINS = "CONTAINS"
    BELONGS_TO = "BELONGS_TO"
    USES = "USES"
    READS_FROM = "READS_FROM"
    WRITES_TO = "WRITES_TO"
    PUBLISHES_TO = "PUBLISHES_TO"
    SUBSCRIBES_TO = "SUBSCRIBES_TO"
    REPLICATES_TO = "REPLICATES_TO"
    ROUTES_TO = "ROUTES_TO"
    PROTECTED_BY = "PROTECTED_BY"
    CONFIGURED_BY = "CONFIGURED_BY"
    MONITORED_BY = "MONITORED_BY"
    BUILT_FROM = "BUILT_FROM"
    DERIVED_FROM = "DERIVED_FROM"


class RelationshipConfidence(str, Enum):
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    EXPECTED = "EXPECTED"
    UNKNOWN = "UNKNOWN"


class DeviceType(str, Enum):
    DESKTOP = "DESKTOP"
    LAPTOP = "LAPTOP"
    PHONE = "PHONE"
    TABLET = "TABLET"
    SERVER = "SERVER"
    VM = "VM"
    CONTAINER_HOST = "CONTAINER_HOST"
    OTHER = "OTHER"


class DeviceStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class EnvironmentType(str, Enum):
    LOCAL = "LOCAL"
    DEVELOPMENT = "DEVELOPMENT"
    TEST = "TEST"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    SANDBOX = "SANDBOX"


class DependencyType(str, Enum):
    RUNTIME = "RUNTIME"
    BUILD = "BUILD"
    NETWORK = "NETWORK"
    DATA = "DATA"
    AUTH = "AUTH"
    CONFIGURATION = "CONFIGURATION"
    DEPLOYMENT = "DEPLOYMENT"


class DriftType(str, Enum):
    CONFIGURATION = "CONFIGURATION"
    VERSION = "VERSION"
    DEPLOYMENT = "DEPLOYMENT"
    TOPOLOGY = "TOPOLOGY"
    RESOURCE = "RESOURCE"
    SECURITY = "SECURITY"
    NETWORK = "NETWORK"
    HEALTH = "HEALTH"


class DriftSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DriftStatus(str, Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class ChangeType(str, Enum):
    CREATED = "CREATED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    RESTARTED = "RESTARTED"
    REDEPLOYED = "REDEPLOYED"
    SCALED = "SCALED"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"


class ChangeSignificance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"


class ImpactLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class FreshnessState(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


# Models
class HealthEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    metric_name: str
    observed_value: Any
    threshold: Any | None = None
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = Field(default_factory=dict)


class HealthRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: HealthStatus = HealthStatus.UNKNOWN
    evidence: list[HealthEvidence] = Field(default_factory=list)
    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str | None = None


class EnvironmentNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    node_id: str
    node_type: NodeType
    canonical_id: str
    display_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None
    status: str = "UNKNOWN"
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class EnvironmentEdge(BaseModel):
    model_config = ConfigDict(extra="ignore")

    edge_id: str
    source: str
    relationship: RelationshipType
    target: str
    confidence: RelationshipConfidence = RelationshipConfidence.OBSERVED
    provenance: dict[str, Any] = Field(default_factory=dict)
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None
    status: str = "ACTIVE"


class EnvironmentDrift(BaseModel):
    model_config = ConfigDict(extra="ignore")

    drift_id: str
    resource: str
    drift_type: DriftType
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: DriftSeverity = DriftSeverity.MEDIUM
    evidence: dict[str, Any] = Field(default_factory=dict)
    status: DriftStatus = DriftStatus.DETECTED


class EnvironmentChange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    change_id: str
    resource: str
    change_type: ChangeType
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    significance: ChangeSignificance = ChangeSignificance.LOW
    confidence: float = 1.0
    verification: dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    model_config = ConfigDict(extra="ignore")

    incident_id: str
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: DriftSeverity = DriftSeverity.MEDIUM
    symptoms: list[str] = Field(default_factory=list)
    affected_resources: list[str] = Field(default_factory=list)
    suspected_cause: str | None = None
    root_cause: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    status: IncidentStatus = IncidentStatus.DETECTED
    timeline: list[dict[str, Any]] = Field(default_factory=list)


class EnvironmentSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None
    version: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    health_summary: dict[str, Any] = Field(default_factory=dict)
    freshness: FreshnessState = FreshnessState.FRESH
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DigitalTwin(BaseModel):
    model_config = ConfigDict(extra="ignore")

    twin_id: str
    scope: ScopeType = ScopeType.SYSTEM
    scope_id: str | None = None
    version: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    nodes: dict[str, EnvironmentNode] = Field(default_factory=dict)
    edges: dict[str, EnvironmentEdge] = Field(default_factory=dict)
    health: dict[str, HealthRecord] = Field(default_factory=dict)
    changes: list[EnvironmentChange] = Field(default_factory=list)
    confidence: float = 1.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    freshness: FreshnessState = FreshnessState.FRESH


class RemediationPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_id: str
    target: str
    current_state: dict[str, Any] = Field(default_factory=dict)
    desired_state: dict[str, Any] = Field(default_factory=dict)
    risk: ImpactLevel = ImpactLevel.MEDIUM
    dependencies: list[str] = Field(default_factory=list)
    rollback_target: dict[str, Any] | None = None
    rollback_verified: bool = False
    verification_postconditions: list[str] = Field(default_factory=list)
    approved: bool = False
    status: str = "PROPOSED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WhatIfSimulationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    simulation_id: str
    target_node: str
    hypothetical_event: str
    affected_nodes: list[str] = Field(default_factory=list)
    blast_radius_score: float = 0.0
    potential_impact: ImpactLevel = ImpactLevel.MEDIUM
    uncertainties: list[str] = Field(default_factory=list)
    is_hypothetical: bool = True
    simulated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReconciliationConflict(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conflict_id: str
    resource: str
    source_a: str
    value_a: Any
    source_b: str
    value_b: Any
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolution_notes: str | None = None

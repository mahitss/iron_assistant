"""Pydantic v2 schemas and domain models for Kairo Resource & Capability Orchestration Engine (Task 59)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"
    DEPRECATED = "DEPRECATED"
    UNKNOWN = "UNKNOWN"


class ResourceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    ALLOCATED = "ALLOCATED"
    EXHAUSTED = "EXHAUSTED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    RESERVED = "RESERVED"


class ResourceType(str, Enum):
    COMPUTE = "COMPUTE"
    MEMORY = "MEMORY"
    STORAGE = "STORAGE"
    DATABASE = "DATABASE"
    CONTAINER = "CONTAINER"
    CLUSTER = "CLUSTER"
    NETWORK = "NETWORK"
    API = "API"
    BANDWIDTH = "BANDWIDTH"
    QUOTA = "QUOTA"
    BUDGET = "BUDGET"
    HUMAN_ATTENTION = "HUMAN_ATTENTION"
    AGENT_CAPACITY = "AGENT_CAPACITY"
    EXECUTION_SLOT = "EXECUTION_SLOT"
    TIME = "TIME"


class ProviderType(str, Enum):
    TOOL = "TOOL"
    AGENT = "AGENT"
    SERVICE = "SERVICE"
    HUMAN = "HUMAN"


class AssignmentStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    ASSIGNED = "ASSIGNED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REALLOCATING = "REALLOCATING"


class OrchestrationStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    VALIDATED = "VALIDATED"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    REBALANCING = "REBALANCING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    ON_TRACK = "ON_TRACK"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"


class ContentionStrategy(str, Enum):
    PRIORITIZE = "PRIORITIZE"
    SEQUENCE = "SEQUENCE"
    RESERVE = "RESERVE"
    SCALE = "SCALE"
    SUBSTITUTE = "SUBSTITUTE"
    DEFER = "DEFER"
    REPLAN = "REPLAN"


# Domain Contracts
class CapabilityDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    capability_id: str = Field(default_factory=lambda: f"cap_{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    version: str = "1.0.0"
    provider: str
    reliability: float = 1.0
    latency_ms: float = 50.0
    cost_estimate: float = 0.0
    risk_level: RiskSeverity = RiskSeverity.LOW
    supported_environments: list[str] = Field(default_factory=lambda: ["development", "staging", "production"])
    required_permissions: list[str] = Field(default_factory=list)
    required_resources: list[dict[str, Any]] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    verification_method: str = "ASSERTION"
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    provenance: dict[str, Any] = Field(default_factory=dict)


class ResourceDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resource_id: str = Field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")
    name: str
    resource_type: ResourceType = ResourceType.COMPUTE
    provider: str = "SYSTEM"
    total_capacity: float = 100.0
    available_capacity: float = 100.0
    allocated_capacity: float = 0.0
    reserved_capacity: float = 0.0
    unit: str = "units"
    environment: str = "development"
    health: HealthStatus = HealthStatus.HEALTHY
    cost_rate: float = 0.0
    constraints: dict[str, Any] = Field(default_factory=dict)
    ownership: str = "SYSTEM"
    status: ResourceStatus = ResourceStatus.AVAILABLE


class ResourceReservation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reservation_id: str = Field(default_factory=lambda: f"rsv_{uuid.uuid4().hex[:8]}")
    resource_id: str
    owner: str
    purpose: str
    scope: str = "GLOBAL"
    amount: float = 1.0
    is_active: bool = True
    authorization_signature: str | None = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=_now_utc)


class TaskCapabilityRequirement(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task_id: str
    title: str = ""
    required_capabilities: list[str] = Field(default_factory=list)
    required_resources: list[dict[str, Any]] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    environment: str = "development"
    verification_criteria: list[str] = Field(default_factory=list)
    is_irreversible: bool = False
    priority: int = 1


class MatchingScore(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider_name: str
    provider_type: ProviderType
    capability_id: str
    overall_score: float = 0.0
    capability_match_score: float = 1.0
    environment_compatibility: bool = True
    reliability_score: float = 1.0
    cost_score: float = 1.0
    latency_score: float = 1.0
    risk_score: float = 1.0
    is_authorized: bool = True
    missing_permissions: list[str] = Field(default_factory=list)
    rationale: str = ""


class ProviderAssignment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assignment_id: str = Field(default_factory=lambda: f"asgn_{uuid.uuid4().hex[:8]}")
    task_id: str
    provider_name: str
    provider_type: ProviderType = ProviderType.TOOL
    capability_id: str
    allocated_resources: list[dict[str, Any]] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    status: AssignmentStatus = AssignmentStatus.ASSIGNED
    rationale: str = ""
    confidence: float = 1.0
    fallback_provider: str | None = None
    verification_criteria: list[str] = Field(default_factory=list)


class ExecutionTopology(BaseModel):
    model_config = ConfigDict(extra="ignore")

    topology_id: str = Field(default_factory=lambda: f"topo_{uuid.uuid4().hex[:8]}")
    execution_waves: list[dict[str, Any]] = Field(default_factory=list)
    synchronization_barriers: list[dict[str, Any]] = Field(default_factory=list)
    handoff_points: list[dict[str, Any]] = Field(default_factory=list)
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class OrchestrationPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    orchestration_id: str = Field(default_factory=lambda: f"orch_{uuid.uuid4().hex[:10]}")
    strategic_plan_id: str | None = None
    name: str
    task_graph: dict[str, Any] = Field(default_factory=dict)
    capability_requirements: list[TaskCapabilityRequirement] = Field(default_factory=list)
    assignments: list[ProviderAssignment] = Field(default_factory=list)
    resource_allocations: list[dict[str, Any]] = Field(default_factory=list)
    reservations: list[ResourceReservation] = Field(default_factory=list)
    execution_waves: list[dict[str, Any]] = Field(default_factory=list)
    fallback_paths: dict[str, str] = Field(default_factory=dict)
    synchronization_points: list[str] = Field(default_factory=list)
    verification_points: list[str] = Field(default_factory=list)
    risk: RiskSeverity = RiskSeverity.LOW
    approvals: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    status: OrchestrationStatus = OrchestrationStatus.DRAFT
    health: HealthStatus = HealthStatus.ON_TRACK
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class OrchestrationRevision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    revision_id: str = Field(default_factory=lambda: f"orev_{uuid.uuid4().hex[:8]}")
    parent_orchestration_id: str
    revision_number: int = 1
    reason: str
    actor: str
    diff_summary: dict[str, Any] = Field(default_factory=dict)
    snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now_utc)


class OrchestrationOutcome(BaseModel):
    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=lambda: f"oout_{uuid.uuid4().hex[:8]}")
    orchestration_id: str
    success: bool = True
    actual_duration: float = 0.0
    actual_cost: float = 0.0
    variance_summary: dict[str, Any] = Field(default_factory=dict)
    lessons_learned: list[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=_now_utc)

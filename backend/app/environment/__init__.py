"""Kairo Environmental Intelligence & Digital Twin Subsystem (Task 54)."""

from app.environment.apis import APIModelManager
from app.environment.applications import ApplicationModelManager
from app.environment.authorization import EnvironmentAuthorizationEngine
from app.environment.auto_healing import AutoHealingGovernor
from app.environment.capacity import CapacityManager
from app.environment.changes import ChangeDetector
from app.environment.cloud import CloudModelManager
from app.environment.clusters import ClusterModelManager
from app.environment.confidence import (
    compute_confidence_score,
    is_source_authoritative,
    map_relationship_confidence,
)
from app.environment.configurations import ConfigurationManager
from app.environment.containers import ContainerModelManager
from app.environment.databases import DatabaseModelManager
from app.environment.dependencies import DependencyManager
from app.environment.deployments import DeploymentModelManager
from app.environment.devices import DeviceModelManager
from app.environment.digital_twin import DigitalTwinEngine
from app.environment.discovery import DiscoveryEngine
from app.environment.drift import DriftDetector
from app.environment.edges import create_environment_edge, generate_edge_id
from app.environment.endpoints import EndpointModelManager
from app.environment.environments import EnvironmentManager
from app.environment.evaluation import EnvironmentEvaluationEngine
from app.environment.events import EnvironmentEventManager
from app.environment.health import HealthManager
from app.environment.incidents import IncidentManager
from app.environment.inventory import InventoryIndex
from app.environment.machines import MachineModelManager
from app.environment.networks import NetworkModelManager
from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.operating_systems import OperatingSystemModelManager
from app.environment.privacy import PrivacyGuard
from app.environment.processes import ProcessModelManager
from app.environment.provenance import build_provenance, generate_observation_id
from app.environment.queues import QueueModelManager
from app.environment.reconciliation import ReconciliationEngine
from app.environment.remediation import RemediationManager
from app.environment.repositories import RepositoryModelManager
from app.environment.resources import ResourceManager
from app.environment.retrieval import ContextRetrievalManager
from app.environment.safety import (
    EnvironmentSafetyError,
    EnvironmentSafetyGuard,
    FalseTopologyError,
    FutureLeakageError,
    ProductionSafetyViolationError,
    RemediationLoopError,
    SecretStorageViolationError,
    UnauthorizedDiscoveryError,
    UnverifiedRollbackError,
)
from app.environment.schemas import (
    ChangeSignificance,
    ChangeType,
    DependencyType,
    DeviceStatus,
    DeviceType,
    DigitalTwin,
    DriftSeverity,
    DriftStatus,
    DriftType,
    EnvironmentChange,
    EnvironmentDrift,
    EnvironmentEdge,
    EnvironmentNode,
    EnvironmentSnapshot,
    EnvironmentType,
    FreshnessState,
    HealthEvidence,
    HealthRecord,
    HealthStatus,
    ImpactLevel,
    Incident,
    IncidentStatus,
    NodeType,
    ReconciliationConflict,
    RelationshipConfidence,
    RelationshipType,
    RemediationPlan,
    ScopeType,
    WhatIfSimulationResult,
)
from app.environment.service import EnvironmentService, environment_service
from app.environment.services import ServiceModelManager
from app.environment.snapshots import SnapshotManager
from app.environment.storage import StorageModelManager
from app.environment.temporal import (
    assert_no_future_leakage,
    calculate_freshness,
    parse_utc,
    utc_now,
    validate_as_of,
)
from app.environment.topology import TopologyGraph
from app.environment.what_if import WhatIfSimulator

__all__ = [
    "ScopeType",
    "NodeType",
    "RelationshipType",
    "RelationshipConfidence",
    "DeviceType",
    "DeviceStatus",
    "HealthStatus",
    "EnvironmentType",
    "DependencyType",
    "DriftType",
    "DriftSeverity",
    "DriftStatus",
    "ChangeType",
    "ChangeSignificance",
    "IncidentStatus",
    "ImpactLevel",
    "FreshnessState",
    "HealthEvidence",
    "HealthRecord",
    "EnvironmentNode",
    "EnvironmentEdge",
    "EnvironmentDrift",
    "EnvironmentChange",
    "Incident",
    "EnvironmentSnapshot",
    "DigitalTwin",
    "RemediationPlan",
    "WhatIfSimulationResult",
    "ReconciliationConflict",
    "DigitalTwinEngine",
    "TopologyGraph",
    "create_environment_node",
    "generate_canonical_id",
    "create_environment_edge",
    "generate_edge_id",
    "DeviceModelManager",
    "MachineModelManager",
    "OperatingSystemModelManager",
    "ProcessModelManager",
    "ApplicationModelManager",
    "ServiceModelManager",
    "DatabaseModelManager",
    "RepositoryModelManager",
    "EnvironmentManager",
    "ContainerModelManager",
    "ClusterModelManager",
    "CloudModelManager",
    "NetworkModelManager",
    "EndpointModelManager",
    "APIModelManager",
    "StorageModelManager",
    "QueueModelManager",
    "DeploymentModelManager",
    "DependencyManager",
    "ConfigurationManager",
    "ResourceManager",
    "CapacityManager",
    "HealthManager",
    "EnvironmentEventManager",
    "ChangeDetector",
    "DriftDetector",
    "ReconciliationEngine",
    "SnapshotManager",
    "DiscoveryEngine",
    "InventoryIndex",
    "IncidentManager",
    "WhatIfSimulator",
    "RemediationManager",
    "AutoHealingGovernor",
    "ContextRetrievalManager",
    "PrivacyGuard",
    "EnvironmentAuthorizationEngine",
    "EnvironmentEvaluationEngine",
    "EnvironmentService",
    "environment_service",
    "EnvironmentSafetyError",
    "SecretStorageViolationError",
    "FalseTopologyError",
    "ProductionSafetyViolationError",
    "UnauthorizedDiscoveryError",
    "UnverifiedRollbackError",
    "RemediationLoopError",
    "FutureLeakageError",
    "EnvironmentSafetyGuard",
    "utc_now",
    "parse_utc",
    "calculate_freshness",
    "validate_as_of",
    "assert_no_future_leakage",
    "generate_observation_id",
    "build_provenance",
    "compute_confidence_score",
    "is_source_authoritative",
    "map_relationship_confidence",
]

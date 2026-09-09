"""Kairo Perception, Environmental Awareness, Multi-Source Observation, and Situational Awareness Engine (Task 46)."""

from app.perception.adapters import (
    AgentAdapter,
    AutomationAdapter,
    BaseSourceAdapter,
    BrowserAdapter,
    CalendarAdapter,
    DeploymentAdapter,
    DeviceAdapter,
    FileSystemAdapter,
    GitAdapter,
    GitHubAdapter,
    NotificationAdapter,
    ServiceHealthAdapter,
    TaskEngineAdapter,
    VisionAdapter,
    VoiceAdapter,
)
from app.perception.changes import (
    ChangeDetector,
    ChangeEvent,
    ChangeType,
)
from app.perception.context import (
    PerceptionContext,
    RelevanceEngine,
)
from app.perception.correlator import (
    CorrelationEdge,
    CorrelationRelation,
    EventCorrelator,
)
from app.perception.deduplication import EventDeduplicator
from app.perception.environment import (
    EnvironmentBoundaryGuard,
    EnvironmentIsolationError,
    EnvironmentType,
)
from app.perception.events import (
    EventAuthenticityError,
    EventType,
    InvalidEventError,
    PayloadSizeExceededError,
    PerceptionEvent,
)
from app.perception.freshness import FreshnessTracker
from app.perception.health import PerceptionHealthMetrics
from app.perception.normalizer import EventNormalizer
from app.perception.observations import Observation
from app.perception.ordering import EventOrderManager
from app.perception.privacy import (
    CrossTenantPerceptionError,
    PerceptionPrivacyGuard,
    PrivacyViolationError,
)
from app.perception.provenance import (
    ProvenanceRecord,
    ProvenanceTracker,
)
from app.perception.reconciliation import (
    EntityResolver,
    ReconciliationError,
    StateConflict,
    StateReconciler,
)
from app.perception.redaction import SecretRedactor
from app.perception.router import router
from app.perception.sensors import (
    BrowserSensor,
    DeviceSensor,
    FileSystemSensor,
    GitSensor,
    PresenceSensor,
    ServiceSensor,
)
from app.perception.service import PerceptionService
from app.perception.significance import (
    ChangeSignificance,
    SignificanceClassifier,
)
from app.perception.situation import (
    Anomaly,
    Situation,
    SituationalAwarenessManager,
)
from app.perception.snapshots import (
    EnvironmentSnapshot,
    SnapshotManager,
)
from app.perception.sources import (
    PerceptionSource,
    PerceptionSourceScope,
    PrivacyLevel,
    SourceRegistry,
    SourceStatus,
    SourceType,
    SourceUnauthorizedError,
)

__all__ = [
    "PerceptionService",
    "PerceptionSource",
    "SourceType",
    "SourceStatus",
    "PrivacyLevel",
    "PerceptionSourceScope",
    "SourceRegistry",
    "SourceUnauthorizedError",
    "PerceptionEvent",
    "EventType",
    "InvalidEventError",
    "EventAuthenticityError",
    "PayloadSizeExceededError",
    "Observation",
    "BaseSourceAdapter",
    "DeviceAdapter",
    "BrowserAdapter",
    "FileSystemAdapter",
    "GitAdapter",
    "GitHubAdapter",
    "DeploymentAdapter",
    "ServiceHealthAdapter",
    "NotificationAdapter",
    "VoiceAdapter",
    "VisionAdapter",
    "TaskEngineAdapter",
    "AgentAdapter",
    "AutomationAdapter",
    "CalendarAdapter",
    "EventNormalizer",
    "EventDeduplicator",
    "EventOrderManager",
    "FreshnessTracker",
    "EventCorrelator",
    "CorrelationEdge",
    "CorrelationRelation",
    "ProvenanceTracker",
    "ProvenanceRecord",
    "ChangeEvent",
    "ChangeType",
    "ChangeSignificance",
    "ChangeDetector",
    "SignificanceClassifier",
    "EnvironmentType",
    "EnvironmentIsolationError",
    "EnvironmentBoundaryGuard",
    "EnvironmentSnapshot",
    "SnapshotManager",
    "StateReconciler",
    "StateConflict",
    "EntityResolver",
    "ReconciliationError",
    "SecretRedactor",
    "PerceptionPrivacyGuard",
    "PrivacyViolationError",
    "CrossTenantPerceptionError",
    "PerceptionContext",
    "RelevanceEngine",
    "Anomaly",
    "Situation",
    "SituationalAwarenessManager",
    "DeviceSensor",
    "BrowserSensor",
    "FileSystemSensor",
    "GitSensor",
    "ServiceSensor",
    "PresenceSensor",
    "PerceptionHealthMetrics",
    "router",
]

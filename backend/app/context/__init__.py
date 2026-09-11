"""Kairo Personal Context Engine module."""

from app.context.project import ProjectService
from app.context.ranking import ContextRanker
from app.context.resolver import ContextResolver
from app.context.safety import ContextSafetyGuard
from app.context.schemas import (
    ContextItem,
    ContextPacket,
    ContextSettings,
    ContextSettingsUpdate,
    ContextType,
    MemoryScope,
    MemorySource,
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)
from app.context.service import ContextEngine
from app.context.session import SessionContextManager
from app.context.universal_schemas import (
    AdaptivePreference,
    AdaptivePreferenceCreate,
    AdaptivePreferenceUpdate,
    ContextConflictItem,
    ContextHierarchyLevel,
    ContextPackage,
    ContextPriorityTier,
    ContextQualityScore,
    ContextRequest,
    ContextSnapshot,
    MissingContextItem,
    PreferenceCategory,
    PreferenceConfidence,
    PreferenceSource,
    UniversalContextItem,
    UniversalContextType,
)
from app.context.universal_service import (
    UniversalContextService,
    get_universal_context_service,
)

__all__ = [
    "ContextEngine",
    "ContextResolver",
    "ContextRanker",
    "ContextSafetyGuard",
    "SessionContextManager",
    "ProjectService",
    "ContextType",
    "ContextItem",
    "ContextPacket",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectStatus",
    "ContextSettings",
    "ContextSettingsUpdate",
    "MemoryScope",
    "MemorySource",
    "UniversalContextType",
    "ContextPriorityTier",
    "ContextHierarchyLevel",
    "PreferenceCategory",
    "PreferenceSource",
    "PreferenceConfidence",
    "ContextQualityScore",
    "MissingContextItem",
    "ContextConflictItem",
    "UniversalContextItem",
    "ContextRequest",
    "ContextPackage",
    "AdaptivePreference",
    "AdaptivePreferenceCreate",
    "AdaptivePreferenceUpdate",
    "ContextSnapshot",
    "UniversalContextService",
    "get_universal_context_service",
]

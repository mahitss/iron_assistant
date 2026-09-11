"""Kairo Autonomous Knowledge & Memory Consolidation Engine (Task 68).

Foundational autonomous memory lifecycle and knowledge consolidation layer.
"""

from app.memory_consolidation.models import (
    DurableMemoryModel,
    MemoryAuditLogModel,
    MemoryConflictModel,
    MemoryConsolidationModel,
    MemoryProvenanceModel,
)
from app.memory_consolidation.router import router as memory_consolidation_router
from app.memory_consolidation.schemas import (
    AbstractionLevel,
    CognitiveClassification,
    ConsolidationCandidate,
    ContextAssemblyRequest,
    ContextAssemblyResult,
    ContradictionReport,
    ContradictionStatus,
    DurableMemory,
    FreshnessState,
    MemoryAuditEventType,
    MemoryCaptureRequest,
    MemoryHealthMetrics,
    MemoryLifecycleState,
    MemoryProvenance,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryType,
    TrustLevel,
)
from app.memory_consolidation.service import (
    MemoryConsolidationService,
    memory_consolidation_service,
)

__all__ = [
    "AbstractionLevel",
    "CognitiveClassification",
    "ConsolidationCandidate",
    "ContextAssemblyRequest",
    "ContextAssemblyResult",
    "ContradictionReport",
    "ContradictionStatus",
    "DurableMemory",
    "DurableMemoryModel",
    "FreshnessState",
    "MemoryAuditEventType",
    "MemoryAuditLogModel",
    "MemoryCaptureRequest",
    "MemoryConflictModel",
    "MemoryConsolidationModel",
    "MemoryConsolidationService",
    "MemoryHealthMetrics",
    "MemoryLifecycleState",
    "MemoryProvenance",
    "MemoryProvenanceModel",
    "MemorySearchRequest",
    "MemorySearchResult",
    "MemoryType",
    "TrustLevel",
    "memory_consolidation_router",
    "memory_consolidation_service",
]

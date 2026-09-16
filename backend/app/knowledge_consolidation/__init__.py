"""KAIRO Autonomous Knowledge Consolidation, Memory Reconstruction, Conflict Resolution & Context Evolution Engine (Task 92).

Foundational autonomous memory evolution and time-aware knowledge layer.
"""

from app.knowledge_consolidation.models import (
    CertaintyState,
    ConflictResolutionRequest,
    ConflictType,
    EvidenceRelationType,
    HypothesisModel,
    HypothesisStatus,
    MemoryConflict,
    MemoryEntity,
    MemoryEvidence,
    MemoryIngestionRequest,
    MemoryProvenance,
    MemoryReconstructionRequest,
    MemoryReconstructionResult,
    MemoryStatus,
    MemoryType,
    ProceduralMemory,
    ProvenanceSourceType,
    RetentionAction,
    RetentionDecision,
    SensitivityClassification,
    TimelineEvent,
    VolatilityClass,
)
from app.knowledge_consolidation.router import router as knowledge_consolidation_router
from app.knowledge_consolidation.service import (
    KnowledgeConsolidationService,
    get_knowledge_consolidation_service,
    knowledge_consolidation_service,
)

__all__ = [
    "CertaintyState",
    "ConflictResolutionRequest",
    "ConflictType",
    "EvidenceRelationType",
    "HypothesisModel",
    "HypothesisStatus",
    "KnowledgeConsolidationService",
    "MemoryConflict",
    "MemoryEntity",
    "MemoryEvidence",
    "MemoryIngestionRequest",
    "MemoryProvenance",
    "MemoryReconstructionRequest",
    "MemoryReconstructionResult",
    "MemoryStatus",
    "MemoryType",
    "ProceduralMemory",
    "ProvenanceSourceType",
    "RetentionAction",
    "RetentionDecision",
    "SensitivityClassification",
    "TimelineEvent",
    "VolatilityClass",
    "get_knowledge_consolidation_service",
    "knowledge_consolidation_router",
    "knowledge_consolidation_service",
]

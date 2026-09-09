"""Kairo Personal Knowledge Graph & Relationship Memory Engine (Task 50)."""

from app.knowledge_graph.assertions import (
    AssertionManager,
    InferenceFactViolationError,
)
from app.knowledge_graph.confidence import ConfidenceCalculator
from app.knowledge_graph.contradictions import ContradictionDetector
from app.knowledge_graph.decisions import (
    DecisionAgreementError,
    DecisionManager,
)
from app.knowledge_graph.edges import (
    EdgeIntegrityError,
    EdgeManager,
)
from app.knowledge_graph.entities import (
    EntityDefinition,
    EntityExtractor,
)
from app.knowledge_graph.evaluation import KnowledgeGraphEvaluator
from app.knowledge_graph.facts import FactValidator
from app.knowledge_graph.forgetting import ForgettingEngine
from app.knowledge_graph.graph import KnowledgeGraph
from app.knowledge_graph.nodes import (
    NodeManager,
    NodeValidationError,
)
from app.knowledge_graph.outcomes import OutcomeManager
from app.knowledge_graph.people import (
    PeopleManager,
    SensitiveProfilingError,
)
from app.knowledge_graph.preferences import PreferenceManager
from app.knowledge_graph.privacy import (
    GraphPrivacyManager,
    MemoryPrivacyViolationError,
    SecretInGraphDetectedError,
)
from app.knowledge_graph.projects import ProjectMemoryManager
from app.knowledge_graph.provenance import ProvenanceRecorder
from app.knowledge_graph.ranking import GraphRanker
from app.knowledge_graph.reconciliation import ContradictionReconciler
from app.knowledge_graph.redaction import GraphRedactor
from app.knowledge_graph.resolver import (
    EntityCollisionError,
    EntityResolver,
)
from app.knowledge_graph.retention import RetentionManager
from app.knowledge_graph.retrieval import GraphRetrievalEngine
from app.knowledge_graph.router import router as knowledge_graph_router
from app.knowledge_graph.safety import (
    GraphSafetyGuard,
    MemorySafetyViolationError,
)
from app.knowledge_graph.schemas import (
    AssertionSchema,
    AssertionStatus,
    ConfidenceTier,
    ContradictionSchema,
    DecisionSchema,
    DecisionStatus,
    EntitySummarySchema,
    GraphQueryResultSchema,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    MemoryType,
    NodeType,
    OutcomeSchema,
    PreferenceCategory,
    PreferenceMemorySchema,
    ProvenanceType,
    RelationshipType,
    ScopeType,
    SkillConfidence,
    TemporalState,
)
from app.knowledge_graph.service import KnowledgeGraphService
from app.knowledge_graph.summarization import GraphSummarizer
from app.knowledge_graph.tasks import TaskMemoryManager
from app.knowledge_graph.temporal import TemporalMemoryEngine
from app.knowledge_graph.versions import VersionManager

__all__ = [
    "KnowledgeGraphService",
    "knowledge_graph_router",
    "KnowledgeGraph",
    "NodeManager",
    "NodeValidationError",
    "EdgeManager",
    "EdgeIntegrityError",
    "EntityResolver",
    "EntityCollisionError",
    "EntityExtractor",
    "EntityDefinition",
    "AssertionManager",
    "InferenceFactViolationError",
    "FactValidator",
    "ProvenanceRecorder",
    "ConfidenceCalculator",
    "TemporalMemoryEngine",
    "VersionManager",
    "ContradictionDetector",
    "ContradictionReconciler",
    "DecisionManager",
    "DecisionAgreementError",
    "PreferenceManager",
    "ProjectMemoryManager",
    "PeopleManager",
    "SensitiveProfilingError",
    "TaskMemoryManager",
    "OutcomeManager",
    "GraphRetrievalEngine",
    "GraphRanker",
    "GraphSummarizer",
    "ForgettingEngine",
    "RetentionManager",
    "GraphPrivacyManager",
    "MemoryPrivacyViolationError",
    "SecretInGraphDetectedError",
    "GraphRedactor",
    "GraphSafetyGuard",
    "MemorySafetyViolationError",
    "KnowledgeGraphEvaluator",
    "NodeType",
    "RelationshipType",
    "AssertionStatus",
    "DecisionStatus",
    "MemoryType",
    "ProvenanceType",
    "ScopeType",
    "TemporalState",
    "ConfidenceTier",
    "PreferenceCategory",
    "SkillConfidence",
    "KnowledgeNodeSchema",
    "KnowledgeEdgeSchema",
    "AssertionSchema",
    "DecisionSchema",
    "PreferenceMemorySchema",
    "OutcomeSchema",
    "ContradictionSchema",
    "GraphQueryResultSchema",
    "EntitySummarySchema",
]

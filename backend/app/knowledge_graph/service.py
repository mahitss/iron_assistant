"""Master Knowledge Graph & Relationship Memory Service orchestrator (Task 50)."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional

from app.knowledge_graph.assertions import AssertionManager
from app.knowledge_graph.confidence import ConfidenceCalculator
from app.knowledge_graph.contradictions import ContradictionDetector
from app.knowledge_graph.decisions import DecisionManager
from app.knowledge_graph.edges import EdgeManager
from app.knowledge_graph.entities import EntityDefinition
from app.knowledge_graph.evaluation import KnowledgeGraphEvaluator
from app.knowledge_graph.facts import FactValidator
from app.knowledge_graph.forgetting import ForgettingEngine
from app.knowledge_graph.graph import KnowledgeGraph
from app.knowledge_graph.nodes import NodeManager
from app.knowledge_graph.outcomes import OutcomeManager
from app.knowledge_graph.people import PeopleManager
from app.knowledge_graph.preferences import PreferenceManager
from app.knowledge_graph.privacy import GraphPrivacyManager
from app.knowledge_graph.projects import ProjectMemoryManager
from app.knowledge_graph.provenance import ProvenanceRecorder
from app.knowledge_graph.ranking import GraphRanker
from app.knowledge_graph.reconciliation import ContradictionReconciler
from app.knowledge_graph.redaction import GraphRedactor
from app.knowledge_graph.resolver import EntityResolver
from app.knowledge_graph.retention import RetentionManager
from app.knowledge_graph.retrieval import GraphRetrievalEngine
from app.knowledge_graph.safety import GraphSafetyGuard
from app.knowledge_graph.schemas import (
    AssertionSchema,
    ContradictionSchema,
    DecisionSchema,
    GraphQueryResultSchema,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    NodeType,
    PreferenceCategory,
    PreferenceMemorySchema,
    RelationshipType,
    ScopeType,
)
from app.knowledge_graph.summarization import GraphSummarizer
from app.knowledge_graph.tasks import TaskMemoryManager
from app.knowledge_graph.temporal import TemporalMemoryEngine
from app.knowledge_graph.versions import VersionManager

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """Master orchestrator implementing:

    OBSERVATION -> EXTRACT -> VALIDATE -> ATTACH PROVENANCE -> SCOPE -> STORE ->
    RETRIEVE -> REASON -> VERIFY -> UPDATE
    """

    def __init__(self) -> None:
        self.nodes = NodeManager()
        self.edges = EdgeManager(self.nodes)
        self.graph = KnowledgeGraph(self.nodes, self.edges)
        self.resolver = EntityResolver(self.nodes)
        self.assertions = AssertionManager()
        self.facts = FactValidator()
        self.provenance = ProvenanceRecorder()
        self.confidence = ConfidenceCalculator()
        self.temporal = TemporalMemoryEngine(self.nodes, self.edges)
        self.versions = VersionManager()
        self.contradictions = ContradictionDetector()
        self.reconciler = ContradictionReconciler()
        self.decisions = DecisionManager()
        self.preferences = PreferenceManager()
        self.projects = ProjectMemoryManager()
        self.people = PeopleManager()
        self.tasks = TaskMemoryManager()
        self.outcomes = OutcomeManager()
        self.retrieval = GraphRetrievalEngine(self.graph)
        self.ranking = GraphRanker()
        self.summarizer = GraphSummarizer(self.graph)
        self.forgetting = ForgettingEngine(self.graph)
        self.retention = RetentionManager()
        self.privacy = GraphPrivacyManager()
        self.redactor = GraphRedactor()
        self.safety = GraphSafetyGuard()
        self.evaluator = KnowledgeGraphEvaluator()

    # =========================================================================
    # CORE ENTITY & EDGE OPERATIONS
    # =========================================================================

    def create_entity(
        self,
        canonical_name: str,
        node_type: NodeType = NodeType.KNOWLEDGE,
        aliases: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        scope: ScopeType = ScopeType.PRIVATE,
        confidence: float = 1.0,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
    ) -> KnowledgeNodeSchema:
        # Audit secret leaks in metadata
        text_repr = f"{canonical_name} {str(metadata or {})}"
        self.privacy.scan_for_secrets(text_repr)
        self.safety.audit_content_for_poisoning(text_repr)

        node = self.nodes.create_node(
            canonical_name=canonical_name,
            node_type=node_type,
            aliases=aliases,
            metadata=metadata,
            scope=scope,
            confidence=confidence,
            user_id=user_id,
            project_id=project_id,
        )
        self.evaluator.record_metric("nodes_created")
        return node

    def link_entities(
        self,
        source_node_id: str,
        relationship: RelationshipType,
        target_node_id: str,
        confidence: float = 1.0,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        scope: ScopeType = ScopeType.PRIVATE,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
    ) -> KnowledgeEdgeSchema:
        edge = self.edges.create_edge(
            source_node_id=source_node_id,
            relationship=relationship,
            target_node_id=target_node_id,
            confidence=confidence,
            valid_from=valid_from,
            valid_until=valid_until,
            scope=scope,
            user_id=user_id,
            project_id=project_id,
        )
        self.summarizer.invalidate_cache(source_node_id)
        self.summarizer.invalidate_cache(target_node_id)
        self.evaluator.record_metric("edges_created")
        return edge

    # =========================================================================
    # ASSERTIONS & CONTRADICTIONS
    # =========================================================================

    def record_assertion(
        self,
        subject: str,
        predicate: str,
        object_val: str,
        source: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        scope: ScopeType = ScopeType.PRIVATE,
        user_id: str = "default_user",
        is_inferred: bool = False,
    ) -> AssertionSchema:
        self.privacy.scan_for_secrets(f"{subject} {predicate} {object_val}")
        self.safety.audit_content_for_poisoning(f"{subject} {predicate} {object_val}")

        assertion = self.assertions.create_assertion(
            subject=subject,
            predicate=predicate,
            object_val=object_val,
            source=source,
            confidence=confidence,
            scope=scope,
            user_id=user_id,
            is_inferred=is_inferred,
        )

        # Check for contradictions
        existing = self.assertions.find_by_subject(subject, user_id=user_id)
        conflict = self.contradictions.check_conflict(assertion, existing)
        if conflict:
            self.evaluator.record_metric("contradictions_detected")

        self.evaluator.record_metric("assertions_recorded")
        return assertion

    # =========================================================================
    # DECISIONS & PREFERENCES
    # =========================================================================

    def record_decision(
        self,
        question: str,
        decision: str,
        alternatives: Optional[List[str]] = None,
        rationale_reference: Optional[str] = None,
        owner: str = "user",
        scope: ScopeType = ScopeType.PROJECT,
        confidence: float = 1.0,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        is_only_discussion: bool = False,
    ) -> DecisionSchema:
        return self.decisions.record_decision(
            question=question,
            decision=decision,
            alternatives=alternatives,
            rationale_reference=rationale_reference,
            owner=owner,
            scope=scope,
            confidence=confidence,
            user_id=user_id,
            project_id=project_id,
            is_only_discussion=is_only_discussion,
        )

    def set_preference(
        self,
        category: PreferenceCategory,
        value: Dict[str, Any],
        scope: ScopeType = ScopeType.PRIVATE,
        confidence: float = 1.0,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
    ) -> PreferenceMemorySchema:
        return self.preferences.set_preference(
            category=category,
            value=value,
            scope=scope,
            confidence=confidence,
            user_id=user_id,
            project_id=project_id,
        )

    def resolve_preference(
        self,
        category: PreferenceCategory,
        user_id: str,
        project_id: Optional[str] = None,
        current_instruction_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resolves active preference with current instruction override support (INVARIANT 71)."""
        return self.preferences.resolve_preference(
            category=category,
            user_id=user_id,
            project_id=project_id,
            current_instruction_override=current_instruction_override,
        )

    # =========================================================================
    # CONVENIENCE RETRIEVAL & DELEGATION
    # =========================================================================

    def traverse(
        self,
        start_node_id: str,
        max_depth: int = 2,
        max_nodes: int = 100,
        user_id: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> GraphQueryResultSchema:
        return self.graph.traverse(
            start_node_id=start_node_id,
            max_depth=max_depth,
            max_nodes=max_nodes,
            user_id=user_id,
            as_of=as_of,
        )

    def summarize(self, node_id: str, force_refresh: bool = False):
        return self.summarizer.summarize_entity(node_id, force_refresh=force_refresh)

    def forget_entity(self, node_id: str, user_id: str, reason: str = "user_request"):
        return self.forgetting.forget_entity(node_id, user_id=user_id, reason=reason)

    def get_entity(self, node_id: str):
        return self.nodes.get_node(node_id)

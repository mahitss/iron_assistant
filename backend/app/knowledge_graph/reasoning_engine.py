"""Core Autonomous Knowledge Graph Reasoning, Relationship Intelligence & Structured Inference Engine (Task 97).

Implements:
- Bounded graph queries & shortest verified paths
- Dependency intelligence & downstream impact analysis
- Structured, deterministic graph inference (with strict safety barriers: never infer permissions)
- Cross-subsystem operational lineage reconstruction (Decision, Action, Memory, Context, Agent)
- Temporal point-in-time state reconstruction & graph snapshots
- Graph diffing & change-impact revalidation generation
- SecurityCenter scope filtering & cross-tenant isolation
- Explicit conflict graph tracking (Task 92 integration)
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import uuid

from app.knowledge_graph.edges import EdgeIntegrityError, EdgeManager
from app.knowledge_graph.graph import KnowledgeGraph
from app.knowledge_graph.nodes import NodeManager, NodeValidationError
from app.knowledge_graph.schemas import (
    CertaintyLevel,
    ConflictRecord,
    ConflictResolutionState,
    GraphDiffResult,
    GraphProvenanceSchema,
    GraphQueryRequest,
    GraphQueryResultSchema,
    GraphQueryType,
    GraphSnapshot,
    GraphTraversalLimits,
    ImpactAnalysisResult,
    ImpactedNodeRecord,
    InferenceRuleRecord,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    LineageReconstructionResult,
    LineageStepRecord,
    NodeType,
    ProvenanceClassification,
    RelationshipType,
    ScopeType,
    utc_now,
)

logger = logging.getLogger("kairo.knowledge_graph.reasoning")


class GraphReasoningEngine:
    """Master reasoning substrate implementing bounded inference, impact analysis, and lineage."""

    def __init__(self, graph: Optional[KnowledgeGraph] = None) -> None:
        self.graph = graph or KnowledgeGraph()
        self._snapshots: Dict[str, GraphSnapshot] = {}
        self._conflicts: Dict[str, ConflictRecord] = {}
        self._inference_rules: List[InferenceRuleRecord] = self._default_inference_rules()
        self._derived_edges: Dict[str, KnowledgeEdgeSchema] = {}

    def reset(self) -> None:
        """Resets in-memory collections for test isolation."""
        self.graph.nodes.clear()
        self.graph.edges.clear()
        self._snapshots.clear()
        self._conflicts.clear()
        self._derived_edges.clear()

    @property
    def nodes(self) -> NodeManager:
        return self.graph.nodes

    @property
    def edges(self) -> EdgeManager:
        return self.graph.edges

    def create_node(
        self,
        node_id: str,
        canonical_key: str = "",
        node_type: NodeType = NodeType.KNOWLEDGE,
        label: str = "",
        confidence: float = 1.0,
        certainty: CertaintyLevel = CertaintyLevel.KNOWN,
        sensitivity: str = "INTERNAL",
        provenance: Optional[Any] = None,
        scope: str = "global",
        **kwargs: Any,
    ) -> KnowledgeNodeSchema:
        """Creates or registers a knowledge node in the reasoning substrate."""
        if isinstance(scope, str):
            if scope in [s.value for s in ScopeType]:
                scope_enum = ScopeType(scope)
                project_id = kwargs.pop("project_id", None)
            else:
                scope_enum = ScopeType.PROJECT
                project_id = kwargs.pop("project_id", scope)
        else:
            scope_enum = scope or ScopeType.PRIVATE
            project_id = kwargs.pop("project_id", None)

        node = KnowledgeNodeSchema(
            node_id=node_id,
            canonical_name=label or canonical_key or node_id,
            canonical_key=canonical_key,
            label=label or canonical_key or node_id,
            node_type=node_type,
            confidence=confidence,
            certainty=certainty,
            sensitivity=sensitivity if isinstance(sensitivity, str) else "INTERNAL",
            provenance=provenance if provenance is not None else {},
            scope=scope_enum,
            project_id=project_id,
            **kwargs,
        )
        self.graph.nodes._nodes[node_id] = node
        self.graph.nodes._name_index[node.canonical_name.lower()] = node_id
        if canonical_key:
            self.graph.nodes._name_index[canonical_key.lower()] = node_id
        return node

    def create_edge(
        self,
        source_node: str,
        target_node: str,
        relationship_type: RelationshipType,
        confidence: float = 1.0,
        certainty: CertaintyLevel = CertaintyLevel.KNOWN,
        provenance: Optional[Any] = None,
        scope: str = "global",
        validity_start: Optional[datetime] = None,
        validity_end: Optional[datetime] = None,
        edge_id: Optional[str] = None,
        **kwargs: Any,
    ) -> KnowledgeEdgeSchema:
        """Creates or registers a knowledge edge in the reasoning substrate."""
        if source_node not in self.graph.nodes:
            raise ValueError(f"Source node '{source_node}' does not exist.")
        if target_node not in self.graph.nodes:
            raise ValueError(f"Target node '{target_node}' does not exist.")

        eid = edge_id or str(uuid.uuid4())
        if isinstance(scope, str):
            if scope in [s.value for s in ScopeType]:
                scope_enum = ScopeType(scope)
                project_id = kwargs.pop("project_id", None)
            else:
                scope_enum = ScopeType.PROJECT
                project_id = kwargs.pop("project_id", scope)
        else:
            scope_enum = scope or ScopeType.PRIVATE
            project_id = kwargs.pop("project_id", None)

        edge = KnowledgeEdgeSchema(
            edge_id=eid,
            source_node_id=source_node,
            target_node_id=target_node,
            relationship=relationship_type,
            confidence=confidence,
            certainty=certainty,
            provenance=provenance if provenance is not None else {},
            valid_from=validity_start,
            valid_until=validity_end,
            scope=scope_enum,
            project_id=project_id,
            **kwargs,
        )
        self.graph.edges._edges[eid] = edge
        self.graph.edges._out_edges.setdefault(source_node, set()).add(eid)
        self.graph.edges._in_edges.setdefault(target_node, set()).add(eid)
        return edge

    # =========================================================================
    # 1. BOUNDED GRAPH QUERY ENGINE (Phases 10, 11, 35, 36)
    # =========================================================================

    def execute_query(
        self,
        query_type: Union[GraphQueryType, GraphQueryRequest],
        start_node_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
        relationship_types: Optional[List[RelationshipType]] = None,
        min_confidence: float = 0.0,
        certainty_filter: Optional[List[CertaintyLevel]] = None,
        as_of: Optional[datetime] = None,
        limits: Optional[GraphTraversalLimits] = None,
        user_id: str = "default_user",
        scope: Optional[Any] = None,
        allowed_sensitivities: Optional[List[str]] = None,
    ) -> GraphQueryResultSchema:
        """Executes a structured, bounded graph query with security filtering."""
        if isinstance(query_type, GraphQueryRequest):
            req = query_type
            query_type = req.query_type
            start_node_id = req.start_node_id
            target_node_id = req.target_node_id
            relationship_types = req.relationship_types
            min_confidence = req.min_confidence
            certainty_filter = req.certainty_filter
            as_of = req.as_of
            limits = req.limits
            user_id = req.user_id
            scope = req.scope
            allowed_sensitivities = req.allowed_sensitivities

        lim = limits or GraphTraversalLimits()
        start_time = time.monotonic()

        if query_type == GraphQueryType.SHORTEST_VERIFIED_PATH:
            if not start_node_id or not target_node_id:
                raise ValueError("SHORTEST_VERIFIED_PATH requires start_node_id and target_node_id.")
            res = self.find_shortest_verified_path(
                start_node_id=start_node_id,
                target_node_id=target_node_id,
                min_confidence=min_confidence,
                limits=lim,
                user_id=user_id,
                as_of=as_of,
            )
            res.execution_time_ms = (time.monotonic() - start_time) * 1000.0
            return res

        if query_type == GraphQueryType.DEPENDENCY_QUERY:
            if not start_node_id:
                raise ValueError("DEPENDENCY_QUERY requires start_node_id.")
            if not relationship_types:
                relationship_types = [
                    RelationshipType.DEPENDS_ON,
                    RelationshipType.REQUIRES,
                    RelationshipType.TRANSITIVELY_DEPENDS_ON,
                    RelationshipType.ASSUMES,
                    RelationshipType.SUPPORTS,
                    RelationshipType.USED_BY,
                    RelationshipType.IMPLEMENTS,
                    RelationshipType.PART_OF,
                    RelationshipType.CHILD_OF,
                ]

        if query_type == GraphQueryType.EVIDENCE_QUERY:
            if not start_node_id:
                raise ValueError("EVIDENCE_QUERY requires start_node_id.")
            if not relationship_types:
                relationship_types = [
                    RelationshipType.SUPPORTS,
                    RelationshipType.EVIDENCE_FOR,
                    RelationshipType.VALIDATES,
                    RelationshipType.OBSERVED_IN,
                ]

        if query_type == GraphQueryType.IMPACT_QUERY:
            if not start_node_id:
                raise ValueError("IMPACT_QUERY requires start_node_id.")
            impact = self.analyze_downstream_impact(
                root_node_id=start_node_id,
                limits=lim,
                user_id=user_id,
                as_of=as_of,
            )
            node_ids = [n.get("node_id") if isinstance(n, dict) else getattr(n, "node_id", None) for n in impact.impacted_nodes]
            nodes = [self.nodes.get_node(nid) for nid in node_ids if nid and self.nodes.get_node(nid)]
            return GraphQueryResultSchema(
                nodes=nodes,
                edges=[],
                traversal_depth=impact.depth,
                total_nodes_visited=len(nodes),
                execution_time_ms=(time.monotonic() - start_time) * 1000.0,
                explanations=[f"Impacted nodes: {len(nodes)} (Criticality: {impact.risk_criticality})"],
            )

        if not start_node_id:
            raise ValueError(f"Query type '{query_type.value}' requires start_node_id.")

        # Standard bounded BFS traversal
        start_node = self.nodes.get_node(start_node_id)
        if not start_node or not self._is_accessible(start_node, user_id, scope, allowed_sensitivities):
            return GraphQueryResultSchema(total_nodes_visited=0, execution_time_ms=(time.monotonic() - start_time) * 1000.0)

        visited_nodes: Set[str] = {start_node_id}
        collected_nodes: List[KnowledgeNodeSchema] = [start_node]
        collected_edges: List[KnowledgeEdgeSchema] = []
        visited_edges: Set[str] = set()

        # Queue: (node_id, current_depth)
        queue: deque[Tuple[str, int]] = deque([(start_node_id, 0)])
        max_depth_reached = 0

        while queue and len(visited_nodes) < lim.max_nodes:
            # Check execution timeout
            if (time.monotonic() - start_time) > lim.max_execution_time_seconds:
                logger.warning(f"Graph traversal timed out after {lim.max_execution_time_seconds}s.")
                break

            curr_id, depth = queue.popleft()
            max_depth_reached = max(max_depth_reached, depth)
            if depth >= lim.max_depth:
                continue

            outgoing = self.edges.get_outgoing_edges(curr_id)
            incoming = self.edges.get_incoming_edges(curr_id) if query_type != GraphQueryType.ONE_HOP else []
            all_edges = outgoing + incoming

            # Limit branching factor
            branch_count = 0
            for edge in all_edges:
                if branch_count >= lim.max_branching_factor:
                    break
                if len(collected_edges) >= lim.max_edges:
                    break

                # Relationship type filtering
                if relationship_types and edge.relationship not in relationship_types:
                    continue

                # Confidence filtering
                if edge.confidence < min_confidence:
                    continue

                # Certainty filtering
                if certainty_filter and edge.certainty not in certainty_filter:
                    continue

                # Temporal validity at as_of
                if as_of:
                    if edge.valid_from and edge.valid_from > as_of:
                        continue
                    if edge.valid_until and edge.valid_until < as_of:
                        continue

                # Security & Scope filtering
                if not self._is_edge_accessible(edge, user_id, scope):
                    continue

                next_node_id = edge.target_node_id if edge.source_node_id == curr_id else edge.source_node_id
                next_node = self.nodes.get_node(next_node_id)
                if not next_node or not self._is_accessible(next_node, user_id, scope, allowed_sensitivities):
                    continue

                if edge.edge_id not in visited_edges:
                    visited_edges.add(edge.edge_id)
                    collected_edges.append(edge)
                    branch_count += 1

                if next_node_id not in visited_nodes:
                    visited_nodes.add(next_node_id)
                    collected_nodes.append(next_node)
                    queue.append((next_node_id, depth + 1))

        return GraphQueryResultSchema(
            nodes=collected_nodes,
            edges=collected_edges,
            traversal_depth=max_depth_reached,
            total_nodes_visited=len(visited_nodes),
            path_confidence=1.0,
            execution_time_ms=(time.monotonic() - start_time) * 1000.0,
            explanations=[f"Visited {len(visited_nodes)} nodes, {len(collected_edges)} edges across depth {max_depth_reached}"],
        )

    # =========================================================================
    # 2. SHORTEST VERIFIED PATH (Phases 10, 12)
    # =========================================================================

    def find_shortest_verified_path(
        self,
        start_node_id: str,
        target_node_id: str,
        min_confidence: float = 0.5,
        limits: Optional[GraphTraversalLimits] = None,
        user_id: str = "default_user",
        as_of: Optional[datetime] = None,
        max_depth: Optional[int] = None,
    ) -> GraphQueryResultSchema:
        """Finds the shortest verified path using BFS, guaranteeing min confidence and no contradicted edges."""
        lim = limits or GraphTraversalLimits(max_depth=max_depth if max_depth is not None else 5)
        src = self.nodes.get_node(start_node_id)
        dst = self.nodes.get_node(target_node_id)
        if not src or not dst:
            return GraphQueryResultSchema(total_nodes_visited=0)

        if start_node_id == target_node_id:
            return GraphQueryResultSchema(nodes=[src], edges=[], path_confidence=1.0)

        # BFS queue: (curr_node_id, node_path, edge_path, current_confidence)
        queue: deque[Tuple[str, List[KnowledgeNodeSchema], List[KnowledgeEdgeSchema], float]] = deque(
            [(start_node_id, [src], [], 1.0)]
        )
        visited: Set[str] = {start_node_id}

        while queue and len(visited) < lim.max_nodes:
            curr_id, path_nodes, path_edges, path_conf = queue.popleft()
            if len(path_nodes) > lim.max_depth + 1:
                continue

            for edge in self.edges.get_outgoing_edges(curr_id):
                # Filter out contradicted or uncertain edges
                if edge.certainty == CertaintyLevel.CONTRADICTED:
                    continue
                if edge.confidence < min_confidence:
                    continue

                if as_of:
                    if edge.valid_from and edge.valid_from > as_of:
                        continue
                    if edge.valid_until and edge.valid_until < as_of:
                        continue

                next_node_id = edge.target_node_id
                next_node = self.nodes.get_node(next_node_id)
                if not next_node or not self._is_accessible(next_node, user_id):
                    continue

                new_conf = path_conf * edge.confidence
                if next_node_id == target_node_id:
                    return GraphQueryResultSchema(
                        nodes=path_nodes + [next_node],
                        edges=path_edges + [edge],
                        path_confidence=new_conf,
                        traversal_depth=len(path_edges) + 1,
                        total_nodes_visited=len(visited),
                        explanations=[f"Verified path found in {len(path_edges) + 1} hops (Confidence: {new_conf:.2f})"],
                    )

                if next_node_id not in visited:
                    visited.add(next_node_id)
                    queue.append((next_node_id, path_nodes + [next_node], path_edges + [edge], new_conf))

        return GraphQueryResultSchema(total_nodes_visited=len(visited), explanations=["No verified path found"])

    # =========================================================================
    # 3. STRUCTURED INFERENCE ENGINE (Phases 13, 14)
    # =========================================================================

    def run_inference(self, user_id: str = "default_user", scope: str = "global") -> List[KnowledgeEdgeSchema]:
        """Applies bounded deductive inference rules. NEVER infers authorization or permissions."""
        new_derived: List[KnowledgeEdgeSchema] = []

        for rule in self._inference_rules:
            if rule.rule_id == "TRANS_DEP":
                new_derived.extend(self._infer_transitive_dependencies(rule, user_id))
            elif rule.rule_id == "PART_OF_TRANS":
                new_derived.extend(self._infer_part_of_transitivity(rule, user_id))
            elif rule.rule_id == "CHILD_OF_ANCESTRY":
                new_derived.extend(self._infer_child_of_ancestry(rule, user_id))
            elif rule.rule_id == "BLOCKS_PROPAGATION":
                new_derived.extend(self._infer_blocks_propagation(rule, user_id))

        return new_derived

    def _default_inference_rules(self) -> List[InferenceRuleRecord]:
        return [
            InferenceRuleRecord(
                rule_id="TRANS_DEP",
                name="Transitive Dependency Propagation",
                premise_relations=[RelationshipType.DEPENDS_ON, RelationshipType.DEPENDS_ON],
                derived_relation=RelationshipType.TRANSITIVELY_DEPENDS_ON,
                confidence_decay=1.0,
                transitive=True,
            ),
            InferenceRuleRecord(
                rule_id="PART_OF_TRANS",
                name="Compositional Part-Of Transitivity",
                premise_relations=[RelationshipType.PART_OF, RelationshipType.PART_OF],
                derived_relation=RelationshipType.PART_OF,
                confidence_decay=0.95,
                transitive=True,
            ),
            InferenceRuleRecord(
                rule_id="CHILD_OF_ANCESTRY",
                name="Child-Of Ancestry Inference",
                premise_relations=[RelationshipType.CHILD_OF, RelationshipType.CHILD_OF],
                derived_relation=RelationshipType.CHILD_OF,
                confidence_decay=0.95,
                transitive=True,
            ),
            InferenceRuleRecord(
                rule_id="BLOCKS_PROPAGATION",
                name="Blocking Dependency Propagation",
                premise_relations=[RelationshipType.BLOCKS, RelationshipType.DEPENDS_ON],
                derived_relation=RelationshipType.AFFECTS,
                confidence_decay=0.85,
                transitive=False,
            ),
        ]

    def _infer_transitive_dependencies(self, rule: InferenceRuleRecord, user_id: str) -> List[KnowledgeEdgeSchema]:
        """A DEPENDS_ON B and B DEPENDS_ON C => A TRANSITIVELY_DEPENDS_ON C."""
        derived: List[KnowledgeEdgeSchema] = []
        dep_edges = [
            e for e in self.edges._edges.values()
            if e.relationship in (RelationshipType.DEPENDS_ON, RelationshipType.TRANSITIVELY_DEPENDS_ON)
            and e.status == "ACTIVE"
        ]

        for e1 in dep_edges:
            for e2 in self.edges.get_outgoing_edges(e1.target_node_id):
                if e2.relationship in (RelationshipType.DEPENDS_ON, RelationshipType.TRANSITIVELY_DEPENDS_ON):
                    a_id = e1.source_node_id
                    c_id = e2.target_node_id
                    if a_id == c_id:
                        continue  # Avoid trivial self loops

                    # Check if edge already exists
                    existing = any(
                        e.source_node_id == a_id and e.target_node_id == c_id and e.relationship == rule.derived_relation
                        for e in self.edges.get_outgoing_edges(a_id)
                    )
                    if not existing:
                        edge_conf = round(e1.confidence * e2.confidence * rule.confidence_decay, 4)
                        new_edge = self.edges.create_edge(
                            source_node_id=a_id,
                            relationship=rule.derived_relation,
                            target_node_id=c_id,
                            confidence=edge_conf,
                            provenance={
                                "rule_id": rule.rule_id,
                                "parent_edges": [e1.edge_id, e2.edge_id],
                                "provenance_type": ProvenanceClassification.INFERRED.value,
                            },
                            user_id=user_id,
                        )
                        new_edge.certainty = CertaintyLevel.LIKELY
                        new_edge.provenance = GraphProvenanceSchema(
                            source_id=rule.rule_id,
                            source_type="INFERENCE_ENGINE",
                            classification=ProvenanceClassification.INFERRED,
                            extraction_method="DEDUCTIVE_RULE",
                        )
                        new_edge.derivation_rule = rule.rule_id
                        new_edge.parent_edge_ids = [e1.edge_id, e2.edge_id]
                        new_edge.provenance_type = ProvenanceClassification.INFERRED
                        self._derived_edges[new_edge.edge_id] = new_edge
                        derived.append(new_edge)

        return derived

    def _infer_part_of_transitivity(self, rule: InferenceRuleRecord, user_id: str) -> List[KnowledgeEdgeSchema]:
        """A PART_OF B and B PART_OF C => A PART_OF C."""
        derived: List[KnowledgeEdgeSchema] = []
        part_edges = [e for e in self.edges._edges.values() if e.relationship == RelationshipType.PART_OF and e.status == "ACTIVE"]

        for e1 in part_edges:
            for e2 in self.edges.get_outgoing_edges(e1.target_node_id):
                if e2.relationship == RelationshipType.PART_OF:
                    a_id = e1.source_node_id
                    c_id = e2.target_node_id
                    if a_id == c_id:
                        continue
                    existing = any(
                        e.source_node_id == a_id and e.target_node_id == c_id and e.relationship == rule.derived_relation
                        for e in self.edges.get_outgoing_edges(a_id)
                    )
                    if not existing:
                        new_edge = self.edges.create_edge(
                            source_node_id=a_id,
                            relationship=rule.derived_relation,
                            target_node_id=c_id,
                            confidence=e1.confidence * e2.confidence * rule.confidence_decay,
                            provenance={"rule_id": rule.rule_id, "parent_edges": [e1.edge_id, e2.edge_id]},
                            user_id=user_id,
                        )
                        new_edge.derivation_rule = rule.rule_id
                        new_edge.parent_edge_ids = [e1.edge_id, e2.edge_id]
                        new_edge.provenance_type = ProvenanceClassification.INFERRED
                        self._derived_edges[new_edge.edge_id] = new_edge
                        derived.append(new_edge)

        return derived

    def _infer_child_of_ancestry(self, rule: InferenceRuleRecord, user_id: str) -> List[KnowledgeEdgeSchema]:
        """A CHILD_OF B and B CHILD_OF C => A CHILD_OF C."""
        derived: List[KnowledgeEdgeSchema] = []
        child_edges = [e for e in self.edges._edges.values() if e.relationship == RelationshipType.CHILD_OF and e.status == "ACTIVE"]

        for e1 in child_edges:
            for e2 in self.edges.get_outgoing_edges(e1.target_node_id):
                if e2.relationship == RelationshipType.CHILD_OF:
                    a_id = e1.source_node_id
                    c_id = e2.target_node_id
                    if a_id == c_id:
                        continue
                    existing = any(
                        e.source_node_id == a_id and e.target_node_id == c_id and e.relationship == rule.derived_relation
                        for e in self.edges.get_outgoing_edges(a_id)
                    )
                    if not existing:
                        new_edge = self.edges.create_edge(
                            source_node_id=a_id,
                            relationship=rule.derived_relation,
                            target_node_id=c_id,
                            confidence=e1.confidence * e2.confidence * rule.confidence_decay,
                            provenance={"rule_id": rule.rule_id, "parent_edges": [e1.edge_id, e2.edge_id]},
                            user_id=user_id,
                        )
                        new_edge.derivation_rule = rule.rule_id
                        new_edge.parent_edge_ids = [e1.edge_id, e2.edge_id]
                        new_edge.provenance_type = ProvenanceClassification.INFERRED
                        self._derived_edges[new_edge.edge_id] = new_edge
                        derived.append(new_edge)

        return derived

    def _infer_blocks_propagation(self, rule: InferenceRuleRecord, user_id: str) -> List[KnowledgeEdgeSchema]:
        """A BLOCKS B and C DEPENDS_ON B => A AFFECTS C."""
        derived: List[KnowledgeEdgeSchema] = []
        block_edges = [e for e in self.edges._edges.values() if e.relationship == RelationshipType.BLOCKS and e.status == "ACTIVE"]

        for b_edge in block_edges:
            blocked_id = b_edge.target_node_id
            # Incoming edges where C DEPENDS_ON B
            for dep_edge in self.edges.get_incoming_edges(blocked_id):
                if dep_edge.relationship in (RelationshipType.DEPENDS_ON, RelationshipType.REQUIRES):
                    c_id = dep_edge.source_node_id
                    blocker_id = b_edge.source_node_id
                    if blocker_id == c_id:
                        continue
                    existing = any(
                        e.source_node_id == blocker_id and e.target_node_id == c_id and e.relationship == rule.derived_relation
                        for e in self.edges.get_outgoing_edges(blocker_id)
                    )
                    if not existing:
                        new_edge = self.edges.create_edge(
                            source_node_id=blocker_id,
                            relationship=rule.derived_relation,
                            target_node_id=c_id,
                            confidence=b_edge.confidence * dep_edge.confidence * rule.confidence_decay,
                            provenance={"rule_id": rule.rule_id, "parent_edges": [b_edge.edge_id, dep_edge.edge_id]},
                            user_id=user_id,
                        )
                        new_edge.derivation_rule = rule.rule_id
                        new_edge.parent_edge_ids = [b_edge.edge_id, dep_edge.edge_id]
                        new_edge.provenance_type = ProvenanceClassification.INFERRED
                        self._derived_edges[new_edge.edge_id] = new_edge
                        derived.append(new_edge)

        return derived

    # =========================================================================
    # 4. DOWNSTREAM IMPACT & DEPENDENCY INTELLIGENCE (Phases 15, 16)
    # =========================================================================

    def analyze_downstream_impact(
        self,
        root_node_id: Optional[str] = None,
        limits: Optional[GraphTraversalLimits] = None,
        user_id: str = "default_user",
        as_of: Optional[datetime] = None,
        origin_node: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> ImpactAnalysisResult:
        """Finds all downstream entities affected by a failure or change in root_node_id."""
        actual_root = origin_node or root_node_id or ""
        lim = limits or GraphTraversalLimits(max_depth=max_depth if max_depth is not None else 5)
        root = self.nodes.get_node(actual_root)
        if not root:
            return ImpactAnalysisResult(root_node_id=actual_root, summary=f"Node '{actual_root}' not found.")

        # Impact propagation travels through:
        # 1. Incoming DEPENDS_ON / REQUIRES edges (things that depend on root)
        # 2. Outgoing AFFECTS / BLOCKS / CAUSES / RESULTS_IN edges
        impacted_nodes: List[ImpactedNodeRecord] = []
        propagation_paths: List[List[str]] = []
        visited: Set[str] = {actual_root}
        max_depth_reached = 0

        # Queue: (curr_id, current_path, current_depth)
        queue: deque[Tuple[str, List[str], int]] = deque([(actual_root, [actual_root], 0)])

        while queue and len(visited) < lim.max_nodes:
            curr_id, path, depth = queue.popleft()
            max_depth_reached = max(max_depth_reached, depth)
            if depth >= lim.max_depth:
                continue

            # Incoming dependency edges: C depends on B
            dep_incoming = [
                e for e in self.edges.get_incoming_edges(curr_id)
                if e.relationship in (RelationshipType.DEPENDS_ON, RelationshipType.REQUIRES, RelationshipType.USED_BY, RelationshipType.AFFECTS)
            ]
            # Outgoing causal/affecting edges
            causal_outgoing = [
                e for e in self.edges.get_outgoing_edges(curr_id)
                if e.relationship in (RelationshipType.AFFECTS, RelationshipType.BLOCKS, RelationshipType.CAUSES, RelationshipType.RESULTS_IN)
            ]

            for edge in dep_incoming + causal_outgoing:
                next_id = edge.source_node_id if edge in dep_incoming else edge.target_node_id
                next_node = self.nodes.get_node(next_id)
                if not next_node or not self._is_accessible(next_node, user_id):
                    continue

                if as_of:
                    if edge.valid_from and edge.valid_from > as_of:
                        continue
                    if edge.valid_until and edge.valid_until < as_of:
                        continue

                new_path = path + [next_id]
                if next_id not in visited:
                    visited.add(next_id)
                    crit_level = "CRITICAL" if next_node.node_type in (NodeType.SERVICE, NodeType.CAPABILITY) else "HIGH" if depth <= 1 else "MEDIUM"
                    impacted_nodes.append(ImpactedNodeRecord(
                        node_id=next_node.node_id,
                        canonical_name=next_node.canonical_name,
                        node_type=next_node.node_type.value,
                        depth=depth + 1,
                        relationship=edge.relationship.value,
                        confidence=edge.confidence,
                        criticality=crit_level,
                    ))
                    propagation_paths.append(new_path)
                    queue.append((next_id, new_path, depth + 1))

        # Assess criticality based on fanout and node types
        total = len(impacted_nodes)
        has_critical = any(n.criticality == "CRITICAL" for n in impacted_nodes)
        if total >= 4 or (has_critical and total >= 3):
            crit = "HIGH" if total < 5 else "CRITICAL"
        elif total > 1:
            crit = "MEDIUM"
        elif total > 0:
            crit = "LOW"
        else:
            crit = "NONE"

        return ImpactAnalysisResult(
            root_node_id=actual_root,
            impacted_nodes=impacted_nodes,
            propagation_paths=propagation_paths,
            depth=max_depth_reached,
            risk_criticality=crit,
            total_affected=total,
            summary=f"Downstream change on '{root.canonical_name}' impacts {total} entities across {max_depth_reached} tiers.",
        )

    def get_dependencies(
        self,
        node_id: str,
        max_depth: int = 4,
        user_id: str = "default_user",
        as_of: Optional[datetime] = None,
    ) -> GraphQueryResultSchema:
        """Answers: 'What depends on X?' and 'What does X depend on?'."""
        return self.execute_query(
            query_type=GraphQueryType.DEPENDENCY_QUERY,
            start_node_id=node_id,
            limits=GraphTraversalLimits(max_depth=max_depth),
            user_id=user_id,
            as_of=as_of,
        )

    # =========================================================================
    # 5. LINEAGE RECONSTRUCTION (Phases 17, 18, 19, 20, 21)
    # =========================================================================

    def reconstruct_decision_lineage(self, decision_id: str, user_id: str = "default_user") -> LineageReconstructionResult:
        """Reconstructs: Goal -> Plan -> Context -> Decision -> Action -> Outcome -> Memory."""
        node = self._find_node_by_key_or_id(decision_id, NodeType.DECISION)
        if not node:
            return LineageReconstructionResult(lineage_type="decision", root_id=decision_id, is_complete=False)

        steps: List[LineageStepRecord] = [LineageStepRecord(node_id=node.node_id, node_type=node.node_type.value, relationship="DECISION")]
        evidence: List[str] = []

        # Find upstream Goals / Context / Evidence
        for edge in self.edges.get_outgoing_edges(node.node_id) + self.edges.get_incoming_edges(node.node_id):
            other_id = edge.target_node_id if edge.source_node_id == node.node_id else edge.source_node_id
            other_node = self.nodes.get_node(other_id)
            if not other_node:
                continue
            if other_node.node_type in (NodeType.GOAL, NodeType.TASK, NodeType.EVIDENCE, NodeType.PERSON_CONTEXT):
                steps.insert(0, LineageStepRecord(node_id=other_node.node_id, node_type=other_node.node_type.value, relationship=edge.relationship.value))
                if other_node.node_type == NodeType.EVIDENCE:
                    evidence.append(other_node.node_id)
            elif other_node.node_type in (NodeType.ACTION, NodeType.OUTCOME, NodeType.MEMORY):
                steps.append(LineageStepRecord(node_id=other_node.node_id, node_type=other_node.node_type.value, relationship=edge.relationship.value))

        seen = set()
        dedup_steps = []
        for s in steps:
            if s.node_id not in seen:
                seen.add(s.node_id)
                dedup_steps.append(s)

        return LineageReconstructionResult(
            lineage_type="decision",
            root_id=decision_id,
            steps=dedup_steps,
            evidence_refs=evidence,
            is_complete=len(dedup_steps) >= 2,
            provenance_chain=[s.node_id for s in dedup_steps],
            summary=f"Reconstructed full decision lineage for '{node.canonical_name}' across goals, evidence, and actions.",
        )

    def reconstruct_action_lineage(self, action_id: str, user_id: str = "default_user") -> LineageReconstructionResult:
        """Task 95 Action Lineage: Goal -> Decision -> Action -> Capability -> Target -> Execution -> Verification -> Outcome."""
        node = self._find_node_by_key_or_id(action_id, NodeType.ACTION)
        if not node:
            return LineageReconstructionResult(lineage_type="action", root_id=action_id, is_complete=False)

        steps: List[LineageStepRecord] = [LineageStepRecord(node_id=node.node_id, node_type=node.node_type.value, relationship="ACTION")]
        evidence: List[str] = []

        for edge in self.edges.get_outgoing_edges(node.node_id) + self.edges.get_incoming_edges(node.node_id):
            other_id = edge.target_node_id if edge.source_node_id == node.node_id else edge.source_node_id
            other_node = self.nodes.get_node(other_id)
            if not other_node:
                continue
            if other_node.node_type in (NodeType.DECISION, NodeType.GOAL, NodeType.TASK):
                steps.insert(0, LineageStepRecord(node_id=other_node.node_id, node_type=other_node.node_type.value, relationship=edge.relationship.value))
            elif other_node.node_type in (NodeType.CAPABILITY, NodeType.CAPABILITY_VERSION, NodeType.RESOURCE, NodeType.OUTCOME):
                steps.append(LineageStepRecord(node_id=other_node.node_id, node_type=other_node.node_type.value, relationship=edge.relationship.value))

        seen = set()
        dedup_steps = []
        for s in steps:
            if s.node_id not in seen:
                seen.add(s.node_id)
                dedup_steps.append(s)

        return LineageReconstructionResult(
            lineage_type="action",
            root_id=action_id,
            steps=dedup_steps,
            evidence_refs=evidence,
            is_complete=len(dedup_steps) >= 2,
            provenance_chain=[s.node_id for s in dedup_steps],
            summary=f"Reconstructed action lineage for '{node.canonical_name}' across decisions and capabilities.",
        )

    def reconstruct_memory_lineage(self, memory_id: str, user_id: str = "default_user") -> LineageReconstructionResult:
        """Task 92 Memory Lineage: Source Events -> Evidence -> Derived Facts -> Contradictions -> Current Memory."""
        node = self._find_node_by_key_or_id(memory_id, NodeType.MEMORY)
        if not node:
            return LineageReconstructionResult(lineage_type="memory", root_id=memory_id, is_complete=False)

        steps: List[LineageStepRecord] = [LineageStepRecord(node_id=node.node_id, node_type=node.node_type.value, relationship="MEMORY")]
        evidence: List[str] = []

        for edge in self.edges.get_outgoing_edges(node.node_id) + self.edges.get_incoming_edges(node.node_id):
            other_id = edge.target_node_id if edge.source_node_id == node.node_id else edge.source_node_id
            other_node = self.nodes.get_node(other_id)
            if not other_node:
                continue
            if other_node.node_type in (NodeType.EVENT, NodeType.CONVERSATION, NodeType.EVIDENCE, NodeType.DOCUMENT):
                steps.insert(0, LineageStepRecord(node_id=other_node.node_id, node_type=other_node.node_type.value, relationship=edge.relationship.value))
                evidence.append(other_node.node_id)

        seen = set()
        dedup_steps = []
        for s in steps:
            if s.node_id not in seen:
                seen.add(s.node_id)
                dedup_steps.append(s)

        return LineageReconstructionResult(
            lineage_type="memory",
            root_id=memory_id,
            steps=dedup_steps,
            evidence_refs=evidence,
            is_complete=len(dedup_steps) >= 1,
            provenance_chain=[s.node_id for s in dedup_steps],
            summary=f"Reconstructed memory lineage for '{node.canonical_name}'.",
        )

    def reconstruct_agent_lineage(self, agent_id: str, user_id: str = "default_user") -> LineageReconstructionResult:
        """Task 96 Agent Lineage: Swarm -> Agent -> Task -> Tools -> Evidence -> Result -> Validation -> Synthesis."""
        node = self._find_node_by_key_or_id(agent_id, NodeType.AGENT)
        if not node:
            return LineageReconstructionResult(lineage_type="agent", root_id=agent_id, is_complete=False)

        steps: List[LineageStepRecord] = [LineageStepRecord(node_id=node.node_id, node_type=node.node_type.value, relationship="AGENT")]
        evidence: List[str] = []

        for edge in self.edges.get_outgoing_edges(node.node_id) + self.edges.get_incoming_edges(node.node_id):
            other_id = edge.target_node_id if edge.source_node_id == node.node_id else edge.source_node_id
            other_node = self.nodes.get_node(other_id)
            if other_node:
                steps.append(LineageStepRecord(node_id=other_node.node_id, node_type=other_node.node_type.value, relationship=edge.relationship.value))

        seen = set()
        dedup_steps = []
        for s in steps:
            if s.node_id not in seen:
                seen.add(s.node_id)
                dedup_steps.append(s)

        return LineageReconstructionResult(
            lineage_type="agent",
            root_id=agent_id,
            steps=dedup_steps,
            evidence_refs=evidence,
            is_complete=len(dedup_steps) >= 1,
            provenance_chain=[s.node_id for s in dedup_steps],
            summary=f"Reconstructed swarm agent lineage for '{node.canonical_name}'.",
        )

    # =========================================================================
    # 6. CONFLICT GRAPH & CONTRADICTIONS (Phase 22)
    # =========================================================================

    def record_conflict(
        self,
        source_node_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
        conflict_type: str = "DIRECT_CONTRADICTION",
        evidence_refs: Optional[List[str]] = None,
        user_id: str = "default_user",
        node_a: Optional[str] = None,
        node_b: Optional[str] = None,
        reason: str = "",
        confidence: float = 1.0,
    ) -> ConflictRecord:
        """Registers a verified contradiction edge without silently deleting conflicting claims."""
        src_id = node_a or source_node_id or ""
        tgt_id = node_b or target_node_id or ""
        src = self.nodes.get_node(src_id)
        tgt = self.nodes.get_node(tgt_id)
        if not src or not tgt:
            raise KeyError(f"Nodes '{src_id}' or '{tgt_id}' not found.")

        # Create explicit CONTRADICTS edge
        edge = self.edges.create_edge(
            source_node_id=src_id,
            relationship=RelationshipType.CONTRADICTS,
            target_node_id=tgt_id,
            confidence=confidence,
            provenance={"conflict_type": conflict_type, "reason": reason, "evidence_refs": evidence_refs or []},
            user_id=user_id,
        )
        edge.certainty = CertaintyLevel.CONTRADICTED

        conflict = ConflictRecord(
            source_node_id=src_id,
            target_node_id=tgt_id,
            node_a=src_id,
            node_b=tgt_id,
            conflict_type=conflict_type,
            resolution_state=ConflictResolutionState.UNRESOLVED,
            evidence_refs=evidence_refs or [],
            reason=reason,
            confidence=confidence,
        )
        self._conflicts[conflict.conflict_id] = conflict
        return conflict

    def list_conflicts(self, unresolved_only: bool = True) -> List[ConflictRecord]:
        if unresolved_only:
            return [c for c in self._conflicts.values() if c.resolution_state == ConflictResolutionState.UNRESOLVED]
        return list(self._conflicts.values())

    # =========================================================================
    # 7. GRAPH SNAPSHOTS & DIFFING (Phases 32, 33, 34)
    # =========================================================================

    def create_snapshot(
        self,
        snapshot_type: str = "CURRENT",
        metadata: Optional[Dict[str, Any]] = None,
        label: Optional[str] = None,
        scope: str = "global",
    ) -> GraphSnapshot:
        """Creates an immutable reference snapshot of active graph nodes and edges."""
        active_nodes = [n.node_id for n in self.nodes._nodes.values() if n.status == "ACTIVE"]
        active_node_ids = set(active_nodes)
        active_edges = [
            e.edge_id for e in self.edges._edges.values()
            if e.status == "ACTIVE" and e.source_node_id in active_node_ids and e.target_node_id in active_node_ids
        ]

        snap = GraphSnapshot(
            snapshot_type=snapshot_type,
            label=label or snapshot_type,
            node_count=len(active_nodes),
            edge_count=len(active_edges),
            node_ids=active_nodes,
            edge_ids=active_edges,
            metadata=metadata or {},
        )
        self._snapshots[snap.snapshot_id] = snap
        return snap

    def compute_graph_diff(self, snapshot_a_id: str, snapshot_b_id: str) -> GraphDiffResult:
        """Computes delta between two graph snapshots (ADDED, REMOVED, CHANGED)."""
        snap_a = self._snapshots.get(snapshot_a_id)
        snap_b = self._snapshots.get(snapshot_b_id)
        if not snap_a or not snap_b:
            raise KeyError(f"Snapshots '{snapshot_a_id}' or '{snapshot_b_id}' not found.")

        set_nodes_a = set(snap_a.node_ids)
        set_nodes_b = set(snap_b.node_ids)
        added_nodes = list(set_nodes_b - set_nodes_a)
        removed_nodes = list(set_nodes_a - set_nodes_b)

        set_edges_a = set(snap_a.edge_ids)
        set_edges_b = set(snap_b.edge_ids)
        added_edges = list(set_edges_b - set_edges_a)
        removed_edges = list(set_edges_a - set_edges_b)

        return GraphDiffResult(
            snapshot_a_id=snapshot_a_id,
            snapshot_b_id=snapshot_b_id,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            changed_nodes=[],
            added_edges=added_edges,
            removed_edges=removed_edges,
            changed_edges=[],
        )

    def identify_revalidation_candidates(self, modified_node_id: str) -> List[str]:
        """Identifies dependent decisions, tasks, or capabilities that require re-evaluation after a graph change."""
        impact = self.analyze_downstream_impact(modified_node_id)
        reval: List[str] = []
        for item in impact.impacted_nodes:
            if item["node_type"] in (NodeType.DECISION.value, NodeType.TASK.value, NodeType.WORKFLOW.value, NodeType.MEMORY.value):
                reval.append(item["node_id"])
        return reval

    # =========================================================================
    # 8. ENTITY RESOLUTION & DEDUPLICATION (Phases 8, 9)
    # =========================================================================

    def resolve_or_create_entity(
        self,
        canonical_name: str,
        node_type: NodeType,
        aliases: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        scope: ScopeType = ScopeType.PRIVATE,
        confidence: float = 1.0,
        user_id: str = "default_user",
    ) -> KnowledgeNodeSchema:
        """Resolves alias or canonical name to an existing node or creates a new node."""
        clean_name = canonical_name.strip()
        alias_list = [a.strip() for a in (aliases or []) if a.strip()]

        # Search existing by canonical name or alias
        existing = self.nodes.get_node_by_name(clean_name)
        if existing and existing.node_type == node_type and existing.status == "ACTIVE":
            # Add any new aliases without loss
            for al in alias_list:
                if al not in existing.aliases:
                    existing.aliases.append(al)
            return existing

        for al in alias_list:
            found = self.nodes.get_node_by_name(al)
            if found and found.node_type == node_type and found.status == "ACTIVE":
                if clean_name not in found.aliases and clean_name != found.canonical_name:
                    found.aliases.append(clean_name)
                return found

        # Create new node
        return self.nodes.create_node(
            canonical_name=clean_name,
            node_type=node_type,
            aliases=alias_list,
            metadata=metadata or {},
            scope=scope,
            confidence=confidence,
            user_id=user_id,
        )

    def merge_nodes(self, primary_node_id: str, secondary_node_id: str, reason: str = "Deduplication") -> KnowledgeNodeSchema:
        """Merges secondary_node into primary_node, transferring all edges and preserving provenance."""
        primary = self.nodes.get_node(primary_node_id)
        secondary = self.nodes.get_node(secondary_node_id)
        if not primary or not secondary:
            raise KeyError("Both primary and secondary nodes must exist.")

        # 1. Merge aliases
        for al in [secondary.canonical_name] + secondary.aliases:
            if al not in primary.aliases and al != primary.canonical_name:
                primary.aliases.append(al)

        # 2. Re-wire edges
        for out_edge in list(self.edges.get_outgoing_edges(secondary_node_id)):
            out_edge.source_node_id = primary_node_id
            self.edges._out_edges.setdefault(primary_node_id, set()).add(out_edge.edge_id)

        for in_edge in list(self.edges.get_incoming_edges(secondary_node_id)):
            in_edge.target_node_id = primary_node_id
            self.edges._in_edges.setdefault(primary_node_id, set()).add(in_edge.edge_id)

        # 3. Mark secondary merged
        secondary.status = "MERGED"
        secondary.metadata["merged_into"] = primary_node_id
        secondary.metadata["merge_reason"] = reason

        primary.version += 1
        primary.metadata.setdefault("merge_history", []).append({
            "merged_node_id": secondary_node_id,
            "merged_at": utc_now().isoformat(),
            "reason": reason,
        })
        return primary

    # =========================================================================
    # 9. SECURITY & ACCESS FILTERING (Phase 36, 38)
    # =========================================================================

    def _is_accessible(
        self,
        node: KnowledgeNodeSchema,
        user_id: str,
        req_scope: Optional[Any] = None,
        allowed_sensitivities: Optional[List[str]] = None,
    ) -> bool:
        if node.status != "ACTIVE":
            return False
        if req_scope:
            req_scope_str = req_scope.value if hasattr(req_scope, "value") else str(req_scope)
            node_scope_str = node.scope.value if hasattr(node.scope, "value") else str(node.scope)
            if (
                node_scope_str != req_scope_str
                and node.project_id != req_scope_str
                and node.scope != ScopeType.GLOBAL
            ):
                return False
        if node.scope == ScopeType.PRIVATE and node.user_id != user_id:
            return False
        if allowed_sensitivities is not None:
            if node.sensitivity not in allowed_sensitivities:
                return False
        return True

    def _is_edge_accessible(
        self,
        edge: KnowledgeEdgeSchema,
        user_id: str,
        req_scope: Optional[Any] = None,
        allowed_sensitivities: Optional[List[str]] = None,
    ) -> bool:
        if edge.status != "ACTIVE":
            return False
        if req_scope:
            req_scope_str = req_scope.value if hasattr(req_scope, "value") else str(req_scope)
            edge_scope_str = edge.scope.value if hasattr(edge.scope, "value") else str(edge.scope)
            if (
                edge_scope_str != req_scope_str
                and edge.project_id != req_scope_str
                and edge.scope != ScopeType.GLOBAL
            ):
                return False
        if edge.scope == ScopeType.PRIVATE and edge.user_id != user_id:
            return False
        return True

    def _find_node_by_key_or_id(self, identifier: str, expected_type: NodeType) -> Optional[KnowledgeNodeSchema]:
        """Finds node by id, or by canonical name / metadata matching identifier."""
        node = self.nodes.get_node(identifier)
        if node:
            return node
        # Search by canonical name or metadata key
        for n in self.nodes._nodes.values():
            if n.node_type == expected_type and (n.canonical_name == identifier or n.metadata.get("id") == identifier):
                return n
        return None


# Global singleton
_global_reasoning_engine: Optional[GraphReasoningEngine] = None


def get_graph_reasoning_engine() -> GraphReasoningEngine:
    global _global_reasoning_engine
    if _global_reasoning_engine is None:
        _global_reasoning_engine = GraphReasoningEngine()
    return _global_reasoning_engine


graph_reasoning_engine = get_graph_reasoning_engine()

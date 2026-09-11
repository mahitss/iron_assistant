"""Reasoning graph representation for Kairo Autonomous Reasoning (Task 71).

Constructs a structured DAG preserving provenance, evidence relationships,
subproblem dependencies, and assumption cascades.
"""

import logging
from typing import Any

from app.reasoning.schemas import (
    GraphEdgeType,
    ReasoningGraph,
    ReasoningGraphEdge,
    ReasoningGraphNode,
    ReasoningSession,
)

logger = logging.getLogger(__name__)


class ReasoningGraphBuilder:
    """Builds, queries, and maintains typed reasoning DAG graphs."""

    def __init__(self) -> None:
        self._nodes: dict[str, ReasoningGraphNode] = {}
        self._edges: list[ReasoningGraphEdge] = []

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        metadata: dict[str, Any] | None = None,
    ) -> ReasoningGraphNode:
        """Add or update a node in the reasoning graph."""
        node = ReasoningGraphNode(
            node_id=node_id,
            node_type=node_type,
            label=label,
            metadata=metadata or {},
        )
        self._nodes[node_id] = node
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: GraphEdgeType,
        weight: float = 1.0,
    ) -> ReasoningGraphEdge:
        """Add a directed typed edge between two nodes."""
        edge = ReasoningGraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
        )
        # Avoid duplicate identical edges
        for existing in self._edges:
            if (
                existing.source_id == source_id
                and existing.target_id == target_id
                and existing.edge_type == edge_type
            ):
                existing.weight = weight
                return existing

        self._edges.append(edge)
        return edge

    def build_from_session(self, session: ReasoningSession) -> ReasoningGraph:
        """Populate the graph completely from a ReasoningSession domain object."""
        # 1. Root Question Node
        root_id = f"q-{session.reasoning_id}"
        self.add_node(
            node_id=root_id,
            node_type="question",
            label=session.question,
            metadata={"depth": session.depth.value, "confidence": session.confidence.value},
        )

        # 2. Subproblems
        for sp in session.subproblems:
            self.add_node(
                node_id=sp.subproblem_id,
                node_type="subproblem",
                label=sp.question,
                metadata={"status": sp.status, "depth_level": sp.depth_level},
            )
            # Edge from root or parent
            parent = sp.parent_id or root_id
            self.add_edge(parent, sp.subproblem_id, GraphEdgeType.DERIVED_FROM)

            # Dependencies between subproblems
            for dep in sp.dependencies:
                self.add_edge(dep, sp.subproblem_id, GraphEdgeType.DEPENDS_ON)

        # 3. Evidence
        for ev in session.evidence:
            self.add_node(
                node_id=ev.evidence_id,
                node_type="evidence",
                label=ev.content_summary[:80],
                metadata={
                    "source_type": ev.source_type,
                    "trust_level": ev.trust_level,
                    "reliability": ev.reliability,
                },
            )

        # 4. Hypotheses
        for hyp in session.hypotheses:
            self.add_node(
                node_id=hyp.hypothesis_id,
                node_type="hypothesis",
                label=hyp.description[:80],
                metadata={"status": hyp.status.value, "confidence": hyp.confidence.value},
            )
            if hyp.subproblem_id:
                self.add_edge(hyp.subproblem_id, hyp.hypothesis_id, GraphEdgeType.LEADS_TO)
            else:
                self.add_edge(root_id, hyp.hypothesis_id, GraphEdgeType.LEADS_TO)

            # Supporting evidence edges
            for se_id in hyp.supporting_evidence_ids:
                if se_id in self._nodes:
                    self.add_edge(se_id, hyp.hypothesis_id, GraphEdgeType.SUPPORTS)

            # Contradicting evidence edges
            for ce_id in hyp.contradicting_evidence_ids:
                if ce_id in self._nodes:
                    self.add_edge(ce_id, hyp.hypothesis_id, GraphEdgeType.CONTRADICTS)

        # 5. Assumptions
        for asm in session.assumptions:
            self.add_node(
                node_id=asm.assumption_id,
                node_type="assumption",
                label=asm.description[:80],
                metadata={"status": asm.status.value},
            )

        # 6. Conclusions
        for concl in session.conclusions:
            self.add_node(
                node_id=concl.conclusion_id,
                node_type="conclusion",
                label=concl.summary[:80],
                metadata={
                    "status": concl.status.value,
                    "confidence": concl.confidence.value,
                    "uncertainty": concl.uncertainty_state.value,
                    "is_verified": concl.is_verified,
                },
            )
            # Hypotheses -> Conclusion
            for hid in concl.supporting_hypothesis_ids:
                if hid in self._nodes:
                    self.add_edge(hid, concl.conclusion_id, GraphEdgeType.SUPPORTS)

            # Assumptions -> Conclusion
            for aid in concl.assumption_ids:
                if aid in self._nodes:
                    self.add_edge(aid, concl.conclusion_id, GraphEdgeType.DEPENDS_ON)

        # 7. Alternatives
        for alt in session.alternatives:
            self.add_node(
                node_id=alt.alternative_id,
                node_type="alternative",
                label=alt.title,
                metadata={"risk": alt.risk_score, "cost": alt.cost_score, "impact": alt.expected_impact},
            )
            self.add_edge(root_id, alt.alternative_id, GraphEdgeType.LEADS_TO)

        return self.export_graph()

    def find_dependents(self, node_id: str) -> list[str]:
        """Find all downstream nodes directly depending on or supported by node_id."""
        dependents = []
        for edge in self._edges:
            if edge.source_id == node_id and edge.edge_type in (
                GraphEdgeType.DEPENDS_ON,
                GraphEdgeType.SUPPORTS,
                GraphEdgeType.LEADS_TO,
            ):
                dependents.append(edge.target_id)
        return dependents

    def find_upstream(self, node_id: str) -> list[str]:
        """Find all upstream sources for node_id."""
        upstream = []
        for edge in self._edges:
            if edge.target_id == node_id:
                upstream.append(edge.source_id)
        return upstream

    def export_graph(self) -> ReasoningGraph:
        """Export as ReasoningGraph schema."""
        return ReasoningGraph(
            nodes=list(self._nodes.values()),
            edges=list(self._edges),
        )

"""Agent and Evidence Provenance Lineage Graph.

Tracks the causal and verifiable lineage connecting:
Goal -> Supervisor -> Subtask -> Agent -> Contract -> Evidence/Artifact -> Synthesis -> Verification -> Result.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid


class ProvenanceNodeType(str, Enum):
    GOAL = "GOAL"
    SUPERVISOR = "SUPERVISOR"
    SUBTASK = "SUBTASK"
    AGENT = "AGENT"
    CONTRACT = "CONTRACT"
    EVIDENCE = "EVIDENCE"
    ARTIFACT = "ARTIFACT"
    SYNTHESIS = "SYNTHESIS"
    VERIFICATION = "VERIFICATION"
    RESULT = "RESULT"


class ProvenanceRelation(str, Enum):
    DECOMPOSED_INTO = "DECOMPOSED_INTO"
    DELEGATED_TO = "DELEGATED_TO"
    BOUND_BY = "BOUND_BY"
    PRODUCED = "PRODUCED"
    CONTRIBUTED_TO = "CONTRIBUTED_TO"
    SYNTHESIZED_FROM = "SYNTHESIZED_FROM"
    VERIFIED_BY = "VERIFIED_BY"
    DERIVED_FROM = "DERIVED_FROM"


@dataclass
class ProvenanceNode:
    node_id: str
    node_type: ProvenanceNodeType
    label: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "verified": self.verified,
        }


@dataclass
class ProvenanceEdge:
    source_id: str
    target_id: str
    relation: ProvenanceRelation
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class ProvenanceGraph:
    """Directed acyclic provenance graph for multi-agent execution."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.nodes: Dict[str, ProvenanceNode] = {}
        self.edges: List[ProvenanceEdge] = []
        self._adjacency: Dict[str, List[str]] = {}
        self._reverse_adjacency: Dict[str, List[str]] = {}

    def add_node(
        self,
        node_id: str,
        node_type: ProvenanceNodeType,
        label: str,
        metadata: Optional[Dict[str, Any]] = None,
        verified: bool = False,
    ) -> ProvenanceNode:
        if node_id in self.nodes:
            # Update existing node attributes if needed
            node = self.nodes[node_id]
            node.verified = node.verified or verified
            if metadata:
                node.metadata.update(metadata)
            return node

        node = ProvenanceNode(
            node_id=node_id,
            node_type=node_type,
            label=label,
            metadata=metadata or {},
            verified=verified,
        )
        self.nodes[node_id] = node
        self._adjacency[node_id] = []
        self._reverse_adjacency[node_id] = []
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: ProvenanceRelation,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProvenanceEdge:
        if source_id not in self.nodes:
            raise KeyError(f"Source node {source_id} not in provenance graph")
        if target_id not in self.nodes:
            raise KeyError(f"Target node {target_id} not in provenance graph")

        edge = ProvenanceEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            metadata=metadata or {},
        )
        self.edges.append(edge)
        self._adjacency[source_id].append(target_id)
        self._reverse_adjacency[target_id].append(source_id)
        return edge

    def get_ancestors(self, node_id: str) -> List[ProvenanceNode]:
        """Return all ancestor nodes leading up to this node."""
        visited: Set[str] = set()
        stack = [node_id]
        ancestors: List[ProvenanceNode] = []

        while stack:
            curr = stack.pop()
            for parent_id in self._reverse_adjacency.get(curr, []):
                if parent_id not in visited:
                    visited.add(parent_id)
                    ancestors.append(self.nodes[parent_id])
                    stack.append(parent_id)
        return ancestors

    def get_descendants(self, node_id: str) -> List[ProvenanceNode]:
        """Return all descendant nodes derived from this node."""
        visited: Set[str] = set()
        stack = [node_id]
        descendants: List[ProvenanceNode] = []

        while stack:
            curr = stack.pop()
            for child_id in self._adjacency.get(curr, []):
                if child_id not in visited:
                    visited.add(child_id)
                    descendants.append(self.nodes[child_id])
                    stack.append(child_id)
        return descendants

    def trace_evidence_lineage(self, evidence_id: str) -> Dict[str, Any]:
        """Trace the full upstream lineage of an evidence item."""
        if evidence_id not in self.nodes:
            return {"error": f"Evidence {evidence_id} not found in graph"}

        ancestors = self.get_ancestors(evidence_id)
        agent_node = next((n for n in ancestors if n.node_type == ProvenanceNodeType.AGENT), None)
        contract_node = next((n for n in ancestors if n.node_type == ProvenanceNodeType.CONTRACT), None)
        subtask_node = next((n for n in ancestors if n.node_type == ProvenanceNodeType.SUBTASK), None)
        goal_node = next((n for n in ancestors if n.node_type == ProvenanceNodeType.GOAL), None)

        evidence_node = self.nodes[evidence_id]
        return {
            "evidence_id": evidence_id,
            "label": evidence_node.label,
            "verified": evidence_node.verified,
            "producing_agent": agent_node.to_dict() if agent_node else None,
            "contract": contract_node.to_dict() if contract_node else None,
            "subtask": subtask_node.to_dict() if subtask_node else None,
            "root_goal": goal_node.to_dict() if goal_node else None,
            "ancestor_count": len(ancestors),
        }

    def verify_lineage_integrity(self, node_id: str) -> bool:
        """Verify that a terminal result or synthesis traces back to an authorized root goal."""
        if node_id not in self.nodes:
            return False
        ancestors = self.get_ancestors(node_id)
        has_goal = any(n.node_type == ProvenanceNodeType.GOAL for n in ancestors)
        has_contract = any(n.node_type == ProvenanceNodeType.CONTRACT for n in ancestors)
        return has_goal and has_contract

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

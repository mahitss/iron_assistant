"""Intent Graph Model, Dependency DAG, and Outcome Traceability (Task 48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.intent.intent_graph")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class GraphNode:
    node_id: str
    node_type: str  # INTENT, GOAL, OBJECTIVE, CONSTRAINT, TASK, OUTCOME
    label: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relationship: str  # CREATES, SATISFIES, CONSTRAINS, DEPENDS_ON


class IntentGraph:
    """Directed Acyclic Graph linking Intent -> Goal -> Objectives -> Constraints -> Tasks -> Outcomes (Spec 74, 144)."""

    def __init__(self, intent_id: str, goal_id: Optional[str] = None) -> None:
        self.graph_id = f"graph_{uuid.uuid4().hex[:8]}"
        self.intent_id = intent_id
        self.goal_id = goal_id
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self.created_at = utc_now()

    def add_node(self, a: str, b: str, label: str = "", metadata: Optional[Dict[str, Any]] = None) -> GraphNode:
        # Flexible argument handling: handles both (node_id, node_type) and (node_type, node_id)
        valid_types = {"INTENT", "GOAL", "OBJECTIVE", "CONSTRAINT", "TASK", "OUTCOME"}
        if a.upper() in valid_types:
            node_type, node_id = a.upper(), b
        else:
            node_id, node_type = a, b.upper()
        node = GraphNode(node_id=node_id, node_type=node_type, label=label or node_id, metadata=metadata or {})
        self._nodes[node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str, relationship: str = "CREATES") -> GraphEdge:
        edge = GraphEdge(source_id=source_id, target_id=target_id, relationship=relationship)
        self._edges.append(edge)
        return edge

    def get_dependencies(self, node_id: str) -> List[str]:
        """Return IDs of nodes that this node depends on or connects to."""
        return [e.target_id for e in self._edges if e.source_id == node_id]


    def build_from_goal(self, goal_data: Dict[str, Any]) -> None:
        """Constructs full lineage DAG from intent through goal, objectives, and constraints."""
        # 1. Intent node
        self.add_node(self.intent_id, "INTENT", f"Intent {self.intent_id}")

        # 2. Goal node
        gid = goal_data.get("goal_id", self.goal_id or f"goal_{self.intent_id}")
        self.add_node(gid, "GOAL", goal_data.get("description", "Goal"))
        self.add_edge(self.intent_id, gid, "FORMULATES_GOAL")

        # 3. Objective nodes
        for idx, obj in enumerate(goal_data.get("objectives", [])):
            oid = obj.get("objective_id", f"obj_{idx}")
            self.add_node(oid, "OBJECTIVE", obj.get("description", "Objective"), metadata=obj)
            self.add_edge(gid, oid, "HAS_OBJECTIVE")

        # 4. Constraint nodes
        for idx, constr in enumerate(goal_data.get("constraints", [])):
            cid = f"constr_{idx}"
            self.add_node(cid, "CONSTRAINT", constr.get("name", "Constraint"), metadata=constr)
            self.add_edge(gid, cid, "CONSTRAINED_BY")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "intent_id": self.intent_id,
            "goal_id": self.goal_id,
            "nodes": [
                {"id": n.node_id, "node_type": n.node_type, "label": n.label, "data": n.metadata}
                for n in self._nodes.values()
            ],
            "edges": [
                {"source": e.source_id, "target": e.target_id, "relationship": e.relationship}
                for e in self._edges
            ],
            "created_at": self.created_at.isoformat(),
        }

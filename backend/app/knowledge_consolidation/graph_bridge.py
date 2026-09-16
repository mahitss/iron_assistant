"""Knowledge Graph integration bridge for KAIRO (Task 92 Phase 18).

Integrates memory consolidation directly with existing KnowledgeNode and KnowledgeEdge
infrastructure without creating a duplicate graph engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.knowledge_consolidation.models import MemoryEntity, MemoryStatus
from app.knowledge_graph.models import EdgeModel, NodeModel

logger = logging.getLogger("kairo.knowledge_consolidation.graph_bridge")

VALID_GRAPH_RELATIONS = {
    "SUPPORTS",
    "CONTRADICTS",
    "SUPERSEDES",
    "DERIVED_FROM",
    "DEPENDS_ON",
    "RELATED_TO",
    "TEMPORALLY_PRECEDES",
    "CAUSES",
    "RESULTS_IN",
    "APPLIES_TO",
}


class KnowledgeGraphBridge:
    """Synchronizes consolidated memory entities and relational edges with kg_nodes & kg_edges."""

    def sync_memory_node(
        self,
        memory: MemoryEntity,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Project a memory entity into a knowledge graph node."""
        node_payload = {
            "id": f"node_{memory.memory_id}",
            "canonical_name": memory.content[:128],
            "node_type": memory.type.value,
            "confidence": memory.confidence,
            "status": memory.status.value,
            "scope": memory.sensitivity.value,
            "user_id": memory.user_id,
            "project_id": memory.project_id,
            "metadata": {
                "memory_id": memory.memory_id,
                "certainty": memory.certainty.value,
                "freshness": memory.freshness,
                "volatility": memory.volatility.value,
            },
        }

        if db is not None:
            try:
                existing = db.query(NodeModel).filter(NodeModel.id == node_payload["id"]).first()
                if existing:
                    existing.canonical_name = node_payload["canonical_name"]
                    existing.confidence = node_payload["confidence"]
                    existing.status = node_payload["status"]
                    existing.metadata_json = node_payload["metadata"]
                else:
                    new_node = NodeModel(
                        id=node_payload["id"],
                        canonical_name=node_payload["canonical_name"],
                        node_type=node_payload["node_type"],
                        confidence=node_payload["confidence"],
                        status=node_payload["status"],
                        scope=node_payload["scope"],
                        user_id=node_payload["user_id"],
                        project_id=node_payload["project_id"],
                        metadata_json=node_payload["metadata"],
                        provenance_json={"memory_id": memory.memory_id},
                    )
                    db.add(new_node)
                db.flush()
            except Exception as exc:
                logger.warning("Failed to sync KG node for memory '%s': %s", memory.memory_id, exc)

        return node_payload

    def create_relation_edge(
        self,
        source_memory_id: str,
        relationship: str,
        target_memory_id: str,
        confidence: float = 1.0,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Create a typed edge between two memory entities in the knowledge graph."""
        rel_clean = relationship.upper()
        if rel_clean not in VALID_GRAPH_RELATIONS:
            rel_clean = "RELATED_TO"

        edge_payload = {
            "source_node_id": f"node_{source_memory_id}",
            "relationship": rel_clean,
            "target_node_id": f"node_{target_memory_id}",
            "confidence": confidence,
        }

        if db is not None:
            try:
                new_edge = EdgeModel(
                    source_node_id=edge_payload["source_node_id"],
                    relationship=edge_payload["relationship"],
                    target_node_id=edge_payload["target_node_id"],
                    confidence=confidence,
                    user_id="default_user",
                    provenance_json={"synced_from": "knowledge_consolidation"},
                )
                db.add(new_edge)
                db.flush()
            except Exception as exc:
                logger.warning("Failed to sync KG edge (%s -> %s): %s", source_memory_id, target_memory_id, exc)

        return edge_payload

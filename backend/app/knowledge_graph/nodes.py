"""Node management, indexing, canonicalization, and alias handling for the Knowledge Graph."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set
import uuid

from app.knowledge_graph.schemas import (
    KnowledgeNodeSchema,
    NodeType,
    ScopeType,
)


class NodeValidationError(Exception):
    """Raised when node integrity or validation fails."""
    pass


class NodeManager:
    """Manages knowledge graph nodes, alias indexes, and scope enforcement."""

    def __init__(self) -> None:
        # node_id -> KnowledgeNodeSchema
        self._nodes: Dict[str, KnowledgeNodeSchema] = {}
        # alias/name (lowercase) -> node_id
        self._name_index: Dict[str, str] = {}

    def create_node(
        self,
        canonical_name: str,
        node_type: NodeType = NodeType.KNOWLEDGE,
        aliases: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        scope: ScopeType = ScopeType.PRIVATE,
        provenance: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        user_id: str = "default_user",
        project_id: Optional[str] = None,
        node_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> KnowledgeNodeSchema:
        clean_name = canonical_name.strip()
        if not clean_name:
            raise NodeValidationError("Canonical name cannot be empty.")

        n_id = node_id or str(uuid.uuid4())
        alias_list = [a.strip() for a in (aliases or []) if a.strip()]
        ts = created_at or datetime.now(UTC)

        node = KnowledgeNodeSchema(
            node_id=n_id,
            node_type=node_type,
            canonical_name=clean_name,
            aliases=alias_list,
            metadata=metadata or {},
            scope=scope,
            provenance=provenance or {"source": "direct_creation"},
            confidence=min(max(confidence, 0.0), 1.0),
            status="ACTIVE",
            user_id=user_id,
            project_id=project_id,
            created_at=ts,
            updated_at=ts,
        )

        self._nodes[n_id] = node
        self._name_index[clean_name.lower()] = n_id
        for alias in alias_list:
            self._name_index[alias.lower()] = n_id

        return node

    def get_node(self, node_id: str) -> Optional[KnowledgeNodeSchema]:
        return self._nodes.get(node_id)

    def find_by_name(self, name_or_alias: str) -> Optional[KnowledgeNodeSchema]:
        nid = self._name_index.get(name_or_alias.strip().lower())
        if nid:
            return self._nodes.get(nid)
        return None

    def add_alias(self, node_id: str, alias: str) -> KnowledgeNodeSchema:
        node = self._nodes.get(node_id)
        if not node:
            raise NodeValidationError(f"Node '{node_id}' not found.")
        clean_alias = alias.strip()
        if clean_alias and clean_alias not in node.aliases:
            node.aliases.append(clean_alias)
            self._name_index[clean_alias.lower()] = node_id
            node.updated_at = datetime.now(UTC)
        return node

    def list_nodes(
        self,
        node_type: Optional[NodeType] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        scope: Optional[ScopeType] = None,
    ) -> List[KnowledgeNodeSchema]:
        results = [n for n in self._nodes.values() if n.status == "ACTIVE"]
        if node_type:
            results = [n for n in results if n.node_type == node_type]
        if user_id:
            results = [n for n in results if n.user_id == user_id]
        if project_id:
            results = [n for n in results if n.project_id == project_id]
        if scope:
            results = [n for n in results if n.scope == scope]
        return results

    def delete_node(self, node_id: str) -> bool:
        node = self._nodes.pop(node_id, None)
        if node:
            self._name_index.pop(node.canonical_name.lower(), None)
            for a in node.aliases:
                self._name_index.pop(a.lower(), None)
            return True
        return False

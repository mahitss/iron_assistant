"""Entity resolution, collision prevention, merge, and split operations with full provenance."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.knowledge_graph.nodes import NodeManager
from app.knowledge_graph.schemas import (
    KnowledgeNodeSchema,
    NodeType,
)


class EntityCollisionError(Exception):
    """Raised when an automated merge is attempted on collision-prone or ambiguous entities."""
    pass


class EntityResolver:
    """Resolves aliases to canonical entities, blocks premature auto-merging, and manages merges/splits."""

    def __init__(self, node_manager: NodeManager) -> None:
        self.node_manager = node_manager
        # merge/split lineage records: list of dicts
        self._lineage_records: List[Dict[str, Any]] = []

    def resolve_entity(
        self,
        name: str,
        expected_type: Optional[NodeType] = None,
        user_id: Optional[str] = None,
    ) -> Optional[KnowledgeNodeSchema]:
        """Resolves a raw name or alias to a canonical KnowledgeNodeSchema."""
        node = self.node_manager.find_by_name(name)
        if node:
            if expected_type and node.node_type != expected_type:
                return None
            if user_id and node.user_id != user_id and node.scope.value == "PRIVATE":
                return None
            return node
        return None

    def merge_entities(
        self,
        primary_node_id: str,
        secondary_node_id: str,
        authorized_by: str,
        confidence: float = 0.95,
    ) -> KnowledgeNodeSchema:
        """INVARIANTS 30, 31, 33: Merges secondary entity into primary entity.

        Requires high confidence (>= 0.9) or explicit user authorization.
        Records merge provenance to allow later splitting.
        """
        primary = self.node_manager.get_node(primary_node_id)
        if not primary:
            raise ValueError(f"Primary node '{primary_node_id}' not found.")

        secondary = self.node_manager.get_node(secondary_node_id)
        if not secondary:
            raise ValueError(f"Secondary node '{secondary_node_id}' not found.")

        # INVARIANT 30: Collision prevention: do not merge if types differ without explicit authorization
        if primary.node_type != secondary.node_type:
            raise EntityCollisionError(
                f"Cannot merge entity '{primary.canonical_name}' ({primary.node_type.value}) with '{secondary.canonical_name}' ({secondary.node_type.value}). Type mismatch."
            )

        if confidence < 0.9 and authorized_by != "user":
            raise EntityCollisionError(
                f"Automated merge rejected due to low confidence ({confidence:.2f} < 0.90). Explicit authorization required."
            )

        # Merge aliases and metadata
        for alias in [secondary.canonical_name] + secondary.aliases:
            if alias not in primary.aliases and alias.lower() != primary.canonical_name.lower():
                self.node_manager.add_alias(primary_node_id, alias)

        primary.metadata.update(secondary.metadata)
        secondary.status = "MERGED"

        # Record merge history
        record = {
            "record_id": str(uuid.uuid4()),
            "action": "MERGE",
            "primary_node_id": primary_node_id,
            "secondary_node_id": secondary_node_id,
            "secondary_snapshot": secondary.model_dump(),
            "authorized_by": authorized_by,
            "confidence": confidence,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._lineage_records.append(record)

        return primary

    def split_entity(
        self,
        primary_node_id: str,
        split_name: str,
        split_aliases: Optional[List[str]] = None,
        authorized_by: str = "user",
    ) -> KnowledgeNodeSchema:
        """INVARIANTS 32 & 34: Corrects an incorrect merge by splitting out an entity with provenance."""
        primary = self.node_manager.get_node(primary_node_id)
        if not primary:
            raise ValueError(f"Primary node '{primary_node_id}' not found.")

        # Remove split name and aliases from primary node
        all_to_remove = {split_name.lower()} | {a.lower() for a in (split_aliases or [])}
        primary.aliases = [a for a in primary.aliases if a.lower() not in all_to_remove]

        # Create new independent node
        new_node = self.node_manager.create_node(
            canonical_name=split_name,
            node_type=primary.node_type,
            aliases=split_aliases or [],
            scope=primary.scope,
            user_id=primary.user_id,
            project_id=primary.project_id,
            provenance={"source": "entity_split_correction", "split_from": primary_node_id},
        )

        record = {
            "record_id": str(uuid.uuid4()),
            "action": "SPLIT",
            "primary_node_id": primary_node_id,
            "new_node_id": new_node.node_id,
            "split_name": split_name,
            "authorized_by": authorized_by,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._lineage_records.append(record)

        return new_node

    def get_lineage(self, node_id: str) -> List[Dict[str, Any]]:
        return [
            r for r in self._lineage_records
            if r.get("primary_node_id") == node_id or r.get("secondary_node_id") == node_id or r.get("new_node_id") == node_id
        ]

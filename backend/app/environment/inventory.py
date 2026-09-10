"""Asset Inventory, Search, and Multi-Index Lookup (Task 54, Prompt #245)."""

from __future__ import annotations

from app.environment.schemas import EnvironmentNode, NodeType, ScopeType


class InventoryIndex:
    """Provides high-performance in-memory indexing and lookup over environment assets."""

    def __init__(self) -> None:
        self._by_id: dict[str, EnvironmentNode] = {}
        self._by_type: dict[NodeType, list[str]] = {}
        self._by_scope: dict[ScopeType, list[str]] = {}
        self._by_status: dict[str, list[str]] = {}

    def index_node(self, node: EnvironmentNode) -> None:
        """Indexes an EnvironmentNode across type, scope, and status."""
        self._by_id[node.node_id] = node

        # Type index
        if node.node_type not in self._by_type:
            self._by_type[node.node_type] = []
        if node.node_id not in self._by_type[node.node_type]:
            self._by_type[node.node_type].append(node.node_id)

        # Scope index
        if node.scope not in self._by_scope:
            self._by_scope[node.scope] = []
        if node.node_id not in self._by_scope[node.scope]:
            self._by_scope[node.scope].append(node.node_id)

        # Status index
        st = node.status.upper()
        if st not in self._by_status:
            self._by_status[st] = []
        if node.node_id not in self._by_status[st]:
            self._by_status[st].append(node.node_id)

    def query(
        self,
        node_type: NodeType | None = None,
        scope: ScopeType | None = None,
        status: str | None = None,
        search_query: str | None = None,
    ) -> list[EnvironmentNode]:
        """Searches indexed nodes by criteria."""
        candidate_ids = set(self._by_id.keys())

        if node_type and node_type in self._by_type:
            candidate_ids.intersection_update(self._by_type[node_type])
        elif node_type:
            return []

        if scope and scope in self._by_scope:
            candidate_ids.intersection_update(self._by_scope[scope])
        elif scope:
            return []

        if status and status.upper() in self._by_status:
            candidate_ids.intersection_update(self._by_status[status.upper()])
        elif status:
            return []

        results = [self._by_id[nid] for nid in candidate_ids]

        if search_query:
            sq = search_query.lower()
            results = [
                n for n in results
                if sq in n.display_name.lower() or sq in n.canonical_id.lower() or sq in n.node_id.lower()
            ]

        return results

"""Graph traversal service for navigating relationships across workspace entities."""

import logging
from collections import deque

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.knowledge.models import KnowledgeEdgeModel, KnowledgeNodeModel
from app.knowledge.schemas import KnowledgeEdgeResponse, KnowledgeGraphResponse, KnowledgeNodeResponse

logger = logging.getLogger("kairo.knowledge.graph")


class GraphTraversalService:
    """Bounded, multi-tenant graph traversal over Knowledge Nodes and Edges."""

    def __init__(
        self,
        max_depth: int | None = None,
        max_nodes: int | None = None,
        max_edges: int | None = None,
    ) -> None:
        settings = get_settings()
        self.max_depth = max_depth or settings.KAIRO_KNOWLEDGE_MAX_DEPTH
        self.max_nodes = max_nodes or settings.KAIRO_KNOWLEDGE_MAX_NODES
        self.max_edges = max_edges or settings.KAIRO_KNOWLEDGE_MAX_EDGES

    async def traverse_subgraph(
        self,
        session: AsyncSession,
        user_id: str,
        root_node_id: str,
        depth_limit: int | None = None,
    ) -> KnowledgeGraphResponse:
        """Traverse connected relationships starting from root_node_id within bounds.

        Strictly enforces user ownership and cycle detection.
        """
        effective_depth = min(depth_limit or self.max_depth, self.max_depth)

        # 1. Verify root node existence and ownership
        root_stmt = select(KnowledgeNodeModel).where(
            and_(
                KnowledgeNodeModel.id == root_node_id,
                KnowledgeNodeModel.user_id == user_id,
                KnowledgeNodeModel.status != "DELETED",
            )
        )
        root_res = await session.execute(root_stmt)
        root_node = root_res.scalar_one_or_none()
        if not root_node:
            raise ValueError(f"Root node '{root_node_id}' not found or access denied.")

        collected_nodes: dict[str, KnowledgeNodeModel] = {root_node.id: root_node}
        collected_edges: dict[str, KnowledgeEdgeModel] = {}

        # Queue items: (node_id, current_depth)
        queue: deque[tuple[str, int]] = deque([(root_node_id, 0)])
        visited_nodes: set[str] = {root_node_id}
        max_depth_reached = 0

        while queue and len(collected_nodes) < self.max_nodes and len(collected_edges) < self.max_edges:
            curr_node_id, curr_depth = queue.popleft()
            max_depth_reached = max(max_depth_reached, curr_depth)

            if curr_depth >= effective_depth:
                continue

            # Query outgoing edges
            out_stmt = select(KnowledgeEdgeModel).where(
                and_(
                    KnowledgeEdgeModel.user_id == user_id,
                    KnowledgeEdgeModel.source_node_id == curr_node_id,
                )
            )
            out_res = await session.execute(out_stmt)
            out_edges = list(out_res.scalars().all())

            # Query incoming edges
            in_stmt = select(KnowledgeEdgeModel).where(
                and_(
                    KnowledgeEdgeModel.user_id == user_id,
                    KnowledgeEdgeModel.target_node_id == curr_node_id,
                )
            )
            in_res = await session.execute(in_stmt)
            in_edges = list(in_res.scalars().all())

            all_adjacent_edges = out_edges + in_edges

            for edge in all_adjacent_edges:
                if len(collected_edges) >= self.max_edges:
                    break
                collected_edges[edge.id] = edge

                neighbor_id = (
                    edge.target_node_id if edge.source_node_id == curr_node_id else edge.source_node_id
                )

                if neighbor_id not in visited_nodes and len(collected_nodes) < self.max_nodes:
                    visited_nodes.add(neighbor_id)
                    # Fetch neighbor node
                    neighbor_stmt = select(KnowledgeNodeModel).where(
                        and_(
                            KnowledgeNodeModel.id == neighbor_id,
                            KnowledgeNodeModel.user_id == user_id,
                            KnowledgeNodeModel.status != "DELETED",
                        )
                    )
                    neighbor_res = await session.execute(neighbor_stmt)
                    neighbor_node = neighbor_res.scalar_one_or_none()
                    if neighbor_node:
                        collected_nodes[neighbor_node.id] = neighbor_node
                        queue.append((neighbor_id, curr_depth + 1))

        nodes_response = [KnowledgeNodeResponse.model_validate(n) for n in collected_nodes.values()]
        edges_response = [KnowledgeEdgeResponse.model_validate(e) for e in collected_edges.values()]

        return KnowledgeGraphResponse(
            root_node_id=root_node_id,
            nodes=nodes_response,
            edges=edges_response,
            depth_reached=max_depth_reached,
        )

    async def get_node_relationships(
        self,
        session: AsyncSession,
        user_id: str,
        node_id: str,
    ) -> list[KnowledgeEdgeResponse]:
        """Fetch all direct incoming and outgoing relationship edges for a single node."""
        stmt = select(KnowledgeEdgeModel).where(
            and_(
                KnowledgeEdgeModel.user_id == user_id,
                (KnowledgeEdgeModel.source_node_id == node_id)
                | (KnowledgeEdgeModel.target_node_id == node_id),
            )
        )
        res = await session.execute(stmt)
        edges = list(res.scalars().all())
        return [KnowledgeEdgeResponse.model_validate(e) for e in edges]

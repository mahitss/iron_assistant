"""Multi-factor ranking without popularity bias (INVARIANTS 86, 90, 197, 198)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import List
from app.knowledge_graph.schemas import KnowledgeNodeSchema


class GraphRanker:
    """Ranks candidate graph nodes by utility, relevance, and recency without degree-popularity bias."""

    @staticmethod
    def rank_nodes(
        candidates: List[KnowledgeNodeSchema],
        active_task_context: str = "",
        now: datetime | None = None,
    ) -> List[KnowledgeNodeSchema]:
        """INVARIANT 198: No popularity bias: node edge degree does not automatically inflate score."""
        current_time = now or datetime.now(UTC)
        context_words = set(active_task_context.lower().split())

        def score_node(node: KnowledgeNodeSchema) -> float:
            score = 0.0

            # 1. Direct relevance to active task context
            node_text = f"{node.canonical_name} {' '.join(node.aliases)}".lower()
            overlap = sum(1 for w in context_words if w in node_text)
            score += overlap * 25.0

            # 2. Confidence weight
            score += node.confidence * 20.0

            # 3. Recency factor (up to 20 points, decaying over 30 days)
            age_days = max((current_time - node.updated_at).total_seconds() / 86400.0, 0.0)
            recency_points = max(20.0 - (age_days * 0.5), 0.0)
            score += recency_points

            # 4. Scope bonus (project-specific matches given slight priority over generic global)
            if node.project_id:
                score += 5.0

            return score

        return sorted(candidates, key=score_node, reverse=True)

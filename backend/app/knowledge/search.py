"""Hybrid search engine combining lexical keyword matching, semantic vector similarity, and recency ranking."""

import hashlib
import json
import logging
import math
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.knowledge.models import KnowledgeNodeModel, KnowledgeSourceModel
from app.knowledge.schemas import KnowledgeSearchRequest, KnowledgeSearchResultItem
from app.memory.embeddings import DeterministicEmbeddingProvider, EmbeddingProvider

logger = logging.getLogger("kairo.knowledge.search")


class HybridSearchEngine:
    """Combines lexical keyword matching, semantic embeddings, recency, and metadata filtering.

    Provides deterministic, calibrated scoring and graceful degradation on embedding failures.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        redis_client: Any | None = None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.redis = redis_client
        self.cache_ttl = 300  # 5 minutes

    async def search(
        self,
        session: AsyncSession,
        user_id: str,
        request: KnowledgeSearchRequest,
    ) -> list[KnowledgeSearchResultItem]:
        """Perform hybrid search over user's knowledge nodes with multi-tenant isolation."""
        # 1. Check Redis Cache for exact query hash
        cache_key = self._build_cache_key(user_id, request)
        if self.redis is not None:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return [KnowledgeSearchResultItem.model_validate(item) for item in data]
            except Exception as exc:
                logger.debug("Knowledge cache read error: %s", exc)

        # 2. Extract query vector with graceful fallback
        query_vector = None
        try:
            query_vector = await self.embedding_provider.embed(request.query)
        except Exception as exc:
            logger.warning("Embedding generation failed, falling back to lexical search: %s", exc)

        # 3. Base Filters
        filters = [
            KnowledgeNodeModel.user_id == user_id,
            KnowledgeNodeModel.status != "DELETED",
        ]
        if request.project_id:
            filters.append(KnowledgeNodeModel.project_id == request.project_id)
        if request.type:
            filters.append(KnowledgeNodeModel.type == request.type.value)
        if request.date_from:
            filters.append(KnowledgeNodeModel.created_at >= request.date_from)
        if request.date_to:
            filters.append(KnowledgeNodeModel.created_at <= request.date_to)

        # 4. Lexical Search Candidate Extraction
        terms = [t.strip().lower() for t in request.query.split() if len(t.strip()) > 1]
        if terms:
            term_clauses = []
            for t in terms:
                pattern = f"%{t}%"
                term_clauses.append(
                    or_(
                        KnowledgeNodeModel.title.ilike(pattern),
                        KnowledgeNodeModel.summary.ilike(pattern),
                        KnowledgeNodeModel.content.ilike(pattern),
                    )
                )
            filters.append(or_(*term_clauses))

        stmt = select(KnowledgeNodeModel).where(and_(*filters)).limit(request.limit * 3)
        res = await session.execute(stmt)
        nodes = list(res.scalars().all())

        # If lexical search returned few nodes and we have query vector, also query vector candidates
        if len(nodes) < request.limit and query_vector:
            vec_stmt = (
                select(KnowledgeNodeModel)
                .where(
                    and_(
                        KnowledgeNodeModel.user_id == user_id,
                        KnowledgeNodeModel.status != "DELETED",
                    )
                )
                .limit(request.limit * 2)
            )
            vec_res = await session.execute(vec_stmt)
            for n in vec_res.scalars().all():
                if not any(existing.id == n.id for existing in nodes):
                    nodes.append(n)

        # 5. Fetch associated sources for provenance in batch
        source_ids = [n.source_id for n in nodes if n.source_id]
        sources_map: dict[str, KnowledgeSourceModel] = {}
        if source_ids:
            src_stmt = select(KnowledgeSourceModel).where(
                and_(
                    KnowledgeSourceModel.user_id == user_id,
                    KnowledgeSourceModel.source_id.in_(source_ids),
                )
            )
            src_res = await session.execute(src_stmt)
            for src in src_res.scalars().all():
                sources_map[src.source_id] = src

        # 6. Hybrid Scoring and Ranking
        scored_results: list[tuple[float, KnowledgeSearchResultItem]] = []
        now = datetime.now(UTC)

        for node in nodes:
            # A. Lexical Score (0.0 to 1.0)
            lex_score = self._compute_lexical_score(request.query, node.title, node.summary)

            # B. Vector Score (0.0 to 1.0)
            vec_score = 0.5  # Neutral default if no vector
            if query_vector is not None and node.embedding is not None:
                vec_score = self._cosine_similarity(query_vector, node.embedding)

            # C. Recency Decay (0.0 to 1.0, 90-day decay horizon)
            node_created = (
                node.created_at.replace(tzinfo=UTC) if node.created_at.tzinfo is None else node.created_at
            )
            age_days = max(0.0, (now - node_created).total_seconds() / 86400.0)
            recency_score = max(0.1, 1.0 - (age_days / 90.0))

            # D. Status Penalty (Superseded nodes rank lower)
            status_multiplier = 0.4 if node.status == "SUPERSEDED" else 1.0

            # Composite Score: 0.40 vector + 0.40 lexical + 0.20 recency
            final_score = (
                (0.40 * vec_score + 0.40 * lex_score + 0.20 * recency_score)
                * status_multiplier
                * node.confidence
            )

            src = sources_map.get(node.source_id)
            source_type = src.source_type if src else "SYSTEM_DERIVED"
            source_url = src.source_url if src else None

            # Generate human explanation
            explanation = None
            if node.project_id and request.project_id:
                explanation = f"Matched via project relevance and keyword overlap ({node.type})"
            elif node.status == "SUPERSEDED":
                explanation = "Historical record (superseded by newer decision)"
            else:
                explanation = f"Source: {source_type}"

            item = KnowledgeSearchResultItem(
                id=node.id,
                title=node.title,
                summary=node.summary,
                type=node.type,
                project_id=node.project_id,
                source_id=node.source_id,
                source_type=source_type,
                source_url=source_url,
                timestamp=node.created_at,
                relevance=round(final_score, 4),
                confidence=node.confidence,
                status=node.status,
                explanation=explanation,
            )
            scored_results.append((final_score, item))

        # 7. Deterministic Sorting
        scored_results.sort(key=lambda x: (x[0], x[1].timestamp), reverse=True)
        final_items = [item for _, item in scored_results[: request.limit]]

        # 8. Cache in Redis
        if self.redis is not None and final_items:
            try:
                dump = json.dumps([item.model_dump(mode="json") for item in final_items])
                await self.redis.setex(cache_key, self.cache_ttl, dump)
            except Exception as exc:
                logger.debug("Knowledge cache write error: %s", exc)

        return final_items

    async def invalidate_cache(self, user_id: str) -> None:
        """Invalidate cached knowledge searches for a user."""
        if self.redis is None:
            return
        try:
            pattern = f"kairo:knowledge:search:{user_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as exc:
            logger.debug("Failed invalidating knowledge search cache: %s", exc)

    def _build_cache_key(self, user_id: str, request: KnowledgeSearchRequest) -> str:
        raw = f"{user_id}:{request.query}:{request.project_id}:{request.type}:{request.source_type}:{request.limit}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"kairo:knowledge:search:{user_id}:{digest}"

    def _compute_lexical_score(self, query: str, title: str, summary: str) -> float:
        """Compute bounded lexical match score between query and node text."""
        q_tokens = set(query.lower().split())
        if not q_tokens:
            return 0.0

        title_lower = title.lower()
        summary_lower = summary.lower()

        # Exact phrase bonus
        if query.lower() in title_lower:
            return 1.0
        if query.lower() in summary_lower:
            return 0.85

        title_tokens = set(title_lower.split())
        summary_tokens = set(summary_lower.split())

        title_matches = len(q_tokens.intersection(title_tokens))
        summary_matches = len(q_tokens.intersection(summary_tokens))

        score = (title_matches * 0.6 + summary_matches * 0.4) / len(q_tokens)
        return min(1.0, max(0.0, score))

    def _cosine_similarity(self, vec_a: list[float], vec_b: Any) -> float:
        """Calculate cosine similarity between two vector lists."""
        try:
            # Handle pgvector Vector object if necessary
            list_b = list(vec_b) if hasattr(vec_b, "__iter__") else vec_b
            if not isinstance(list_b, list) or len(vec_a) != len(list_b):
                return 0.5

            dot = sum(a * b for a, b in zip(vec_a, list_b, strict=False))
            norm_a = math.sqrt(sum(a * a for a in vec_a))
            norm_b = math.sqrt(sum(b * b for b in list_b))

            if norm_a == 0.0 or norm_b == 0.0:
                return 0.5

            sim = dot / (norm_a * norm_b)
            # Normalize [-1.0, 1.0] to [0.0, 1.0]
            return max(0.0, min(1.0, (sim + 1.0) / 2.0))
        except Exception:
            return 0.5

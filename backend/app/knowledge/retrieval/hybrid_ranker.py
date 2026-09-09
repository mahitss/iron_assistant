"""Hybrid ranker combining BM25, Vector Search, RRF, trust weights, and freshness decay."""

import logging
import math
from datetime import datetime, timezone
from typing import Any

from app.knowledge.schemas import (
    FRESHNESS_DECAY,
    TRUST_WEIGHTS,
    DocumentChunk,
    FreshnessState,
    RetrievalPlan,
    RetrievalResult,
    TrustTier,
)

logger = logging.getLogger("kairo.knowledge.retrieval.hybrid_ranker")


class HybridRanker:
    """Combines dense and sparse search rankings using Reciprocal Rank Fusion (RRF) and contextual boosting."""

    def __init__(self, rrf_k: int = 60) -> None:
        self.rrf_k = rrf_k

    def fuse_and_rank(
        self,
        bm25_results: list[tuple[DocumentChunk, float]],
        vector_results: list[tuple[DocumentChunk, float]],
        plan: RetrievalPlan,
        code_matches: list[DocumentChunk] | None = None,
    ) -> list[RetrievalResult]:
        """Merge lexical, vector, and code results with RRF, trust weights, and freshness penalties."""
        code_matches = code_matches or []

        # Ranks mapping
        bm25_ranks: dict[str, int] = {chunk.id: rank for rank, (chunk, _) in enumerate(bm25_results, start=1)}
        bm25_scores: dict[str, float] = {chunk.id: score for chunk, score in bm25_results}

        vector_ranks: dict[str, int] = {chunk.id: rank for rank, (chunk, _) in enumerate(vector_results, start=1)}
        vector_scores: dict[str, float] = {chunk.id: score for chunk, score in vector_results}

        # Unique chunk set
        all_chunks: dict[str, DocumentChunk] = {}
        for chunk, _ in bm25_results:
            all_chunks[chunk.id] = chunk
        for chunk, _ in vector_results:
            all_chunks[chunk.id] = chunk
        for chunk in code_matches:
            all_chunks[chunk.id] = chunk

        final_results: list[RetrievalResult] = []

        now = datetime.now(timezone.utc)

        for chunk_id, chunk in all_chunks.items():
            # Calculate RRF score
            rrf_score = 0.0
            if chunk_id in bm25_ranks:
                rrf_score += plan.bm25_weight / (self.rrf_k + bm25_ranks[chunk_id])
            if chunk_id in vector_ranks:
                rrf_score += plan.vector_weight / (self.rrf_k + vector_ranks[chunk_id])

            # Code symbol boost if present
            code_boost = 0.0
            if any(c.id == chunk_id for c in code_matches):
                code_boost = plan.code_symbol_weight * 0.5
                rrf_score += code_boost

            # Apply Trust Tier weight
            trust_multiplier = TRUST_WEIGHTS.get(chunk.metadata.trust_tier, 1.0)

            # Apply Freshness decay
            freshness_multiplier = FRESHNESS_DECAY.get(chunk.metadata.freshness, 1.0)

            # Apply Recency exponential decay (if indexed_at is known)
            age_multiplier = 1.0
            if chunk.metadata.indexed_at:
                try:
                    delta_days = max(0.0, (now - chunk.metadata.indexed_at).total_seconds() / 86400.0)
                    age_multiplier = math.exp(-0.005 * delta_days)
                except Exception:
                    pass

            composite_score = rrf_score * trust_multiplier * freshness_multiplier * age_multiplier

            # Generate citation metadata
            citation_label, citation_url, line_range, time_range = self._build_citation(chunk)

            final_results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=composite_score,
                    bm25_score=bm25_scores.get(chunk_id),
                    vector_score=vector_scores.get(chunk_id),
                    rrf_score=rrf_score,
                    citation_label=citation_label,
                    citation_url=citation_url,
                    line_range=line_range,
                    time_range=time_range,
                )
            )

        # Sort descending by composite score
        final_results.sort(key=lambda r: r.score, reverse=True)
        return final_results[: plan.target_limit]

    def _build_citation(self, chunk: DocumentChunk) -> tuple[str, str | None, str | None, str | None]:
        meta = chunk.metadata
        label_parts = []

        if meta.file_path:
            label_parts.append(meta.file_path)
        elif meta.headings:
            label_parts.append(" > ".join(meta.headings[:2]))
        else:
            label_parts.append(f"Doc {meta.document_id}")

        line_range = None
        if meta.line_start and meta.line_end:
            line_range = f"L{meta.line_start}-L{meta.line_end}"
            label_parts.append(f"({line_range})")
        elif meta.page:
            label_parts.append(f"(p. {meta.page})")

        time_range = None
        if meta.start_time is not None and meta.end_time is not None:
            time_range = f"{meta.start_time:.1f}s - {meta.end_time:.1f}s"
            if meta.speaker:
                label_parts.append(f"[{time_range}, Speaker: {meta.speaker}]")
            else:
                label_parts.append(f"[{time_range}]")

        citation_label = " ".join(label_parts)
        citation_url = meta.source_url or (f"file:///{meta.file_path}" if meta.file_path else None)

        return citation_label, citation_url, line_range, time_range

"""Re-ranking engine providing cross-feature scoring, threshold cutoffs, and MMR diversity filtering."""

import logging
import re
from typing import Any

from app.knowledge.schemas import RetrievalResult

logger = logging.getLogger("kairo.knowledge.reranking")


class ReRanker:
    """Refines candidate retrieval results through deep lexical-semantic alignment and diversity filtering."""

    def __init__(self, diversity_penalty: float = 0.3, min_score_threshold: float = 0.0001) -> None:
        self.diversity_penalty = diversity_penalty
        self.min_score_threshold = min_score_threshold

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Rerank candidates using exact matches, phrase overlaps, and diversity deduplication."""
        if not candidates:
            return []

        q_terms = set(re.findall(r"\b\w+\b", query.lower()))
        q_phrase = query.strip().lower()

        scored: list[tuple[float, RetrievalResult]] = []

        for cand in candidates:
            text = cand.chunk.content.lower()
            meta = cand.chunk.metadata

            # 1. Base score from hybrid ranker
            boost = 1.0

            # 2. Exact phrase bonus
            if q_phrase in text:
                boost += 0.5

            # 3. Heading match bonus
            for h in meta.headings:
                if any(t in h.lower() for t in q_terms):
                    boost += 0.25
                    break

            # 4. Term coverage ratio
            doc_terms = set(re.findall(r"\b\w+\b", text))
            overlap = len(q_terms.intersection(doc_terms))
            coverage_ratio = overlap / max(1, len(q_terms))
            boost += coverage_ratio * 0.4

            final_score = cand.score * boost
            if final_score >= self.min_score_threshold:
                cand.score = final_score
                scored.append((final_score, cand))

        # Sort by updated score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Apply MMR-like diversity filter across sections/documents
        selected: list[RetrievalResult] = []
        seen_sections: dict[str, int] = {}

        for _, item in scored:
            sec_key = f"{item.chunk.metadata.document_id}:{item.chunk.metadata.section_id or 'main'}"
            times_seen = seen_sections.get(sec_key, 0)

            # Apply diversity penalty for repeated sections
            penalty = 1.0 - (times_seen * self.diversity_penalty)
            if penalty > 0.1:
                item.score = item.score * penalty
                selected.append(item)
                seen_sections[sec_key] = times_seen + 1

            if len(selected) >= top_k:
                break

        # Final sort
        selected.sort(key=lambda x: x.score, reverse=True)
        return selected

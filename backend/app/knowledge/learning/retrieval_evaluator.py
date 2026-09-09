"""Retrieval evaluation, feedback logging, and parameter auto-tuning."""

import logging
from collections import deque
from typing import Any

from app.knowledge.schemas import RetrievalMetrics, RetrievalResult

logger = logging.getLogger("kairo.knowledge.learning")


class RetrievalEvaluator:
    """Collects retrieval telemetry, computes ranking metrics, and adapts hybrid weights."""

    def __init__(self, history_size: int = 1000) -> None:
        self.history_size = history_size
        self._history: deque[dict[str, Any]] = deque(maxlen=history_size)
        self._bm25_weight: float = 0.4
        self._vector_weight: float = 0.6

    def record_event(
        self,
        query: str,
        results: list[RetrievalResult],
        grounding_score: float = 1.0,
        user_feedback: float | None = None,  # +1.0 for positive, -1.0 for negative
        relevant_chunk_ids: list[str] | None = None,
    ) -> None:
        """Record an evaluation event."""
        event = {
            "query": query,
            "results_count": len(results),
            "chunk_ids": [r.chunk.id for r in results],
            "grounding_score": grounding_score,
            "user_feedback": user_feedback,
            "relevant_chunk_ids": relevant_chunk_ids or [],
        }
        self._history.append(event)

        # Online adaptation if feedback is present
        if user_feedback is not None:
            self._adapt_from_feedback(user_feedback, results)

    def _adapt_from_feedback(self, feedback: float, results: list[RetrievalResult]) -> None:
        """Dynamically adjust BM25 vs Vector weights."""
        if not results:
            return

        top_item = results[0]
        bm25_val = top_item.bm25_score or 0.0
        vec_val = top_item.vector_score or 0.0

        if feedback > 0:
            # Reward whichever component contributed more to the positive result
            if bm25_val > vec_val:
                self._bm25_weight = min(0.8, self._bm25_weight + 0.02)
                self._vector_weight = max(0.2, self._vector_weight - 0.02)
            else:
                self._vector_weight = min(0.8, self._vector_weight + 0.02)
                self._bm25_weight = max(0.2, self._bm25_weight - 0.02)
        elif feedback < 0:
            # Penalize dominant component
            if bm25_val > vec_val:
                self._bm25_weight = max(0.2, self._bm25_weight - 0.02)
                self._vector_weight = min(0.8, self._vector_weight + 0.02)
            else:
                self._vector_weight = max(0.2, self._vector_weight - 0.02)
                self._bm25_weight = min(0.8, self._bm25_weight + 0.02)

    def get_current_weights(self) -> tuple[float, float]:
        """Return tuned (bm25_weight, vector_weight)."""
        return round(self._bm25_weight, 2), round(self._vector_weight, 2)

    def compute_metrics(self) -> RetrievalMetrics:
        """Compute aggregate evaluation metrics across recorded events."""
        if not self._history:
            return RetrievalMetrics(
                total_queries=0,
                mrr=0.0,
                hit_rate_at_1=0.0,
                hit_rate_at_3=0.0,
                hit_rate_at_5=0.0,
                avg_grounding_score=1.0,
                feedback_positive_ratio=0.0,
            )

        total = len(self._history)
        rr_sum = 0.0
        hits_1 = 0
        hits_3 = 0
        hits_5 = 0
        grounding_sum = 0.0
        feedback_pos = 0
        feedback_total = 0

        for ev in self._history:
            grounding_sum += ev["grounding_score"]
            relevant = set(ev["relevant_chunk_ids"])

            if ev["user_feedback"] is not None:
                feedback_total += 1
                if ev["user_feedback"] > 0:
                    feedback_pos += 1

            if relevant:
                found_rank = 0
                for rank, cid in enumerate(ev["chunk_ids"], start=1):
                    if cid in relevant:
                        found_rank = rank
                        break

                if found_rank > 0:
                    rr_sum += 1.0 / found_rank
                    if found_rank <= 1:
                        hits_1 += 1
                    if found_rank <= 3:
                        hits_3 += 1
                    if found_rank <= 5:
                        hits_5 += 1
            else:
                # Default assume top 1 was relevant if no explicit ground truth provided and feedback positive
                if ev["user_feedback"] and ev["user_feedback"] > 0:
                    rr_sum += 1.0
                    hits_1 += 1
                    hits_3 += 1
                    hits_5 += 1

        return RetrievalMetrics(
            total_queries=total,
            mrr=round(rr_sum / max(1, total), 3),
            hit_rate_at_1=round(hits_1 / max(1, total), 3),
            hit_rate_at_3=round(hits_3 / max(1, total), 3),
            hit_rate_at_5=round(hits_5 / max(1, total), 3),
            avg_grounding_score=round(grounding_sum / max(1, total), 3),
            feedback_positive_ratio=round(feedback_pos / max(1, feedback_total), 3) if feedback_total > 0 else 1.0,
        )

    def clear(self) -> None:
        self._history.clear()

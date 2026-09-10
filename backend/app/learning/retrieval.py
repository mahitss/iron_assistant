"""Adaptive context retrieval optimization based on execution feedback (INVARIANTS 145-146)."""

from __future__ import annotations

from typing import Any


class AdaptiveRetrievalEngine:
    """Dynamically adjusts retrieval weights and ranking heuristics based on outcome feedback."""

    def __init__(self) -> None:
        # source_type -> float weight multiplier
        self._source_weights: dict[str, float] = {
            "code_repository": 1.0,
            "project_documentation": 1.0,
            "episodic_memory": 0.9,
            "knowledge_fabric": 0.95,
            "web_external": 0.6,
        }

    def record_retrieval_feedback(
        self,
        retrieved_source: str,
        was_relevant: bool,
        task_succeeded: bool,
        user_corrected: bool = False,
    ) -> float:
        """INVARIANT 146: Updates source weights based on relevance, user correction, and task outcome."""
        current_weight = self._source_weights.get(retrieved_source, 1.0)

        if user_corrected:
            # Strong penalty if retrieved context misled the user or required correction
            new_weight = max(current_weight - 0.15, 0.2)
        elif was_relevant and task_succeeded:
            # Positive boost for relevant and successful retrieval
            new_weight = min(current_weight + 0.05, 1.5)
        elif not was_relevant:
            # Mild dampening if retrieved context was irrelevant
            new_weight = max(current_weight - 0.05, 0.3)
        else:
            new_weight = current_weight

        self._source_weights[retrieved_source] = round(new_weight, 3)
        return self._source_weights[retrieved_source]

    def get_source_weights(self) -> dict[str, float]:
        return dict(self._source_weights)

    def apply_ranking_weights(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Applies adaptive weights to retrieved candidates."""
        scored = []
        for item in items:
            source = item.get("source", "knowledge_fabric")
            base_score = item.get("score", 0.5)
            weight = self._source_weights.get(source, 1.0)
            item_copy = dict(item)
            item_copy["adapted_score"] = round(base_score * weight, 3)
            scored.append(item_copy)

        scored.sort(key=lambda x: x["adapted_score"], reverse=True)
        return scored

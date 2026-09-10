"""Bounded behavioral adaptation without runtime model weight modification (INVARIANTS 80-84, 91)."""

from __future__ import annotations

from typing import Any
from app.learning.schemas import AdaptationType


class ModelWeightModificationError(Exception):
    """Raised if an attempt is made to modify foundation model weights during runtime learning."""
    pass


class BehaviorAdaptationEngine:
    """Manages bounded adaptations in routing, retrieval, planning heuristics, draft formatting, and tool selection."""

    def __init__(self) -> None:
        # adaptation_key -> config dict
        self._active_adaptations: dict[str, dict[str, Any]] = {}
        self._adaptation_history: list[dict[str, Any]] = []

    def apply_adaptation(
        self,
        adaptation_type: AdaptationType,
        target_component: str,
        adaptation_payload: dict[str, Any],
        is_runtime_call: bool = True,
    ) -> dict[str, Any]:
        """INVARIANT 80 & 81: Applies bounded adaptation.
        Strictly forbids foundation model weight modifications at runtime.
        """
        # INVARIANT 81: Check for weights tampering
        if "weights" in adaptation_payload or "model_weights" in adaptation_payload:
            raise ModelWeightModificationError(
                "INVARIANT 81: Foundation model weights cannot be modified during runtime learning. "
                "Model fine-tuning must follow governed offline CI/CD pipelines."
            )

        key = f"{adaptation_type.value}:{target_component}"
        prior_state = self._active_adaptations.get(key)

        record = {
            "key": key,
            "adaptation_type": adaptation_type.value,
            "target_component": target_component,
            "payload": adaptation_payload,
            "prior_state": prior_state,
        }
        self._active_adaptations[key] = adaptation_payload
        self._adaptation_history.append(record)
        return record

    def rollback_adaptation(self, adaptation_type: AdaptationType, target_component: str) -> bool:
        """INVARIANT 91: Learned behavior must be completely reversible."""
        key = f"{adaptation_type.value}:{target_component}"
        if key in self._active_adaptations:
            del self._active_adaptations[key]
            return True
        return False

    def get_adaptation(self, adaptation_type: AdaptationType, target_component: str) -> dict[str, Any] | None:
        key = f"{adaptation_type.value}:{target_component}"
        return self._active_adaptations.get(key)

    def list_active_adaptations(self) -> dict[str, dict[str, Any]]:
        return dict(self._active_adaptations)

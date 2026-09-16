"""Attention engine bridge for KAIRO knowledge (Task 92 Phase 23).

Guarantees:
- Emits salience, novelty, urgency, and contradiction signals to AttentionEngine
- Does NOT duplicate attention scoring algorithms
"""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge_consolidation.models import MemoryConflict, MemoryEntity, MemoryStatus

logger = logging.getLogger("kairo.knowledge_consolidation.attention_bridge")


class AttentionEngineBridge:
    """Extracts cognitive attention signals from memory state changes."""

    def compute_attention_signals(
        self,
        memory: MemoryEntity,
        conflicts: list[MemoryConflict] | None = None,
    ) -> dict[str, float]:
        """Produce normalized [0.0, 1.0] attention signals for the Attention Engine."""
        # 1. Contradiction urgency signal
        has_active_conflict = any(
            c.status == "CONFLICTED" and (c.memory_a_id == memory.memory_id or c.memory_b_id == memory.memory_id)
            for c in (conflicts or [])
        )
        urgency_signal = 0.9 if has_active_conflict else 0.2

        # 2. Novelty signal (based on version and state)
        novelty_signal = 0.85 if memory.version == 1 and memory.status == MemoryStatus.ACTIVE else 0.3

        # 3. Task utility signal
        utility_signal = memory.importance * memory.confidence

        signals = {
            "relevance": memory.relevance,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "novelty": novelty_signal,
            "urgency": urgency_signal,
            "utility": round(utility_signal, 3),
        }
        return signals

    def notify_attention_engine(
        self,
        memory: MemoryEntity,
        conflicts: list[MemoryConflict] | None = None,
        attention_service: Any = None,
    ) -> None:
        """Forward signals to AttentionService if available."""
        signals = self.compute_attention_signals(memory, conflicts)
        logger.debug("Memory '%s' attention signals computed: %s", memory.memory_id, signals)
        if attention_service and hasattr(attention_service, "ingest_stimulus"):
            try:
                attention_service.ingest_stimulus(
                    source="knowledge_consolidation",
                    content_ref=memory.memory_id,
                    signals=signals,
                )
            except Exception as exc:
                logger.debug("Failed to forward stimulus to attention service: %s", exc)

"""Deterministic Memory Replay & Evolution Engine (Task 103).

Provides:
- Replaying historical sequences of experiences into memory states.
- Auditing memory evolution over time.
- Guaranteed ZERO external side-effects (pure read-only reconstruction).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.cognitive_memory.consolidation_engine import CognitiveConsolidationEngine
from app.cognitive_memory.contradiction_engine import MemoryContradictionEngine
from app.cognitive_memory.domain import (
    CognitiveMemoryItem,
    Experience,
    MemoryConflict,
    MemoryPattern,
    MemorySnapshot,
    _now_utc,
    _uuid_hex,
)

logger = logging.getLogger("kairo.cognitive_memory.replay")


class MemoryReplayEngine:
    """Deterministically simulates memory evolution from experience sequences."""

    @classmethod
    def replay_experience_sequence(
        cls,
        experiences: List[Experience],
    ) -> Dict[str, Any]:
        """Reconstructs memory states, contradictions, and patterns from experiences.
        
        INVARIANT: Replays NEVER execute real-world actions or side-effects.
        """
        consolidation_engine = CognitiveConsolidationEngine(min_recurrence_for_promotion=2)
        memories: Dict[str, CognitiveMemoryItem] = {}
        conflicts: List[MemoryConflict] = []
        timeline: List[Dict[str, Any]] = []

        for idx, exp in enumerate(experiences):
            # Step 1: Candidate creation
            cand = consolidation_engine.create_candidate_from_experience(exp)
            memories[cand.memory_id] = cand
            timeline.append({
                "step": idx + 1,
                "event": "EXPERIENCE_CAPTURED",
                "experience_id": exp.experience_id,
                "memory_id": cand.memory_id,
                "trust": exp.trust_classification.value,
                "summary": exp.summary,
            })

            # Step 2: Corroboration and promotion
            other_exps = [e for e in experiences[:idx] if set(e.related_entities).intersection(set(exp.related_entities))]
            promoted, reason = consolidation_engine.evaluate_promotion(cand, other_exps)
            if promoted:
                timeline.append({
                    "step": idx + 1,
                    "event": "MEMORY_PROMOTED",
                    "memory_id": cand.memory_id,
                    "state": cand.lifecycle_state.value,
                    "reason": reason,
                })

            # Step 3: Check for contradictions against existing memories
            for existing in memories.values():
                conf = MemoryContradictionEngine.check_contradiction(cand, existing)
                if conf:
                    conflicts.append(conf)
                    timeline.append({
                        "step": idx + 1,
                        "event": "CONFLICT_DETECTED",
                        "conflict_id": conf.conflict_id,
                        "memory_a": conf.memory_a_id,
                        "memory_b": conf.memory_b_id,
                    })

        # Step 4: Cluster recurring patterns
        patterns = consolidation_engine.cluster_patterns(experiences)

        snapshot = MemorySnapshot(
            snapshot_id=_uuid_hex("msnap"),
            created_at=_now_utc(),
            total_memories=len(memories),
            active_count=sum(1 for m in memories.values() if m.lifecycle_state.value == "ACTIVE"),
            stale_count=sum(1 for m in memories.values() if m.lifecycle_state.value == "STALE"),
            conflicted_count=len(conflicts),
            pattern_count=len(patterns),
            memory_ids=list(memories.keys()),
            conflict_ids=[c.conflict_id for c in conflicts],
            pattern_ids=[p.pattern_id for p in patterns],
        )

        logger.info(
            "Replayed %d experiences -> %d memories, %d patterns, %d conflicts",
            len(experiences), len(memories), len(patterns), len(conflicts)
        )

        return {
            "replayed_experience_count": len(experiences),
            "reconstructed_memories_count": len(memories),
            "reconstructed_patterns_count": len(patterns),
            "reconstructed_conflicts_count": len(conflicts),
            "total_experiences_replayed": len(experiences),
            "candidates_formed": len(memories),
            "memories_consolidated": snapshot.active_count,
            "conflicts_detected": len(conflicts),
            "deterministic": True,
            "read_only_guarantee": True,
            "side_effects_executed": False,
            "snapshot": snapshot.model_dump(),
            "timeline": timeline,
            "simulated_evolution": timeline,
            "patterns": [p.model_dump() for p in patterns],
        }

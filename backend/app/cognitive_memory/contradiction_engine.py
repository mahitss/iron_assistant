"""Memory Contradiction & World-State Reconciliation Engine (Task 103).

Enforces:
- Contradiction detection preserving dialectic tension.
- Current World-State Primacy: When memory conflicts with live world observation,
  current world-state wins unconditionally for operational truth.
- Explicit user corrections supersede prior memory with full version lineage.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.cognitive_memory.domain import (
    CognitiveMemoryItem,
    ExperienceTrust,
    FreshnessState,
    MemoryConflict,
    MemoryLifecycleState,
    _now_utc,
    _uuid_hex,
)
from app.world_state.reconciliation_engine import get_world_state_reconciliation_engine

logger = logging.getLogger("kairo.cognitive_memory.contradiction")


class MemoryContradictionEngine:
    """Detects opposing memory claims, creates conflict records, and enforces world-state primacy."""

    @classmethod
    def check_contradiction(
        cls,
        mem_a: CognitiveMemoryItem,
        mem_b: CognitiveMemoryItem,
    ) -> Optional[MemoryConflict]:
        """Detects if two memories within the same scope make contradictory assertions."""
        if mem_a.memory_id == mem_b.memory_id:
            return None
        if mem_a.scope != mem_b.scope:
            return None  # Scoped isolation; different projects/scopes don't automatically contradict

        # Check for overlapping entity with divergent claims
        common_entities = set(mem_a.related_entities).intersection(set(mem_b.related_entities))
        if not common_entities:
            return None

        # Check structured key divergence or opposing content
        contradiction_detected = False
        details: Dict[str, Any] = {}

        for k, v_a in mem_a.structured_data.items():
            if k in mem_b.structured_data:
                v_b = mem_b.structured_data[k]
                if v_a != v_b:
                    contradiction_detected = True
                    details[k] = {"claim_a": v_a, "claim_b": v_b}

        if contradiction_detected:
            ent = list(common_entities)[0] if common_entities else "SYSTEM"
            disc_sum = f"Contradiction on {ent}: {list(details.keys())} mismatch {details}"
            conflict = MemoryConflict(
                conflict_id=_uuid_hex("mconf"),
                memory_a_id=mem_a.memory_id,
                memory_b_id=mem_b.memory_id,
                memory_a_claim=mem_a.content,
                memory_b_claim=mem_b.content,
                scope=mem_a.scope,
                status="ACTIVE",
                entity_reference=ent,
                discrepancy_summary=disc_sum,
                evidence=details,
            )
            logger.warning(
                "Memory conflict detected between %s and %s over %s",
                mem_a.memory_id, mem_b.memory_id, details
            )
            return conflict

        return None

    @classmethod
    def reconcile_with_world_state(
        cls,
        memory: CognitiveMemoryItem,
        target_entity_id: str,
        attribute_name: str,
        current_world_value: Optional[Any] = None,
    ) -> Tuple[FreshnessState, Optional[str]]:
        """Reconciles a historical memory against empirical current World-State (Task 98).
        
        INVARIANT: Current World-State Wins!
        Historical memory cannot override current verified sensor/environment observations.
        """
        try:
            if current_world_value is not None:
                empirical_value = current_world_value
            else:
                world_engine = get_world_state_reconciliation_engine()
                entity = world_engine.get_entity(target_entity_id)
                if not entity:
                    return FreshnessState.UNKNOWN, "Target entity not registered in current world state."

                attr_record = entity.attributes.get(attribute_name)
                if not attr_record:
                    return FreshnessState.UNKNOWN, f"Attribute '{attribute_name}' not tracked in world state."

                empirical_value = attr_record.value
            memory_value = memory.structured_data.get(attribute_name)

            if memory_value is not None and memory_value != empirical_value:
                # Discrepancy: Memory claims old value, reality has new value!
                memory.freshness = FreshnessState.STALE
                memory.lifecycle_state = MemoryLifecycleState.CONFLICTED
                msg = (
                    f"World-State Overrule: Memory asserts '{attribute_name}={memory_value}', "
                    f"but live World-State observes '{empirical_value}'. Memory marked STALE."
                )
                logger.info(msg)
                return FreshnessState.STALE, msg

            memory.freshness = FreshnessState.CURRENT
            memory.last_verified_at = _now_utc()
            return FreshnessState.CURRENT, "Memory consistent with current empirical world-state."

        except Exception as exc:
            logger.error("World-state reconciliation error: %s", exc)
            return FreshnessState.UNKNOWN, str(exc)

    @classmethod
    def apply_user_correction(
        cls,
        old_memory: CognitiveMemoryItem,
        new_content: str,
        new_facts: Optional[Dict[str, Any]] = None,
        reason: str = "User explicit correction",
    ) -> CognitiveMemoryItem:
        """Applies an explicit user correction by superseding the old memory and producing v+1."""
        new_mem = CognitiveMemoryItem(
            memory_id=_uuid_hex("mem"),
            memory_type=old_memory.memory_type,
            lifecycle_state=MemoryLifecycleState.ACTIVE,
            scope=old_memory.scope,
            scope_id=old_memory.scope_id,
            content=new_content,
            structured_data=new_facts or old_memory.structured_data,
            confidence=0.98,
            importance=max(old_memory.importance, 0.8),
            freshness=FreshnessState.CURRENT,
            trust_classification=ExperienceTrust.USER_CONFIRMED,
            version=old_memory.version + 1,
            supersedes=old_memory.memory_id,
            related_entities=old_memory.related_entities,
            preconditions=old_memory.preconditions,
            procedure_steps=old_memory.procedure_steps,
            verification_criteria=old_memory.verification_criteria,
        )

        old_memory.lifecycle_state = MemoryLifecycleState.SUPERSEDED
        old_memory.superseded_by = new_mem.memory_id
        old_memory.freshness = FreshnessState.STALE
        old_memory.updated_at = _now_utc()

        logger.info(
            "User correction applied: Memory %s superseded by %s (v%d)",
            old_memory.memory_id, new_mem.memory_id, new_mem.version
        )
        return new_mem

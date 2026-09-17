"""Evidence, Alignment & Belief Integration Engine for Task 108.

Implements:
- Section 16: Intent Evidence (provenance-backed evidence from message, dialogue, memory, beliefs).
- Section 17: Context Integration (Task 93: CURRENT, HISTORICAL, ASSUMED, UNKNOWN).
- Section 18: Memory Integration (Task 103: memory informs interpretation, but NEVER overrides current explicit instruction).
- Section 19: Belief Integration (Task 107: integrates belief arbitration; uncertainty remains UNKNOWN).
- Section 43: Multi-Source Intent provenance.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.intent.domain import (
    EpistemicStatus,
    Intent,
    IntentEvidence,
    generate_id,
    utc_now,
)

logger = logging.getLogger("kairo.intent.evidence_alignment")


class EvidenceAndAlignmentEngine:
    """Aggregates multi-source evidence and aligns intent with memory and beliefs."""

    @classmethod
    def collect_evidence(
        cls,
        intent: Intent,
        raw_text: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        memory_records: Optional[List[Dict[str, Any]]] = None,
        belief_records: Optional[List[Dict[str, Any]]] = None,
    ) -> List[IntentEvidence]:
        """Collects provenance-backed evidence items for an intent."""
        evidence_items: List[IntentEvidence] = []

        # 1. Primary explicit instruction evidence
        evidence_items.append(IntentEvidence(
            evidence_id=generate_id("iev"),
            intent_id=intent.intent_id,
            source_type="CURRENT_MESSAGE",
            source_ref=f"user_raw_text:{len(raw_text)}chars",
            content=raw_text,
            reliability=1.0,
            created_at=utc_now(),
        ))

        # 2. Conversation context evidence
        if conversation_history:
            recent_turns = conversation_history[-3:]
            evidence_items.append(IntentEvidence(
                evidence_id=generate_id("iev"),
                intent_id=intent.intent_id,
                source_type="CONVERSATION_CONTEXT",
                source_ref=f"dialogue_history:{len(recent_turns)}_turns",
                content=f"Context from last {len(recent_turns)} turns incorporated.",
                reliability=0.85,
                created_at=utc_now(),
            ))

        # 3. Lifelong memory (Task 103)
        if memory_records:
            evidence_items.append(IntentEvidence(
                evidence_id=generate_id("iev"),
                intent_id=intent.intent_id,
                source_type="MEMORY",
                source_ref=f"task103_lifelong_memory:{len(memory_records)}_items",
                content="Historical preferences and project terminology referenced as advisory context.",
                reliability=0.75,
                created_at=utc_now(),
            ))

        # 4. Belief Engine (Task 107)
        if belief_records:
            evidence_items.append(IntentEvidence(
                evidence_id=generate_id("iev"),
                intent_id=intent.intent_id,
                source_type="BELIEFS",
                source_ref=f"task107_beliefs:{len(belief_records)}_items",
                content="Verified epistemic beliefs used for fact and target grounding.",
                reliability=0.9,
                created_at=utc_now(),
            ))

        return evidence_items

    @classmethod
    def reconcile_memory_vs_current(
        cls,
        current_directive: str,
        historical_preference: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Enforces Rule 18: Current explicit user instruction ALWAYS beats historical memory.
        
        Returns:
            (winning_instruction, reason)
        """
        if not historical_preference:
            return current_directive, "No historical preference conflict."

        logger.info("Reconciling current instruction ('%s') vs historical memory ('%s'). Current instruction wins.",
                    current_directive, historical_preference)
        return current_directive, f"Current explicit instruction takes precedence over historical preference '{historical_preference}'."

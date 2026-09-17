"""Consolidation, Promotion & Lifelong Learning Engine (Task 103).

Coordinates:
- Aggregating experiences into Candidate Memories.
- Enforcing evidence-based promotion thresholds.
- Memory Poisoning Defense: untrusted input cannot become trusted truth via frequency alone.
- Clustering recurring experiences into high-level MemoryPattern abstractions.
- Non-destructive evolution with preserved provenance.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.cognitive_memory.domain import (
    CognitiveMemoryItem,
    Experience,
    ExperienceTrust,
    FreshnessState,
    MemoryLifecycleState,
    MemoryPattern,
    MemoryScope,
    MemoryType,
    _now_utc,
    _uuid_hex,
)

logger = logging.getLogger("kairo.cognitive_memory.consolidation")


class CognitiveConsolidationEngine:
    """Manages evidence accumulation, candidate promotion, and pattern extraction."""

    def __init__(self, min_recurrence_for_promotion: int = 2) -> None:
        self.min_recurrence = min_recurrence_for_promotion

    def create_candidate_from_experience(self, exp: Experience) -> CognitiveMemoryItem:
        """Converts an initial experience into an unverified Candidate Memory."""
        # Map source to appropriate memory type
        m_type = MemoryType.EPISODIC
        if "procedure" in exp.summary.lower() or "recovery" in exp.summary.lower():
            m_type = MemoryType.PROCEDURAL
        elif exp.source_type.value in ("USER_FEEDBACK", "USER_CORRECTION"):
            m_type = MemoryType.PREFERENCE
        elif "failure" in exp.summary.lower() or exp.outcome == "FAILURE":
            m_type = MemoryType.FAILURE
        elif "capability" in exp.summary.lower():
            m_type = MemoryType.CAPABILITY

        decay_days = 90.0 if m_type == MemoryType.PROCEDURAL else (7.0 if m_type == MemoryType.ENVIRONMENTAL else 30.0)

        # Procedural extraction
        preconditions = exp.structured_facts.get("preconditions", [])
        steps = exp.structured_facts.get("steps", [])
        criteria = exp.structured_facts.get("verification_criteria", [])

        candidate = CognitiveMemoryItem(
            memory_id=_uuid_hex("mem"),
            memory_type=m_type,
            lifecycle_state=MemoryLifecycleState.CANDIDATE,
            scope=exp.scope,
            scope_id=exp.metadata.get("scope_id") if exp.metadata else None,
            content=exp.summary,
            structured_data=exp.structured_facts,
            confidence=exp.confidence * 0.75,  # Unverified candidate discount
            confidence_evidence="Single operational occurrence (unverified candidate)",
            importance=exp.importance,
            freshness=FreshnessState.CURRENT,
            trust_classification=exp.trust_classification,
            observed_at=exp.occurred_at,
            decay_rate_days=decay_days,
            source_experience_ids=[exp.experience_id],
            evidence_experience_ids=[exp.experience_id],
            related_entities=exp.related_entities,
            preconditions=preconditions,
            procedure_steps=steps,
            expected_outcome=exp.outcome,
            verification_criteria=criteria,
            verification_references=exp.verification_references,
            metadata=dict(exp.metadata) if exp.metadata else {},
        )
        return candidate

    def evaluate_promotion(
        self,
        memory: CognitiveMemoryItem,
        corroborating_experiences: List[Experience],
    ) -> Tuple[bool, str]:
        """Evaluates whether a candidate memory meets rigorous empirical promotion criteria.
        
        Poisoning Defense Invariant:
        Untrusted inputs (EXTERNAL_UNTRUSTED) CAN NEVER be promoted to VERIFIED or ACTIVE
        state merely through repetition.
        """
        # 1. Poisoning Defense check
        if memory.trust_classification == ExperienceTrust.EXTERNAL_UNTRUSTED:
            memory.confidence_evidence = "UNTRUSTED: Untrusted external sources cannot achieve verified memory status."
            return False, "Promotion denied: Untrusted external sources cannot achieve verified memory status."

        # 2. Check if any corroborating experience is from a confirmed user source
        user_confirmed = any(
            e.trust_classification == ExperienceTrust.USER_CONFIRMED for e in corroborating_experiences
        )
        if user_confirmed:
            memory.lifecycle_state = MemoryLifecycleState.ACTIVE
            memory.confidence = 0.95
            memory.trust_classification = ExperienceTrust.USER_CONFIRMED
            memory.updated_at = _now_utc()
            return True, "Promoted to ACTIVE via explicit user confirmation."

        # 3. Check empirical recurrence and verification threshold
        distinct_corroborating = [
            e for e in corroborating_experiences
            if e.experience_id not in memory.source_experience_ids
        ]
        verified_count = sum(
            1 for e in distinct_corroborating
            if e.trust_classification in (ExperienceTrust.ACTION_VERIFIED, ExperienceTrust.WORLD_STATE_VERIFIED, ExperienceTrust.SYSTEM_VERIFIED)
        )

        total_experiences = len(memory.source_experience_ids) + len(distinct_corroborating)

        if verified_count >= 1 and total_experiences >= self.min_recurrence:
            memory.lifecycle_state = MemoryLifecycleState.ACTIVE
            # Evidence-backed confidence calculation (not manufactured)
            memory.confidence = min(0.92, 0.70 + (0.05 * verified_count))
            memory.trust_classification = ExperienceTrust.SYSTEM_VERIFIED
            memory.updated_at = _now_utc()
            return True, f"Promoted to ACTIVE via {verified_count} verified empirical corroborations."

        return False, f"Insufficient evidence: {verified_count} verified observations out of {total_experiences} required."

    def cluster_patterns(
        self,
        experiences: List[Experience],
        scope: MemoryScope = MemoryScope.PROJECT,
    ) -> List[MemoryPattern]:
        """Identifies recurring themes across experiences and generates MemoryPattern records."""
        groups: Dict[str, List[Experience]] = defaultdict(list)

        for exp in experiences:
            # Group by outcome + primary entity/source
            primary_entity = exp.related_entities[0] if exp.related_entities else exp.source_type.value
            key = f"{exp.outcome}:{primary_entity}:{exp.scope.value}"
            groups[key].append(exp)

        patterns: List[MemoryPattern] = []
        for key, exps in groups.items():
            if len(exps) >= self.min_recurrence:
                outcome, entity, sc = key.split(":", 2)
                pat_type = MemoryType.FAILURE if outcome == "FAILURE" else MemoryType.PATTERN
                title = f"Recurring {outcome.lower()} pattern on {entity}"
                desc = f"Observed {len(exps)} occurrences of {outcome} affecting {entity} under scope {sc}."

                pattern = MemoryPattern(
                    pattern_id=_uuid_hex("pat"),
                    pattern_type=pat_type,
                    title=title,
                    description=desc,
                    scope=MemoryScope(sc),
                    recurrence_count=len(exps),
                    confidence=min(0.95, 0.60 + (0.08 * len(exps))),
                    first_seen=min(e.occurred_at for e in exps),
                    last_seen=max(e.occurred_at for e in exps),
                    source_experience_ids=[e.experience_id for e in exps],
                    context_conditions={"primary_entity": entity, "outcome": outcome},
                )
                patterns.append(pattern)

        return patterns

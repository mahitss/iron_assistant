"""Contextual Attention Modulation Engine (Task 109, Spec 6).

Dynamically modulates attention salience and filtering based on:
1. Current User Intent (Task 108)
2. Active Mission & Goals (Task 100)
3. Active Situation & Hypotheses (Task 99)
4. Security & Governance State (EmergencyStop, SecurityCenter)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.attention.domain import AttentionCandidate, AttentionScore


class ContextualAttentionEngine:
    """Modulates candidate salience based on active environmental and operational context."""

    @classmethod
    def modulate(
        cls,
        candidate: AttentionCandidate,
        *,
        active_user_intent_ids: Optional[List[str]] = None,
        active_mission_ids: Optional[List[str]] = None,
        active_situation_ids: Optional[List[str]] = None,
        is_emergency_stop_active: bool = False,
        operational_mode: str = "NORMAL",  # NORMAL, FOCUS, CRITICAL_INCIDENT, QUIET_HOURS
    ) -> AttentionScore:
        """Modulates an attention candidate's score according to active context."""
        base_score = candidate.score

        user_intent_ids = active_user_intent_ids or []
        mission_ids = active_mission_ids or []
        situation_ids = active_situation_ids or []

        # 1. EmergencyStop Primacy: If EmergencyStop is active, emergency/recovery candidates
        # receive maximal attention, while unrelated background work is dampened
        if is_emergency_stop_active:
            if candidate.type in ("SAFETY", "SECURITY", "RECOVERY") or "EMERGENCY" in candidate.title.upper():
                return base_score.model_copy(
                    update={
                        "urgency": 1.0,
                        "importance": 1.0,
                        "composite_salience": 1.0,
                        "contributing_factors": base_score.contributing_factors + ["EmergencyStop Active Primacy"],
                        "explanation": f"MAXIMUM PRIORITY: EmergencyStop engaged. Candidate '{candidate.title}' prioritized.",
                    }
                )
            else:
                # Dampen non-safety candidates while EmergencyStop is active
                dampened_salience = round(base_score.composite_salience * 0.1, 4)
                return base_score.model_copy(
                    update={
                        "composite_salience": dampened_salience,
                        "contributing_factors": base_score.contributing_factors + ["EmergencyStop non-critical dampening"],
                        "explanation": "Dampened: Non-critical candidate while EmergencyStop is active.",
                    }
                )

        # 2. User Intent Alignment (Task 108)
        intent_match = (
            candidate.related_user_intent
            and candidate.related_user_intent in user_intent_ids
        )
        user_relevance_boost = 0.25 if intent_match else 0.0

        # 3. Active Mission Alignment (Task 100)
        mission_match = (
            candidate.related_mission
            and candidate.related_mission in mission_ids
        )
        mission_relevance_boost = 0.25 if mission_match else 0.0

        # 4. Active Situation / Incident Alignment (Task 99)
        situation_match = (
            candidate.related_situation
            and candidate.related_situation in situation_ids
        )
        situation_boost = 0.20 if situation_match else 0.0

        # 5. Operational Mode Modulation
        mode_modifier = 1.0
        if operational_mode == "FOCUS":
            # In FOCUS mode, distractors are penalized unless directly aligned with current mission
            if not (mission_match or intent_match):
                mode_modifier = 0.6
        elif operational_mode == "QUIET_HOURS":
            # Only critical safety/security items pass unattenuated
            if candidate.type not in ("SECURITY", "SAFETY", "FAILURE"):
                mode_modifier = 0.4

        new_user_rel = min(1.0, round(base_score.user_relevance + user_relevance_boost, 4))
        new_mission_rel = min(1.0, round(base_score.mission_relevance + mission_relevance_boost, 4))
        new_urgency = min(1.0, round(base_score.urgency + situation_boost, 4))

        # Recompute modulated composite salience
        raw_composite = (
            (base_score.importance * 0.20)
            + (new_urgency * 0.18)
            + (base_score.risk * 0.16)
            + (base_score.deadline_pressure * 0.12)
            + (new_mission_rel * 0.12)
            + (new_user_rel * 0.10)
            + (base_score.dependency_impact * 0.08)
            + (base_score.novelty * 0.04)
        )
        cost_moderator = 1.0 - (0.15 * base_score.interruption_cost + 0.10 * base_score.resource_cost)
        modulated_composite = max(0.0, min(1.0, round(raw_composite * cost_moderator * mode_modifier, 4)))

        new_factors = list(base_score.contributing_factors)
        if intent_match:
            new_factors.append("Active user intent boost (+0.25)")
        if mission_match:
            new_factors.append("Active mission alignment boost (+0.25)")
        if situation_match:
            new_factors.append("Active situation relevance boost (+0.20)")
        if mode_modifier < 1.0:
            new_factors.append(f"Operational mode '{operational_mode}' dampening")

        return base_score.model_copy(
            update={
                "user_relevance": new_user_rel,
                "mission_relevance": new_mission_rel,
                "urgency": new_urgency,
                "composite_salience": modulated_composite,
                "contributing_factors": new_factors,
                "explanation": "; ".join(new_factors) if new_factors else base_score.explanation,
            }
        )

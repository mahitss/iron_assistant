"""Downstream Bridges for Task 112:
Adapters connecting Causal Explanations to Context Working Set, Attention, and Safety Governance.

Strict Invariants:
- EXPLANATION TEXT CANNOT AUTHORIZE ACTIONS
- EXPLANATIONS CANNOT OVERRIDE EMERGENCY STOP
- CONTEXT RECEIVES STRICTLY BOUNDED EXPLANATIONS (NO FULL GRAPH DUMPS)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.causal.explanation.domain import (
    CausalExplanation,
    ExplanationLifecycleStage,
    RootCauseCategory,
)


class DownstreamExplanationBridges:
    """Provides bounded integration payloads for downstream cognitive systems."""

    @classmethod
    def format_for_context_working_set(
        cls,
        explanation: CausalExplanation,
        max_contributors: int = 3,
        max_alternatives: int = 2,
    ) -> Dict[str, Any]:
        """Formats bounded causal context for Task 110 Cognitive Working Set."""
        contributors_payload = [
            {
                "entity": c.entity_id,
                "role": c.role.value,
                "contribution": c.qualitative_contribution,
                "description": c.description,
            }
            for c in explanation.contributors[:max_contributors]
        ]

        alternatives_payload = [
            {
                "name": alt.name,
                "proposed_cause": alt.proposed_cause,
                "discriminating_test": alt.discriminating_observation,
            }
            for alt in explanation.alternatives[:max_alternatives]
        ]

        return {
            "explanation_id": explanation.explanation_id,
            "target_entity": explanation.target_entity,
            "lifecycle_stage": explanation.lifecycle_stage.value,
            "primary_cause": explanation.primary_cause or "CAUSE UNKNOWN",
            "root_category": explanation.root_cause_category.value,
            "composite_confidence": explanation.confidence.composite_confidence,
            "is_verified": explanation.is_verified,
            "key_contributors": contributors_payload,
            "competing_alternatives": alternatives_payload,
            "unresolved_gaps_count": len(explanation.unresolved_gaps),
            "verification_next_step": explanation.what_would_verify_this,
        }

    @classmethod
    def format_attention_signals(
        cls,
        explanation: CausalExplanation,
    ) -> List[Dict[str, Any]]:
        """Extracts salience signals for Task 109 Attention without assuming priority authority."""
        signals = []

        # Contradicted explanation alert
        if explanation.lifecycle_stage == ExplanationLifecycleStage.CONTRADICTED:
            signals.append({
                "signal_type": "EXPLANATION_CONTRADICTION_ALERT",
                "entity_id": explanation.target_entity,
                "urgency_boost": 0.4,
                "importance_boost": 0.5,
                "description": f"Explanation for '{explanation.target_entity}' was contradicted by post-incident evidence.",
            })

        # High-uncertainty critical failure
        if explanation.confidence.uncertainty_score > 0.7 and explanation.root_cause_category != RootCauseCategory.UNKNOWN:
            signals.append({
                "signal_type": "EXPLANATION_HIGH_UNCERTAINTY",
                "entity_id": explanation.target_entity,
                "urgency_boost": 0.3,
                "importance_boost": 0.4,
                "description": f"Explanation for '{explanation.target_entity}' has high epistemic uncertainty ({explanation.confidence.uncertainty_score:.2f}).",
            })

        return signals

    @classmethod
    def evaluate_emergency_stop_override(
        cls,
        is_emergency_stop_active: bool,
    ) -> Tuple[bool, str]:
        """Guarantees that EmergencyStop strictly halts any action regardless of causal explanation."""
        if is_emergency_stop_active:
            return True, "EmergencyStop active. All action execution is strictly halted regardless of explanation."
        return False, "Nominal operation."

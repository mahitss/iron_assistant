"""World Model & Digital Twin Bridge for Causal Discovery (Task 73, Spec 29, 30, 31).

Coordinates with:
- Task 65: Autonomous World Model & Long-Horizon Foresight (`app/foresight`)
- Task 54: Environmental Digital Twin (`app/environment`)
- Task 56: Simulation & Counterfactuals (`app/simulation`)

Strict Invariant:
Never treat SIMULATED STATE as REAL WORLD STATE.
Never promote unverified causal candidates to definitive world model causal edges without evidence.
"""

from __future__ import annotations

import logging
from typing import Any

from app.causal.discovery_schemas import (
    CausalRelationship,
    CausalRelationshipState,
)

logger = logging.getLogger(__name__)


class WorldModelBridge:
    """Synchronizes verified causal knowledge with the autonomous World Model and Digital Twin."""

    @staticmethod
    def sync_to_world_model(relationship: CausalRelationship) -> dict[str, Any]:
        """Convert a verified or supported causal relationship into World Model graph updates."""
        try:
            from app.foresight.relationships import foresight_relationship_manager
            from app.foresight.schemas import RelationshipType, WorldScope

            # Map status to World Model relationship type
            if relationship.status == CausalRelationshipState.VERIFIED:
                rel_type = RelationshipType.CAUSES
            elif relationship.status in {
                CausalRelationshipState.SUPPORTED,
                CausalRelationshipState.STRONGLY_SUPPORTED,
            }:
                rel_type = RelationshipType.CONTRIBUTES_TO
            else:
                rel_type = RelationshipType.CORRELATES_WITH

            # Use evidence list or fallback to verification reference
            ev = list(relationship.evidence_refs)
            if relationship.verification_refs:
                ev.extend([f"verif:{v}" for v in relationship.verification_refs])
            if not ev:
                ev = [f"auto_discovery:{relationship.causal_relation_id}"]

            # Synchronize with foresight relationship manager
            foresight_rel = foresight_relationship_manager.add_relationship(
                source_entity_id=relationship.cause_entity,
                target_entity_id=relationship.effect_entity,
                relationship_type=rel_type,
                causal_strength=relationship.confidence,
                evidence=ev,
                confidence=relationship.confidence,
                conditions=[f"{k}={v}" for k, v in relationship.conditions.items()],
                scope=WorldScope.SYSTEM,
                is_critical=relationship.strength.value in {"STRONG", "MODERATE"},
                provenance={
                    "source": "causal_discovery_engine_task73",
                    "causal_relation_id": relationship.causal_relation_id,
                    "environment": relationship.environment,
                    "model_version": relationship.model_version,
                },
            )
            return {
                "synced": True,
                "world_model_rel_id": foresight_rel.rel_id,
                "relationship_type": rel_type.value,
            }
        except Exception as e:
            logger.debug(f"Unable to sync relationship {relationship.causal_relation_id} to World Model: {e}")
            return {
                "synced": False,
                "reason": str(e),
            }

    @staticmethod
    def run_digital_twin_counterfactual(
        relationship: CausalRelationship,
        baseline_state: dict[str, Any],
        intervened_cause_value: Any,
    ) -> dict[str, Any]:
        """Run a synthetic digital twin simulation clearly labeled SIMULATED (Task 56, Spec 30, 31)."""
        # Invariant: Clearly label as SIMULATED STATE, distinct from REAL WORLD
        effect_delta = 0.0
        if relationship.effect_size:
            effect_delta = relationship.effect_size.measurement
        elif relationship.strength.value == "STRONG":
            effect_delta = 1.0
        elif relationship.strength.value == "MODERATE":
            effect_delta = 0.5
        else:
            effect_delta = 0.1

        simulated_effect = {
            "entity": relationship.effect_entity,
            "variable": relationship.effect_variable,
            "baseline_value": baseline_state.get(relationship.effect_variable, 0.0),
            "simulated_delta": effect_delta,
            "simulated_value": float(baseline_state.get(relationship.effect_variable, 0.0)) + effect_delta,
            "confidence": relationship.confidence,
            "is_simulation": True,  # Critical Invariant: Not real world observation
            "simulation_label": "SIMULATED_STATE",
        }
        return simulated_effect

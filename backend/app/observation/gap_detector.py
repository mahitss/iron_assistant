"""Information Gap Detection and 'Existing Data First' Resolution Engine for Task 114.
Identifies absent facts, missing telemetry, and epistemic voids while prioritizing existing internal evidence.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid

from app.observation.domain import (
    InformationGap,
    UncertaintyDimensionType,
    UncertaintyLevel,
    UncertaintyState,
    utc_now,
)

logger = logging.getLogger("kairo.observation.gap_detector")


class InformationGapDetector:
    """Detects critical information gaps and checks existing internal data before proposing queries."""

    @classmethod
    def detect_gaps(
        cls,
        uncertainty_state: UncertaintyState,
        question: str = "",
        dependent_decision: Optional[Dict[str, Any]] = None,
        dependent_mission: Optional[Dict[str, Any]] = None,
        causal_hypotheses: Optional[List[str]] = None,
        existing_internal_data: Optional[List[Dict[str, Any]]] = None,
    ) -> List[InformationGap]:
        gaps: List[InformationGap] = []
        existing_internal_data = existing_internal_data or []

        # 1. Gaps from critical or high-uncertainty dimensions
        for dim_name, dim in uncertainty_state.dimensions.items():
            if dim.level in {UncertaintyLevel.UNKNOWN, UncertaintyLevel.CONTESTED, UncertaintyLevel.STALE} or (
                dim.level == UncertaintyLevel.UNCERTAIN and dim.is_critical
            ):
                dim_enum = UncertaintyDimensionType(dim_name)
                gap = InformationGap(
                    question=f"What is the verified state and provenance of {uncertainty_state.target_entity} for dimension '{dim_name}'?",
                    missing_information=dim.description or f"Missing verifiable data for {dim_name}",
                    affected_entity=uncertainty_state.target_entity,
                    affected_state=dim_name,
                    source_candidates=["system_telemetry", "world_state_twin", "runtime_diagnostics"],
                    why_it_matters=f"Dimension '{dim_name}' is currently {dim.level.value} with confidence {dim.confidence:.2f}.",
                    dependent_decision_id=dependent_decision.get("decision_id") if dependent_decision else None,
                    dependent_mission_id=dependent_mission.get("mission_id") if dependent_mission else None,
                    uncertainty_dimensions=[dim_enum],
                    severity="CRITICAL" if dim.is_critical else "HIGH" if dim.level == UncertaintyLevel.CONTESTED else "MEDIUM",
                    freshness_requirement_seconds=30.0 if dim.is_critical else 120.0,
                    temporal_scope="CURRENT",
                )
                cls._check_existing_data_first(gap, existing_internal_data)
                gaps.append(gap)

        # 2. Gaps from competing causal hypotheses (Section 22)
        if causal_hypotheses and len(causal_hypotheses) >= 2:
            gap = InformationGap(
                question=f"Which causal hypothesis explains {uncertainty_state.target_entity}: '{causal_hypotheses[0]}' or '{causal_hypotheses[1]}'?",
                missing_information=f"Discriminating observation between {causal_hypotheses[0]} and {causal_hypotheses[1]}",
                affected_entity=uncertainty_state.target_entity,
                affected_state="CAUSAL_DISPUTE",
                source_candidates=["causal_trace", "network_telemetry", "queue_backlog"],
                why_it_matters="Resolving root-cause dispute is necessary to select appropriate remediation action.",
                uncertainty_dimensions=[UncertaintyDimensionType.CAUSAL, UncertaintyDimensionType.STATE],
                severity="HIGH",
                freshness_requirement_seconds=60.0,
            )
            cls._check_existing_data_first(gap, existing_internal_data)
            gaps.append(gap)

        # 3. Gaps from explicit question or intent ambiguity (Section 19)
        if question and any(term in question.lower() for term in ["intent", "clarify", "user mean", "interpret"]):
            gap = InformationGap(
                question=question,
                missing_information="User intent between ambiguous candidate commands remains unresolved.",
                affected_entity=uncertainty_state.target_entity,
                affected_state="USER_INTENT",
                source_candidates=["user_dialogue", "intent_engine"],
                why_it_matters="Execution without intent clarification risks destructive or unintended side effects.",
                uncertainty_dimensions=[UncertaintyDimensionType.INTENT],
                severity="HIGH",
                freshness_requirement_seconds=300.0,
            )
            cls._check_existing_data_first(gap, existing_internal_data)
            gaps.append(gap)

        return gaps

    @classmethod
    def _check_existing_data_first(
        cls,
        gap: InformationGap,
        existing_internal_data: List[Dict[str, Any]],
    ) -> None:
        """Section 13: Search existing Kairo internal data before acquiring new information."""
        target_entity_clean = gap.affected_entity.lower()
        missing_clean = gap.missing_information.lower()

        for item in existing_internal_data:
            item_entity = str(item.get("entity", "")).lower()
            item_content = str(item.get("content", "") or item.get("value", "")).lower()
            item_type = str(item.get("context_type", "") or item.get("data_type", "")).lower()
            item_freshness = float(item.get("freshness_seconds", 0.0))

            # Match criteria: same entity, relevant topic, fresh enough, reliable
            if (target_entity_clean in item_entity or item_entity in target_entity_clean) and (
                any(w in item_content for w in gap.affected_state.lower().split("_")) or
                any(w in item_content for w in missing_clean.split() if len(w) > 4)
            ):
                if item_freshness <= gap.freshness_requirement_seconds:
                    gap.is_resolved_by_existing_data = True
                    gap.existing_evidence_id = str(item.get("id") or item.get("evidence_id") or "internal_cache")
                    gap.why_it_matters += f" [RESOLVED INTERNALLY: Found existing valid evidence '{gap.existing_evidence_id}']"
                    logger.info(
                        f"Existing Data First: Gap '{gap.gap_id}' resolved by internal item '{gap.existing_evidence_id}'."
                    )
                    break

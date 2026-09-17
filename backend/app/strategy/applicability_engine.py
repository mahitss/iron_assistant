"""Applicability Engine for Kairo Strategy Engine (Task 106).

Evaluates whether a strategy is viable in a given operational context, returning:
- APPLICABLE: Conditions met, preconditions satisfied, no contraindications.
- NOT_APPLICABLE: Target conditions do not match context.
- UNCERTAIN: Missing context, stale world-state, or degraded capabilities.
- BLOCKED: Active contraindication or EmergencyStop engaged.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.strategy.domain import (
    ApplicabilityStatus,
    ConditionOperator,
    ContraindicationSeverity,
    Strategy,
    StrategyApplicability,
    generate_id,
    utc_now,
)

logger = logging.getLogger("kairo.strategy.applicability_engine")


class ApplicabilityEngine:
    """Evaluates context against strategy conditions, preconditions, and contraindications."""

    def evaluate_applicability(
        self,
        strategy: Strategy,
        context: Dict[str, Any],
        emergency_stop_active: bool = False,
    ) -> StrategyApplicability:
        """Evaluate strategy applicability against operational context."""
        applicability_id = generate_id("sapp")
        blocking_reasons: List[str] = []
        uncertainty_reasons: List[str] = []

        # 1. EmergencyStop Absolute Check
        if emergency_stop_active or context.get("emergency_stop") is True:
            blocking_reasons.append("EmergencyStop is currently active; all mutating strategies are BLOCKED fail-closed.")
            return StrategyApplicability(
                id=applicability_id,
                strategy_id=strategy.id,
                version_id=strategy.current_version_id,
                evaluation_context=context,
                applicability_status=ApplicabilityStatus.BLOCKED,
                applicability_score=0.0,
                blocking_reasons=blocking_reasons,
                uncertainty_reasons=uncertainty_reasons,
                evaluated_at=utc_now(),
            )

        # 2. Check Contraindications (Hard Blocks or Restrictions)
        for contra in strategy.contraindications:
            trigger = contra.trigger_condition
            matched = False
            for k, v in trigger.items():
                if k in context and context[k] == v:
                    matched = True
                    break
            if matched:
                msg = f"Contraindication triggered [{contra.contraindication_type}]: {contra.rationale}"
                if contra.severity == ContraindicationSeverity.PROHIBITIVE:
                    blocking_reasons.append(msg)
                else:
                    uncertainty_reasons.append(f"Advisory contraindication: {contra.rationale}")

        if blocking_reasons:
            return StrategyApplicability(
                id=applicability_id,
                strategy_id=strategy.id,
                version_id=strategy.current_version_id,
                evaluation_context=context,
                applicability_status=ApplicabilityStatus.BLOCKED,
                applicability_score=0.0,
                blocking_reasons=blocking_reasons,
                uncertainty_reasons=uncertainty_reasons,
                evaluated_at=utc_now(),
            )

        # 3. Check World-State & Capability Staleness (Task 98 & Task 101 Invariants)
        world_state_stale = context.get("world_state_stale", False)
        if world_state_stale:
            uncertainty_reasons.append("Required world-state is STALE or unverified. Cannot confirm applicability.")

        capability_health = context.get("capability_health", "HEALTHY")
        if capability_health in ("DEGRADED", "UNAVAILABLE", "UNKNOWN"):
            uncertainty_reasons.append(f"Target capability state is {capability_health}. Usability uncertain.")

        # 4. Check Preconditions
        for pre in strategy.preconditions:
            key = pre.verification_key
            if key in context:
                val = context[key]
                if val != pre.expected_state:
                    if pre.is_hard_requirement:
                        blocking_reasons.append(
                            f"Precondition failed [{pre.precondition_type}]: expected {pre.expected_state}, got {val}"
                        )
                    else:
                        uncertainty_reasons.append(
                            f"Soft precondition degraded [{pre.precondition_type}]: {pre.requirement_description}"
                        )
            else:
                # Missing precondition evidence implies uncertainty, not outright failure
                uncertainty_reasons.append(
                    f"Precondition unverified [{pre.precondition_type}]: missing key '{key}' in context."
                )

        if blocking_reasons:
            return StrategyApplicability(
                id=applicability_id,
                strategy_id=strategy.id,
                version_id=strategy.current_version_id,
                evaluation_context=context,
                applicability_status=ApplicabilityStatus.BLOCKED,
                applicability_score=0.0,
                blocking_reasons=blocking_reasons,
                uncertainty_reasons=uncertainty_reasons,
                evaluated_at=utc_now(),
            )

        # 5. Check Target Conditions (Matching Task/Situation/Domain)
        total_conditions = len(strategy.conditions)
        matched_conditions = 0

        for cond in strategy.conditions:
            path = cond.field_path
            target = cond.target_value
            op = cond.operator

            if path not in context:
                if cond.is_mandatory:
                    # Missing mandatory condition means context is not applicable
                    return StrategyApplicability(
                        id=applicability_id,
                        strategy_id=strategy.id,
                        version_id=strategy.current_version_id,
                        evaluation_context=context,
                        applicability_status=ApplicabilityStatus.NOT_APPLICABLE,
                        applicability_score=0.0,
                        blocking_reasons=[f"Mandatory condition field '{path}' not found in context"],
                        uncertainty_reasons=uncertainty_reasons,
                        evaluated_at=utc_now(),
                    )
                continue

            actual = context[path]
            is_match = False
            if op == ConditionOperator.EQUALS:
                is_match = (actual == target)
            elif op == ConditionOperator.NOT_EQUALS:
                is_match = (actual != target)
            elif op == ConditionOperator.GREATER_THAN:
                is_match = (actual > target)
            elif op == ConditionOperator.LESS_THAN:
                is_match = (actual < target)
            elif op == ConditionOperator.IN_SET:
                is_match = (actual in target)
            elif op == ConditionOperator.CONTAINS:
                is_match = (target in actual)
            elif op == ConditionOperator.EXISTS:
                is_match = (actual is not None)

            if is_match:
                matched_conditions += 1
            elif cond.is_mandatory:
                return StrategyApplicability(
                    id=applicability_id,
                    strategy_id=strategy.id,
                    version_id=strategy.current_version_id,
                    evaluation_context=context,
                    applicability_status=ApplicabilityStatus.NOT_APPLICABLE,
                    applicability_score=0.0,
                    blocking_reasons=[
                        f"Condition mismatch on '{path}': expected {op.value} {target}, got {actual}"
                    ],
                    uncertainty_reasons=uncertainty_reasons,
                    evaluated_at=utc_now(),
                )

        score = (matched_conditions / total_conditions) if total_conditions > 0 else 1.0

        # If any uncertainty exists, degrade status to UNCERTAIN
        if uncertainty_reasons:
            return StrategyApplicability(
                id=applicability_id,
                strategy_id=strategy.id,
                version_id=strategy.current_version_id,
                evaluation_context=context,
                applicability_status=ApplicabilityStatus.UNCERTAIN,
                applicability_score=round(score * 0.7, 3),
                blocking_reasons=[],
                uncertainty_reasons=uncertainty_reasons,
                evaluated_at=utc_now(),
            )

        return StrategyApplicability(
            id=applicability_id,
            strategy_id=strategy.id,
            version_id=strategy.current_version_id,
            evaluation_context=context,
            applicability_status=ApplicabilityStatus.APPLICABLE,
            applicability_score=round(score, 3),
            blocking_reasons=[],
            uncertainty_reasons=[],
            evaluated_at=utc_now(),
        )

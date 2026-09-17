"""Strategy Candidate Generation Engine for Kairo Strategy Engine (Task 106).

Synthesizes structured candidate strategies from detected patterns, explicitly
attaching counterexamples, contraindications, preconditions, and expected outcomes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid

from app.strategy.domain import (
    ConditionOperator,
    ContraindicationSeverity,
    EvidenceSourceType,
    Strategy,
    StrategyCategory,
    StrategyCondition,
    StrategyContraindication,
    StrategyEvidence,
    StrategyFailureMode,
    StrategyOutcome,
    StrategyPrecondition,
    StrategyStatus,
    StrategyVersion,
    generate_id,
    utc_now,
)
from app.strategy.pattern_detector import DetectedPattern

logger = logging.getLogger("kairo.strategy.candidate_generator")


class CandidateGenerationEngine:
    """Transforms statistical patterns into bounded, verifiable strategy candidates."""

    def generate_candidate_strategy(
        self,
        pattern: DetectedPattern,
        cluster_evidences: Optional[List[StrategyEvidence]] = None,
    ) -> Strategy:
        """Construct a full Strategy candidate structure from a validated pattern."""
        strategy_id = generate_id("strat")
        stable_id = f"strat_stable_{uuid.uuid4().hex[:8]}"

        # Map string category to StrategyCategory enum safely
        try:
            category_enum = StrategyCategory(pattern.category)
        except ValueError:
            category_enum = StrategyCategory.DECISION

        strategy = Strategy(
            id=strategy_id,
            stable_id=stable_id,
            name=f"Learned Strategy: {pattern.approach_summary[:60]}",
            category=category_enum,
            objective=f"Optimize {pattern.category.lower()} execution under {pattern.target_conditions}",
            recommended_approach=pattern.approach_summary,
            lifecycle_status=StrategyStatus.CANDIDATE,
            domain_scope=pattern.domain_scope,
            tested_domain=f"Conditions: {pattern.target_conditions}",
            supported_domain=f"Similar {pattern.category.lower()} workloads within {pattern.domain_scope}",
            unknown_domain="Untested multi-region distributed or extreme-concurrency workloads",
            confidence=pattern.conservative_confidence,
            uncertainty=pattern.uncertainty,
            success_rate=pattern.success_rate,
            failure_rate=pattern.failure_rate,
            usage_count=0,
            validity_window_seconds=604800,  # 7 days
            is_stale=False,
            is_safety_critical=(category_enum in (StrategyCategory.SECURITY_DEFENSE, StrategyCategory.RECOVERY)),
            provenance_type="PATTERN_DETECTION",
            provenance_id=pattern.pattern_id,
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        # 1. Initial Version
        version = StrategyVersion(
            id=generate_id("sver"),
            strategy_id=strategy_id,
            version_number=1,
            change_reason="Synthesized from empirical experience pattern",
            change_description=f"Initial candidate derived from {pattern.frequency} observations",
            parameters={"target_conditions": pattern.target_conditions},
            rules=[{"approach": pattern.approach_summary}],
            lifecycle_status=StrategyStatus.CANDIDATE,
            confidence=pattern.conservative_confidence,
            uncertainty=pattern.uncertainty,
            evidence_count=pattern.frequency,
            counterexample_count=pattern.failure_count,
            created_at=utc_now(),
        )
        version.calculate_checksum()
        strategy.current_version_id = version.id
        strategy.versions.append(version)

        # 2. Conditions
        for k, v in pattern.target_conditions.items():
            strategy.conditions.append(
                StrategyCondition(
                    strategy_id=strategy_id,
                    version_id=version.id,
                    condition_type="CONTEXT_MATCH",
                    operator=ConditionOperator.EQUALS,
                    field_path=k,
                    target_value=v,
                    is_mandatory=True,
                )
            )

        # 3. Preconditions
        strategy.preconditions.append(
            StrategyPrecondition(
                strategy_id=strategy_id,
                version_id=version.id,
                precondition_type="CAPABILITY_READY",
                requirement_description="Required capabilities must be in healthy state",
                verification_key="self_model.capability.status",
                expected_state="READY",
                is_hard_requirement=True,
            )
        )
        strategy.preconditions.append(
            StrategyPrecondition(
                strategy_id=strategy_id,
                version_id=version.id,
                precondition_type="WORLD_STATE_STABLE",
                requirement_description="World-state must be freshly reconciled without active drift",
                verification_key="world_state.is_stale",
                expected_state=False,
                is_hard_requirement=False, # Section 20: Stale world state returns UNCERTAIN
            )
        )

        # 4. Contraindications (Synthesized from counterexample analysis)
        if pattern.failure_count > 0:
            strategy.contraindications.append(
                StrategyContraindication(
                    strategy_id=strategy_id,
                    version_id=version.id,
                    contraindication_type="RESOURCE_PRESSURE_HIGH",
                    severity=ContraindicationSeverity.PROHIBITIVE,
                    trigger_condition={"resource_pressure": "HIGH"},
                    rationale="Historical failures observed when resource pressure exceeded nominal thresholds.",
                )
            )
        # Always add standard safety contraindication
        strategy.contraindications.append(
            StrategyContraindication(
                strategy_id=strategy_id,
                version_id=version.id,
                contraindication_type="EMERGENCY_STOP_ACTIVE",
                severity=ContraindicationSeverity.PROHIBITIVE,
                trigger_condition={"emergency_stop": True},
                rationale="EmergencyStop halts all mutating and privileged strategy execution.",
            )
        )

        # 5. Expected Outcomes
        strategy.outcomes.append(
            StrategyOutcome(
                strategy_id=strategy_id,
                version_id=version.id,
                dimension="SUCCESS_RATE",
                expected_delta=round(pattern.success_rate - 0.5, 3),
                variance=0.05,
                success_criteria=f"Empirical success rate >= {pattern.success_rate:.2f}",
                measurement_unit="ratio",
            )
        )

        # 6. Failure Modes
        for ce_summary in pattern.counterexample_summaries:
            strategy.failure_modes.append(
                StrategyFailureMode(
                    strategy_id=strategy_id,
                    version_id=version.id,
                    failure_class="EXCEPTION_BOUNDARY",
                    symptom=ce_summary,
                    known_cause="Condition shift or transient resource saturation",
                    frequency=pattern.failure_rate,
                )
            )

        # 7. Attach Evidences if available
        if cluster_evidences:
            for ev in cluster_evidences:
                ev.strategy_id = strategy_id
                ev.version_id = version.id
                if ev.is_counterexample:
                    strategy.counterexamples.append(ev)
                else:
                    strategy.evidences.append(ev)

        logger.info(
            f"Generated candidate strategy {strategy.id} (confidence={strategy.confidence:.2f}, {len(strategy.counterexamples)} counterexamples preserved)."
        )
        return strategy

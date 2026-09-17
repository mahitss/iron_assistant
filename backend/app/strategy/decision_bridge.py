"""Decision Bridge for Kairo Strategy Engine (Task 106).

Provides a strictly typed, advisory candidate contract for Task 94 Decision Intelligence.
Enforces that Strategy Engine NEVER executes actions directly or makes unilateral choices.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.strategy.domain import (
    ApplicabilityStatus,
    Strategy,
    StrategyApplicability,
    StrategyStatus,
)
from app.strategy.schemas import StrategyCandidateContract

logger = logging.getLogger("kairo.strategy.decision_bridge")


class DecisionCandidateBundle(BaseModel):
    """Bundle of evaluated strategy candidates presented to Decision Intelligence."""

    context_summary: Dict[str, Any]
    candidate_count: int
    ranked_candidates: List[StrategyCandidateContract]
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    advisory_warning: str = (
        "DECISION AUTHORITY NOTICE: These strategies are empirical recommendations only. "
        "The Decision Engine remains authoritative for trade-off evaluation, NO_ACTION consideration, "
        "and action selection. The Strategy Engine possesses zero action execution authority."
    )


class DecisionBridge:
    """Bridges Strategy Engine outputs to Task 94 Decision Intelligence."""

    def format_candidate_contract(
        self,
        strategy: Strategy,
        applicability: StrategyApplicability,
    ) -> StrategyCandidateContract:
        """Format an evaluated Strategy into a typed contract for Task 94."""
        version_num = 1
        if strategy.versions:
            version_num = strategy.versions[-1].version_number

        expected_outcomes = [
            {
                "dimension": o.dimension,
                "expected_delta": o.expected_delta,
                "success_criteria": o.success_criteria,
            }
            for o in strategy.outcomes
        ]

        failure_modes = [
            {
                "failure_class": f.failure_class,
                "symptom": f.symptom,
                "known_cause": f.known_cause,
            }
            for f in strategy.failure_modes
        ]

        preconditions = [
            {
                "type": p.precondition_type,
                "description": p.requirement_description,
                "is_hard": p.is_hard_requirement,
            }
            for p in strategy.preconditions
        ]

        contraindications = [
            {
                "type": c.contraindication_type,
                "severity": c.severity.value,
                "rationale": c.rationale,
            }
            for c in strategy.contraindications
        ]

        freshness_label = "STALE" if strategy.is_stale else "FRESH"

        return StrategyCandidateContract(
            strategy_id=strategy.id,
            strategy_version=version_num,
            name=strategy.name,
            category=strategy.category,
            objective=strategy.objective,
            recommended_approach=strategy.recommended_approach,
            applicability_status=applicability.applicability_status,
            applicability_score=applicability.applicability_score,
            confidence=strategy.confidence,
            uncertainty=strategy.uncertainty,
            evidence_count=len(strategy.evidences),
            counterexample_count=len(strategy.counterexamples),
            expected_outcomes=expected_outcomes,
            known_failure_modes=failure_modes,
            preconditions=preconditions,
            contraindications=contraindications,
            tested_domain=strategy.tested_domain,
            supported_domain=strategy.supported_domain,
            unknown_domain=strategy.unknown_domain,
            freshness=freshness_label,
            provenance=f"{strategy.provenance_type}:{strategy.provenance_id}",
        )

    def prepare_decision_candidates(
        self,
        evaluated_pairs: List[tuple[Strategy, StrategyApplicability]],
        conflicts: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionCandidateBundle:
        """Filter, sort, and bundle candidates for presentation to Task 94 Decision Intelligence."""
        candidates: List[StrategyCandidateContract] = []

        # Only present candidates that are APPLICABLE or UNCERTAIN (never BLOCKED or NOT_APPLICABLE)
        for strategy, app in evaluated_pairs:
            if app.applicability_status in (ApplicabilityStatus.APPLICABLE, ApplicabilityStatus.UNCERTAIN):
                # Ensure strategy is AVAILABLE or VALIDATED
                if strategy.lifecycle_status in (StrategyStatus.AVAILABLE, StrategyStatus.VALIDATED, StrategyStatus.CANDIDATE):
                    candidate_dto = self.format_candidate_contract(strategy, app)
                    candidates.append(candidate_dto)

        # Sort by composite utility: applicability_score * confidence
        candidates.sort(
            key=lambda c: (c.applicability_score * c.confidence),
            reverse=True,
        )

        logger.info(
            f"Prepared {len(candidates)} ranked candidates for Decision Intelligence across context: {context}"
        )

        return DecisionCandidateBundle(
            context_summary=context or {},
            candidate_count=len(candidates),
            ranked_candidates=candidates,
            conflicts=conflicts or [],
        )

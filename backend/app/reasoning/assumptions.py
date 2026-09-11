"""Assumption tracking and invalidation cascades for Kairo Reasoning Engine (Task 71).

Explicitly tracks assumptions upon which sub-problems, hypotheses, and conclusions rely.
Enforces:
- Assumption validation / invalidation lifecycle
- Immediate invalidation cascades across dependent conclusions
- Provenance tracking of assumption validation sources
"""

import logging

from app.reasoning.schemas import (
    AssumptionStatus,
    ConclusionStatus,
    ReasoningAssumption,
    ReasoningConclusion,
)

logger = logging.getLogger(__name__)


class AssumptionTracker:
    """Manages assumptions and invalidation propagation for a reasoning session."""

    def __init__(self) -> None:
        self._assumptions: dict[str, ReasoningAssumption] = {}

    def register_assumption(
        self,
        description: str,
        assumption_id: str | None = None,
        initial_status: AssumptionStatus = AssumptionStatus.UNVERIFIED,
    ) -> ReasoningAssumption:
        """Register a new assumption."""
        assumption = ReasoningAssumption(
            description=description,
            status=initial_status,
        )
        if assumption_id:
            assumption.assumption_id = assumption_id

        self._assumptions[assumption.assumption_id] = assumption
        logger.info(
            f"Registered assumption {assumption.assumption_id}: '{description}' (status={initial_status})"
        )
        return assumption

    def link_conclusion(self, assumption_id: str, conclusion_id: str) -> None:
        """Record that a conclusion depends on this assumption."""
        if assumption_id in self._assumptions:
            if conclusion_id not in self._assumptions[assumption_id].dependent_conclusion_ids:
                self._assumptions[assumption_id].dependent_conclusion_ids.append(conclusion_id)

    def validate_assumption(
        self,
        assumption_id: str,
        validation_source: str,
    ) -> ReasoningAssumption:
        """Mark an assumption as empirically validated."""
        if assumption_id not in self._assumptions:
            raise KeyError(f"Assumption {assumption_id} not found")

        asm = self._assumptions[assumption_id]
        asm.status = AssumptionStatus.VALIDATED
        asm.validation_source = validation_source
        logger.info(f"Assumption {assumption_id} validated via {validation_source}")
        return asm

    def invalidate_assumption(
        self,
        assumption_id: str,
        reason: str,
        conclusions_pool: list[ReasoningConclusion] | None = None,
    ) -> tuple[ReasoningAssumption, list[str]]:
        """Mark an assumption as invalidated and cascade to dependent conclusions.

        Returns the updated assumption and a list of invalidated conclusion IDs.
        """
        if assumption_id not in self._assumptions:
            raise KeyError(f"Assumption {assumption_id} not found")

        asm = self._assumptions[assumption_id]
        asm.status = AssumptionStatus.INVALIDATED
        asm.validation_source = f"Invalidated: {reason}"
        logger.warning(f"Assumption {assumption_id} invalidated: {reason}")

        affected_conclusions: list[str] = []
        if conclusions_pool:
            for concl in conclusions_pool:
                if (
                    concl.conclusion_id in asm.dependent_conclusion_ids
                    or assumption_id in concl.assumption_ids
                ):
                    concl.status = ConclusionStatus.INVALIDATED
                    concl.is_verified = False
                    affected_conclusions.append(concl.conclusion_id)
                    logger.warning(
                        f"Conclusion {concl.conclusion_id} INVALIDATED due to broken assumption {assumption_id}"
                    )

        return asm, affected_conclusions

    def get_assumption(self, assumption_id: str) -> ReasoningAssumption | None:
        return self._assumptions.get(assumption_id)

    def list_assumptions(self) -> list[ReasoningAssumption]:
        return list(self._assumptions.values())

    def check_stability(self) -> dict[str, int]:
        """Summary of assumption stability."""
        summary = {
            "total": len(self._assumptions),
            "validated": 0,
            "unverified": 0,
            "invalidated": 0,
        }
        for asm in self._assumptions.values():
            if asm.status == AssumptionStatus.VALIDATED:
                summary["validated"] += 1
            elif asm.status == AssumptionStatus.UNVERIFIED:
                summary["unverified"] += 1
            elif asm.status == AssumptionStatus.INVALIDATED:
                summary["invalidated"] += 1
        return summary

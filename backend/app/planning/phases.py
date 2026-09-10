"""Phase lifecycle, entry/exit criteria verification for Strategic Planning (Task 58)."""

from __future__ import annotations

import logging
from typing import Any

from app.planning.schemas import PhaseStatus, PlanPhase

logger = logging.getLogger(__name__)


class PhaseManager:
    """Manages strategic phases, verifying entry/exit gates strictly."""

    def create_phase(
        self,
        name: str,
        phase_order: int = 1,
        entry_criteria: list[str] | None = None,
        exit_criteria: list[str] | None = None,
        milestone_ids: list[str] | None = None,
        package_ids: list[str] | None = None,
    ) -> PlanPhase:
        """Create a strategic phase with explicit criteria."""
        return PlanPhase(
            name=name,
            phase_order=phase_order,
            status=PhaseStatus.PLANNED,
            entry_criteria=entry_criteria or [],
            exit_criteria=exit_criteria or [],
            milestone_ids=milestone_ids or [],
            package_ids=package_ids or [],
        )

    def validate_entry_criteria(
        self,
        phase: PlanPhase,
        current_state: dict[str, Any] | None = None,
        verified_prerequisites: list[str] | None = None,
        approvals: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """A phase must not begin if mandatory entry criteria or approvals are missing."""
        missing: list[str] = []
        verified_set = set(verified_prerequisites or [])
        approval_set = set(approvals or [])

        for criterion in phase.entry_criteria:
            crit_lower = criterion.lower()
            if "approval" in crit_lower:
                if not any(appr.lower() in crit_lower or crit_lower in appr.lower() for appr in approval_set):
                    missing.append(f"Missing required approval: '{criterion}'")
            elif criterion not in verified_set:
                missing.append(f"Unsatisfied entry prerequisite: '{criterion}'")

        is_valid = len(missing) == 0
        if not is_valid:
            logger.warning(
                "Phase '%s' entry criteria validation failed: %s",
                phase.name,
                missing,
            )
        return is_valid, missing

    def validate_exit_criteria(
        self,
        phase: PlanPhase,
        verified_outcomes: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Verify completion conditions. Tasks attempted is NOT equivalent to verified exit."""
        missing: list[str] = []
        verified_set = set(verified_outcomes or [])

        for criterion in phase.exit_criteria:
            if criterion not in verified_set:
                missing.append(f"Unverified exit criterion: '{criterion}'")

        is_valid = len(missing) == 0
        if not is_valid:
            logger.warning(
                "Phase '%s' exit criteria unverified: %s",
                phase.name,
                missing,
            )
        return is_valid, missing

    def transition_phase(
        self,
        phase: PlanPhase,
        target_status: PhaseStatus,
        verified_prerequisites: list[str] | None = None,
        approvals: list[str] | None = None,
        verified_outcomes: list[str] | None = None,
    ) -> tuple[PlanPhase, bool, list[str]]:
        """Transition phase state with gate enforcement."""
        if target_status == PhaseStatus.IN_PROGRESS:
            valid, missing = self.validate_entry_criteria(
                phase,
                verified_prerequisites=verified_prerequisites,
                approvals=approvals,
            )
            if not valid:
                phase.status = PhaseStatus.BLOCKED
                return phase, False, missing
            phase.status = PhaseStatus.IN_PROGRESS
            return phase, True, []

        if target_status == PhaseStatus.COMPLETED:
            valid, missing = self.validate_exit_criteria(
                phase,
                verified_outcomes=verified_outcomes,
            )
            if not valid:
                return phase, False, missing
            phase.status = PhaseStatus.COMPLETED
            return phase, True, []

        phase.status = target_status
        return phase, True, []


phase_manager = PhaseManager()

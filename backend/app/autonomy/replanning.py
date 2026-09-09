"""Adaptive Replanning, Structural Plan Diffs, and Version Management (Task 45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.autonomy.replanning")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PlanDiff:
    """Detailed structural difference between two plan versions (Spec 77)."""

    added_steps: List[str] = field(default_factory=list)
    removed_steps: List[str] = field(default_factory=list)
    modified_steps: List[str] = field(default_factory=list)
    reordered_steps: List[str] = field(default_factory=list)
    is_material_change: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "added_steps": self.added_steps,
            "removed_steps": self.removed_steps,
            "modified_steps": self.modified_steps,
            "reordered_steps": self.reordered_steps,
            "is_material_change": self.is_material_change,
        }


class ReplanningManager:
    """Manages adaptive plan regeneration, plan versioning, and diff tracking (Spec 73-80)."""

    def __init__(self, materiality_threshold: int = 1) -> None:
        self.materiality_threshold = materiality_threshold

    def calculate_plan_diff(
        self,
        old_steps: List[Dict[str, Any]],
        new_steps: List[Dict[str, Any]],
    ) -> PlanDiff:
        """Compute structural differences between prior plan and replanned DAG (Spec 77)."""
        old_ids = [s.get("step_id", s.get("id")) for s in old_steps]
        new_ids = [s.get("step_id", s.get("id")) for s in new_steps]

        old_set = set(old_ids)
        new_set = set(new_ids)

        added = [sid for sid in new_ids if sid not in old_set]
        removed = [sid for sid in old_ids if sid not in new_set]

        # Check modified steps
        old_map = {s.get("step_id", s.get("id")): s for s in old_steps}
        modified = []
        for s in new_steps:
            sid = s.get("step_id", s.get("id"))
            if sid in old_map and s != old_map[sid]:
                modified.append(sid)

        # Check reordering of preserved steps
        common_old = [sid for sid in old_ids if sid in new_set]
        common_new = [sid for sid in new_ids if sid in old_set]
        reordered = [sid for sid, other in zip(common_old, common_new) if sid != other]

        changes_count = len(added) + len(removed) + len(modified)
        is_material = changes_count >= self.materiality_threshold

        diff = PlanDiff(
            added_steps=added,
            removed_steps=removed,
            modified_steps=modified,
            reordered_steps=reordered,
            is_material_change=is_material,
        )
        logger.info(
            "Plan diff: +%d, -%d, ~%d steps (material=%s)",
            len(added),
            len(removed),
            len(modified),
            is_material,
        )
        return diff

    def create_replan_version(
        self,
        current_version: int,
        diff: PlanDiff,
    ) -> tuple[int, bool]:
        """Increment version and determine whether fresh approvals are mandatory (Spec 76, 78)."""
        new_version = current_version + 1
        requires_fresh_approval = diff.is_material_change
        return new_version, requires_fresh_approval

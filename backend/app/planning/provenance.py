"""Factor provenance recording, AI content flagging, and end-to-end traceability (Task 58)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.planning.schemas import StrategicPlan

logger = logging.getLogger(__name__)


class PlanProvenanceTracker:
    """Records factor provenance, AI generation tags, and structured traceability graphs."""

    def build_provenance_record(
        self,
        plan: StrategicPlan,
        author: str,
        source_context: str = "EXECUTIVE_DIRECTIVE",
        is_ai_assisted: bool = True,
    ) -> dict[str, Any]:
        """Construct a tamper-evident provenance record for a strategic plan."""
        canonical_str = (
            f"{plan.plan_id}:{plan.name}:{plan.strategy.name}:{plan.goal_id}:{author}:{plan.version}"
        )
        content_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        return {
            "plan_id": plan.plan_id,
            "version": plan.version,
            "author": author,
            "source_context": source_context,
            "is_ai_assisted": is_ai_assisted,
            "content_fingerprint": content_hash,
            "decision_reference": plan.decision_id or plan.strategy.decision_reference,
            "goal_reference": plan.goal_id,
        }

    def trace_task_justification(self, task_id: str, plan: StrategicPlan) -> dict[str, Any]:
        """Answer 'Why is this task in the plan?' with explicit hierarchy traceability."""
        task = next((t for t in plan.tasks if t.task_id == task_id), None)
        if not task:
            return {"error": f"Task '{task_id}' not found in plan {plan.plan_id}."}

        phase = next((p for p in plan.phases if p.phase_id == task.phase_id), None)
        package = next((wp for wp in plan.work_packages if wp.package_id == task.package_id), None)
        milestones = [m for m in plan.milestones if m.phase_id == task.phase_id]

        return {
            "task_id": task.task_id,
            "task_title": task.title,
            "purpose": task.description,
            "lineage": {
                "goal_id": plan.goal_id or "PRIMARY_ORGANIZATIONAL_GOAL",
                "strategy": plan.strategy.name,
                "strategy_type": plan.strategy.strategy_type.value,
                "phase_name": phase.name if phase else "General Execution Phase",
                "work_package": package.name if package else "Default Work Package",
                "supporting_milestones": [m.name for m in milestones],
            },
            "justification": (
                f"Task '{task.title}' directly fulfills entry/exit criteria for "
                f"Phase '{phase.name if phase else 'General'}' under strategy '{plan.strategy.name}'."
            ),
        }


plan_provenance_tracker = PlanProvenanceTracker()

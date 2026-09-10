"""Plan readiness consultation and capability alignment (INVARIANTS 45, 46, 47)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.metacognition.actions import ActionEngine
from app.metacognition.capabilities import CapabilityManager
from app.metacognition.schemas import ActionReadinessSchema, ExecutionReadiness


class PlanReadinessEvaluator:
    """Consults operational capability and policy state prior to plan execution."""

    def __init__(self, capability_manager: CapabilityManager) -> None:
        self.capability_manager = capability_manager

    def evaluate_plan_steps(
        self,
        steps: List[Dict[str, Any]],
        is_user_authorized: bool = True,
        policy_permits_all: bool = True,
    ) -> Dict[str, Any]:
        """INVARIANT 46: Evaluates readiness of each step in a prospective plan."""
        available_caps = [
            c.name for c in self.capability_manager.list_capabilities()
            if c.state in ("AVAILABLE", "RESTRICTED")
        ]

        step_evaluations: List[ActionReadinessSchema] = []
        is_overall_executable = True
        critical_blockers = []

        for step in steps:
            action_name = step.get("action", "unknown_step")
            req_caps = step.get("required_capabilities", [])
            req_approval = step.get("requires_approval", False)

            readiness = ActionEngine.assess_readiness(
                action_name=action_name,
                required_capabilities=req_caps,
                available_capabilities=available_caps,
                is_authorized=is_user_authorized,
                is_policy_permitted=policy_permits_all,
                requires_approval=req_approval,
            )
            step_evaluations.append(readiness)

            if readiness.readiness != ExecutionReadiness.READY.value:
                is_overall_executable = False
                critical_blockers.extend(readiness.blocking_reasons)

        return {
            "is_executable": is_overall_executable,
            "step_count": len(steps),
            "step_evaluations": [s.model_dump() for s in step_evaluations],
            "critical_blockers": list(set(critical_blockers)),
        }

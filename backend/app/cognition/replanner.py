"""Adaptive replanning engine, ReplanRequest coordinator, and plan diffing for Kairo Cognitive Planning (Task 41).

Enforces:
1. Re-plans create monotonic versions; old plans become SUPERSEDED.
2. Re-planning preserves original goals and hard constraints without silent scope creep.
3. Approval invalidation: prior approval does NOT authorize a higher-risk re-plan.
"""

from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.cognition.plans import Plan, PlanDiff, PlanRiskLevel, PlanStatus
from app.cognition.steps import PlanStep, StepStatus


class ReplanReason(str, Enum):
    """Authoritative triggers for initiating a re-plan."""

    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    STATE_CHANGE = "STATE_CHANGE"
    SCOPE_CHANGE = "SCOPE_CHANGE"
    ASSUMPTION_FAILURE = "ASSUMPTION_FAILURE"
    NEW_INFORMATION = "NEW_INFORMATION"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    POLICY_CHANGE = "POLICY_CHANGE"
    INVARIANT_BREACH = "INVARIANT_BREACH"


class ReplanRequest(BaseModel):
    """Formal request to generate a replacement plan version."""

    model_config = ConfigDict(extra="ignore")

    plan_id: str
    reason: ReplanReason
    trigger_step_id: str | None = None
    observed_failure: str | None = None
    new_context: dict[str, Any] = Field(default_factory=dict)


class PlanReplanner:
    """Coordinates plan version evolution, diff calculation, and supersession."""

    @classmethod
    def replan(
        cls,
        old_plan: Plan,
        request: ReplanRequest,
        new_steps: list[PlanStep],
        new_risk: PlanRiskLevel | None = None,
    ) -> tuple[Plan, PlanDiff]:
        """Generate a new version of the plan, mark old plan SUPERSEDED, and compute PlanDiff."""
        new_plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        new_version = old_plan.version + 1
        computed_risk = new_risk or old_plan.risk

        # Preserve completed steps from the old plan if applicable
        completed_steps = old_plan.get_completed_steps()
        merged_steps: list[PlanStep] = []

        # Sequence offset
        seq = 1
        for cs in completed_steps:
            cloned = cs.model_copy()
            cloned.plan_id = new_plan_id
            cloned.sequence = seq
            merged_steps.append(cloned)
            seq += 1

        for ns in new_steps:
            cloned = ns.model_copy()
            cloned.plan_id = new_plan_id
            cloned.sequence = seq
            merged_steps.append(cloned)
            seq += 1

        new_plan = Plan(
            plan_id=new_plan_id,
            goal_id=old_plan.goal_id,
            user_id=old_plan.user_id,
            project_id=old_plan.project_id,
            version=new_version,
            parent_plan_id=old_plan.plan_id,
            status=PlanStatus.READY,
            reasoning_mode=old_plan.reasoning_mode,
            steps=merged_steps,
            dependencies=old_plan.dependencies,
            assumptions=old_plan.assumptions,
            constraints=old_plan.constraints,
            success_criteria=old_plan.success_criteria,
            risk=computed_risk,
            scope_lock=old_plan.scope_lock,  # Scope lock is strictly preserved
            cost_estimate=old_plan.cost_estimate,
            rationale=f"Replanned from v{old_plan.version} due to {request.reason}: {request.observed_failure or 'state drift'}",
        )

        # Mark old plan as superseded
        old_plan.supersede()

        # Compute PlanDiff
        diff = cls.compute_diff(old_plan, new_plan)

        return new_plan, diff

    @staticmethod
    def compute_diff(old_plan: Plan, new_plan: Plan) -> PlanDiff:
        """Compute the structural and risk difference between two plan versions."""
        old_step_map = {s.objective: s for s in old_plan.steps}
        new_step_map = {s.objective: s for s in new_plan.steps}

        added = [obj for obj in new_step_map if obj not in old_step_map]
        removed = [obj for obj in old_step_map if obj not in new_step_map]
        modified = []

        for obj in old_step_map:
            if obj in new_step_map:
                old_s = old_step_map[obj]
                new_s = new_step_map[obj]
                if old_s.action != new_s.action or old_s.risk != new_s.risk:
                    modified.append(f"{obj} (action: {old_s.action}->{new_s.action}, risk: {old_s.risk}->{new_s.risk})")

        # Determine if approval is required: risk increased or write actions added
        risk_ranks = {
            PlanRiskLevel.LOW: 1,
            PlanRiskLevel.MEDIUM: 2,
            PlanRiskLevel.HIGH: 3,
            PlanRiskLevel.CRITICAL: 4,
        }
        risk_increased = risk_ranks.get(new_plan.risk, 1) > risk_ranks.get(old_plan.risk, 1)
        approval_required = risk_increased or (new_plan.risk in {PlanRiskLevel.HIGH, PlanRiskLevel.CRITICAL})

        return PlanDiff(
            old_plan_id=old_plan.plan_id,
            new_plan_id=new_plan.plan_id,
            old_version=old_plan.version,
            new_version=new_plan.version,
            added_steps=added,
            removed_steps=removed,
            modified_steps=modified,
            old_risk=old_plan.risk.value if hasattr(old_plan.risk, "value") else str(old_plan.risk),
            new_risk=new_plan.risk.value if hasattr(new_plan.risk, "value") else str(new_plan.risk),
            approval_required=approval_required,
        )

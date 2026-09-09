"""User-facing plan previews, contextual explanations, and decision factors for Kairo Cognitive Planning (Task 41).

Enforces:
1. Clear, structured previews (Goal, Steps, Risk, Required Approval, Potential Blockers).
2. Contextual explanations ('Why this step?') based on observable decision factors without exposing private chain-of-thought.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.cognition.plans import Plan, PlanRiskLevel
from app.cognition.steps import PlanStep


class PlanPreview(BaseModel):
    """User-facing executive preview of a proposed plan."""

    model_config = ConfigDict(extra="ignore")

    goal_id: str
    plan_id: str
    version: int
    total_steps: int
    risk: str
    approval_required: bool
    estimated_duration_seconds: float
    potential_blockers: list[str] = Field(default_factory=list)
    step_summaries: list[dict[str, Any]] = Field(default_factory=list)


class StepExplanation(BaseModel):
    """Explains why an individual step is necessary and how it will be verified."""

    model_config = ConfigDict(extra="ignore")

    step_id: str
    objective: str
    action: str
    why_this_step: str
    risk: str
    dependencies: list[str]
    verification_method: str


class PlanExplainer:
    """Generates user-safe previews and explanations."""

    @staticmethod
    def generate_preview(plan: Plan) -> PlanPreview:
        """Create a user-facing preview of the plan."""
        approval_required = plan.risk in {PlanRiskLevel.HIGH, PlanRiskLevel.CRITICAL}
        for s in plan.steps:
            if s.risk.value == "DESTRUCTIVE":
                approval_required = True
                break

        est_duration = sum(15.0 for _ in plan.steps)
        summaries = [
            {
                "sequence": s.sequence,
                "step_id": s.step_id,
                "objective": s.objective,
                "action": s.action,
                "risk": s.risk.value if hasattr(s.risk, "value") else str(s.risk),
            }
            for s in plan.steps
        ]

        return PlanPreview(
            goal_id=plan.goal_id,
            plan_id=plan.plan_id,
            version=plan.version,
            total_steps=len(plan.steps),
            risk=plan.risk.value if hasattr(plan.risk, "value") else str(plan.risk),
            approval_required=approval_required,
            estimated_duration_seconds=est_duration,
            potential_blockers=[],
            step_summaries=summaries,
        )

    @staticmethod
    def explain_step(step: PlanStep, parent_plan: Plan | None = None) -> StepExplanation:
        """Provide a rationale for why a step exists in the plan."""
        why = f"Step is required to achieve objective '{step.objective}'."
        action = step.action.lower()

        if "inspect" in action or "read" in action or "query" in action:
            why = (
                f"Kairo is observing '{step.action}' before performing any modifications "
                "to ground the action in verified state (Read-First Principle)."
            )
        elif "patch" in action or "write" in action:
            why = (
                f"Applying targeted change '{step.action}' based on the verified root cause "
                "from preceding diagnostic inspection steps."
            )
        elif "test" in action or "runner" in action:
            why = "Executing regression and unit tests to independently verify that changes did not introduce breakage."
        elif "health" in action or "verify" in action:
            why = "Conducting end-to-end health probe to ensure all service invariants remain operational."

        return StepExplanation(
            step_id=step.step_id,
            objective=step.objective,
            action=step.action,
            why_this_step=why,
            risk=step.risk.value if hasattr(step.risk, "value") else str(step.risk),
            dependencies=step.dependencies,
            verification_method=step.verification.check_type,
        )

"""Structured task planner, objective decomposition, template library, and plan validator (Spec 11, 12, 13, 74, 75, 96)."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.models.router import ModelRouter, get_model_router
from app.tasks.dependencies import DependencyResolver
from app.tasks.policies import TaskPolicyEngine, TaskPolicyViolationError
from app.tasks.replanner import TaskReplanner
from app.tasks.schemas import (
    StepStatus,
    TaskBudget,
    TaskPlanSchema,
    TaskResource,
    TaskRiskLevel,
    TaskStepSchema,
    VerificationCriterion,
)

logger = logging.getLogger("kairo.tasks.planner")


class InvalidPlanError(ValueError):
    """Raised when a generated plan fails structural, dependency, or security validation."""
    pass


class TaskPlanner:
    """Decomposes an objective into a structured, validated DAG TaskPlan."""

    def __init__(self, model_router: ModelRouter | None = None) -> None:
        self.model_router = model_router or get_model_router()

    async def create_initial_plan(
        self,
        task_id: str,
        objective: str,
        context: dict[str, Any] | None = None,
        budget: TaskBudget | None = None,
    ) -> TaskPlanSchema:
        """Create a version 1 TaskPlan for the objective (Spec 11, 12)."""
        clean_obj = objective.strip()
        obj_lower = clean_obj.lower()

        # Check for matching built-in templates first (Spec 96)
        if any(w in obj_lower for w in ["ci failure", "ci is failing", "investigate ci", "investigate why"]):
            plan = self._build_ci_investigation_template(task_id, clean_obj)
        elif any(w in obj_lower for w in ["research", "vector-search", "summarize what matters", "analyze documentation"]):
            plan = self._build_research_template(task_id, clean_obj)
        elif any(w in obj_lower for w in ["fix the failing test", "fix test", "safe code fix", "apply fix"]):
            plan = self._build_code_fix_template(task_id, clean_obj)
        else:
            # General fallback structured decomposition
            plan = self._build_general_task_plan(task_id, clean_obj)

        # Validate the generated plan (Spec 13)
        self.validate_plan(plan, clean_obj, budget)
        return plan

    def validate_plan(
        self,
        plan: TaskPlanSchema,
        original_objective: str,
        budget: TaskBudget | None = None,
    ) -> None:
        """Validate DAG integrity, dependency absence, goal drift, and budget bounds (Spec 13, 139)."""
        if not plan.steps:
            raise InvalidPlanError("Plan must contain at least one step.")

        # 1. Validate DAG topological order and cycle freedom (Spec 10)
        DependencyResolver.validate_dag(plan.steps)

        # 2. Validate against goal drift (Spec 139)
        for s in plan.steps:
            TaskPolicyEngine.validate_goal_alignment(original_objective, s.objective)

        # 3. Validate step count does not violate budget limit (Spec 14)
        if budget and len(plan.steps) > budget.max_steps:
            raise InvalidPlanError(
                f"Plan step count ({len(plan.steps)}) exceeds maximum allowed step budget ({budget.max_steps})."
            )

    # --- Built-in Specialized Task Templates (Spec 96) ---

    def _build_research_template(self, task_id: str, objective: str) -> TaskPlanSchema:
        """Template for multi-source research tasks with parallel read steps."""
        plan_id = f"plan_{task_id}_v1"
        s1 = TaskStepSchema(
            id=f"step_{task_id}_1",
            task_id=task_id,
            plan_id=plan_id,
            sequence=1,
            title="Search and gather primary research documentation",
            objective="Query documentation and reference sources for target domain",
            skill_id="web_research",
            tool_name="web_search",
            arguments={"query": objective},
            dependencies=[],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        s2 = TaskStepSchema(
            id=f"step_{task_id}_2",
            task_id=task_id,
            plan_id=plan_id,
            sequence=2,
            title="Inspect secondary technical sources and benchmarks in parallel",
            objective="Retrieve secondary benchmarks and complementary technical details",
            skill_id="web_research",
            tool_name="web_search",
            arguments={"query": f"{objective} architecture benchmarks"},
            dependencies=[],  # Independent! Can run in parallel with step 1
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        s3 = TaskStepSchema(
            id=f"step_{task_id}_3",
            task_id=task_id,
            plan_id=plan_id,
            sequence=3,
            title="Synthesize findings and compile architectural summary",
            objective="Synthesize evidence from gathered sources into structured actionable report",
            skill_id="general_reasoning",
            tool_name=None,
            dependencies=[s1.id, s2.id],  # Depends on both research steps
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        steps = [s1, s2, s3]
        criteria = [
            VerificationCriterion(
                type="subjective_llm",
                description="Comprehensive synthesis summarizing key findings with citations",
            )
        ]
        return TaskPlanSchema(
            id=plan_id,
            task_id=task_id,
            version=1,
            plan_hash=TaskReplanner.compute_plan_hash(steps),
            steps=steps,
            verification_criteria=criteria,
        )

    def _build_ci_investigation_template(self, task_id: str, objective: str) -> TaskPlanSchema:
        """Template for CI / GitHub failure analysis."""
        plan_id = f"plan_{task_id}_v1"
        s1 = TaskStepSchema(
            id=f"step_{task_id}_1",
            task_id=task_id,
            plan_id=plan_id,
            sequence=1,
            title="Inspect CI workflow run and failure logs",
            objective="Fetch the latest failing workflow run logs and error stack trace",
            skill_id="github_intelligence",
            tool_name="github_get_workflow_run",
            dependencies=[],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        s2 = TaskStepSchema(
            id=f"step_{task_id}_2",
            task_id=task_id,
            plan_id=plan_id,
            sequence=2,
            title="Identify failing commit and diff",
            objective="Analyze commit history and diff that introduced the failure",
            skill_id="developer",
            tool_name="git_diff",
            dependencies=[s1.id],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        s3 = TaskStepSchema(
            id=f"step_{task_id}_3",
            task_id=task_id,
            plan_id=plan_id,
            sequence=3,
            title="Research root cause and identify necessary fixes",
            objective="Synthesize failure logs with code diff to determine root cause",
            skill_id="general_reasoning",
            tool_name=None,
            dependencies=[s2.id],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        steps = [s1, s2, s3]
        criteria = [
            VerificationCriterion(
                type="contains_text",
                target="root cause",
                description="Investigation report clearly documents root cause",
            )
        ]
        return TaskPlanSchema(
            id=plan_id,
            task_id=task_id,
            version=1,
            plan_hash=TaskReplanner.compute_plan_hash(steps),
            steps=steps,
            verification_criteria=criteria,
        )

    def _build_code_fix_template(self, task_id: str, objective: str) -> TaskPlanSchema:
        """Template for safe code fix flow (Inspect -> Propose -> Approval -> Apply -> Verify)."""
        plan_id = f"plan_{task_id}_v1"
        s1 = TaskStepSchema(
            id=f"step_{task_id}_1",
            task_id=task_id,
            plan_id=plan_id,
            sequence=1,
            title="Inspect failing test output and target files",
            objective="Read test failure output and identify offending source code file",
            skill_id="developer",
            tool_name="code_search",
            dependencies=[],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        s2 = TaskStepSchema(
            id=f"step_{task_id}_2",
            task_id=task_id,
            plan_id=plan_id,
            sequence=2,
            title="Propose patch for test fix",
            objective="Generate exact diff patch to resolve the failure without side effects",
            skill_id="developer",
            tool_name="git_diff",
            dependencies=[s1.id],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        s3 = TaskStepSchema(
            id=f"step_{task_id}_3",
            task_id=task_id,
            plan_id=plan_id,
            sequence=3,
            title="Apply proposed patch to source file",
            objective="Write updated code to target file",
            skill_id="developer",
            tool_name="edit_file",
            dependencies=[s2.id],
            risk_level=TaskRiskLevel.WRITE,
            approval_required=True,  # Invariant: File modification requires approval
            resources=[TaskResource(type="FILE", id="backend/app/target.py", mode="WRITE")],
        )
        s4 = TaskStepSchema(
            id=f"step_{task_id}_4",
            task_id=task_id,
            plan_id=plan_id,
            sequence=4,
            title="Execute test suite to verify fix",
            objective="Run pytest test command to verify test passes with exit code 0",
            skill_id="developer",
            tool_name="run_tests",
            dependencies=[s3.id],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        steps = [s1, s2, s3, s4]
        criteria = [
            VerificationCriterion(
                type="exit_code",
                target="0",
                expected_value=0,
                description="Test suite runs cleanly with exit code 0",
            )
        ]
        return TaskPlanSchema(
            id=plan_id,
            task_id=task_id,
            version=1,
            plan_hash=TaskReplanner.compute_plan_hash(steps),
            steps=steps,
            verification_criteria=criteria,
        )

    def _build_general_task_plan(self, task_id: str, objective: str) -> TaskPlanSchema:
        """Generic two-step read and synthesis task plan."""
        plan_id = f"plan_{task_id}_v1"
        s1 = TaskStepSchema(
            id=f"step_{task_id}_1",
            task_id=task_id,
            plan_id=plan_id,
            sequence=1,
            title=f"Analyze objective: {objective[:50]}",
            objective=objective,
            skill_id="general_reasoning",
            tool_name=None,
            dependencies=[],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        s2 = TaskStepSchema(
            id=f"step_{task_id}_2",
            task_id=task_id,
            plan_id=plan_id,
            sequence=2,
            title="Synthesize and finalize outcome",
            objective="Compile final results and verify completion criteria",
            skill_id="general_reasoning",
            tool_name=None,
            dependencies=[s1.id],
            risk_level=TaskRiskLevel.READ,
            approval_required=False,
        )
        steps = [s1, s2]
        return TaskPlanSchema(
            id=plan_id,
            task_id=task_id,
            version=1,
            plan_hash=TaskReplanner.compute_plan_hash(steps),
            steps=steps,
            verification_criteria=[
                VerificationCriterion(type="subjective_llm", description="Verify objective satisfied")
            ],
        )

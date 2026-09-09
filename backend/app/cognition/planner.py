"""Central Cognitive Planner for Kairo Cognitive Planning & Reasoning (Task 41).

Core Architectural Invariant:
LLM: PROPOSES
Planner: STRUCTURES
Policy: AUTHORIZES
Task Engine: EXECUTES
Verifier: CHECKS
World Model: REPRESENTS CURRENT STATE
Memory: REMEMBERS RELEVANT HISTORY

The Planner must NEVER directly execute tools or perform external side effects.
"""

from datetime import UTC, datetime
import logging
from typing import Any
import uuid

from app.cognition.alternatives import AlternativeEvaluator, PlanAlternative
from app.cognition.assumptions import AssumptionValidator, PlanAssumption
from app.cognition.confidence import EvidenceAssessment
from app.cognition.constraints import ConstraintEngine
from app.cognition.decomposer import PlanDecomposer
from app.cognition.evaluator import PlanEvaluator, PlanValidationReport
from app.cognition.explain import PlanExplainer, PlanPreview, StepExplanation
from app.cognition.goals import Goal, GoalPriority, GoalScope, GoalStatus, GoalType
from app.cognition.plans import Plan, PlanDiff, PlanRiskLevel, PlanStatus, ScopeLock
from app.cognition.reasoning import DecisionFactors, ReasoningEngine, ReasoningMode
from app.cognition.replanner import PlanReplanner, ReplanReason, ReplanRequest
from app.cognition.scheduler import PlanScheduler
from app.cognition.state import CognitiveStateBridge, PlanFreshnessState
from app.cognition.steps import PlanStep, StepRiskLevel, StepStatus
from app.cognition.strategies import StrategyRegistry
from app.cognition.verifier import CognitiveVerifier, StepVerificationResult

logger = logging.getLogger("kairo.cognition.planner")


def utc_now() -> datetime:
    return datetime.now(UTC)


class CognitivePlanner:
    """End-to-end cognitive planning and reasoning engine."""

    def __init__(
        self,
        constraint_engine: ConstraintEngine | None = None,
        strategy_registry: StrategyRegistry | None = None,
        scheduler: PlanScheduler | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self.constraints = constraint_engine or ConstraintEngine()
        self.strategies = strategy_registry or StrategyRegistry()
        self.scheduler = scheduler or PlanScheduler()
        self.event_bus = event_bus

        # In-memory stores (backed by models via repository/session in DB mode)
        self._goals: dict[str, Goal] = {}
        self._plans: dict[str, Plan] = {}
        self._freshness: dict[str, PlanFreshnessState] = {}
        self._traces: list[dict[str, Any]] = []

    def create_goal(
        self,
        description: str,
        user_id: str,
        project_id: str | None = None,
        goal_type: GoalType | None = None,
        priority: GoalPriority = GoalPriority.NORMAL,
        constraints: dict[str, Any] | None = None,
        success_criteria: list[str] | None = None,
        allowed_resources: list[str] | None = None,
        allowed_environments: list[str] | None = None,
        deadline: datetime | None = None,
    ) -> Goal:
        """Create and register a validated Goal."""
        # Defense against prompt injection / goal hijacking in description
        sanitized_desc = self._sanitize_goal_input(description)

        # Infer goal type if not provided
        if goal_type is None:
            desc_lower = sanitized_desc.lower()
            if any(w in desc_lower for w in ("fix", "patch", "build", "code", "ci")):
                goal_type = GoalType.DEVELOPMENT
            elif any(w in desc_lower for w in ("research", "find", "compare")):
                goal_type = GoalType.RESEARCH
            elif any(w in desc_lower for w in ("cron", "trigger", "schedule")):
                goal_type = GoalType.AUTOMATION
            else:
                goal_type = GoalType.OPERATIONAL

        scope = GoalScope(
            user_id=user_id,
            project_id=project_id,
            allowed_resources=allowed_resources or [],
            allowed_environments=allowed_environments or ["development"],
        )

        goal = Goal(
            description=sanitized_desc,
            goal_type=goal_type,
            priority=priority,
            constraints=constraints or {},
            success_criteria=success_criteria or ["Goal executed with verified success criteria."],
            scope=scope,
            deadline=deadline,
        )
        self._goals[goal.goal_id] = goal
        self._emit_event("goal.created", {"goal_id": goal.goal_id, "user_id": user_id})
        return goal

    def build_plan(
        self,
        goal: Goal,
        reasoning_mode: ReasoningMode | None = None,
        override_risk: PlanRiskLevel | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[Plan, PlanValidationReport, list[PlanAlternative]]:
        """Transform a Goal into a structured Plan with alternatives and validation."""
        selected_mode = reasoning_mode or ReasoningEngine.select_mode(goal.description, goal.goal_type.value)
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"

        # 1. Decompose into PlanSteps
        steps = PlanDecomposer.decompose_goal(goal, plan_id, selected_mode, context)

        # 2. Derive Overall Risk Level
        highest_step_risk = StepRiskLevel.READ
        for s in steps:
            if s.risk == StepRiskLevel.DESTRUCTIVE:
                highest_step_risk = StepRiskLevel.DESTRUCTIVE
                break
            elif s.risk == StepRiskLevel.WRITE:
                highest_step_risk = StepRiskLevel.WRITE

        risk_map = {
            StepRiskLevel.READ: PlanRiskLevel.LOW,
            StepRiskLevel.WRITE: PlanRiskLevel.MEDIUM,
            StepRiskLevel.DESTRUCTIVE: PlanRiskLevel.HIGH,
        }
        computed_risk = override_risk or risk_map.get(highest_step_risk, PlanRiskLevel.LOW)

        # 3. Create ScopeLock
        scope_lock = ScopeLock(
            allowed_resources=list(goal.scope.allowed_resources),
            allowed_environments=list(goal.scope.allowed_environments),
            project_id=goal.scope.project_id,
            user_id=goal.scope.user_id,
            locked=True,
        )

        # 4. Assemble Plan
        plan = Plan(
            plan_id=plan_id,
            goal_id=goal.goal_id,
            user_id=goal.scope.user_id,
            project_id=goal.scope.project_id,
            version=1,
            status=PlanStatus.DRAFT,
            reasoning_mode=selected_mode.value,
            steps=steps,
            dependencies={s.step_id: s.dependencies for s in steps},
            constraints=goal.constraints,
            success_criteria=goal.success_criteria,
            risk=computed_risk,
            scope_lock=scope_lock,
            rationale=f"Structured using {selected_mode.value} mode for objective: {goal.description}",
        )

        # 5. Evaluate Feasibility and Validation
        validation_report = PlanEvaluator.evaluate_plan(
            plan=plan,
            environment=goal.scope.allowed_environments[0] if goal.scope.allowed_environments else "development",
        )

        if validation_report.is_valid and validation_report.is_feasible:
            plan.status = PlanStatus.READY

        # 6. Generate Alternatives
        alternatives = AlternativeEvaluator.generate_alternatives(goal.description, plan)

        # 7. Store Plan and Freshness State
        self._plans[plan.plan_id] = plan
        self._freshness[plan.plan_id] = PlanFreshnessState(plan_id=plan.plan_id)

        # 8. Record Trace and Emit Event
        self._record_trace(
            plan_id=plan.plan_id,
            event_type="plan.created",
            decision_factors={
                "reasoning_mode": selected_mode.value,
                "steps_count": len(steps),
                "quality_score": validation_report.quality_score,
                "risk": plan.risk.value,
            },
        )
        self._emit_event("plan.created", {"plan_id": plan.plan_id, "goal_id": goal.goal_id})

        return plan, validation_report, alternatives

    def replan_plan(
        self,
        plan_id: str,
        reason: ReplanReason,
        failure_description: str | None = None,
    ) -> tuple[Plan, PlanDiff]:
        """Adaptively re-plan when assumptions or verification checks fail."""
        old_plan = self._plans.get(plan_id)
        if not old_plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        req = ReplanRequest(
            plan_id=plan_id,
            reason=reason,
            observed_failure=failure_description,
        )

        goal = self._goals.get(old_plan.goal_id)
        if not goal:
            raise ValueError(f"Underlying goal '{old_plan.goal_id}' not found.")

        # Re-decompose with diagnostic or fallback mode
        new_mode = ReasoningMode.DIAGNOSTIC if reason in {ReplanReason.DEPENDENCY_FAILURE, ReplanReason.ASSUMPTION_FAILURE} else ReasoningMode.DECOMPOSITION
        temp_id = f"plan_{uuid.uuid4().hex[:12]}"
        new_steps = PlanDecomposer.decompose_goal(goal, temp_id, new_mode)

        new_plan, diff = PlanReplanner.replan(old_plan, req, new_steps)

        self._plans[new_plan.plan_id] = new_plan
        self._freshness[new_plan.plan_id] = PlanFreshnessState(plan_id=new_plan.plan_id)

        self._record_trace(
            plan_id=new_plan.plan_id,
            event_type="plan.replanned",
            decision_factors={
                "old_version": old_plan.version,
                "new_version": new_plan.version,
                "reason": reason.value,
                "approval_required": diff.approval_required,
            },
        )
        self._emit_event("plan.replanned", {"old_plan_id": plan_id, "new_plan_id": new_plan.plan_id})
        return new_plan, diff

    def verify_step_execution(
        self,
        plan_id: str,
        step_id: str,
        output_result: dict[str, Any] | None,
        current_state: dict[str, Any] | None = None,
    ) -> StepVerificationResult:
        """Run independent verification on a completed step (Spec 74-79)."""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        step = plan.get_step(step_id)
        if not step:
            raise ValueError(f"Step '{step_id}' not found in plan '{plan_id}'.")

        state = current_state or CognitiveStateBridge.get_current_context(plan.user_id, plan.project_id)
        verification_result = CognitiveVerifier.verify_postconditions(step, output_result, state)

        if verification_result.verified:
            step.status = StepStatus.COMPLETED
            step.output_result = output_result
            self._emit_event("plan.step_completed", {"plan_id": plan_id, "step_id": step_id})
        else:
            step.status = StepStatus.FAILED
            step.error_message = verification_result.failure_reason
            self._emit_event("plan.step_failed", {"plan_id": plan_id, "step_id": step_id, "reason": verification_result.failure_reason})

        # Check if entire plan completed
        if plan.is_all_completed():
            plan.status = PlanStatus.COMPLETED
            self._emit_event("plan.completed", {"plan_id": plan_id})

        return verification_result

    def merge_subplans(
        self,
        parent_goal: Goal,
        subplans: list[Plan],
        supervisor_user_id: str,
    ) -> Plan:
        """Merge specialist sub-agent plans (Multi-Agent Planning, Specs 106-110)."""
        merged_steps: list[PlanStep] = []
        seen_objectives: set[str] = set()
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"

        seq = 1
        for subplan in subplans:
            for step in subplan.steps:
                if step.objective not in seen_objectives:
                    seen_objectives.add(step.objective)
                    cloned = step.model_copy()
                    cloned.plan_id = plan_id
                    cloned.sequence = seq
                    merged_steps.append(cloned)
                    seq += 1

        scope_lock = ScopeLock(
            allowed_resources=list(parent_goal.scope.allowed_resources),
            allowed_environments=list(parent_goal.scope.allowed_environments),
            project_id=parent_goal.scope.project_id,
            user_id=supervisor_user_id,
            locked=True,
        )

        merged_plan = Plan(
            plan_id=plan_id,
            goal_id=parent_goal.goal_id,
            user_id=supervisor_user_id,
            project_id=parent_goal.scope.project_id,
            version=1,
            status=PlanStatus.READY,
            reasoning_mode="MULTI_AGENT_MERGE",
            steps=merged_steps,
            dependencies={s.step_id: s.dependencies for s in merged_steps},
            constraints=parent_goal.constraints,
            success_criteria=parent_goal.success_criteria,
            risk=PlanRiskLevel.MEDIUM,
            scope_lock=scope_lock,
            rationale=f"Merged {len(subplans)} specialist subplans under Supervisor coordination.",
        )

        self._plans[merged_plan.plan_id] = merged_plan
        return merged_plan

    def get_plan(self, plan_id: str) -> Plan | None:
        """Fetch plan by ID."""
        return self._plans.get(plan_id)

    def get_goal(self, goal_id: str) -> Goal | None:
        """Fetch goal by ID."""
        return self._goals.get(goal_id)

    def get_plan_preview(self, plan_id: str) -> PlanPreview:
        """Generate user-facing preview."""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")
        return PlanExplainer.generate_preview(plan)

    def explain_step(self, plan_id: str, step_id: str) -> StepExplanation:
        """Generate structured rationale for why a step is necessary."""
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")
        step = plan.get_step(step_id)
        if not step:
            raise ValueError(f"Step '{step_id}' not found in plan '{plan_id}'.")
        return PlanExplainer.explain_step(step, plan)

    def get_dashboard_summary(self, user_id: str) -> dict[str, Any]:
        """Aggregate high-level cognitive telemetry for user command center."""
        user_goals = [g for g in self._goals.values() if g.scope.user_id == user_id]
        user_plans = [p for p in self._plans.values() if p.user_id == user_id]

        active_plans = [p for p in user_plans if p.status in {PlanStatus.RUNNING, PlanStatus.READY}]
        completed_plans = [p for p in user_plans if p.status == PlanStatus.COMPLETED]
        waiting_approval = [p for p in user_plans if p.status == PlanStatus.WAITING_APPROVAL or p.risk in {PlanRiskLevel.HIGH, PlanRiskLevel.CRITICAL}]

        return {
            "total_goals": len(user_goals),
            "total_plans": len(user_plans),
            "active_plans": len(active_plans),
            "completed_plans": len(completed_plans),
            "waiting_approval": len(waiting_approval),
            "plans": [PlanExplainer.generate_preview(p).model_dump() for p in user_plans[:10]],
            "queue": self.scheduler.get_queue_status(),
        }

    @staticmethod
    def _sanitize_goal_input(raw_input: str) -> str:
        """Disarm potential prompt injection attempts in goal description."""
        # Strip command override tokens
        disarmed = raw_input.replace("<system>", "").replace("</system>", "")
        disarmed = disarmed.replace("IGNORE PREVIOUS INSTRUCTIONS", "[BLOCKED_INSTRUCTION]")
        disarmed = disarmed.replace("BYPASS_POLICY", "[BLOCKED_TOKEN]")
        return disarmed.strip()

    def _record_trace(self, plan_id: str, event_type: str, decision_factors: dict[str, Any]) -> None:
        """Record append-only trace record."""
        trace = {
            "id": f"trc_{uuid.uuid4().hex[:12]}",
            "plan_id": plan_id,
            "event_type": event_type,
            "decision_factors": decision_factors,
            "timestamp": utc_now().isoformat(),
        }
        self._traces.append(trace)

    def _emit_event(self, event_name: str, payload: dict[str, Any]) -> None:
        """Emit event on the EventBus if connected."""
        if self.event_bus and hasattr(self.event_bus, "publish"):
            try:
                self.event_bus.publish(f"cognition.{event_name}", payload)
            except Exception as e:
                logger.warning(f"Failed to publish cognitive event '{event_name}': {e}")

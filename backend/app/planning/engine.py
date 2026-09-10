"""Strategic planning engine orchestrating gap analysis, synthesis, analysis, and execution proposals (Task 58)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.planning.critical_path import critical_path_engine
from app.planning.milestones import milestone_manager
from app.planning.phases import phase_manager
from app.planning.provenance import plan_provenance_tracker
from app.planning.resources import resource_manager
from app.planning.risks import plan_risk_engine
from app.planning.scheduling import scheduling_engine
from app.planning.schemas import (
    CurrentStateAssessment,
    DesiredStateDefinition,
    GapAnalysis,
    HealthStatus,
    PlanCheckpoint,
    PlanMilestone,
    PlanPhase,
    PlanStatus,
    RiskSeverity,
    StrategicPlan,
    StrategyOption,
    WorkPackage,
)
from app.planning.strategies import strategy_generator
from app.planning.tasks import task_manager

logger = logging.getLogger(__name__)


class StrategicPlanningEngine:
    """Core domain engine answering: 'How do we get from current state to desired future state?'"""

    def compute_gap_analysis(
        self,
        current_state: CurrentStateAssessment,
        desired_state: DesiredStateDefinition,
    ) -> GapAnalysis:
        """Compute missing capabilities, technical gaps, blockers, and decisions needed."""
        verified_aspects_lower = {a.lower() for a in current_state.verified_aspects}
        missing_capabilities: list[str] = []
        technical_gaps: list[str] = []
        blockers: list[str] = []
        required_decisions: list[str] = []

        # Compare completion invariants against verified aspects
        for inv in desired_state.completion_invariants:
            if not any(v in inv.lower() for v in verified_aspects_lower):
                missing_capabilities.append(f"Target invariant not met: '{inv}'")

        # Compare metrics
        for metric, target_val in desired_state.target_metrics.items():
            current_val = current_state.active_telemetry.get(metric)
            if current_val is None:
                technical_gaps.append(f"Telemetry missing for target metric '{metric}' (target: {target_val}).")
            else:
                is_inverse = any(k in metric.lower() for k in ("latency", "error", "cost", "time", "deficit", "downtime"))
                has_gap = (current_val > target_val) if is_inverse else (current_val < target_val)
                if has_gap or (current_val != target_val and not is_inverse):
                    technical_gaps.append(
                        f"Metric deficit in '{metric}': current {current_val} vs target {target_val}."
                    )

        if current_state.is_stale:
            blockers.append("Current environment state is STALE. Fresh digital twin sync required.")

        return GapAnalysis(
            missing_capabilities=missing_capabilities,
            missing_resources=[],
            technical_gaps=technical_gaps,
            blockers=blockers,
            required_decisions=required_decisions,
        )

    def synthesize_strategic_plan(
        self,
        name: str,
        purpose: str,
        current_state: CurrentStateAssessment,
        desired_state: DesiredStateDefinition,
        goal_id: str | None = None,
        strategy_option: StrategyOption | None = None,
        author: str = "SYSTEM_PLANNER",
        deadline: datetime | None = None,
        decision_id: str | None = None,
    ) -> StrategicPlan:
        """Generate a complete living strategic plan from goal, states, and selected strategy."""
        gap = self.compute_gap_analysis(current_state, desired_state)

        # Select or generate strategy
        selected_strategy = strategy_option
        if not selected_strategy:
            options = strategy_generator.generate_strategies(gap, desired_state, decision_id=decision_id)
            selected_strategy = options[0]  # Default to top recommended (Incremental)

        # 1. Generate Standard Strategic Phases
        phases: list[PlanPhase] = [
            phase_manager.create_phase(
                name="Phase 1: Environment & Pre-requisite Preparation",
                phase_order=1,
                entry_criteria=["Digital Twin synchronization verified", "Baseline telemetry active"],
                exit_criteria=["Execution sandbox validated", "Initial backups verified"],
            ),
            phase_manager.create_phase(
                name="Phase 2: Core Implementation & Work Packages",
                phase_order=2,
                entry_criteria=["Phase 1 completion verified", "Architectural decision sign-off"],
                exit_criteria=["All test assertions passing", "Work packages integrated"],
            ),
            phase_manager.create_phase(
                name="Phase 3: Rollout & Verification Gate",
                phase_order=3,
                entry_criteria=["Phase 2 exit verified", "Staging dry-run successful"],
                exit_criteria=desired_state.verification_criteria
                or ["Target metrics achieved", "Zero regressions detected"],
            ),
        ]

        p1_id = phases[0].phase_id
        p2_id = phases[1].phase_id
        p3_id = phases[2].phase_id

        # 2. Generate Milestones
        milestones: list[PlanMilestone] = [
            milestone_manager.create_milestone(
                name="M1: Preconditions & Infrastructure Ready",
                phase_id=p1_id,
                description="Sandbox, tools, and baselines validated.",
                weight=1.0,
                verification_criteria=["Digital Twin synchronization verified"],
            ),
            milestone_manager.create_milestone(
                name="M2: Core Capabilities Implemented",
                phase_id=p2_id,
                description="All underlying work package tasks executed.",
                weight=2.0,
                dependencies=["M1: Preconditions & Infrastructure Ready"],
                verification_criteria=["All test assertions passing"],
            ),
            milestone_manager.create_milestone(
                name="M3: Desired Future State Verified",
                phase_id=p3_id,
                description="Final verification and state invariants satisfied.",
                weight=3.0,
                dependencies=["M2: Core Capabilities Implemented"],
                verification_criteria=desired_state.completion_invariants or ["Target metrics achieved"],
            ),
        ]

        # 3. Generate Tasks & Work Packages
        t1 = task_manager.create_task(
            title="Sync Digital Twin state & verify baselines",
            description="Verify telemetry and environmental invariants before applying mutations.",
            phase_id=p1_id,
            duration_min=0.5,
            duration_expected=1.0,
            duration_max=2.0,
            verification_criteria=["Digital Twin synchronization verified"],
        )
        t2 = task_manager.create_task(
            title="Execute core strategic transformation tasks",
            description="Apply incremental or modular changes aligned with selected strategy.",
            phase_id=p2_id,
            dependencies=[t1.task_id],
            duration_min=1.0,
            duration_expected=2.5,
            duration_max=5.0,
            verification_criteria=["All test assertions passing"],
        )
        t3 = task_manager.create_task(
            title="Run comprehensive verification and acceptance suite",
            description="Verify that desired state invariants and health checks hold true.",
            phase_id=p3_id,
            dependencies=[t2.task_id],
            duration_min=0.5,
            duration_expected=1.5,
            duration_max=3.0,
            verification_criteria=desired_state.verification_criteria or ["Target metrics achieved"],
        )

        tasks = [t1, t2, t3]

        wp1 = WorkPackage(
            phase_id=p1_id,
            name="WP-1: Environment Readiness",
            description="Prerequisites and readiness package",
            task_ids=[t1.task_id],
        )
        wp2 = WorkPackage(
            phase_id=p2_id,
            name="WP-2: Core Transformation",
            description="Core implementation work package",
            task_ids=[t2.task_id],
        )
        wp3 = WorkPackage(
            phase_id=p3_id,
            name="WP-3: Verification & Sign-off",
            description="Verification suite and acceptance package",
            task_ids=[t3.task_id],
        )
        work_packages = [wp1, wp2, wp3]

        # Link to phases
        phases[0].milestone_ids = [milestones[0].milestone_id]
        phases[0].package_ids = [wp1.package_id]
        phases[1].milestone_ids = [milestones[1].milestone_id]
        phases[1].package_ids = [wp2.package_id]
        phases[2].milestone_ids = [milestones[2].milestone_id]
        phases[2].package_ids = [wp3.package_id]

        # 4. Schedule Execution Waves
        waves = scheduling_engine.cluster_execution_waves(tasks)

        # 5. Checkpoints
        checkpoints = [
            PlanCheckpoint(
                trigger_milestone_id=milestones[0].milestone_id,
                name="CP-1: Post-Preparation Health Check",
                expected_state={"preconditions_met": True, "stale": False},
            ),
            PlanCheckpoint(
                trigger_milestone_id=milestones[1].milestone_id,
                name="CP-2: Mid-Plan Progress & Variance Review",
                expected_state={"errors": 0, "tests_passed": True},
            ),
        ]

        # 6. Multi-level Risk Evaluation
        risks = plan_risk_engine.evaluate_plan_risks(selected_strategy, tasks, milestones)

        # Assemble plan
        plan = StrategicPlan(
            name=name,
            purpose=purpose,
            goal_id=goal_id,
            decision_id=decision_id or selected_strategy.decision_reference,
            current_state=current_state,
            desired_state=desired_state,
            gap_analysis=gap,
            strategy=selected_strategy,
            phases=phases,
            milestones=milestones,
            work_packages=work_packages,
            tasks=tasks,
            execution_waves=waves,
            checkpoints=checkpoints,
            risks=risks,
            health=HealthStatus.ON_TRACK,
            status=PlanStatus.DRAFT,
            deadline=deadline,
        )

        # Provenance tracking
        plan.provenance = plan_provenance_tracker.build_provenance_record(
            plan=plan, author=author, source_context="STRATEGIC_PLANNING_ENGINE"
        )

        return plan

    def analyze_plan(self, plan: StrategicPlan) -> dict[str, Any]:
        """Deep structured analysis of critical path, duration, schedule feasibility, and risk."""
        cpm_result = critical_path_engine.compute_critical_path(plan.tasks)
        start_time = plan.created_at
        deadline_eval = scheduling_engine.evaluate_deadline_feasibility(
            plan.tasks, start_time=start_time, deadline=plan.deadline
        )
        total_resources = resource_manager.calculate_total_requirements(plan.tasks)
        rollback_info = plan_risk_engine.generate_rollback_strategy(plan.tasks)

        return {
            "plan_id": plan.plan_id,
            "name": plan.name,
            "strategy": {
                "name": plan.strategy.name,
                "type": plan.strategy.strategy_type.value,
                "complexity": plan.strategy.estimated_complexity,
                "reversibility": plan.strategy.reversibility,
            },
            "critical_path": cpm_result,
            "deadline_feasibility": deadline_eval,
            "total_resource_requirements": total_resources,
            "execution_waves_count": len(plan.execution_waves),
            "rollback_strategy": rollback_info,
            "risks_summary": {
                "total_risks": len(plan.risks),
                "critical_risks": len([r for r in plan.risks if r.severity == RiskSeverity.CRITICAL]),
                "high_risks": len([r for r in plan.risks if r.severity == RiskSeverity.HIGH]),
            },
        }

    def generate_execution_proposal(self, plan: StrategicPlan) -> dict[str, Any]:
        """Produce an executable plan proposal for Autonomous Execution / Policy Engine.

        INVARIANT 1: Plan is not execution.
        INVARIANT 18: Planning cannot bypass safety systems.
        """
        # Invariant 1: Plan is not execution; strictly returns proposal structure
        proposal_waves: list[dict[str, Any]] = []
        for wave in plan.execution_waves:
            wave_tasks = [t for t in plan.tasks if t.task_id in wave.task_ids]
            proposal_waves.append({
                "wave_number": wave.wave_number,
                "estimated_duration_hours": wave.estimated_duration,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "title": t.title,
                        "owner": t.owner,
                        "is_irreversible": t.is_irreversible,
                        "verification_criteria": t.verification_criteria,
                    }
                    for t in wave_tasks
                ],
            })

        return {
            "proposal_id": f"prop_{plan.plan_id}",
            "plan_id": plan.plan_id,
            "plan_name": plan.name,
            "version": plan.version,
            "status": "PROPOSAL_PENDING_AUTHORIZATION",
            "execution_boundary_enforced": True,
            "total_waves": len(proposal_waves),
            "waves": proposal_waves,
            "required_gates": {
                "policy_check_required": True,
                "authorization_required": True,
                "approval_signature_required": any(t.is_irreversible for t in plan.tasks),
            },
        }


strategic_planning_engine = StrategicPlanningEngine()

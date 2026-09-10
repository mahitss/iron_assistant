"""Multi-level risk assessment, propagation, contingency plans, and rollback gates (Task 58)."""

from __future__ import annotations

import logging
from typing import Any

from app.planning.schemas import (
    PlanMilestone,
    PlanRisk,
    PlanTask,
    RiskSeverity,
    StrategyOption,
)

logger = logging.getLogger(__name__)


class PlanRiskEngine:
    """Evaluates risks across strategic tiers, tracks risk propagation, and secures rollback strategies."""

    def evaluate_plan_risks(
        self,
        strategy: StrategyOption,
        tasks: list[PlanTask],
        milestones: list[PlanMilestone],
    ) -> list[PlanRisk]:
        """Aggregate risks from strategy characteristics, task attributes, and milestone gates."""
        risks: list[PlanRisk] = []

        # 1. Strategy-level risk
        if strategy.expected_risk in (RiskSeverity.HIGH, RiskSeverity.CRITICAL):
            risks.append(
                PlanRisk(
                    description=f"High strategic risk inherent in chosen archetype: {strategy.name}",
                    severity=strategy.expected_risk,
                    probability="HIGH" if strategy.expected_risk == RiskSeverity.CRITICAL else "MEDIUM",
                    mitigation="Implement frequent checkpoints and strict rollback criteria.",
                    contingency_plan="Halt deployment and fall back to legacy system.",
                )
            )

        # 2. Task-level risks & Irreversible actions
        for task in tasks:
            if task.is_irreversible:
                risks.append(
                    PlanRisk(
                        description=f"Irreversible task action: '{task.title}' ({task.task_id})",
                        severity=RiskSeverity.HIGH,
                        probability="LOW",
                        mitigation="Require explicit stakeholder sign-off and complete verified data backup prior to run.",
                        contingency_plan="Engage disaster recovery procedures; data recovery from cold storage.",
                    )
                )
            elif task.risk_level in (RiskSeverity.HIGH, RiskSeverity.CRITICAL):
                risks.append(
                    PlanRisk(
                        description=f"High operational task risk: '{task.title}'",
                        severity=task.risk_level,
                        probability="MEDIUM",
                        mitigation="Run dry-run simulation in sandbox before execution.",
                        contingency_plan="Isolate affected service instance and retry with bounded backoff.",
                    )
                )

        # 3. Unverified / Complex Milestones
        for m in milestones:
            if len(m.dependencies) >= 3:
                risks.append(
                    PlanRisk(
                        description=f"Milestone '{m.name}' has high dependency fan-in ({len(m.dependencies)} dependencies).",
                        severity=RiskSeverity.MEDIUM,
                        probability="MEDIUM",
                        mitigation="Continuous integration monitoring of upstream prerequisite milestones.",
                        contingency_plan="Descale dependent scope or stagger downstream deliverables.",
                    )
                )

        return risks

    def propagate_task_failure_impact(
        self,
        failed_task_id: str,
        tasks: list[PlanTask],
        milestones: list[PlanMilestone],
    ) -> dict[str, Any]:
        """Trace the downstream impact of a task failure across dependent tasks and milestones."""
        task_map = {t.task_id: t for t in tasks}
        impacted_task_ids: set[str] = set()

        # BFS forward through dependencies
        queue = [failed_task_id]
        while queue:
            curr_id = queue.pop(0)
            for t in tasks:
                if curr_id in t.dependencies and t.task_id not in impacted_task_ids:
                    impacted_task_ids.add(t.task_id)
                    queue.append(t.task_id)

        # Check impacted milestones
        impacted_milestones: list[str] = []
        for m in milestones:
            # If any impacted task is related or if milestone directly references dependencies
            for t_id in impacted_task_ids:
                if t_id in m.dependencies:
                    impacted_milestones.append(m.name)

        return {
            "failed_task_id": failed_task_id,
            "failed_task_title": task_map.get(failed_task_id, None).title if failed_task_id in task_map else "Unknown",
            "directly_blocked_task_count": len([t for t in tasks if failed_task_id in t.dependencies]),
            "total_downstream_impacted_tasks": len(impacted_task_ids),
            "impacted_task_ids": list(impacted_task_ids),
            "impacted_milestones": impacted_milestones,
            "severity": "CRITICAL" if len(impacted_task_ids) > len(tasks) * 0.4 else "HIGH",
            "recommendation": "Pause dependent waves; invoke contingency plan or trigger replanning.",
        }

    def generate_rollback_strategy(
        self,
        tasks: list[PlanTask],
    ) -> dict[str, Any]:
        """Synthesize rollback steps and safety precautions for the plan."""
        has_irreversible = any(t.is_irreversible for t in tasks)
        rollback_steps = [
            "Signal pause to autonomous execution waves.",
            "Verify state of active database transactions and revert uncommitted mutations.",
            "Switch traffic routing back to stable predecessor baseline.",
            "Verify environment health via Digital Twin telemetry.",
        ]

        if has_irreversible:
            rollback_steps.append(
                "CAUTION: Irreversible tasks present. Point-in-time snapshot restoration required for data integrity."
            )

        return {
            "rollback_trigger": "Failure of any critical wave task or unrecoverable checkpoint variance.",
            "is_fully_reversible": not has_irreversible,
            "steps": rollback_steps,
            "verification_criteria": [
                "Baseline system metrics return to normal thresholds.",
                "Zero data corruption confirmed via integrity checksums.",
            ],
        }


plan_risk_engine = PlanRiskEngine()

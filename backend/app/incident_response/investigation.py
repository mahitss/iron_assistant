"""Investigation plan generator, safe diagnostics, and Value of Information prioritization (Task 61)."""

from __future__ import annotations

import logging
import uuid

from app.incident_response.schemas import (
    CausalHypothesisItem,
    DiagnosticTask,
    InvestigationPlan,
)

logger = logging.getLogger(__name__)


class InvestigationEngine:
    """Constructs disciplined investigation plans prioritizing safe, read-only diagnostics based on Value of Information.

    Invariant 13 & 14: Investigation != Mitigation. Diagnostics do not mutate production state.
    Invariant 22 & 23: Prioritizes diagnostics with high Value of Information (VOI) to distinguish hypotheses.
    """

    def build_investigation_plan(
        self,
        incident_id: str,
        affected_resources: list[str],
        hypotheses: list[CausalHypothesisItem],
    ) -> InvestigationPlan:
        """Synthesize prioritized diagnostic tasks based on candidate hypotheses and affected resources."""
        tasks: list[DiagnosticTask] = []

        # 1. Broad baseline and health check diagnostics (low risk, high baseline value)
        for res in affected_resources[:3]:
            tasks.append(
                DiagnosticTask(
                    task_id=f"diag_health_{uuid.uuid4().hex[:6]}",
                    name=f"Check Health and Saturation: {res}",
                    target_resource=res,
                    purpose="Inspect CPU, memory, and connection saturation metrics against baselines",
                    is_read_only=True,
                    estimated_risk="LOW",
                    voi_score=0.75,
                )
            )

        # 2. Hypothesis-specific diagnostics (high VOI to confirm or refute candidate causes)
        for hyp in hypotheses:
            cause_lower = hyp.candidate_cause.lower()

            if "deploy" in cause_lower or "commit" in cause_lower:
                tasks.append(
                    DiagnosticTask(
                        task_id=f"diag_deploy_{uuid.uuid4().hex[:6]}",
                        name="Inspect Recent Deployment Diffs & Rollout Logs",
                        target_resource=affected_resources[0] if affected_resources else "cluster",
                        purpose="Compare git commit SHA, container image digest, and rollout timing",
                        is_read_only=True,
                        estimated_risk="LOW",
                        voi_score=0.95,
                    )
                )

            if "database" in cause_lower or "lock" in cause_lower or "pool" in cause_lower:
                tasks.append(
                    DiagnosticTask(
                        task_id=f"diag_db_{uuid.uuid4().hex[:6]}",
                        name="Analyze Database Lock Contention & Active Queries",
                        target_resource="db-primary",
                        purpose="Inspect pg_stat_activity, connection pool saturation, and blocked transactions",
                        is_read_only=True,
                        estimated_risk="LOW",
                        voi_score=0.90,
                    )
                )

            if "dependency" in cause_lower or "network" in cause_lower or "timeout" in cause_lower:
                tasks.append(
                    DiagnosticTask(
                        task_id=f"diag_dep_{uuid.uuid4().hex[:6]}",
                        name="Verify Upstream/Downstream Dependency Latencies",
                        target_resource=affected_resources[0] if affected_resources else "network",
                        purpose="Probe egress network latency and response codes across service boundaries",
                        is_read_only=True,
                        estimated_risk="LOW",
                        voi_score=0.85,
                    )
                )

        # Sort tasks descending by Value of Information score
        tasks.sort(key=lambda t: t.voi_score, reverse=True)

        plan = InvestigationPlan(
            investigation_id=f"inv_{uuid.uuid4().hex[:8]}",
            incident_id=incident_id,
            tasks=tasks,
            findings=[],
            completed_task_ids=[],
        )

        logger.info("INVESTIGATION_PLAN_CREATED: incident=%s tasks_count=%d", incident_id, len(tasks))
        return plan


investigation_engine = InvestigationEngine()

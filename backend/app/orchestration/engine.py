"""Core Orchestration Engine answering capability requirements, topology, allocation, and failovers (Task 59)."""

from __future__ import annotations

import logging
from typing import Any

from app.orchestration.assignment import AssignmentEngine, assignment_engine
from app.orchestration.audit import OrchestrationAuditor, orchestration_auditor
from app.orchestration.capability_registry import CapabilityRegistry, default_capability_registry
from app.orchestration.contention import ContentionResolver, contention_resolver
from app.orchestration.matching import CapabilityMatcher, capability_matcher
from app.orchestration.plans import OrchestrationLifecycleManager, orchestration_lifecycle_manager
from app.orchestration.provenance import OrchestrationProvenanceTracker, provenance_tracker
from app.orchestration.recovery import RecoveryEngine, recovery_engine
from app.orchestration.resource_registry import ResourceRegistry, default_resource_registry
from app.orchestration.safety import (
    OrchestrationSafetyError,
    sanitize_orchestration_directive,
)
from app.orchestration.schemas import (
    HealthStatus,
    OrchestrationPlan,
    OrchestrationStatus,
    ProviderAssignment,
    RiskSeverity,
    TaskCapabilityRequirement,
)
from app.orchestration.topology import TopologyEngine, topology_engine

logger = logging.getLogger(__name__)


class OrchestrationEngine:
    """Unified engine coordinating requirements, capabilities, resources, topologies, and resilience."""

    def __init__(
        self,
        capability_registry: CapabilityRegistry | None = None,
        resource_registry: ResourceRegistry | None = None,
        matcher: CapabilityMatcher | None = None,
        assignment_eng: AssignmentEngine | None = None,
        contention_res: ContentionResolver | None = None,
        topology_eng: TopologyEngine | None = None,
        recovery_eng: RecoveryEngine | None = None,
        provenance_tr: OrchestrationProvenanceTracker | None = None,
        lifecycle_mgr: OrchestrationLifecycleManager | None = None,
        auditor: OrchestrationAuditor | None = None,
    ) -> None:
        self.capability_registry = capability_registry or default_capability_registry
        self.resource_registry = resource_registry or default_resource_registry
        self.matcher = matcher or capability_matcher
        self.assignment_engine = assignment_eng or assignment_engine
        self.contention_resolver = contention_res or contention_resolver
        self.topology_engine = topology_eng or topology_engine
        self.recovery_engine = recovery_eng or recovery_engine
        self.provenance_tracker = provenance_tr or provenance_tracker
        self.lifecycle_manager = lifecycle_mgr or orchestration_lifecycle_manager
        self.auditor = auditor or orchestration_auditor

    def analyze_feasibility(
        self,
        tasks: list[dict[str, Any]],
        environment: str = "development",
        granted_permissions: set[str] | None = None,
    ) -> dict[str, Any]:
        """Perform comprehensive gap analysis: required capabilities vs available, resources, permissions, blockers."""
        granted = granted_permissions or set()
        env_clean = environment.strip().lower()

        requirements: list[TaskCapabilityRequirement] = []
        for t in tasks:
            req = self.matcher.extract_task_requirements(t, default_environment=env_clean)
            requirements.append(req)

        missing_capabilities: list[dict[str, Any]] = []
        missing_resources: list[dict[str, Any]] = []
        permission_blockers: list[dict[str, Any]] = []
        candidate_assignments: list[dict[str, Any]] = []

        # 1. Capability & Permission Analysis
        for req in requirements:
            ranked = self.matcher.rank_candidates(requirement=req, granted_permissions=granted)
            if not ranked:
                missing_capabilities.append({
                    "task_id": req.task_id,
                    "title": req.title,
                    "required_capabilities": req.required_capabilities,
                    "environment": req.environment,
                    "status": "CAPABILITY_UNAVAILABLE",
                })
            else:
                top = ranked[0]
                if not top.is_authorized:
                    permission_blockers.append({
                        "task_id": req.task_id,
                        "provider": top.provider_name,
                        "missing_permissions": top.missing_permissions,
                    })
                candidate_assignments.append({
                    "task_id": req.task_id,
                    "selected_provider": top.provider_name,
                    "score": top.overall_score,
                    "is_authorized": top.is_authorized,
                })

        # 2. Resource Contention & Shortages
        resource_conflicts = self.contention_resolver.detect_contention(requirements)
        for conflict in resource_conflicts:
            missing_resources.append(conflict)

        # 3. Determine Feasibility Status
        if missing_capabilities or permission_blockers:
            feasibility = "BLOCKED"
        elif missing_resources:
            feasibility = "PARTIALLY_FEASIBLE"
        else:
            feasibility = "FEASIBLE"

        return {
            "feasibility": feasibility,
            "environment": env_clean,
            "total_tasks": len(requirements),
            "missing_capabilities": missing_capabilities,
            "missing_resources": missing_resources,
            "permission_blockers": permission_blockers,
            "candidate_assignments": candidate_assignments,
            "contention_detected": len(resource_conflicts) > 0,
        }

    def create_orchestration_plan(
        self,
        name: str,
        tasks: list[dict[str, Any]],
        strategic_plan_id: str | None = None,
        dependencies: dict[str, list[str]] | None = None,
        environment: str = "development",
        granted_permissions: set[str] | None = None,
        actor: str = "system",
    ) -> OrchestrationPlan:
        """Transform strategic tasks, capabilities, and resources into an executable OrchestrationPlan."""
        clean_name = sanitize_orchestration_directive(name)
        granted = granted_permissions or set()
        deps = dependencies or {}

        # 1. Extract requirements
        requirements: list[TaskCapabilityRequirement] = []
        for t in tasks:
            req = self.matcher.extract_task_requirements(t, default_environment=environment)
            requirements.append(req)

        # 2. Assign vetted providers and record provenance
        assignments: list[ProviderAssignment] = []
        for req in requirements:
            asgn = self.assignment_engine.assign_task(
                requirement=req,
                granted_permissions=granted,
            )
            assignments.append(asgn)

            # Record selection provenance
            ranked = self.matcher.rank_candidates(requirement=req, granted_permissions=granted)
            self.provenance_tracker.record_selection_provenance(
                task_id=req.task_id,
                assignment=asgn,
                evaluated_candidates=ranked,
                requirement=req,
            )

        # 3. Generate execution topology, DAG, waves, and barriers
        topo = self.topology_engine.build_topology(
            requirements=requirements,
            assignments=assignments,
            task_dependencies=deps,
        )

        # 4. Detect overall risk
        overall_risk = RiskSeverity.LOW
        for req in requirements:
            if req.is_irreversible or "deploy_service" in req.required_capabilities:
                overall_risk = RiskSeverity.HIGH

        plan = OrchestrationPlan(
            strategic_plan_id=strategic_plan_id,
            name=clean_name,
            task_graph={"dependencies": deps, "nodes": topo.nodes, "edges": topo.edges},
            capability_requirements=requirements,
            assignments=assignments,
            execution_waves=topo.execution_waves,
            fallback_paths={a.task_id: a.fallback_provider for a in assignments if a.fallback_provider},
            synchronization_points=[b["barrier_id"] for b in topo.synchronization_barriers],
            verification_points=[req.task_id for req in requirements if req.verification_criteria],
            risk=overall_risk,
            status=OrchestrationStatus.READY,
            health=HealthStatus.ON_TRACK,
        )

        self.lifecycle_manager.save_plan(plan)

        self.auditor.record_event(
            event_type="ORCHESTRATION_CREATED",
            actor=actor,
            orchestration_id=plan.orchestration_id,
            details={
                "name": clean_name,
                "task_count": len(tasks),
                "environment": environment,
                "risk": overall_risk.value,
            },
        )

        logger.info("ORCHESTRATION_PLAN_CREATED: id=%s name=%s tasks=%d", plan.orchestration_id, clean_name, len(tasks))
        return plan

    def trigger_failover(
        self,
        orchestration_id: str,
        task_id: str,
        error_message: str,
        actor: str = "system",
    ) -> dict[str, Any]:
        """Trigger dynamic failover to secondary or emergency fallback provider."""
        plan = self.lifecycle_manager.get_plan(orchestration_id)

        target_asgn: ProviderAssignment | None = None
        for asgn in plan.assignments:
            if asgn.task_id == task_id:
                target_asgn = asgn
                break

        if not target_asgn:
            raise OrchestrationSafetyError(f"Task '{task_id}' not found in plan '{orchestration_id}'.")

        target_req: TaskCapabilityRequirement | None = None
        for req in plan.capability_requirements:
            if req.task_id == task_id:
                target_req = req
                break

        if not target_req:
            target_req = TaskCapabilityRequirement(task_id=task_id, required_capabilities=[])

        recovery_action = self.recovery_engine.handle_task_failure(
            task_id=task_id,
            assignment=target_asgn,
            requirement=target_req,
            error_message=error_message,
        )

        if recovery_action["action"] == "FAILOVER":
            old_provider = target_asgn.provider_name
            target_asgn.provider_name = recovery_action["new_provider"]
            target_asgn.status = OrchestrationStatus.READY  # reset status for new provider

            # Record revision diff
            self.lifecycle_manager.create_revision(
                orchestration_id=orchestration_id,
                actor=actor,
                reason=f"Failover from {old_provider} due to: {error_message}",
                new_assignments=plan.assignments,
            )

        self.auditor.record_event(
            event_type="FAILOVER_TRIGGERED",
            actor=actor,
            orchestration_id=orchestration_id,
            task_id=task_id,
            details=recovery_action,
        )

        return recovery_action


orchestration_engine = OrchestrationEngine()

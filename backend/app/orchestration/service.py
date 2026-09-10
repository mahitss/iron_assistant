"""Service facade providing database persistence and transactional orchestration workflows (Task 59)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.engine import OrchestrationEngine, orchestration_engine
from app.orchestration.models import (
    OrchestrationPlanModel,
    ResourceReservationModel,
    TaskAssignmentModel,
)
from app.orchestration.schemas import (
    CapabilityDefinition,
    CapabilityStatus,
    HealthStatus,
    OrchestrationPlan,
    OrchestrationStatus,
    ProviderAssignment,
    ResourceDefinition,
    ResourceReservation,
    ResourceType,
)

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Service facade coordinating engine domain logic with database persistence."""

    def __init__(self, engine: OrchestrationEngine | None = None) -> None:
        self._engine = engine or orchestration_engine

    async def analyze(
        self,
        tasks: list[dict[str, Any]],
        environment: str = "development",
        granted_permissions: set[str] | None = None,
    ) -> dict[str, Any]:
        """Analyze feasibility, capability gaps, and resource bottlenecks."""
        return self._engine.analyze_feasibility(
            tasks=tasks,
            environment=environment,
            granted_permissions=granted_permissions,
        )

    async def create_orchestration_plan(
        self,
        name: str,
        tasks: list[dict[str, Any]],
        strategic_plan_id: str | None = None,
        dependencies: dict[str, list[str]] | None = None,
        environment: str = "development",
        granted_permissions: set[str] | None = None,
        actor: str = "system",
        db: AsyncSession | None = None,
    ) -> OrchestrationPlan:
        """Create and optionally persist an OrchestrationPlan."""
        plan = self._engine.create_orchestration_plan(
            name=name,
            tasks=tasks,
            strategic_plan_id=strategic_plan_id,
            dependencies=dependencies,
            environment=environment,
            granted_permissions=granted_permissions,
            actor=actor,
        )

        if db:
            plan_model = OrchestrationPlanModel(
                orchestration_id=plan.orchestration_id,
                strategic_plan_id=plan.strategic_plan_id,
                name=plan.name,
                task_graph=plan.task_graph,
                execution_waves=plan.execution_waves,
                status=plan.status.value,
                health=plan.health.value,
                version=plan.version,
                provenance=plan.provenance,
            )
            db.add(plan_model)

            for asgn in plan.assignments:
                asgn_model = TaskAssignmentModel(
                    assignment_id=asgn.assignment_id,
                    orchestration_id=plan.orchestration_id,
                    task_id=asgn.task_id,
                    provider_name=asgn.provider_name,
                    provider_type=asgn.provider_type.value,
                    capability_id=asgn.capability_id,
                    allocated_resources=asgn.allocated_resources,
                    required_permissions=asgn.required_permissions,
                    status=asgn.status.value,
                    rationale=asgn.rationale,
                    confidence=asgn.confidence,
                    fallback_provider=asgn.fallback_provider,
                    verification_criteria=asgn.verification_criteria,
                )
                db.add(asgn_model)

            await db.commit()
            await db.refresh(plan_model)

        return plan

    async def get_orchestration_plan(
        self,
        orchestration_id: str,
        db: AsyncSession | None = None,
    ) -> OrchestrationPlan:
        """Fetch orchestration plan by ID."""
        if db:
            result = await db.execute(
                select(OrchestrationPlanModel).where(OrchestrationPlanModel.orchestration_id == orchestration_id)
            )
            model = result.scalar_one_or_none()
            if model:
                # Load assignments
                asgn_res = await db.execute(
                    select(TaskAssignmentModel).where(TaskAssignmentModel.orchestration_id == orchestration_id)
                )
                assignments = [
                    ProviderAssignment(
                        assignment_id=a.assignment_id,
                        task_id=a.task_id,
                        provider_name=a.provider_name,
                        provider_type=a.provider_type,
                        capability_id=a.capability_id,
                        allocated_resources=a.allocated_resources,
                        required_permissions=a.required_permissions,
                        status=a.status,
                        rationale=a.rationale,
                        confidence=a.confidence,
                        fallback_provider=a.fallback_provider,
                        verification_criteria=a.verification_criteria,
                    )
                    for a in asgn_res.scalars().all()
                ]
                return OrchestrationPlan(
                    orchestration_id=model.orchestration_id,
                    strategic_plan_id=model.strategic_plan_id,
                    name=model.name,
                    task_graph=model.task_graph,
                    execution_waves=model.execution_waves,
                    status=OrchestrationStatus(model.status),
                    health=HealthStatus(model.health),
                    version=model.version,
                    provenance=model.provenance,
                    assignments=assignments,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )

        return self._engine.lifecycle_manager.get_plan(orchestration_id)

    async def list_orchestrations(
        self,
        status: OrchestrationStatus | None = None,
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[OrchestrationPlan]:
        """List active or historical orchestration plans."""
        if db:
            query = select(OrchestrationPlanModel)
            if status:
                query = query.where(OrchestrationPlanModel.status == status.value)
            query = query.order_by(OrchestrationPlanModel.created_at.desc()).limit(limit)
            result = await db.execute(query)
            models = result.scalars().all()
            return [
                OrchestrationPlan(
                    orchestration_id=m.orchestration_id,
                    strategic_plan_id=m.strategic_plan_id,
                    name=m.name,
                    task_graph=m.task_graph,
                    execution_waves=m.execution_waves,
                    status=OrchestrationStatus(m.status),
                    health=HealthStatus(m.health),
                    version=m.version,
                    provenance=m.provenance,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )
                for m in models
            ]

        # In-memory fallback
        plans = list(self._engine.lifecycle_manager._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        return plans[-limit:]

    async def get_capabilities(
        self,
        environment: str | None = None,
        status: CapabilityStatus | None = None,
        db: AsyncSession | None = None,
    ) -> list[CapabilityDefinition]:
        """List capabilities from registry or database."""
        return self._engine.capability_registry.list_all(environment=environment, status=status)

    async def get_resources(
        self,
        environment: str | None = None,
        resource_type: ResourceType | None = None,
        db: AsyncSession | None = None,
    ) -> list[ResourceDefinition]:
        """List managed resources from registry or database."""
        return self._engine.resource_registry.list_all(environment=environment, resource_type=resource_type)

    async def reserve_resource(
        self,
        resource_id: str,
        owner: str,
        purpose: str,
        amount: float,
        expires_at: datetime,
        scope: str = "GLOBAL",
        db: AsyncSession | None = None,
    ) -> ResourceReservation:
        """Reserve resource capacity."""
        rsv = self._engine.resource_registry.reserve(
            resource_id=resource_id,
            owner=owner,
            purpose=purpose,
            amount=amount,
            expires_at=expires_at,
            scope=scope,
        )

        if db:
            rsv_model = ResourceReservationModel(
                reservation_id=rsv.reservation_id,
                resource_id=rsv.resource_id,
                owner=rsv.owner,
                purpose=rsv.purpose,
                scope=rsv.scope,
                amount=rsv.amount,
                is_active=rsv.is_active,
                expires_at=rsv.expires_at,
                created_at=rsv.created_at,
            )
            db.add(rsv_model)
            await db.commit()

        return rsv

    async def release_reservation(
        self,
        reservation_id: str,
        db: AsyncSession | None = None,
    ) -> bool:
        """Release an active resource reservation."""
        released = self._engine.resource_registry.release_reservation(reservation_id)
        if db:
            res = await db.execute(
                select(ResourceReservationModel).where(ResourceReservationModel.reservation_id == reservation_id)
            )
            rsv_model = res.scalar_one_or_none()
            if rsv_model:
                rsv_model.is_active = False
                await db.commit()
        return released

    async def revalidate(
        self,
        orchestration_id: str,
        current_environment: str,
        active_permissions: set[str],
    ) -> bool:
        """Revalidate plan assignments against current environmental constraints."""
        return self._engine.lifecycle_manager.revalidate_plan(
            orchestration_id=orchestration_id,
            current_environment=current_environment,
            active_permissions=active_permissions,
        )

    async def trigger_failover(
        self,
        orchestration_id: str,
        task_id: str,
        error_message: str,
        actor: str = "system",
    ) -> dict[str, Any]:
        """Trigger dynamic failover to fallback provider."""
        return self._engine.trigger_failover(
            orchestration_id=orchestration_id,
            task_id=task_id,
            error_message=error_message,
            actor=actor,
        )

    def explain_task(self, task_id: str) -> dict[str, Any]:
        """Explain why a provider was chosen for a task."""
        return self._engine.provenance_tracker.explain_assignment(task_id)

    def get_audit_trail(
        self,
        orchestration_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return cryptographic audit log entries."""
        return self._engine.auditor.get_events(orchestration_id=orchestration_id, limit=limit)


orchestration_service = OrchestrationService()

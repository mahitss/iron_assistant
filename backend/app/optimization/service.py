"""Service facade coordinating optimization domain logic with database transactions (Task 62)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.optimization.engine import OptimizationEngine, optimization_engine
from app.optimization.models import (
    OptimizationCanaryModel,
    OptimizationChangeSetModel,
    OptimizationExperimentModel,
    OptimizationMetricModel,
)
from app.optimization.safety import optimization_kill_switch
from app.optimization.schemas import (
    ApproveRecommendationRequest,
    CalibrationRecord,
    CanaryDeployment,
    ChangeSet,
    CreateExperimentRequest,
    DriftRecord,
    EvaluateOptimizationRequest,
    Experiment,
    ExperimentStatus,
    IngestMeasurementRequest,
    MetricMeasurement,
    OptimizationBaseline,
    OptimizationEvaluation,
    OptimizationRecommendation,
    RollbackPlan,
)

logger = logging.getLogger(__name__)


class OptimizationService:
    """Coordinates optimization engine domain evaluations with transactional database persistence."""

    def __init__(self, engine: OptimizationEngine | None = None) -> None:
        self._engine = engine or optimization_engine

    async def evaluate_system(
        self,
        req: EvaluateOptimizationRequest,
        db: AsyncSession | None = None,
    ) -> OptimizationEvaluation:
        """Execute continuous evaluation and generate bounded adaptive recommendations."""
        return self._engine.evaluate_system(
            scope=req.scope,
            include_simulation=req.include_simulation,
        )

    async def ingest_measurement(
        self,
        req: IngestMeasurementRequest,
        db: AsyncSession | None = None,
    ) -> MetricMeasurement:
        """Record an incoming raw performance measurement."""
        meas = MetricMeasurement(
            metric_name=req.metric_name,
            value=req.value,
            source=req.source,
            scope=req.scope,
            tags=req.tags,
        )
        self._engine.metrics_engine.record_measurement(meas)

        if db:
            model = OptimizationMetricModel(
                measurement_id=meas.measurement_id,
                metric_name=meas.metric_name,
                value=meas.value,
                source=meas.source,
                scope=meas.scope,
                tags=meas.tags,
                timestamp=meas.timestamp,
            )
            db.add(model)
            await db.commit()

        return meas

    async def list_recommendations(self) -> list[OptimizationRecommendation]:
        """List active adaptive tuning recommendations."""
        return self._engine.list_recommendations()

    async def get_recommendation(self, recommendation_id: str) -> OptimizationRecommendation | None:
        """Retrieve recommendation by ID."""
        return self._engine.get_recommendation(recommendation_id)

    async def approve_recommendation(
        self,
        req: ApproveRecommendationRequest,
        db: AsyncSession | None = None,
    ) -> tuple[ChangeSet, CanaryDeployment]:
        """Approve recommendation and launch canary rollout."""
        cs, canary = self._engine.approve_and_canary(
            recommendation_id=req.recommendation_id,
            approver=req.approver,
        )

        if db:
            cs_model = OptimizationChangeSetModel(
                change_set_id=cs.change_set_id,
                version=cs.version,
                target_parameter=cs.target_parameter,
                before_state=cs.before_state,
                after_state=cs.after_state,
                diff=cs.diff,
                reason=cs.reason,
                risk=cs.risk.value,
                status=cs.status.value,
                approval_id=cs.approval_id,
                approver=cs.approver,
                rollback_strategy=cs.rollback_strategy,
                created_at=cs.created_at,
            )
            canary_model = OptimizationCanaryModel(
                canary_id=canary.canary_id,
                change_set_id=canary.change_set_id,
                rollout_state=canary.rollout_state.value,
                traffic_percentage=canary.traffic_percentage,
                blast_radius_scope=canary.blast_radius_scope,
                is_verified=canary.is_verified,
                failure_threshold_reached=canary.failure_threshold_reached,
                started_at=canary.started_at,
                updated_at=canary.updated_at,
            )
            db.add(cs_model)
            db.add(canary_model)
            await db.commit()

        return cs, canary

    async def create_experiment(
        self,
        req: CreateExperimentRequest,
        db: AsyncSession | None = None,
    ) -> Experiment:
        """Define a new sandboxed A/B experiment."""
        exp = self._engine.experiment_manager.create_experiment(
            hypothesis=req.hypothesis,
            target_metrics=req.target_metrics,
            control_parameters=req.control_parameters,
            variants=req.variants,
            safety_gates=req.safety_gates,
            stop_conditions=req.stop_conditions,
        )

        if db:
            exp_model = OptimizationExperimentModel(
                experiment_id=exp.experiment_id,
                hypothesis=exp.hypothesis,
                target_metrics=exp.target_metrics,
                control_parameters=exp.control_parameters,
                variants=[v.model_dump() for v in exp.variants],
                status=exp.status.value,
                safety_gates=exp.safety_gates,
                stop_conditions=exp.stop_conditions,
                created_at=exp.created_at,
            )
            db.add(exp_model)
            await db.commit()

        return exp

    async def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Retrieve experiment by ID."""
        return self._engine.experiment_manager.get_experiment(experiment_id)

    async def list_experiments(self, status: ExperimentStatus | None = None) -> list[Experiment]:
        """List tracked experiments."""
        return self._engine.experiment_manager.list_experiments(status=status)

    async def approve_experiment(self, experiment_id: str, approver: str = "ADMIN") -> Experiment:
        """Approve experiment for activation."""
        return self._engine.experiment_manager.approve_experiment(experiment_id, approver=approver)

    async def start_experiment(self, experiment_id: str) -> Experiment:
        """Activate experiment into running state."""
        return self._engine.experiment_manager.start_experiment(experiment_id)

    async def verify_canary(
        self,
        canary_id: str,
        is_verified: bool = True,
        advance_to_full: bool = True,
    ) -> CanaryDeployment:
        """Verify canary operation and advance rollout."""
        return self._engine.verify_and_rollout(
            canary_id=canary_id,
            is_verified=is_verified,
            advance_to_full=advance_to_full,
        )

    async def rollback_canary(
        self,
        canary_id: str,
        reason: str = "Operator triggered rollback",
        actor: str = "OPERATOR",
    ) -> RollbackPlan:
        """Abort canary and revert parameter to nominal state."""
        return self._engine.abort_and_rollback(canary_id=canary_id, reason=reason, actor=actor)

    async def list_change_sets(self) -> list[ChangeSet]:
        """List recorded change sets."""
        return self._engine.change_set_manager.list_change_sets()

    async def list_baselines(self) -> list[OptimizationBaseline]:
        """List active baselines."""
        return self._engine.baseline_manager.list_baselines()

    async def list_drift(self) -> list[DriftRecord]:
        """Retrieve detected drift events."""
        return self._engine.drift_detector.list_drift_records()

    async def list_calibration(self) -> list[CalibrationRecord]:
        """Retrieve calibration tracking history."""
        return self._engine.calibration_tracker.list_calibration_records()

    def get_audit_trail(
        self,
        change_set_id: str | None = None,
        experiment_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve cryptographic audit events."""
        return self._engine.auditor.get_events(
            change_set_id=change_set_id,
            experiment_id=experiment_id,
            limit=limit,
        )

    def set_kill_switch(self, engage: bool, reason: str, actor: str) -> dict[str, Any]:
        """Toggle emergency optimization freeze."""
        if engage:
            optimization_kill_switch.activate(reason=reason, actor=actor)
        else:
            optimization_kill_switch.deactivate(reason=reason, actor=actor)

        self._engine.auditor.record_event(
            event_type="KILL_SWITCH_TOGGLED",
            actor=actor,
            details={"engage": engage, "reason": reason},
        )

        return {
            "is_active": optimization_kill_switch.is_active,
            "kill_switch_active": optimization_kill_switch.is_active,
            "reason": reason,
            "actor": actor,
        }


optimization_service = OptimizationService()

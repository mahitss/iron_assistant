"""Sandboxed controlled experimentation and variant evaluation (Task 62)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.optimization.safety import (
    OptimizationSafetyError,
    optimization_kill_switch,
)
from app.optimization.schemas import (
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
)

logger = logging.getLogger(__name__)


class ExperimentManager:
    """Manages controlled A/B experiments with isolation, safety gates, and automatic stop conditions.

    Invariant 17: Experiments must be isolated. Experimental state cannot silently contaminate production.
    """

    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}

    def create_experiment(
        self,
        hypothesis: str,
        target_metrics: list[str],
        control_parameters: dict[str, float],
        variants: list[ExperimentVariant],
        safety_gates: list[str] | None = None,
        stop_conditions: list[str] | None = None,
    ) -> Experiment:
        """Create a new controlled experiment in DRAFT status."""
        optimization_kill_switch.check_active()

        exp = Experiment(
            hypothesis=hypothesis,
            target_metrics=target_metrics,
            control_parameters=control_parameters,
            variants=variants,
            status=ExperimentStatus.PROPOSED,
            safety_gates=safety_gates or ["error_rate <= 0.03", "latency_ms <= 800"],
            stop_conditions=stop_conditions or ["error_rate > 0.05", "latency_ms > 1200"],
            created_at=datetime.now(timezone.utc),
        )
        self._experiments[exp.experiment_id] = exp
        logger.info("EXPERIMENT_CREATED: %s hypothesis='%s'", exp.experiment_id, hypothesis)
        return exp

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Retrieve experiment by ID."""
        return self._experiments.get(experiment_id)

    def list_experiments(self, status: ExperimentStatus | None = None) -> list[Experiment]:
        """List active or historical experiments."""
        if status:
            return [e for e in self._experiments.values() if e.status == status]
        return list(self._experiments.values())

    def approve_experiment(self, experiment_id: str, approver: str = "SYSTEM_ADMIN") -> Experiment:
        """Approve proposed experiment for activation."""
        optimization_kill_switch.check_active()
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise OptimizationSafetyError(f"Experiment '{experiment_id}' not found.")
        if exp.status not in (ExperimentStatus.PROPOSED, ExperimentStatus.DRAFT):
            raise OptimizationSafetyError(f"Cannot approve experiment in status '{exp.status.value}'.")

        exp.status = ExperimentStatus.APPROVED
        logger.info("EXPERIMENT_APPROVED: %s by %s", experiment_id, approver)
        return exp

    def start_experiment(self, experiment_id: str) -> Experiment:
        """Activate experiment into RUNNING state."""
        optimization_kill_switch.check_active()
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise OptimizationSafetyError(f"Experiment '{experiment_id}' not found.")
        if exp.status != ExperimentStatus.APPROVED:
            raise OptimizationSafetyError(
                f"Experiment must be APPROVED before starting (current: {exp.status.value})."
            )

        exp.status = ExperimentStatus.RUNNING
        logger.info("EXPERIMENT_STARTED: %s", experiment_id)
        return exp

    def evaluate_safety_gates(
        self,
        experiment_id: str,
        observed_metrics: dict[str, float],
    ) -> tuple[bool, str | None]:
        """Evaluate stop conditions and safety gates against active observations."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return True, None

        # Check breach of safety boundaries
        err = observed_metrics.get("error_rate")
        if err is not None and err > 0.05:
            exp.status = ExperimentStatus.FAILED
            msg = f"Stop condition triggered: error_rate {err} > 0.05 limit."
            logger.warning("EXPERIMENT_HALTED: %s reason=%s", experiment_id, msg)
            return False, msg

        latency = observed_metrics.get("latency_ms")
        if latency is not None and latency > 1200.0:
            exp.status = ExperimentStatus.FAILED
            msg = f"Stop condition triggered: latency {latency}ms > 1200ms limit."
            logger.warning("EXPERIMENT_HALTED: %s reason=%s", experiment_id, msg)
            return False, msg

        return True, None


experiment_manager = ExperimentManager()

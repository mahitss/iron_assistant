"""Experiment Queue and Dependency Scheduling (Task 72).

Manages prioritized scheduling of experiments, dependency resolution (A -> B),
concurrency limits, and human-in-the-loop approval gating.
"""

from collections import deque

from app.discovery.schemas import (
    ExperimentDesign,
    ExperimentStatus,
    RiskLevel,
)
from app.discovery.state_machine import validate_experiment_transition


class ExperimentQueueManager:
    """Prioritizes and schedules scientific experiments with dependency tracking."""

    def __init__(
        self,
        max_concurrent_experiments: int = 5,
        max_queue_size: int = 100,
        resource_budget: float = 100.0,
    ):
        self.max_concurrent = max_concurrent_experiments
        self.max_queue_size = max_queue_size
        self.resource_budget = resource_budget

        self._queue: deque[ExperimentDesign] = deque()
        self._experiments: dict[str, ExperimentDesign] = {}
        self._completed_experiment_ids: set[str] = set()
        self._running_experiment_ids: set[str] = set()
        self._allocated_budget: float = 0.0

    def enqueue(self, experiment: ExperimentDesign) -> bool:
        """Adds an experiment to the queue if capacity permits."""
        if len(self._queue) >= self.max_queue_size:
            return False

        self._experiments[experiment.experiment_id] = experiment

        # If it has unfulfilled dependencies, mark BLOCKED
        if not self._are_dependencies_met(experiment):
            experiment.status = ExperimentStatus.BLOCKED
        elif experiment.authorization_required and not experiment.is_authorized:
            experiment.status = ExperimentStatus.APPROVAL_REQUIRED
        else:
            experiment.status = ExperimentStatus.READY

        self._queue.append(experiment)
        self._sort_queue()
        return True

    def _are_dependencies_met(self, experiment: ExperimentDesign) -> bool:
        """Checks if all prerequisite experiments have completed successfully."""
        for dep_id in experiment.dependencies:
            if dep_id not in self._completed_experiment_ids:
                return False
        return True

    def _sort_queue(self) -> None:
        """Sorts pending experiments by priority:

        Higher information gain first, lower cost, lower risk.
        """
        risk_weights = {
            RiskLevel.SAFE: 1,
            RiskLevel.LOW_RISK: 2,
            RiskLevel.MEDIUM_RISK: 3,
            RiskLevel.HIGH_RISK: 4,
            RiskLevel.CRITICAL_RISK: 5,
        }

        ready_items = [e for e in self._queue if e.status == ExperimentStatus.READY]
        other_items = [e for e in self._queue if e.status != ExperimentStatus.READY]

        ready_items.sort(
            key=lambda e: (
                -e.expected_information_gain,
                risk_weights.get(e.risk_level, 3),
                e.estimated_cost,
            )
        )
        self._queue = deque(ready_items + other_items)

    def approve_experiment(
        self,
        experiment_id: str,
        approver: str,
    ) -> ExperimentDesign | None:
        """Grants human-in-the-loop authorization for a gated experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None

        exp.is_authorized = True
        exp.authorized_by = approver

        if self._are_dependencies_met(exp):
            validate_experiment_transition(exp.status, ExperimentStatus.APPROVED)
            exp.status = ExperimentStatus.APPROVED
            validate_experiment_transition(exp.status, ExperimentStatus.READY)
            exp.status = ExperimentStatus.READY
        else:
            exp.status = ExperimentStatus.BLOCKED

        self._sort_queue()
        return exp

    def pop_next_runnable(self) -> ExperimentDesign | None:
        """Selects the highest priority ready experiment that fits resource bounds."""
        if len(self._running_experiment_ids) >= self.max_concurrent:
            return None

        # Re-check blocked items whose dependencies may now be satisfied
        for exp in list(self._queue):
            if exp.status == ExperimentStatus.BLOCKED and self._are_dependencies_met(exp):
                if exp.authorization_required and not exp.is_authorized:
                    exp.status = ExperimentStatus.APPROVAL_REQUIRED
                else:
                    exp.status = ExperimentStatus.READY

        self._sort_queue()

        for i, exp in enumerate(self._queue):
            if exp.status == ExperimentStatus.READY:
                # Check resource budget
                if self._allocated_budget + exp.estimated_cost > self.resource_budget:
                    continue  # Exceeds budget constraint

                # Found runnable experiment
                del self._queue[i]
                validate_experiment_transition(exp.status, ExperimentStatus.RUNNING)
                exp.status = ExperimentStatus.RUNNING
                self._running_experiment_ids.add(exp.experiment_id)
                self._allocated_budget += exp.estimated_cost
                return exp

        return None

    def mark_completed(self, experiment_id: str) -> None:
        """Marks an experiment as successfully completed and releases allocated resources."""
        exp = self._experiments.get(experiment_id)
        if exp:
            validate_experiment_transition(exp.status, ExperimentStatus.COMPLETED)
            exp.status = ExperimentStatus.COMPLETED
            self._completed_experiment_ids.add(experiment_id)
            if experiment_id in self._running_experiment_ids:
                self._running_experiment_ids.remove(experiment_id)
                self._allocated_budget = max(0.0, self._allocated_budget - exp.estimated_cost)

        # Unblock dependent experiments
        self._unblock_dependents()

    def mark_failed(self, experiment_id: str, reason: str = "") -> None:
        """Marks an execution as failed."""
        exp = self._experiments.get(experiment_id)
        if exp:
            validate_experiment_transition(exp.status, ExperimentStatus.FAILED)
            exp.status = ExperimentStatus.FAILED
            if experiment_id in self._running_experiment_ids:
                self._running_experiment_ids.remove(experiment_id)
                self._allocated_budget = max(0.0, self._allocated_budget - exp.estimated_cost)

    def mark_invalid(self, experiment_id: str, reason: str = "") -> None:
        """Marks an experiment as invalid (confounded or defective methodology)."""
        exp = self._experiments.get(experiment_id)
        if exp:
            validate_experiment_transition(exp.status, ExperimentStatus.INVALID)
            exp.status = ExperimentStatus.INVALID
            if experiment_id in self._running_experiment_ids:
                self._running_experiment_ids.remove(experiment_id)
                self._allocated_budget = max(0.0, self._allocated_budget - exp.estimated_cost)

    def _unblock_dependents(self) -> None:
        """Wakes up experiments waiting on completed prerequisites."""
        for exp in self._queue:
            if exp.status == ExperimentStatus.BLOCKED and self._are_dependencies_met(exp):
                if exp.authorization_required and not exp.is_authorized:
                    exp.status = ExperimentStatus.APPROVAL_REQUIRED
                else:
                    exp.status = ExperimentStatus.READY

    def get_status_counts(self) -> dict[str, int]:
        """Returns aggregate metrics on experiment statuses."""
        counts: dict[str, int] = {}
        for exp in self._experiments.values():
            counts[exp.status.value] = counts.get(exp.status.value, 0) + 1
        return counts

    def get_experiment(self, experiment_id: str) -> ExperimentDesign | None:
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[ExperimentDesign]:
        return list(self._experiments.values())

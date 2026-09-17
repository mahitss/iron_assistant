"""Staged experiment runner, firewall safety boundaries, deterministic assignment,
and stop condition monitoring for Task 105.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.adaptation.domain import (
    AssignmentStrategy,
    ExperimentAssignment,
    ExperimentGate,
    ExperimentObservation,
    ExperimentPlan,
    ExperimentRun,
    ExperimentVariant,
    FailureTaxonomy,
    RunStatus,
    SandboxEnvironment,
    StopConditionType,
    VariantType,
)
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.adaptation.experiment_engine")


class ExperimentFirewall:
    """Fail-closed safety and authorization firewall for candidate experiments."""

    @classmethod
    def check_firewall(
        cls,
        plan: ExperimentPlan,
        actor: str = "kairo.adaptation",
        user_id: Optional[str] = None,
    ) -> tuple[bool, list[str]]:
        """Evaluates all mandatory pre-execution checks fail-closed.
        If ANY gate fails: BLOCK execution.
        """
        blockers: list[str] = []

        # 1. EmergencyStop Primacy (Absolute)
        e_stop = get_emergency_stop_service()
        if e_stop.is_stopped(user_id):
            blockers.append("EMERGENCY_STOP_ACTIVE: Mutating and experimental execution is blocked.")

        # 2. Rollback Strategy Requirement
        if not plan.rollback_condition or not plan.rollback_condition.strip():
            blockers.append("MISSING_ROLLBACK_STRATEGY: Every experiment must define an explicit rollback condition.")

        # 3. Stop Conditions Defined
        if not plan.stop_conditions:
            blockers.append("MISSING_STOP_CONDITIONS: Experiment must define hard stop conditions.")

        # 4. Resource Budget Sanity
        budget = plan.resource_budget or {}
        max_cost = budget.get("max_cost_usd", 0.0)
        if max_cost > 100.0:
            blockers.append(f"EXCESSIVE_RESOURCE_BUDGET: Experiment cost ${max_cost:.2f} exceeds ceiling $100.00.")

        # 5. Variants Sanity
        has_baseline = any(v.variant_type == VariantType.BASELINE for v in plan.variants)
        has_candidate = any(v.variant_type == VariantType.CANDIDATE for v in plan.variants)
        if not has_baseline:
            blockers.append("MISSING_CONTROL_GROUP: Experiment must define an immutable BASELINE control variant.")
        if not has_candidate:
            blockers.append("MISSING_CANDIDATE_VARIANT: Experiment must define at least one CANDIDATE variant.")

        # 6. Time Limit Verification
        if plan.time_limit_seconds > 86400.0:
            blockers.append("EXCESSIVE_TIME_LIMIT: Experiment time limit exceeds maximum 24 hours.")

        passed = len(blockers) == 0
        if not passed:
            logger.warning("Experiment plan %s blocked by firewall: %s", plan.id, "; ".join(blockers))
        return passed, blockers


class ExperimentAssignmentEngine:
    """Deterministic, reproducible assignment of scenarios and populations to variants."""

    @classmethod
    def assign_population(
        cls,
        plan: ExperimentPlan,
        scenarios: list[str],
        seed: int = 42,
        strategy: AssignmentStrategy = AssignmentStrategy.DETERMINISTIC_MODULO,
    ) -> list[ExperimentAssignment]:
        """Generates reproducible assignments of scenarios to variants without bias or leakage."""
        assignments: list[ExperimentAssignment] = []
        variant_ids = [v.id for v in plan.variants]
        if not variant_ids:
            return assignments

        sorted_scenarios = sorted(scenarios)
        k = len(variant_ids)

        for i, scen_id in enumerate(sorted_scenarios):
            if strategy == AssignmentStrategy.DETERMINISTIC_MODULO:
                idx = (i + seed) % k
            elif strategy == AssignmentStrategy.HASH_RING:
                h = int(hashlib.sha256(f"{seed}:{scen_id}".encode("utf-8")).hexdigest(), 16)
                idx = h % k
            else: # Stratified
                idx = (i * 3 + seed) % k

            chosen_variant = variant_ids[idx]
            assignments.append(
                ExperimentAssignment(
                    plan_id=plan.id,
                    assignment_seed=seed,
                    strategy=strategy,
                    scenario_id=scen_id,
                    variant_id=chosen_variant,
                )
            )

        return assignments


class ExperimentEngine:
    """Manages staged experiment execution, stop condition evaluation, and observation collection."""

    def __init__(self) -> None:
        self.plans: dict[str, ExperimentPlan] = {}
        self.runs: dict[str, ExperimentRun] = {}
        self.observations: dict[str, list[ExperimentObservation]] = {}
        self.gates: dict[str, list[ExperimentGate]] = {}

    def create_plan(
        self,
        program_id: str,
        objective: str,
        hypothesis_id: str,
        variants: list[ExperimentVariant],
        dataset_id: str = "default_eval_dataset",
        evaluation_suite_id: str = "comprehensive_suite",
        target_metrics: Optional[list[str]] = None,
        sandbox_environment: SandboxEnvironment = SandboxEnvironment.SIMULATION,
        resource_budget: Optional[dict[str, Any]] = None,
        time_limit_seconds: float = 1800.0,
        rollback_condition: str = "Error rate > 5% or safety regression",
    ) -> ExperimentPlan:
        """Constructs and registers a structured ExperimentPlan."""
        # Ensure variants have fingerprints and plan_id
        plan = ExperimentPlan(
            program_id=program_id,
            objective=objective,
            hypothesis_id=hypothesis_id,
            variants=variants,
            dataset_id=dataset_id,
            evaluation_suite_id=evaluation_suite_id,
            target_metrics=target_metrics or ["quality", "safety", "latency"],
            sandbox_environment=sandbox_environment,
            resource_budget=resource_budget or {"max_cost_usd": 5.0, "max_tokens": 50000},
            time_limit_seconds=time_limit_seconds,
            rollback_condition=rollback_condition,
        )
        for v in plan.variants:
            v.plan_id = plan.id
            v.compute_fingerprint()

        self.plans[plan.id] = plan
        logger.info("Created ExperimentPlan: %s for Program: %s", plan.id, program_id)
        return plan

    def start_run(
        self,
        plan_id: str,
        stage_number: int = 1,
        environment: Optional[SandboxEnvironment] = None,
        target_sample_count: int = 20,
        actor: str = "kairo.adaptation",
    ) -> ExperimentRun:
        """Validates firewall gates and initializes an ExperimentRun. Fails closed if blocked."""
        plan = self.plans.get(plan_id)
        if not plan:
            raise ValueError(f"Experiment plan '{plan_id}' not found.")

        # Firewall check
        passed, blockers = ExperimentFirewall.check_firewall(plan, actor=actor)
        if not passed:
            run = ExperimentRun(
                plan_id=plan.id,
                program_id=plan.program_id,
                stage_number=stage_number,
                environment=environment or plan.sandbox_environment,
                status=RunStatus.BLOCKED,
                stop_reason=f"Blocked by firewall: {'; '.join(blockers)}",
            )
            self.runs[run.id] = run
            logger.warning("Experiment run %s BLOCKED: %s", run.id, run.stop_reason)
            return run

        run = ExperimentRun(
            plan_id=plan.id,
            program_id=plan.program_id,
            stage_number=stage_number,
            environment=environment or plan.sandbox_environment,
            status=RunStatus.RUNNING,
            target_sample_count=target_sample_count,
            started_at=datetime.now(UTC),
        )
        self.runs[run.id] = run
        self.observations[run.id] = []
        self.gates[run.id] = []
        logger.info("Started ExperimentRun: %s (Stage %d, env=%s)", run.id, stage_number, run.environment.value)
        return run

    def check_stop_conditions(
        self,
        run: ExperimentRun,
        error_count: int,
        total_count: int,
        safety_violation_count: int,
        max_observed_latency_ms: float,
        elapsed_seconds: float,
    ) -> tuple[bool, Optional[StopConditionType], str]:
        """Evaluates hard and soft stop conditions during execution.
        Returns: (should_stop, condition_type, reason)
        """
        # 1. EmergencyStop check (absolute primacy)
        e_stop = get_emergency_stop_service()
        if e_stop.is_stopped():
            return True, StopConditionType.EMERGENCY_STOP, "EmergencyStop was activated globally."

        # 2. Safety violation check
        if safety_violation_count > 0:
            return True, StopConditionType.SAFETY_VIOLATION, f"Detected {safety_violation_count} safety invariant breach(es)."

        # 3. Timeout check
        plan = self.plans.get(run.plan_id)
        max_time = plan.time_limit_seconds if plan else 1800.0
        if elapsed_seconds > max_time:
            return True, StopConditionType.TIMEOUT, f"Execution elapsed {elapsed_seconds:.1f}s exceeded limit {max_time:.1f}s."

        # 4. Error rate threshold check (> 10% error rate after at least 5 samples)
        if total_count >= 5:
            error_rate = error_count / total_count
            if error_rate > 0.10:
                return True, StopConditionType.ERROR_RATE_THRESHOLD, f"Error rate {error_rate * 100:.1f}% exceeded 10.0% threshold."

        # 5. Excessive latency check (> 15000ms)
        if max_observed_latency_ms > 15000.0:
            return True, StopConditionType.EXCESSIVE_LATENCY, f"Max latency {max_observed_latency_ms:.1f}ms breached 15s threshold."

        return False, None, ""

    def record_observation(
        self,
        run_id: str,
        variant_id: str,
        scenario_id: str,
        step_index: int,
        latency_ms: float,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        has_error: bool = False,
        error_message: Optional[str] = None,
        world_state_drift: bool = False,
        execution_output: str = "",
    ) -> ExperimentObservation:
        """Records an execution observation and updates run sample count."""
        obs = ExperimentObservation(
            run_id=run_id,
            variant_id=variant_id,
            scenario_id=scenario_id,
            step_index=step_index,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            has_error=has_error,
            error_message=error_message,
            world_state_drift_detected=world_state_drift,
            execution_output=execution_output,
        )
        if run_id not in self.observations:
            self.observations[run_id] = []
        self.observations[run_id].append(obs)

        run = self.runs.get(run_id)
        if run:
            run.current_sample_count = len(self.observations[run_id])
        return obs

    def evaluate_gate(
        self,
        run_id: str,
        gate_name: str,
        measured_value: Optional[float],
        threshold: Optional[float],
        is_critical_security: bool = False,
    ) -> ExperimentGate:
        """Evaluates a fail-closed experiment safety gate."""
        passed = False
        reason = ""

        if measured_value is None or threshold is None:
            passed = False
            reason = "Insufficient evidence: missing measured value or threshold."
        elif is_critical_security:
            if measured_value >= 1.0:
                passed = True
                reason = "100% security invariance satisfied."
            else:
                passed = False
                reason = f"Security gate violated: {measured_value:.2f} < 1.0."
        else:
            if measured_value >= threshold:
                passed = True
                reason = f"Gate passed ({measured_value:.2f} >= {threshold:.2f})."
            else:
                passed = False
                reason = f"Gate breached: {measured_value:.2f} below threshold {threshold:.2f}."

        gate = ExperimentGate(
            run_id=run_id,
            gate_name=gate_name,
            passed=passed,
            is_critical_security=is_critical_security,
            threshold=threshold,
            measured_value=measured_value,
            reason=reason,
        )
        if run_id not in self.gates:
            self.gates[run_id] = []
        self.gates[run_id].append(gate)

        run = self.runs.get(run_id)
        if run and not passed:
            run.passed_safety_gates = False

        return gate

    def stop_run(self, run_id: str, reason: str, is_failure: bool = False) -> ExperimentRun:
        """Transitions an experiment run to STOPPED or FAILED."""
        run = self.runs.get(run_id)
        if not run:
            raise ValueError(f"Experiment run '{run_id}' not found.")
        new_status = RunStatus.FAILED if is_failure else RunStatus.STOPPED
        run.transition_to(new_status, reason=reason)
        logger.info("Experiment run %s transitioned to %s: %s", run.id, run.status.value, reason)
        return run

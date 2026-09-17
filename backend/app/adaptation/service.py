"""Master coordinator service for Task 105:
Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine.

Coordinates the entire governed lifecycle:
EXPERIENCE -> EVALUATE -> FIND WEAKNESS -> FORM HYPOTHESIS -> DESIGN EXPERIMENT
-> SIMULATE/REPLAY -> GOVERN -> CONTROLLED TEST -> MEASURE -> COMPARE -> VERIFY
-> PROPOSE EVOLUTION -> GOVERNED CAPABILITY CHANGE -> RE-EVALUATE -> CONSOLIDATE EXPERIENCE
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.adaptation.comparison_engine import ComparisonEngine
from app.adaptation.domain import (
    AdaptationEvent,
    AdaptationHypothesis,
    AdaptationProgram,
    ComparisonVerdict,
    EvolutionChangeSet,
    EvolutionProposal,
    EvolutionProposalStatus,
    EvolutionReview,
    EvolutionValidation,
    ExperimentAssignment,
    ExperimentComparison,
    ExperimentDecision,
    ExperimentEvidence,
    ExperimentGate,
    ExperimentObservation,
    ExperimentPlan,
    ExperimentRun,
    ExperimentVariant,
    ProgramStatus,
    ReviewStatus,
    RunStatus,
    SandboxEnvironment,
    StopConditionType,
    ValidationStatus,
    VariantConfigType,
    VariantType,
)
from app.adaptation.evolution_engine import EvolutionEngine
from app.adaptation.experiment_engine import ExperimentAssignmentEngine, ExperimentEngine, ExperimentFirewall
from app.adaptation.hypothesis_engine import HypothesisEngine
from app.adaptation.meta_adaptation import MetaAdaptationEngine
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.adaptation.service")


class AutonomousAdaptationService:
    """Master service orchestrating closed-loop autonomous adaptation and governed evolution."""

    def __init__(
        self,
        hypothesis_engine: Optional[HypothesisEngine] = None,
        experiment_engine: Optional[ExperimentEngine] = None,
        comparison_engine: Optional[ComparisonEngine] = None,
        evolution_engine: Optional[EvolutionEngine] = None,
        meta_engine: Optional[MetaAdaptationEngine] = None,
    ) -> None:
        self.hypothesis_engine = hypothesis_engine or HypothesisEngine()
        self.experiment_engine = experiment_engine or ExperimentEngine()
        self.comparison_engine = comparison_engine or ComparisonEngine()
        self.evolution_engine = evolution_engine or EvolutionEngine()
        self.meta_engine = meta_engine or MetaAdaptationEngine()

        # In-memory primary registries (mirrored with DB models)
        self.programs: dict[str, AdaptationProgram] = {}
        self.events: list[AdaptationEvent] = []

    # ==========================================================================
    # 1. EVENT EMISSION
    # ==========================================================================

    def emit_event(
        self,
        event_type: str,
        program_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        proposal_id: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> AdaptationEvent:
        """Records an event in the adaptation audit trail and dispatches to system bus."""
        evt = AdaptationEvent(
            event_type=event_type,
            program_id=program_id,
            experiment_id=experiment_id,
            proposal_id=proposal_id,
            correlation_id=correlation_id or uuid.uuid4().hex[:16],
            payload=payload or {},
            occurred_at=datetime.now(UTC),
        )
        self.events.append(evt)
        logger.info("[EVENT] %s: %s", event_type, evt.id)
        return evt

    # ==========================================================================
    # 2. ADAPTATION PROGRAM LIFECYCLE
    # ==========================================================================

    def create_program(
        self,
        title: str,
        objective: str,
        problem_statement: str,
        affected_capability: str,
        originating_finding_id: Optional[str] = None,
        affected_mission_id: Optional[str] = None,
        affected_situation_id: Optional[str] = None,
        affected_decision_id: Optional[str] = None,
        baseline_id: str = "latest_golden_baseline",
        constraints: Optional[list[str]] = None,
        risks: Optional[list[str]] = None,
        expected_benefit: str = "",
        expected_cost: str = "",
        success_criteria: Optional[dict[str, Any]] = None,
        failure_criteria: Optional[dict[str, Any]] = None,
        safety_criteria: Optional[list[str]] = None,
        resource_budget: Optional[dict[str, Any]] = None,
        time_budget_seconds: float = 3600.0,
        rollback_strategy: str = "Revert to frozen baseline capability parameters",
        validation_strategy: str = "Multi-suite offline replay + simulation gate",
        provenance: Optional[dict[str, Any]] = None,
    ) -> AdaptationProgram:
        """Initializes a new bounded AdaptationProgram."""
        program = AdaptationProgram(
            title=title,
            objective=objective,
            problem_statement=problem_statement,
            originating_finding_id=originating_finding_id,
            affected_capability=affected_capability,
            affected_mission_id=affected_mission_id,
            affected_situation_id=affected_situation_id,
            affected_decision_id=affected_decision_id,
            baseline_id=baseline_id,
            constraints=constraints or [],
            risks=risks or [],
            expected_benefit=expected_benefit or f"Remediate regression in {affected_capability}",
            expected_cost=expected_cost or "Estimated 10,000 tokens",
            success_criteria=success_criteria or {"quality_delta": 0.05},
            failure_criteria=failure_criteria or {"error_rate_max": 0.02},
            safety_criteria=safety_criteria or ["Zero safety violations", "Zero security regressions"],
            resource_budget=resource_budget or {"max_cost_usd": 10.0, "max_tokens": 100000},
            time_budget_seconds=time_budget_seconds,
            rollback_strategy=rollback_strategy,
            validation_strategy=validation_strategy,
            provenance=provenance or {"source": "ContinuousEvaluation"},
            status=ProgramStatus.DRAFT,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.programs[program.id] = program
        self.emit_event(
            "adaptation.created",
            program_id=program.id,
            payload={"title": program.title, "affected_capability": program.affected_capability},
        )
        return program

    def get_program(self, program_id: str) -> Optional[AdaptationProgram]:
        return self.programs.get(program_id)

    def list_programs(self, status: Optional[ProgramStatus] = None) -> list[AdaptationProgram]:
        progs = list(self.programs.values())
        if status:
            progs = [p for p in progs if p.status == status]
        return sorted(progs, key=lambda x: x.created_at, reverse=True)

    # ==========================================================================
    # 3. HYPOTHESIS MANAGEMENT
    # ==========================================================================

    def create_hypothesis(
        self,
        program_id: str,
        condition_change: str,
        expected_outcome: str,
        evidence_reasoning: str,
        confidence: float = 0.5,
        measurable_outcomes: Optional[dict[str, float]] = None,
        falsification_criteria: Optional[list[str]] = None,
        assumptions: Optional[list[str]] = None,
        counter_hypotheses: Optional[list[str]] = None,
        evidence_references: Optional[list[str]] = None,
    ) -> AdaptationHypothesis:
        """Formulates and binds a measurable hypothesis to a program."""
        program = self.programs.get(program_id)
        if not program:
            raise ValueError(f"Program '{program_id}' not found.")

        hyp = self.hypothesis_engine.form_hypothesis(
            condition_change=condition_change,
            expected_outcome=expected_outcome,
            evidence_reasoning=evidence_reasoning,
            confidence=confidence,
            measurable_outcomes=measurable_outcomes,
            falsification_criteria=falsification_criteria,
            assumptions=assumptions,
            counter_hypotheses=counter_hypotheses,
            evidence_references=evidence_references,
            originating_finding_id=program.originating_finding_id,
        )
        program.hypothesis_id = hyp.id
        program.updated_at = datetime.now(UTC)

        self.emit_event(
            "hypothesis.created",
            program_id=program.id,
            payload={"hypothesis_id": hyp.id, "confidence": hyp.confidence},
        )
        return hyp

    def get_hypothesis(self, hypothesis_id: str) -> Optional[AdaptationHypothesis]:
        return self.hypothesis_engine.hypotheses.get(hypothesis_id)

    # ==========================================================================
    # 4. EXPERIMENT ORCHESTRATION
    # ==========================================================================

    def design_experiment(
        self,
        program_id: str,
        objective: str,
        hypothesis_id: str,
        candidate_config_delta: dict[str, Any],
        target_artifact_id: str,
        sandbox_environment: SandboxEnvironment = SandboxEnvironment.SIMULATION,
        resource_budget: Optional[dict[str, Any]] = None,
        time_limit_seconds: float = 1800.0,
    ) -> ExperimentPlan:
        """Constructs a structured experiment plan with Baseline, Candidate, and No-Action variants."""
        program = self.programs.get(program_id)
        if not program:
            raise ValueError(f"Program '{program_id}' not found.")

        # Baseline control variant (immutable)
        v_baseline = ExperimentVariant(
            name=f"baseline_{program.affected_capability}",
            variant_type=VariantType.BASELINE,
            config_type=VariantConfigType.CAPABILITY_VERSION,
            target_artifact_id=target_artifact_id,
            configuration_delta={},
            is_control=True,
        )

        # Candidate intervention variant
        v_candidate = ExperimentVariant(
            name=f"candidate_{program.affected_capability}",
            variant_type=VariantType.CANDIDATE,
            config_type=VariantConfigType.CONFIGURATION,
            target_artifact_id=target_artifact_id,
            configuration_delta=candidate_config_delta,
            is_control=False,
        )

        # No-Action control variant
        v_no_action = ExperimentVariant(
            name=f"no_action_{program.affected_capability}",
            variant_type=VariantType.NO_ACTION,
            config_type=VariantConfigType.CONFIGURATION,
            target_artifact_id=target_artifact_id,
            configuration_delta={"mode": "noop"},
            is_control=True,
        )

        plan = self.experiment_engine.create_plan(
            program_id=program_id,
            objective=objective,
            hypothesis_id=hypothesis_id,
            variants=[v_baseline, v_candidate, v_no_action],
            sandbox_environment=sandbox_environment,
            resource_budget=resource_budget,
            time_limit_seconds=time_limit_seconds,
        )

        program.transition_to(ProgramStatus.APPROVED, reason="Experiment plan designed and approved for testing.")
        self.emit_event(
            "experiment.created",
            program_id=program_id,
            payload={"plan_id": plan.id, "variants_count": len(plan.variants)},
        )
        return plan

    def start_experiment(
        self,
        plan_id: str,
        stage_number: int = 1,
        target_sample_count: int = 20,
        actor: str = "kairo.adaptation",
    ) -> ExperimentRun:
        """Launches an experiment run through the fail-closed firewall."""
        plan = self.experiment_engine.plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        program = self.programs.get(plan.program_id)
        if program and program.status != ProgramStatus.EXPERIMENTING:
            program.transition_to(ProgramStatus.EXPERIMENTING, reason="Experiment run started.")

        run = self.experiment_engine.start_run(
            plan_id=plan_id,
            stage_number=stage_number,
            environment=plan.sandbox_environment,
            target_sample_count=target_sample_count,
            actor=actor,
        )

        if run.status == RunStatus.BLOCKED:
            if program:
                program.transition_to(ProgramStatus.BLOCKED, reason=run.stop_reason or "Blocked by firewall")
            self.emit_event(
                "experiment.blocked",
                program_id=plan.program_id,
                experiment_id=run.id,
                payload={"reason": run.stop_reason},
            )
        else:
            self.emit_event(
                "experiment.started",
                program_id=plan.program_id,
                experiment_id=run.id,
                payload={"stage": stage_number, "target_samples": target_sample_count},
            )

        return run

    def execute_controlled_test_cycle(
        self,
        run_id: str,
        simulated_scenarios: Optional[list[str]] = None,
        candidate_quality_delta: float = 0.08,
        candidate_latency_delta_ms: float = -30.0,
        simulate_safety_failure: bool = False,
    ) -> ExperimentComparison:
        """Executes a simulated closed test cycle for an active experiment run.
        Records observations, evaluates gates, and computes comparison.
        """
        run = self.experiment_engine.runs.get(run_id)
        if not run:
            raise ValueError(f"Run '{run_id}' not found.")
        plan = self.experiment_engine.plans.get(run.plan_id)
        if not plan:
            raise ValueError(f"Plan '{run.plan_id}' not found.")

        # Check EmergencyStop
        e_stop = get_emergency_stop_service()
        if e_stop.is_stopped():
            run.transition_to(RunStatus.STOPPED, reason="EmergencyStop is active. Run halted immediately.")
            self.emit_event("experiment.stopped", experiment_id=run.id, payload={"reason": "EmergencyStop active"})
            cmp = ExperimentComparison(
                run_id=run.id,
                baseline_variant_id=plan.variants[0].id,
                candidate_variant_id=plan.variants[1].id,
                verdict=ComparisonVerdict.INCONCLUSIVE,
                rationale="Halted due to active EmergencyStop.",
            )
            self.comparison_engine.comparisons[cmp.id] = cmp
            return cmp

        scenarios = simulated_scenarios or [f"eval_case_{i:03d}" for i in range(run.target_sample_count)]

        # Generate deterministic assignment
        assignments = ExperimentAssignmentEngine.assign_population(plan, scenarios, seed=42)

        baseline_var = next(v for v in plan.variants if v.variant_type == VariantType.BASELINE)
        candidate_var = next(v for v in plan.variants if v.variant_type == VariantType.CANDIDATE)
        no_action_var = next((v for v in plan.variants if v.variant_type == VariantType.NO_ACTION), None)

        # Record observations across assigned scenarios
        observations: list[ExperimentObservation] = []
        for i, asgn in enumerate(assignments):
            is_cand = asgn.variant_id == candidate_var.id
            lat = 450.0 + (candidate_latency_delta_ms if is_cand else 0.0) + (i % 5) * 10
            err = simulate_safety_failure and is_cand and (i == 3)
            err_msg = "Safety invariant breached in candidate variant" if err else None

            obs = self.experiment_engine.record_observation(
                run_id=run.id,
                variant_id=asgn.variant_id,
                scenario_id=asgn.scenario_id,
                step_index=i,
                latency_ms=lat,
                tokens_used=1200,
                cost_usd=0.015,
                has_error=err,
                error_message=err_msg,
                world_state_drift=False,
                execution_output="Simulated scenario completion.",
            )
            observations.append(obs)

        # Evaluate safety gate
        self.experiment_engine.evaluate_gate(
            run_id=run.id,
            gate_name="SAFETY_INVARIANTS_GATE",
            measured_value=0.0 if simulate_safety_failure else 1.0,
            threshold=1.0,
            is_critical_security=True,
        )

        if simulate_safety_failure:
            run.transition_to(RunStatus.FAILED, reason="Safety invariant breached during test execution.")
            self.emit_event("experiment.safety_failure", experiment_id=run.id, payload={"details": "Critical security gate failed"})
            cmp = ExperimentComparison(
                run_id=run.id,
                baseline_variant_id=baseline_var.id,
                candidate_variant_id=candidate_var.id,
                verdict=ComparisonVerdict.REGRESSED,
                rationale="Safety gate failed with invariant breach.",
                sample_size=len(observations),
            )
            self.comparison_engine.comparisons[cmp.id] = cmp
            return cmp

        # Compute comparison
        base_metrics = {"quality": 0.80, "safety": 1.0, "latency_ms": 480.0, "reliability": 0.98}
        cand_metrics = {
            "quality": 0.80 + candidate_quality_delta,
            "safety": 1.0,
            "latency_ms": 480.0 + candidate_latency_delta_ms,
            "reliability": 0.99,
        }
        no_action_metrics = {"quality": 0.65, "safety": 1.0, "latency_ms": 500.0, "reliability": 0.95}

        cmp = self.comparison_engine.compare_variants(
            run_id=run.id,
            baseline_variant=baseline_var,
            candidate_variant=candidate_var,
            no_action_variant=no_action_var,
            baseline_metrics=base_metrics,
            candidate_metrics=cand_metrics,
            no_action_metrics=no_action_metrics,
            observations=observations,
            min_sample_size=10,
        )

        run.transition_to(RunStatus.COMPLETED, reason=cmp.rationale)

        # Seal evidence
        hyp = self.hypothesis_engine.hypotheses.get(plan.hypothesis_id)
        hyp_text = f"IF {hyp.condition_change} THEN {hyp.expected_outcome}" if hyp else "Adaptation hypothesis"
        evidence = self.comparison_engine.package_sealed_evidence(
            run_id=run.id,
            program_id=plan.program_id,
            hypothesis_text=hyp_text,
            baseline_summary=base_metrics,
            candidate_summary=cand_metrics,
            comparison=cmp,
            observations_count=len(observations),
            safety_gates_passed=True,
            resource_consumed={"cost_usd": len(observations) * 0.015, "tokens_used": len(observations) * 1200},
        )

        self.emit_event(
            "experiment.completed",
            program_id=plan.program_id,
            experiment_id=run.id,
            payload={"verdict": cmp.verdict.value, "evidence_id": evidence.id},
        )
        return cmp

    # ==========================================================================
    # 5. EVOLUTION PROPOSAL & GOVERNANCE
    # ==========================================================================

    def create_evolution_proposal(
        self,
        program_id: str,
        run_id: str,
        target_version: str = "1.1.0",
        deployment_scope: str = "CANARY_10_PERCENT",
    ) -> EvolutionProposal:
        """Constructs an EvolutionProposal and ChangeSet from verified experimental evidence."""
        program = self.programs.get(program_id)
        run = self.experiment_engine.runs.get(run_id)
        if not program or not run:
            raise ValueError("Program or run not found.")

        plan = self.experiment_engine.plans.get(run.plan_id)
        if not plan:
            raise ValueError("Plan not found.")

        # Locate comparison and evidence
        cmp = next((c for c in self.comparison_engine.comparisons.values() if c.run_id == run_id), None)
        evidence = next((e for e in self.comparison_engine.evidences.values() if e.run_id == run_id), None)
        if not cmp or not evidence:
            raise ValueError(f"No comparison or sealed evidence found for run '{run_id}'.")

        candidate_var = next(v for v in plan.variants if v.variant_type == VariantType.CANDIDATE)

        proposal = self.evolution_engine.create_proposal_from_evidence(
            program_id=program.id,
            evidence=evidence,
            comparison=cmp,
            title=f"Evolution Proposal: {program.title}",
            affected_capability=program.affected_capability,
            current_version=program.version,
            target_version=target_version,
            baseline_id=program.baseline_id,
            candidate_variant_id=candidate_var.id,
            deployment_scope=deployment_scope,
        )

        # Generate immutable changeset
        changeset = self.evolution_engine.generate_changeset(
            proposal=proposal,
            configuration_delta=candidate_var.configuration_delta,
            dependencies=[],
        )

        program.transition_to(ProgramStatus.VALIDATING, reason="Evolution proposal and changeset generated.")
        self.emit_event(
            "evolution.proposed",
            program_id=program.id,
            proposal_id=proposal.id,
            payload={"target_version": target_version, "changeset_id": changeset.id},
        )
        return proposal

    def review_evolution_proposal(
        self,
        proposal_id: str,
        reviewer: str,
        status: ReviewStatus,
        rationale: str,
        approval_reference_id: Optional[str] = None,
    ) -> EvolutionReview:
        """Formal governance or human review on an evolution proposal."""
        review = self.evolution_engine.record_review(
            proposal_id=proposal_id,
            reviewer=reviewer,
            status=status,
            rationale=rationale,
            approval_reference_id=approval_reference_id,
        )

        proposal = self.evolution_engine.proposals.get(proposal_id)
        if proposal and status == ReviewStatus.APPROVED:
            program = self.programs.get(proposal.program_id)
            if program and program.status in {ProgramStatus.VALIDATING, ProgramStatus.EXPERIMENTING}:
                program.transition_to(ProgramStatus.SUCCESSFUL, reason=f"Proposal approved by {reviewer}")
            self.emit_event(
                "evolution.approved",
                program_id=proposal.program_id,
                proposal_id=proposal.id,
                payload={"reviewer": reviewer, "approval_ref": approval_reference_id},
            )
        elif proposal and status == ReviewStatus.REJECTED:
            program = self.programs.get(proposal.program_id)
            if program:
                program.transition_to(ProgramStatus.FAILED, reason=f"Proposal rejected by {reviewer}: {rationale}")
            self.emit_event(
                "evolution.rejected",
                program_id=proposal.program_id,
                proposal_id=proposal.id,
                payload={"reviewer": reviewer, "rationale": rationale},
            )

        return review

    def validate_evolution(
        self,
        proposal_id: str,
        changeset_id: str,
        include_holdout: bool = True,
    ) -> EvolutionValidation:
        """Runs multi-suite validation prior to capability promotion."""
        val = self.evolution_engine.run_evolution_validation(
            proposal_id=proposal_id,
            changeset_id=changeset_id,
            include_holdout=include_holdout,
        )
        self.emit_event(
            "evolution.validated",
            proposal_id=proposal_id,
            payload={"overall_status": val.overall_status.value, "holdout_passed": val.holdout_passed},
        )
        return val

    # ==========================================================================
    # 6. MEMORY & SELF-MODEL HANDOFFS
    # ==========================================================================

    async def handoff_to_cognitive_memory(
        self,
        summary: str,
        evidence_dict: dict[str, Any],
        outcome: str = "SUCCESS",
    ) -> Optional[str]:
        """Consolidates verified adaptation findings into Task 103 Lifelong Memory (record_experience)."""
        try:
            from app.cognitive_memory.service import get_cognitive_memory_service
            from app.cognitive_memory.domain import ExperienceSource, ExperienceTrust

            mem_service = get_cognitive_memory_service()
            exp, _ = mem_service.record_experience(
                summary=f"Autonomous Adaptation: {summary}",
                structured_facts=evidence_dict,
                source_type=ExperienceSource.VERIFICATION,
                trust_classification=ExperienceTrust.SYSTEM_VERIFIED if outcome == "SUCCESS" else ExperienceTrust.OBSERVED,
                confidence=0.92,
                importance=0.85,
            )
            return exp.experience_id
        except Exception as exc:
            logger.warning("Cognitive memory handoff skipped: %s", exc)
            return None

    # ==========================================================================
    # 7. DASHBOARD METRICS
    # ==========================================================================

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Calculates global KPIs for the Adaptation & Evolution console."""
        progs = list(self.programs.values())
        runs = list(self.experiment_engine.runs.values())
        props = list(self.evolution_engine.proposals.values())
        e_stop = get_emergency_stop_service()

        return {
            "active_experiments": sum(1 for r in runs if r.status == RunStatus.RUNNING),
            "blocked_count": sum(1 for r in runs if r.status == RunStatus.BLOCKED) + sum(1 for p in progs if p.status == ProgramStatus.BLOCKED),
            "failed_count": sum(1 for r in runs if r.status == RunStatus.FAILED),
            "inconclusive_count": sum(1 for r in runs if r.status == RunStatus.INCONCLUSIVE),
            "improving_count": sum(1 for c in self.comparison_engine.comparisons.values() if c.verdict == ComparisonVerdict.IMPROVED),
            "regressing_count": sum(1 for c in self.comparison_engine.comparisons.values() if c.verdict == ComparisonVerdict.REGRESSED),
            "awaiting_review_count": sum(1 for p in props if p.status in {EvolutionProposalStatus.SUBMITTED, EvolutionProposalStatus.UNDER_REVIEW}),
            "awaiting_approval_count": sum(1 for p in props if p.status == EvolutionProposalStatus.APPROVED and p.required_approval),
            "validating_count": sum(1 for p in progs if p.status == ProgramStatus.VALIDATING),
            "emergency_stop_active": e_stop.is_stopped(),
            "recent_programs": progs[:10],
            "recent_experiments": runs[:10],
            "recent_proposals": props[:10],
        }


# Singleton accessor
_service_instance: Optional[AutonomousAdaptationService] = None

def get_adaptation_service() -> AutonomousAdaptationService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AutonomousAdaptationService()
    return _service_instance

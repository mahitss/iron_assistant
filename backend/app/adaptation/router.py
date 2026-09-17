"""REST API Router for Task 105:
Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adaptation.domain import (
    EvolutionProposalStatus,
    ProgramStatus,
    ReviewStatus,
    RunStatus,
    SandboxEnvironment,
)
from app.adaptation.schemas import (
    AdaptationDashboardResponse,
    AdaptationHypothesisCreate,
    AdaptationHypothesisResponse,
    AdaptationProgramCreate,
    AdaptationProgramResponse,
    AdaptationProgramUpdate,
    EvolutionChangeSetResponse,
    EvolutionProposalCreate,
    EvolutionProposalResponse,
    EvolutionReviewRequest,
    EvolutionReviewResponse,
    EvolutionValidationRequest,
    EvolutionValidationResponse,
    ExperimentActionRequest,
    ExperimentComparisonResponse,
    ExperimentEvidenceResponse,
    ExperimentGateResponse,
    ExperimentPlanCreate,
    ExperimentPlanResponse,
    ExperimentRunCreate,
    ExperimentRunResponse,
)
from app.adaptation.service import AutonomousAdaptationService, get_adaptation_service

router = APIRouter(tags=["Adaptation & Governed Evolution"])


# ==============================================================================
# 1. DASHBOARD
# ==============================================================================

@router.get("/adaptation/dashboard", response_model=AdaptationDashboardResponse)
async def get_adaptation_dashboard(
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Returns real-time KPIs and status for the Adaptation & Evolution console."""
    return service.get_dashboard_summary()


# ==============================================================================
# 2. ADAPTATION PROGRAMS
# ==============================================================================

@router.get("/adaptation/programs", response_model=list[AdaptationProgramResponse])
async def list_adaptation_programs(
    status_filter: Optional[ProgramStatus] = Query(None, alias="status"),
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """List all registered adaptation programs."""
    return service.list_programs(status=status_filter)


@router.post("/adaptation/programs", response_model=AdaptationProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_adaptation_program(
    payload: AdaptationProgramCreate,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Creates a new bounded improvement initiative program."""
    program = service.create_program(
        title=payload.title,
        objective=payload.objective,
        problem_statement=payload.problem_statement,
        affected_capability=payload.affected_capability,
        originating_finding_id=payload.originating_finding_id,
        affected_mission_id=payload.affected_mission_id,
        affected_situation_id=payload.affected_situation_id,
        affected_decision_id=payload.affected_decision_id,
        baseline_id=payload.baseline_id,
        constraints=payload.constraints,
        risks=payload.risks,
        expected_benefit=payload.expected_benefit,
        expected_cost=payload.expected_cost,
        success_criteria=payload.success_criteria,
        failure_criteria=payload.failure_criteria,
        safety_criteria=payload.safety_criteria,
        resource_budget=payload.resource_budget,
        time_budget_seconds=payload.time_budget_seconds,
        rollback_strategy=payload.rollback_strategy,
        validation_strategy=payload.validation_strategy,
        provenance=payload.provenance,
    )
    return program


@router.get("/adaptation/programs/{program_id}", response_model=AdaptationProgramResponse)
async def get_adaptation_program(
    program_id: str,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Retrieves an adaptation program by ID."""
    program = service.get_program(program_id)
    if not program:
        raise HTTPException(status_code=404, detail=f"Adaptation program '{program_id}' not found.")
    return program


# ==============================================================================
# 3. HYPOTHESES
# ==============================================================================

@router.get("/adaptation/hypotheses", response_model=list[AdaptationHypothesisResponse])
async def list_hypotheses(
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """List all formulated adaptation hypotheses."""
    return list(service.hypothesis_engine.hypotheses.values())


@router.post("/adaptation/hypotheses", response_model=AdaptationHypothesisResponse, status_code=status.HTTP_201_CREATED)
async def create_hypothesis(
    payload: AdaptationHypothesisCreate,
    program_id: str = Query(..., description="Program ID to bind hypothesis to"),
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Formulates and validates a measurable IF-THEN-BECAUSE hypothesis."""
    try:
        return service.create_hypothesis(
            program_id=program_id,
            condition_change=payload.condition_change,
            expected_outcome=payload.expected_outcome,
            evidence_reasoning=payload.evidence_reasoning,
            confidence=payload.confidence,
            measurable_outcomes=payload.measurable_outcomes,
            falsification_criteria=payload.falsification_criteria,
            assumptions=payload.assumptions,
            counter_hypotheses=payload.counter_hypotheses,
            evidence_references=payload.evidence_references,
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


# ==============================================================================
# 4. EXPERIMENTS
# ==============================================================================

@router.get("/adaptation/experiments", response_model=list[ExperimentRunResponse])
async def list_experiments(
    status_filter: Optional[RunStatus] = Query(None, alias="status"),
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """List all experiment runs."""
    runs = list(service.experiment_engine.runs.values())
    if status_filter:
        runs = [r for r in runs if r.status == status_filter]
    return sorted(runs, key=lambda x: x.created_at, reverse=True)


@router.post("/adaptation/experiments", response_model=ExperimentPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment_plan(
    payload: ExperimentPlanCreate,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Designs a structured experiment plan."""
    from app.adaptation.domain import ExperimentVariant
    variants = [
        ExperimentVariant(
            name=v.name,
            variant_type=v.variant_type,
            config_type=v.config_type,
            target_artifact_id=v.target_artifact_id,
            configuration_delta=v.configuration_delta,
            is_control=v.is_control,
        )
        for v in payload.variants
    ]
    try:
        plan = service.experiment_engine.create_plan(
            program_id=payload.program_id,
            objective=payload.objective,
            hypothesis_id=payload.hypothesis_id,
            variants=variants,
            dataset_id=payload.dataset_id,
            evaluation_suite_id=payload.evaluation_suite_id,
            target_metrics=payload.target_metrics,
            sandbox_environment=payload.sandbox_environment,
            resource_budget=payload.resource_budget,
            time_limit_seconds=payload.time_limit_seconds,
            rollback_condition=payload.rollback_condition,
        )
        return plan
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.get("/adaptation/experiments/{run_id}", response_model=ExperimentRunResponse)
async def get_experiment_run(
    run_id: str,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Get details of a specific experiment run."""
    run = service.experiment_engine.runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Experiment run '{run_id}' not found.")
    return run


@router.post("/adaptation/experiments/{plan_id}/start", response_model=ExperimentRunResponse)
async def start_experiment_run(
    plan_id: str,
    stage_number: int = Query(1, ge=1, le=5),
    target_samples: int = Query(20, ge=5, le=500),
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Starts an experiment run subject to fail-closed firewall checks."""
    try:
        run = service.start_experiment(plan_id=plan_id, stage_number=stage_number, target_sample_count=target_samples)
        return run
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/adaptation/experiments/{run_id}/stop", response_model=ExperimentRunResponse)
async def stop_experiment_run(
    run_id: str,
    payload: ExperimentActionRequest,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Stops an active experiment run."""
    try:
        run = service.experiment_engine.stop_run(run_id=run_id, reason=payload.reason or "Manual stop requested")
        service.emit_event("experiment.stopped", experiment_id=run_id, payload={"reason": payload.reason})
        return run
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.post("/adaptation/experiments/{run_id}/pause", response_model=ExperimentRunResponse)
async def pause_experiment_run(
    run_id: str,
    payload: ExperimentActionRequest,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Pauses an active experiment run."""
    run = service.experiment_engine.runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    run.transition_to(RunStatus.PAUSED, reason=payload.reason or "Paused by user")
    service.emit_event("experiment.paused", experiment_id=run_id)
    return run


@router.post("/adaptation/experiments/{run_id}/resume", response_model=ExperimentRunResponse)
async def resume_experiment_run(
    run_id: str,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Resumes a paused experiment run."""
    run = service.experiment_engine.runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    run.transition_to(RunStatus.RUNNING, reason="Resumed by user")
    service.emit_event("experiment.resumed", experiment_id=run_id)
    return run


@router.get("/adaptation/experiments/{run_id}/results", response_model=ExperimentComparisonResponse)
async def get_experiment_results(
    run_id: str,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Retrieves statistical comparison results for an experiment run."""
    cmp = next((c for c in service.comparison_engine.comparisons.values() if c.run_id == run_id), None)
    if not cmp:
        raise HTTPException(status_code=404, detail=f"No comparison results available for run '{run_id}'.")
    return cmp


@router.get("/adaptation/experiments/{run_id}/evidence", response_model=ExperimentEvidenceResponse)
async def get_experiment_evidence(
    run_id: str,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Retrieves immutable sealed evidence for an experiment run."""
    evi = next((e for e in service.comparison_engine.evidences.values() if e.run_id == run_id), None)
    if not evi:
        raise HTTPException(status_code=404, detail=f"No evidence package sealed for run '{run_id}'.")
    return evi


@router.get("/adaptation/comparisons", response_model=list[ExperimentComparisonResponse])
async def list_comparisons(
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """List all computed experiment comparisons."""
    return list(service.comparison_engine.comparisons.values())


@router.get("/adaptation/gates", response_model=list[ExperimentGateResponse])
async def list_gates(
    run_id: Optional[str] = Query(None),
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """List all evaluated safety and security gates."""
    all_gates: list[Any] = []
    if run_id:
        all_gates = service.experiment_engine.gates.get(run_id, [])
    else:
        for glist in service.experiment_engine.gates.values():
            all_gates.extend(glist)
    return all_gates


# ==============================================================================
# 5. EVOLUTION PROPOSALS, REVIEWS & CHANGESETS
# ==============================================================================

@router.get("/evolution/proposals", response_model=list[EvolutionProposalResponse])
async def list_evolution_proposals(
    status_filter: Optional[EvolutionProposalStatus] = Query(None, alias="status"),
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """List all formal evolution proposals."""
    props = list(service.evolution_engine.proposals.values())
    if status_filter:
        props = [p for p in props if p.status == status_filter]
    return sorted(props, key=lambda x: x.created_at, reverse=True)


@router.post("/evolution/proposals", response_model=EvolutionProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_evolution_proposal(
    program_id: str = Query(...),
    run_id: str = Query(...),
    target_version: str = Query("1.1.0"),
    deployment_scope: str = Query("CANARY_10_PERCENT"),
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Generates an EvolutionProposal and immutable ChangeSet from verified experimental evidence."""
    try:
        return service.create_evolution_proposal(
            program_id=program_id,
            run_id=run_id,
            target_version=target_version,
            deployment_scope=deployment_scope,
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.get("/evolution/proposals/{proposal_id}", response_model=EvolutionProposalResponse)
async def get_evolution_proposal(
    proposal_id: str,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Retrieves an evolution proposal by ID."""
    prop = service.evolution_engine.proposals.get(proposal_id)
    if not prop:
        raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' not found.")
    return prop


@router.post("/evolution/proposals/{proposal_id}/review", response_model=EvolutionReviewResponse)
async def review_evolution_proposal(
    proposal_id: str,
    payload: EvolutionReviewRequest,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Records formal human or governance review on an evolution proposal."""
    try:
        return service.review_evolution_proposal(
            proposal_id=proposal_id,
            reviewer=payload.reviewer,
            status=payload.status,
            rationale=payload.rationale,
            approval_reference_id=payload.approval_reference_id,
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@router.get("/evolution/reviews", response_model=list[EvolutionReviewResponse])
async def list_evolution_reviews(
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """List all recorded evolution reviews."""
    return list(service.evolution_engine.reviews.values())


@router.get("/evolution/changesets", response_model=list[EvolutionChangeSetResponse])
async def list_changesets(
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """List all immutable evolution changesets."""
    return list(service.evolution_engine.changesets.values())


@router.post("/evolution/validation", response_model=EvolutionValidationResponse)
async def validate_evolution_changeset(
    payload: EvolutionValidationRequest,
    service: AutonomousAdaptationService = Depends(get_adaptation_service),
) -> Any:
    """Executes multi-suite validation prior to capability promotion."""
    try:
        return service.validate_evolution(
            proposal_id=payload.proposal_id,
            changeset_id=payload.changeset_id,
            include_holdout=payload.include_holdout,
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

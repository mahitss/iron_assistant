"""FastAPI REST routers for Kairo Autonomous Hypothesis, Experimentation & Scientific Discovery Engine (Task 72)."""

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.discovery.schemas import (
    DiscoveryAuditEvent,
    DiscoveryHealthMetrics,
    DiscoveryHypothesis,
    DiscoveryRequest,
    DiscoverySession,
    DiscoveryState,
    EnvironmentType,
    ExperimentDesign,
    ExperimentObservation,
    ExperimentResult,
    ExperimentType,
    PreExecutionPrediction,
)
from app.discovery.service import get_discovery_service

# Routers
discovery_router = APIRouter(prefix="/discovery", tags=["Discovery Engine"])
experiments_router = APIRouter(prefix="/experiments", tags=["Experimentation Engine"])


# -----------------------------------------------------------------------------
# Request Payloads
# -----------------------------------------------------------------------------


class GenerateHypothesesRequest(BaseModel):
    candidate_explanations: list[dict[str, Any]] = Field(
        ...,
        description="Candidate explanations with descriptions and falsification criteria",
    )


class DesignExperimentRequest(BaseModel):
    discovery_id: str
    hypothesis_ids: list[str]
    objective: str
    experiment_type: ExperimentType = ExperimentType.OBSERVATIONAL
    environment: EnvironmentType = EnvironmentType.STAGING
    description: str = ""
    independent_variables: dict[str, Any] = Field(default_factory=dict)
    dependent_variables: list[str] = Field(default_factory=list)
    control_variables: dict[str, Any] = Field(default_factory=dict)
    potential_confounders: list[str] = Field(default_factory=list)
    baseline: dict[str, Any] = Field(default_factory=dict)
    expected_result: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)
    falsification_criteria: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    estimated_cost: float = 0.1
    estimated_duration_sec: int = 60
    expected_information_gain: float = 0.8
    scope: str = "isolated"


class RecordPredictionRequest(BaseModel):
    hypothesis_id: str
    expected_direction: str = Field(..., description="decrease, increase, neutral")
    confidence: float = 0.75
    expected_range: str = ""
    assumptions: list[str] = Field(default_factory=list)


class ApproveExperimentRequest(BaseModel):
    approver: str = Field(..., description="Name or role authorizing the experiment")


class ExecuteExperimentRequest(BaseModel):
    mock_observation_value: Any | None = None


class RecordObservationRequest(BaseModel):
    source: str
    measurement_metric: str
    value: Any
    unit: str = ""
    environment: EnvironmentType = EnvironmentType.STAGING
    raw_reference: str = ""
    verification_state: str = "UNVERIFIED"
    is_simulation: bool = False


class AnalyzeExperimentRequest(BaseModel):
    controls_intact: bool = True
    confounders_detected: list[str] = Field(default_factory=list)
    environment_valid: bool = True
    measurement_error: str | None = None


class ReplicateExperimentRequest(BaseModel):
    original_experiment_id: str
    replication_experiment_id: str


# -----------------------------------------------------------------------------
# Discovery Endpoints (/discovery)
# -----------------------------------------------------------------------------


@discovery_router.post("/start", response_model=DiscoverySession, status_code=status.HTTP_201_CREATED)
async def start_discovery(
    payload: DiscoveryRequest,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = "default",
    x_workspace_id: Annotated[str | None, Header(alias="X-Workspace-ID")] = "default",
) -> DiscoverySession:
    """Initiates an autonomous scientific discovery session."""
    payload.tenant_id = x_tenant_id or "default"
    payload.workspace_id = x_workspace_id or "default"
    service = get_discovery_service()
    return service.start_discovery(payload)


@discovery_router.get("/{discovery_id}", response_model=DiscoverySession)
async def get_discovery(discovery_id: str) -> DiscoverySession:
    """Retrieves discovery session state and artifacts."""
    service = get_discovery_service()
    session = service.get_discovery(discovery_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Discovery session '{discovery_id}' not found.")
    return session


@discovery_router.get("", response_model=list[DiscoverySession])
async def list_discoveries(
    tenant_id: str = "default",
    workspace_id: str = "default",
    status_filter: DiscoveryState | None = None,
) -> list[DiscoverySession]:
    """Lists discovery sessions for the workspace."""
    service = get_discovery_service()
    return service.list_discoveries(tenant_id=tenant_id, workspace_id=workspace_id, status=status_filter)


@discovery_router.post("/{discovery_id}/hypotheses", response_model=list[DiscoveryHypothesis])
async def add_hypotheses(
    discovery_id: str,
    payload: GenerateHypothesesRequest,
) -> list[DiscoveryHypothesis]:
    """Generates competing hypotheses for the discovery question."""
    service = get_discovery_service()
    try:
        return service.generate_hypotheses(discovery_id, payload.candidate_explanations)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@discovery_router.get("/{discovery_id}/hypotheses", response_model=list[DiscoveryHypothesis])
async def get_hypotheses(discovery_id: str) -> list[DiscoveryHypothesis]:
    """Gets ranked hypotheses for a discovery session."""
    service = get_discovery_service()
    session = service.get_discovery(discovery_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Discovery session '{discovery_id}' not found.")
    return session.hypotheses


@discovery_router.post("/{discovery_id}/conclude", response_model=DiscoverySession)
async def conclude_discovery(discovery_id: str) -> DiscoverySession:
    """Concludes discovery, validates results, and consolidates candidate knowledge."""
    service = get_discovery_service()
    try:
        return service.conclude_discovery(discovery_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@discovery_router.get("/{discovery_id}/audit", response_model=list[DiscoveryAuditEvent])
async def get_discovery_audit(discovery_id: str) -> list[DiscoveryAuditEvent]:
    """Returns provenance and audit events for a discovery session."""
    service = get_discovery_service()
    return service.get_audit_trail(discovery_id=discovery_id)


# -----------------------------------------------------------------------------
# Experimentation Endpoints (/experiments)
# -----------------------------------------------------------------------------


@experiments_router.post("/design", response_model=ExperimentDesign, status_code=status.HTTP_201_CREATED)
async def design_experiment(payload: DesignExperimentRequest) -> ExperimentDesign:
    """Designs a controlled, safety-gated scientific experiment."""
    service = get_discovery_service()
    try:
        return service.design_experiment(
            discovery_id=payload.discovery_id,
            hypothesis_ids=payload.hypothesis_ids,
            objective=payload.objective,
            experiment_type=payload.experiment_type,
            environment=payload.environment,
            description=payload.description,
            independent_variables=payload.independent_variables,
            dependent_variables=payload.dependent_variables,
            control_variables=payload.control_variables,
            potential_confounders=payload.potential_confounders,
            baseline=payload.baseline,
            expected_result=payload.expected_result,
            success_criteria=payload.success_criteria,
            failure_criteria=payload.failure_criteria,
            falsification_criteria=payload.falsification_criteria,
            dependencies=payload.dependencies,
            estimated_cost=payload.estimated_cost,
            estimated_duration_sec=payload.estimated_duration_sec,
            expected_information_gain=payload.expected_information_gain,
            scope=payload.scope,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@experiments_router.get("/queue")
async def get_experiment_queue() -> dict[str, Any]:
    """Returns status counts and pending queue items."""
    service = get_discovery_service()
    return {
        "status_counts": service.queue_manager.get_status_counts(),
        "experiments": service.queue_manager.list_experiments(),
    }


@experiments_router.get("/health", response_model=DiscoveryHealthMetrics)
async def get_experiments_health() -> DiscoveryHealthMetrics:
    """Returns Task 72 health metrics."""
    service = get_discovery_service()
    return service.get_health_metrics()


@experiments_router.get("/{experiment_id}", response_model=ExperimentDesign)
async def get_experiment(experiment_id: str) -> ExperimentDesign:
    """Retrieves an experiment specification."""
    service = get_discovery_service()
    exp = service.queue_manager.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    return exp


@experiments_router.post("/{experiment_id}/prediction", response_model=PreExecutionPrediction)
async def record_prediction(
    experiment_id: str,
    payload: RecordPredictionRequest,
) -> PreExecutionPrediction:
    """Records immutable prediction BEFORE executing the experiment."""
    service = get_discovery_service()
    try:
        return service.record_pre_execution_prediction(
            experiment_id=experiment_id,
            hypothesis_id=payload.hypothesis_id,
            expected_direction=payload.expected_direction,
            confidence=payload.confidence,
            expected_range=payload.expected_range,
            assumptions=payload.assumptions,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@experiments_router.post("/{experiment_id}/approve", response_model=ExperimentDesign)
async def approve_experiment(
    experiment_id: str,
    payload: ApproveExperimentRequest,
) -> ExperimentDesign:
    """Grants human-in-the-loop authorization for a gated experiment."""
    service = get_discovery_service()
    try:
        return service.approve_experiment(experiment_id, payload.approver)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@experiments_router.post("/{experiment_id}/start", response_model=ExperimentResult)
async def start_experiment(
    experiment_id: str,
    payload: ExecuteExperimentRequest | None = None,
) -> ExperimentResult:
    """Runs safe or approved experiment, capturing empirical observations and running analysis."""
    service = get_discovery_service()
    mock_val = payload.mock_observation_value if payload else None
    try:
        return service.execute_safe_experiment(experiment_id, mock_observation_value=mock_val)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@experiments_router.post("/{experiment_id}/observation", response_model=ExperimentObservation)
async def record_observation(
    experiment_id: str,
    payload: RecordObservationRequest,
) -> ExperimentObservation:
    """Captures empirical measurement for an experiment."""
    service = get_discovery_service()
    try:
        return service.record_observation(
            experiment_id=experiment_id,
            source=payload.source,
            measurement_metric=payload.measurement_metric,
            value=payload.value,
            unit=payload.unit,
            environment=payload.environment,
            raw_reference=payload.raw_reference,
            verification_state=payload.verification_state,
            is_simulation=payload.is_simulation,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@experiments_router.post("/{experiment_id}/analyze", response_model=ExperimentResult)
async def analyze_experiment(
    experiment_id: str,
    payload: AnalyzeExperimentRequest,
) -> ExperimentResult:
    """Evaluates prediction vs empirical observations."""
    service = get_discovery_service()
    try:
        return service.analyze_experiment(
            experiment_id=experiment_id,
            controls_intact=payload.controls_intact,
            confounders_detected=payload.confounders_detected,
            environment_valid=payload.environment_valid,
            measurement_error=payload.measurement_error,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@experiments_router.post("/{experiment_id}/rollback")
async def rollback_experiment(experiment_id: str) -> dict[str, Any]:
    """Rolls back state changes from a mutable experiment."""
    service = get_discovery_service()
    try:
        return service.rollback_experiment(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@experiments_router.post("/{experiment_id}/cleanup")
async def cleanup_experiment(experiment_id: str) -> dict[str, Any]:
    """Cleans up ephemeral resources for an experiment."""
    service = get_discovery_service()
    try:
        return service.cleanup_experiment(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@experiments_router.post("/replicate")
async def replicate_experiment(payload: ReplicateExperimentRequest) -> dict[str, Any]:
    """Evaluates replication consistency between two experimental trials."""
    service = get_discovery_service()
    try:
        return service.replicate_experiment(
            original_experiment_id=payload.original_experiment_id,
            replication_experiment_id=payload.replication_experiment_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@experiments_router.get("/{experiment_id}/explanation")
async def get_experiment_explanation(experiment_id: str) -> dict[str, Any]:
    """Provides safe scientific rationale for why an experiment was selected."""
    service = get_discovery_service()
    try:
        return service.get_experiment_explanation(experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

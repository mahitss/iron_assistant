"""FastAPI REST API routes for Kairo Causal Reasoning and Causal Graph Engine (Task 55)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.causal.discovery_schemas import (
    CausalCandidateProposal,
    CausalDriftReport,
    CausalQualityMetrics,
    CausalQuestionResponse,
    CausalRelationship,
    CausalRelationshipState,
    InterventionRecord,
)
from app.causal.discovery_schemas import (
    CausalQuestionRequest as DiscoveryQuestionRequest,
)
from app.causal.discovery_service import discovery_service
from app.causal.safety import (
    CorrelationAsCausationError,
    ModelOutputAsEvidenceError,
    UnauthorizedInterventionError,
)
from app.causal.schemas import (
    CausalEdge,
    CausalEvidence,
    CausalExplanation,
    CausalGraph,
    CausalNode,
    CausalRelationshipType,
    CounterfactualScenario,
    FallacyDetectionResult,
    Intervention,
    InterventionType,
    RootCauseAnalysis,
)
from app.causal.service import causal_service

router = APIRouter(prefix="/api/v1/causal", tags=["causal"])


# Request models
class AddNodeRequest(BaseModel):
    entity: str
    variable: str
    state: Any
    source: str = "telemetry"
    confidence: float = 1.0
    graph_id: str = "system_default"


class AddEdgeRequest(BaseModel):
    cause: str
    effect: str
    relationship: CausalRelationshipType = CausalRelationshipType.CAUSES
    confidence: float = 0.5
    evidence: list[CausalEvidence] = Field(default_factory=list)
    graph_id: str = "system_default"


class AnalyzeIncidentRequest(BaseModel):
    incident_id: str
    symptom: str
    telemetry_metrics: dict[str, float] = Field(default_factory=dict)
    service_dependencies: dict[str, list[str]] = Field(default_factory=dict)


class CausalQuestionRequest(BaseModel):
    incident_id: str
    question: str


class ProposeInterventionRequest(BaseModel):
    target: str
    change: dict[str, Any]
    expected_effect: dict[str, Any]
    intervention_type: InterventionType = InterventionType.CONFIG_CHANGE
    risk: str = "MEDIUM"
    is_production: bool = False
    approved_by: str | None = None


class EvaluateInterventionRequest(BaseModel):
    actual_effect: dict[str, Any]
    hypothesis_id: str | None = None


class CounterfactualRequest(BaseModel):
    removed_cause: str
    baseline_state: dict[str, Any] = Field(default_factory=dict)


class DetectFallaciesRequest(BaseModel):
    cause: str
    effect: str
    evidence: list[CausalEvidence] = Field(default_factory=list)
    temporal_only: bool = False


# Routes
@router.get("/graph", response_model=CausalGraph)
def get_causal_graph(graph_id: str = Query("system_default")) -> CausalGraph:
    """Retrieve the causal graph."""
    return causal_service.get_graph(graph_id=graph_id)


@router.post("/nodes", response_model=CausalNode)
def add_causal_node(req: AddNodeRequest) -> CausalNode:
    """Add or update a node in the causal graph."""
    return causal_service.add_node(
        entity=req.entity,
        variable=req.variable,
        state=req.state,
        source=req.source,
        confidence=req.confidence,
        graph_id=req.graph_id,
    )


@router.post("/edges", response_model=CausalEdge)
def add_causal_edge(req: AddEdgeRequest) -> CausalEdge:
    """Add a causal edge with evidence validation."""
    try:
        return causal_service.add_edge(
            cause=req.cause,
            effect=req.effect,
            relationship=req.relationship,
            confidence=req.confidence,
            evidence=req.evidence,
            graph_id=req.graph_id,
        )
    except (CorrelationAsCausationError, ModelOutputAsEvidenceError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze", response_model=RootCauseAnalysis)
def analyze_root_cause(req: AnalyzeIncidentRequest) -> RootCauseAnalysis:
    """Perform root cause analysis on an incident."""
    return causal_service.analyze_root_cause(
        incident_id=req.incident_id,
        symptom=req.symptom,
        telemetry_metrics=req.telemetry_metrics,
        service_dependencies=req.service_dependencies,
    )


@router.get("/analysis/{incident_id}", response_model=RootCauseAnalysis)
def get_root_cause_analysis(incident_id: str) -> RootCauseAnalysis:
    """Retrieve an existing root cause analysis."""
    analysis = causal_service._analyses.get(incident_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis for incident '{incident_id}' not found.")
    return analysis


@router.get("/explanation/{incident_id}", response_model=CausalExplanation)
def get_causal_explanation(incident_id: str) -> CausalExplanation:
    """Retrieve a complete 6-part causal explanation."""
    return causal_service.explain_incident(incident_id=incident_id)


@router.post("/question")
def ask_causal_question(req: CausalQuestionRequest) -> dict[str, Any]:
    """Ask natural language causal questions."""
    return causal_service.ask_question(incident_id=req.incident_id, question=req.question)


@router.post("/interventions/propose", response_model=Intervention)
def propose_intervention(req: ProposeInterventionRequest) -> Intervention:
    """Propose an intervention to test a hypothesis."""
    try:
        return causal_service.propose_intervention(
            target=req.target,
            change=req.change,
            expected_effect=req.expected_effect,
            intervention_type=req.intervention_type,
            risk=req.risk,
            is_production=req.is_production,
            approved_by=req.approved_by,
        )
    except UnauthorizedInterventionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/interventions/{intervention_id}/evaluate")
def evaluate_intervention(intervention_id: str, req: EvaluateInterventionRequest) -> dict[str, Any]:
    """Evaluate outcome of an intervention."""
    try:
        intv, evidence, matched = causal_service.evaluate_intervention(
            intervention_id=intervention_id,
            actual_effect=req.actual_effect,
            hypothesis_id=req.hypothesis_id,
        )
        return {
            "intervention": intv.model_dump(),
            "evidence": evidence.model_dump(),
            "effect_matched": matched,
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/counterfactuals/evaluate", response_model=CounterfactualScenario)
def evaluate_counterfactual(req: CounterfactualRequest) -> CounterfactualScenario:
    """Evaluate what would have happened if X had not occurred."""
    return causal_service.evaluate_counterfactual(
        removed_cause=req.removed_cause,
        baseline_state=req.baseline_state,
    )


@router.post("/fallacies/detect", response_model=FallacyDetectionResult)
def detect_fallacies(req: DetectFallaciesRequest) -> FallacyDetectionResult:
    """Audit for cognitive and statistical fallacies."""
    return causal_service.detect_fallacies(
        cause=req.cause,
        effect=req.effect,
        evidence=req.evidence,
        temporal_only=req.temporal_only,
    )


@router.get("/blast-radius/{service_name}")
def get_blast_radius(service_name: str) -> dict[str, Any]:
    """Get topological blast radius distinguishing reachability from causality."""
    return causal_service.get_blast_radius(origin_service=service_name)


# ==========================================
# Task 73: Autonomous Causal Discovery Routes
# ==========================================


class InvalidateRelationshipRequest(BaseModel):
    reason: str
    actor: str = "SYSTEM"


class VerifyRelationshipRequest(BaseModel):
    verification_ref: str
    reason: str = "Empirical verification passed"
    actor: str = "SYSTEM"


class RecordInterventionRequest(BaseModel):
    target: str
    previous_state: dict[str, Any] = Field(default_factory=dict)
    new_state: dict[str, Any] = Field(default_factory=dict)
    experiment_id: str | None = None
    environment: str = "STAGING"
    operator: str = "SYSTEM"
    authorization: dict[str, Any] = Field(default_factory=dict)
    rollback_plan: dict[str, Any] = Field(default_factory=dict)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    outcome: dict[str, Any] = Field(default_factory=dict)


class EvaluateExperimentRequest(BaseModel):
    relation_id: str
    experiment_id: str
    intervention_target: str
    observed_delta: float
    is_controlled: bool = True
    verification_ref: str | None = None
    actor: str = "SYSTEM"


@router.get("/relationships", response_model=list[CausalRelationship])
def get_causal_relationships(
    status: CausalRelationshipState | None = None,
    environment: str | None = None,
    cause_entity: str | None = None,
    effect_entity: str | None = None,
) -> list[CausalRelationship]:
    """List discovered or hypothesized causal relationships with filters."""
    return discovery_service.get_relationships(
        status=status,
        environment=environment,
        cause_entity=cause_entity,
        effect_entity=effect_entity,
    )


@router.get("/relationships/{relation_id}", response_model=CausalRelationship)
def get_causal_relationship(relation_id: str) -> CausalRelationship:
    """Retrieve detailed metadata of a specific causal relationship."""
    try:
        return discovery_service.get_relationship(relation_id=relation_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/propose-candidate")
def propose_causal_candidate(req: CausalCandidateProposal) -> dict[str, Any]:
    """Ingest observational candidate correlation and run discovery pipeline."""
    rel, findings = discovery_service.propose_candidate(proposal=req)
    return {
        "relationship": rel.model_dump(),
        "findings": findings,
    }


@router.post("/hypotheses", response_model=CausalRelationship)
def register_causal_hypothesis(req: CausalRelationship) -> CausalRelationship:
    """Register an explicitly constructed causal hypothesis."""
    return discovery_service.register_hypothesis(relationship=req)


@router.get("/hypotheses", response_model=list[CausalRelationship])
def list_causal_hypotheses() -> list[CausalRelationship]:
    """List active causal hypotheses."""
    return discovery_service.get_relationships(status=CausalRelationshipState.HYPOTHESIZED)


@router.get("/relationships/{relation_id}/evidence")
def get_relationship_evidence(relation_id: str) -> dict[str, Any]:
    """Retrieve all linked evidence and experiment references for a relationship."""
    try:
        rel = discovery_service.get_relationship(relation_id=relation_id)
        return {
            "relation_id": rel.causal_relation_id,
            "evidence_refs": rel.evidence_refs,
            "experiment_refs": rel.experiment_refs,
            "verification_refs": rel.verification_refs,
            "contradiction_refs": rel.contradiction_refs,
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/relationships/{relation_id}/explanation")
def get_relationship_explanation(relation_id: str) -> dict[str, Any]:
    """Generate safe causal explanation without exposing private chain-of-thought (Spec 51)."""
    try:
        return discovery_service.get_explanation(relation_id=relation_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/relationships/{relation_id}/trace")
def get_relationship_trace(relation_id: str) -> dict[str, Any]:
    """Retrieve queryable causal trace: cause -> mechanism -> effect -> evidence -> experiment (Spec 52)."""
    try:
        return discovery_service.get_causal_trace(relation_id=relation_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/relationships/{relation_id}/provenance")
def get_relationship_provenance(relation_id: str) -> dict[str, Any]:
    """Retrieve full audit and lifecycle provenance for a relationship."""
    try:
        rel = discovery_service.get_relationship(relation_id=relation_id)
        return {
            "relation_id": rel.causal_relation_id,
            "model_version": rel.model_version,
            "created_at": rel.created_at.isoformat(),
            "updated_at": rel.updated_at.isoformat(),
            "provenance": rel.provenance,
            "change_reason": rel.change_reason,
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/relationships/{relation_id}/invalidate", response_model=CausalRelationship)
def invalidate_causal_relationship(relation_id: str, req: InvalidateRelationshipRequest) -> CausalRelationship:
    """Explicitly invalidate a causal relationship with reason."""
    try:
        return discovery_service.invalidate_relationship(relation_id=relation_id, reason=req.reason, actor=req.actor)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/relationships/{relation_id}/verify", response_model=CausalRelationship)
def verify_causal_relationship(relation_id: str, req: VerifyRelationshipRequest) -> CausalRelationship:
    """Verify a causal relationship with formal verification ref from Task 42."""
    try:
        return discovery_service.verify_relationship(
            relation_id=relation_id,
            verification_ref=req.verification_ref,
            reason=req.reason,
            actor=req.actor,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/conflicts")
def get_causal_conflicts() -> list[dict[str, Any]]:
    """Retrieve active competing causal models and agent dissents (Spec 44)."""
    return discovery_service.get_conflicts()


@router.get("/drift", response_model=list[CausalDriftReport])
def get_causal_drift() -> list[CausalDriftReport]:
    """Retrieve detected causal and world-model drift reports (Spec 47, 48)."""
    return discovery_service.get_drift_reports()


@router.get("/health", response_model=CausalQualityMetrics)
def get_causal_health() -> CausalQualityMetrics:
    """Retrieve engine telemetry and model quality metrics (Spec 50)."""
    return discovery_service.get_quality_metrics()


@router.post("/query", response_model=CausalQuestionResponse)
def query_causal_engine(req: DiscoveryQuestionRequest) -> CausalQuestionResponse:
    """Query the Causal Question Engine for one of the 8 core question types (Spec 34)."""
    return discovery_service.query_engine(request=req)


@router.post("/interventions", response_model=InterventionRecord)
def record_intervention(req: RecordInterventionRequest) -> InterventionRecord:
    """Record an empirical DO(X = v) intervention (Spec 7, 8)."""
    return discovery_service.record_intervention(
        target=req.target,
        previous_state=req.previous_state,
        new_state=req.new_state,
        experiment_id=req.experiment_id,
        environment=req.environment,
        operator=req.operator,
        authorization=req.authorization,
        rollback_plan=req.rollback_plan,
        observations=req.observations,
        outcome=req.outcome,
    )


@router.get("/interventions", response_model=list[InterventionRecord])
def list_interventions() -> list[InterventionRecord]:
    """List recorded empirical interventions."""
    return list(discovery_service._interventions.values())


@router.post("/experiments/evaluate")
def evaluate_discovery_experiment(req: EvaluateExperimentRequest) -> dict[str, Any]:
    """Evaluate experiment outcome from Task 72 and advance causal lifecycle."""
    try:
        rel, msg = discovery_service.evaluate_experiment_outcome(
            relation_id=req.relation_id,
            experiment_id=req.experiment_id,
            intervention_target=req.intervention_target,
            observed_delta=req.observed_delta,
            is_controlled=req.is_controlled,
            verification_ref=req.verification_ref,
            actor=req.actor,
        )
        return {
            "relationship": rel.model_dump(),
            "message": msg,
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/experiments/discriminative")
def get_discriminative_experiments() -> list[dict[str, Any]]:
    """Retrieve synthesized discriminative experiments to resolve competing hypotheses (Spec 32, 55)."""
    return discovery_service.generate_discriminative_experiments()


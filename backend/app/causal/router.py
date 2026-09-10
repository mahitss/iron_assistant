"""FastAPI REST API routes for Kairo Causal Reasoning and Causal Graph Engine (Task 55)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

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

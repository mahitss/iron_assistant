"""FastAPI REST API router for Kairo Autonomous Risk Propagation & Cascade Engine (Task 75)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.propagation.schemas import (
    BottleneckNode,
    CascadeChain,
    CascadeEvaluation,
    ImpactDimensions,
    PropagationAnalysis,
    PropagationEdge,
    PropagationScope,
    ResilienceAssessment,
    SinglePointOfFailure,
    TriggerType,
)
from app.propagation.service import default_propagation_service

router = APIRouter(prefix="", tags=["Risk Propagation & Cascade Analysis"])


class AnalyzePropagationRequest(BaseModel):
    origin_entity: str = Field(..., description="Root component or event triggering the propagation")
    trigger: str = Field(..., description="Description of the trigger event or state change")
    trigger_type: TriggerType = Field(default=TriggerType.STATE_CHANGE)
    scope: PropagationScope = Field(default=PropagationScope.SERVICE)
    tenant_id: str = Field(default="default_tenant")
    snapshot_id: Optional[str] = None
    custom_edges: Optional[List[PropagationEdge]] = None
    custom_entities: Optional[Dict[str, Dict[str, Any]]] = None
    initial_impact: Optional[ImpactDimensions] = None
    initial_confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    regime_factor: float = Field(default=1.0, ge=0.1, le=5.0)


class EvaluateOutcomeRequest(BaseModel):
    actual_degraded_nodes: List[str] = Field(default_factory=list)
    actual_event_timestamps: Optional[Dict[str, datetime]] = None
    actual_impact_severities: Optional[Dict[str, float]] = None


# =====================================================================
# ENDPOINTS (Spec 63)
# =====================================================================

@router.post("/propagation/analyze", response_model=PropagationAnalysis, status_code=status.HTTP_201_CREATED)
async def analyze_propagation(request: AnalyzePropagationRequest) -> PropagationAnalysis:
    """Analyze systemic downstream risk propagation from an origin trigger (Spec 63)."""
    return default_propagation_service.analyze_propagation(
        origin_entity=request.origin_entity,
        trigger=request.trigger,
        trigger_type=request.trigger_type,
        scope=request.scope,
        tenant_id=request.tenant_id,
        snapshot_id=request.snapshot_id,
        custom_edges=request.custom_edges,
        custom_entities=request.custom_entities,
        initial_impact=request.initial_impact,
        initial_confidence=request.initial_confidence,
        regime_factor=request.regime_factor,
    )


@router.get("/propagation/active", response_model=List[CascadeChain])
async def list_active_cascades(
    tenant_id: str = Query("default_tenant"),
) -> List[CascadeChain]:
    """Retrieve all actively projected cascades (Spec 63)."""
    return default_propagation_service.list_active_cascades(tenant_id=tenant_id)


@router.get("/propagation/cascades", response_model=List[CascadeChain])
async def list_cascades(
    tenant_id: str = Query("default_tenant"),
) -> List[CascadeChain]:
    """Alias for listing active cascades (Spec 63)."""
    return default_propagation_service.list_active_cascades(tenant_id=tenant_id)


@router.get("/propagation/bottlenecks", response_model=List[BottleneckNode])
async def list_bottlenecks(
    tenant_id: str = Query("default_tenant"),
) -> List[BottleneckNode]:
    """List disproportionately important bottleneck nodes across recent analyses (Spec 13, 63)."""
    all_bottlenecks: Dict[str, BottleneckNode] = {}
    for analysis in default_propagation_service._analyses.values():
        if analysis.tenant_id == tenant_id:
            for b in analysis.bottlenecks:
                all_bottlenecks[b.entity_id] = b
    return list(all_bottlenecks.values())


@router.get("/propagation/single-points-of-failure", response_model=List[SinglePointOfFailure])
async def list_single_points_of_failure(
    tenant_id: str = Query("default_tenant"),
) -> List[SinglePointOfFailure]:
    """List detected single points of failure across system structure (Spec 14, 63)."""
    all_spofs: Dict[str, SinglePointOfFailure] = {}
    for analysis in default_propagation_service._analyses.values():
        if analysis.tenant_id == tenant_id:
            for s in analysis.single_points_of_failure:
                all_spofs[s.entity_id] = s
    return list(all_spofs.values())


@router.get("/propagation/resilience", response_model=Dict[str, Any])
async def get_systemic_resilience(
    tenant_id: str = Query("default_tenant"),
) -> Dict[str, Any]:
    """Get overall systemic resilience findings across known topologies (Spec 16, 63)."""
    recent_analyses = [a for a in default_propagation_service._analyses.values() if a.tenant_id == tenant_id]
    if not recent_analyses:
        return {
            "tenant_id": tenant_id,
            "status": "NO_ANALYSES_RECORDED",
            "mean_resilience_score": 0.5,
            "total_analyses": 0,
        }

    mean_res = sum(a.resilience_assessment.systemic_resilience_score for a in recent_analyses) / len(recent_analyses)
    return {
        "tenant_id": tenant_id,
        "mean_resilience_score": round(mean_res, 3),
        "total_analyses_evaluated": len(recent_analyses),
        "most_recent_assessment": recent_analyses[-1].resilience_assessment,
    }


@router.get("/propagation/{propagation_id}", response_model=PropagationAnalysis)
async def get_propagation_analysis(propagation_id: str) -> PropagationAnalysis:
    """Retrieve a specific propagation analysis by ID (Spec 63)."""
    analysis = default_propagation_service.get_analysis(propagation_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{propagation_id}' not found.")
    return analysis


@router.get("/propagation/{propagation_id}/graph", response_model=Dict[str, Any])
async def get_propagation_graph(propagation_id: str) -> Dict[str, Any]:
    """Retrieve the visual topological graph for a propagation analysis (Spec 63, 66)."""
    analysis = default_propagation_service.get_analysis(propagation_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{propagation_id}' not found.")

    nodes = []
    nodes.append({"id": analysis.origin_entity, "label": analysis.origin_entity, "role": "TRIGGER", "depth": 0})
    for d in analysis.direct_effects:
        nodes.append({"id": d.target_entity, "label": d.target_entity, "role": "DIRECT_EFFECT", "depth": 1, "confidence": d.confidence})
    for s in analysis.second_order_effects:
        nodes.append({"id": s.target_entity, "label": s.target_entity, "role": "SECOND_ORDER", "depth": 2, "confidence": s.confidence})

    edges = []
    for c in analysis.cascades:
        for e in c.edges:
            edges.append(e)

    return {
        "propagation_id": propagation_id,
        "origin_entity": analysis.origin_entity,
        "nodes": nodes,
        "edges": edges,
        "propagation_depth": analysis.propagation_depth,
        "is_truncated": analysis.is_truncated,
    }


@router.get("/propagation/{propagation_id}/explanation", response_model=Dict[str, Any])
async def get_propagation_explanation(propagation_id: str) -> Dict[str, Any]:
    """Retrieve structured, explainable steps of the propagation path (Spec 54, 63)."""
    explanation = default_propagation_service.get_explanation(propagation_id)
    if not explanation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{propagation_id}' not found.")
    return explanation


@router.get("/propagation/{propagation_id}/provenance", response_model=Dict[str, Any])
async def get_propagation_provenance(propagation_id: str) -> Dict[str, Any]:
    """Retrieve data lineage and snapshot sources for the propagation run (Spec 55, 63)."""
    analysis = default_propagation_service.get_analysis(propagation_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{propagation_id}' not found.")

    return {
        "propagation_id": propagation_id,
        "graph_snapshot": analysis.graph_snapshot,
        "provenance": analysis.provenance,
        "assumptions": analysis.assumptions,
        "uncertainty_breakdown": analysis.uncertainty,
    }


@router.get("/propagation/{propagation_id}/scenarios", response_model=Dict[str, Any])
async def get_propagation_scenarios(
    propagation_id: str,
    intervention_type: str = Query("ADD_REDUNDANCY", description="Intervention: ADD_REDUNDANCY or REMOVE_DEPENDENCY"),
    target_entity: Optional[str] = Query(None, description="Entity to apply intervention to"),
) -> Dict[str, Any]:
    """Run and compare counterfactual intervention scenarios (Spec 32, 63)."""
    analysis = default_propagation_service.get_analysis(propagation_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{propagation_id}' not found.")

    target = target_entity or (analysis.direct_effects[0].target_entity if analysis.direct_effects else analysis.origin_entity)
    snapshot = default_propagation_service.snapshot_engine.get_snapshot(analysis.graph_snapshot.snapshot_id)

    if not snapshot:
        # Fallback to reconstructing snapshot from analysis edges
        edges: List[PropagationEdge] = []
        for d in analysis.direct_effects:
            edges.append(
                PropagationEdge(
                    source_entity=analysis.origin_entity,
                    target_entity=d.target_entity,
                    relationship_type=d.relationship_type,
                    confidence=d.confidence,
                )
            )
        snapshot = default_propagation_service.snapshot_engine.create_snapshot(
            tenant_id=analysis.tenant_id,
            edges=edges,
        )

    sim_res = default_propagation_service.resilience_engine.simulate_counterfactual(
        origin_entity=analysis.origin_entity,
        snapshot=snapshot,
        intervention_type=intervention_type,
        target_entity=target,
    )

    return {
        "propagation_id": propagation_id,
        "origin_entity": analysis.origin_entity,
        "counterfactual_result": sim_res,
    }


@router.post("/propagation/{propagation_id}/outcome", response_model=CascadeEvaluation)
async def evaluate_propagation_outcome(
    propagation_id: str,
    outcome: EvaluateOutcomeRequest,
) -> CascadeEvaluation:
    """Evaluate predicted cascade against actual realized outcomes (Spec 59, 60, 63)."""
    from app.propagation.evaluation import default_cascade_evaluator

    analysis = default_propagation_service.get_analysis(propagation_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis '{propagation_id}' not found.")

    return default_cascade_evaluator.evaluate(
        analysis=analysis,
        actual_degraded_nodes=outcome.actual_degraded_nodes,
        actual_event_timestamps=outcome.actual_event_timestamps,
        actual_impact_severities=outcome.actual_impact_severities,
    )

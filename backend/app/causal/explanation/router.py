"""FastAPI REST router for Task 112:
KAIRO Autonomous Causal Explanation, Event Chain Reconstruction & "Why Did This Happen?" Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.causal.explanation.domain import (
    CausalAlternative,
    CausalExplanation,
    CausalLink,
    CounterfactualScenario,
    EventChain,
    ExplanationGap,
    ExplanationRequest,
    ExplanationVerification,
)
from app.causal.explanation.schemas import (
    CreateExplanationRequest,
    ExplanationFeedbackRequest,
    ExplanationSummaryResponse,
    VerifyExplanationRequest,
)
from app.causal.explanation.service import CausalExplanationService

router = APIRouter(prefix="/explanations", tags=["causal_explanations"])


@router.post("", response_model=CausalExplanation)
def create_explanation(req: CreateExplanationRequest) -> CausalExplanation:
    """Generate an evidence-backed causal explanation for a target entity or incident."""
    svc = CausalExplanationService.get_instance()
    domain_req = ExplanationRequest(
        target_entity=req.target_entity,
        target_event_id=req.target_event_id,
        target_state_change=req.target_state_change,
        target_incident_id=req.target_incident_id,
        user_query=req.user_query,
        time_window_start=req.time_window_start,
        time_window_end=req.time_window_end,
        max_chain_depth=req.max_chain_depth,
        min_confidence_threshold=req.min_confidence_threshold,
        scope=req.scope,
    )
    return svc.generate_explanation(domain_req)


@router.get("", response_model=List[ExplanationSummaryResponse])
def list_explanations(limit: int = Query(20, ge=1, le=100)) -> List[ExplanationSummaryResponse]:
    """List recent causal explanations."""
    svc = CausalExplanationService.get_instance()
    expls = svc.list_explanations(limit=limit)
    return [
        ExplanationSummaryResponse(
            explanation_id=e.explanation_id,
            target_entity=e.target_entity,
            lifecycle_stage=e.lifecycle_stage.value,
            primary_cause=e.primary_cause,
            root_cause_category=e.root_cause_category.value,
            composite_confidence=e.confidence.composite_confidence,
            is_verified=e.is_verified,
            is_cause_unknown=e.is_cause_unknown,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in expls
    ]


@router.get("/{explanation_id}", response_model=CausalExplanation)
def get_explanation(explanation_id: str) -> CausalExplanation:
    """Retrieve complete causal explanation by ID."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    return expl


@router.get("/{explanation_id}/timeline")
def get_explanation_timeline(explanation_id: str) -> Dict[str, Any]:
    """Retrieve the chronological event chain timeline."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    return expl.event_chain.model_dump() if expl.event_chain else {"steps": []}


@router.get("/{explanation_id}/chain", response_model=List[CausalLink])
def get_explanation_chain(explanation_id: str) -> List[CausalLink]:
    """Retrieve causal links and mechanistic steps."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    return expl.causal_links


@router.get("/{explanation_id}/hypotheses")
def get_explanation_hypotheses(explanation_id: str) -> Dict[str, Any]:
    """Retrieve primary and alternative hypotheses."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    return {
        "primary_cause": expl.primary_cause,
        "primary_mechanism": expl.primary_mechanism,
        "category": expl.root_cause_category.value,
        "alternatives": [alt.model_dump() for alt in expl.alternatives],
    }


@router.get("/{explanation_id}/evidence")
def get_explanation_evidence(explanation_id: str) -> List[Dict[str, Any]]:
    """Retrieve supporting and contradicting evidence."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    evidence = []
    for link in expl.causal_links:
        evidence.extend([ev.model_dump() for ev in link.supporting_evidence])
        evidence.extend([ev.model_dump() for ev in link.contradicting_evidence])
    return evidence


@router.get("/{explanation_id}/alternatives", response_model=List[CausalAlternative])
def get_explanation_alternatives(explanation_id: str) -> List[CausalAlternative]:
    """Retrieve competing alternative causal explanations."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    return expl.alternatives


@router.get("/{explanation_id}/counterfactuals", response_model=List[CounterfactualScenario])
def get_explanation_counterfactuals(explanation_id: str) -> List[CounterfactualScenario]:
    """Retrieve counterfactual what-if scenarios (explicitly marked is_hypothetical=True)."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    return expl.counterfactuals


@router.get("/{explanation_id}/gaps", response_model=List[ExplanationGap])
def get_explanation_gaps(explanation_id: str) -> List[ExplanationGap]:
    """Retrieve unresolved causal gaps and telemetry uncertainties."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    return expl.unresolved_gaps


@router.get("/{explanation_id}/snapshot")
def get_explanation_snapshot(explanation_id: str) -> Dict[str, Any]:
    """Retrieve immutable point-in-time explanation snapshot."""
    svc = CausalExplanationService.get_instance()
    expl = svc.get_explanation(explanation_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explanation '{explanation_id}' not found.")
    return {
        "snapshot_id": f"snap_{expl.explanation_id}_v{expl.version}",
        "captured_at": expl.updated_at.isoformat(),
        "explanation": expl.model_dump(),
    }


@router.get("/{explanation_id}/verification", response_model=List[ExplanationVerification])
def get_explanation_verifications(explanation_id: str) -> List[ExplanationVerification]:
    """Retrieve follow-up empirical verification history."""
    svc = CausalExplanationService.get_instance()
    return svc.get_verifications(explanation_id)


@router.post("/{explanation_id}/verify", response_model=CausalExplanation)
def verify_explanation(explanation_id: str, req: VerifyExplanationRequest) -> CausalExplanation:
    """Record follow-up empirical verification result."""
    svc = CausalExplanationService.get_instance()
    try:
        return svc.verify_explanation(
            explanation_id=explanation_id,
            actual_observation=req.actual_observation,
            predicted_consequence=req.predicted_consequence,
            actor=req.actor,
            notes=req.notes,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{explanation_id}/feedback")
def record_explanation_feedback(explanation_id: str, req: ExplanationFeedbackRequest) -> Dict[str, Any]:
    """Record user or operator feedback."""
    svc = CausalExplanationService.get_instance()
    return svc.record_feedback(
        explanation_id=explanation_id,
        actor=req.actor,
        feedback_text=req.feedback_text,
        is_accurate=req.is_accurate,
        suggested_alternative=req.suggested_alternative,
    )


@router.post("/{explanation_id}/refresh", response_model=CausalExplanation)
def refresh_explanation(explanation_id: str) -> CausalExplanation:
    """Re-evaluate explanation with current telemetry, superseding prior version."""
    svc = CausalExplanationService.get_instance()
    try:
        return svc.refresh_explanation(explanation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

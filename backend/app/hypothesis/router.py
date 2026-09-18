"""FastAPI Router for Task 115:
Autonomous Hypothesis Management, Competing Explanations, Evidence Update, Falsification & Uncertainty Resolution Engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.hypothesis.domain import (
    HypothesisScope,
)
from app.hypothesis.schemas import (
    AttachEvidenceRequest,
    CreateHypothesisRequest,
    CreateHypothesisSetRequest,
    HypothesisFeedbackRequest,
    MergeHypothesesRequest,
    SplitHypothesisRequest,
)
from app.hypothesis.service import get_hypothesis_service

router = APIRouter(prefix="/api", tags=["Hypothesis Engine"])


# --- Hypothesis Sets ---

@router.post("/hypothesis-sets", status_code=status.HTTP_201_CREATED)
def create_hypothesis_set(req: CreateHypothesisSetRequest) -> Dict[str, Any]:
    """Initializes a new competing hypothesis set with candidate explanations and UNKNOWN."""
    svc = get_hypothesis_service()
    scope = None
    if req.scope:
        scope = HypothesisScope(
            entity_ids=req.scope.entity_ids,
            subsystems=req.scope.subsystems,
            time_window_start=req.scope.time_window_start,
            time_window_end=req.scope.time_window_end,
            environment=req.scope.environment,
            context_keys=req.scope.context_keys,
        )
    hset = svc.create_hypothesis_set(
        target_description=req.target_description,
        scope=scope,
        target_incident_id=req.target_incident_id,
        candidate_explanations=req.candidate_explanations,
    )
    return hset.to_dict()


@router.get("/hypothesis-sets")
def list_hypothesis_sets() -> List[Dict[str, Any]]:
    """Lists all active and historical hypothesis sets."""
    svc = get_hypothesis_service()
    return [s.to_dict() for s in svc.list_hypothesis_sets()]


@router.get("/hypothesis-sets/{set_id}")
def get_hypothesis_set(set_id: str) -> Dict[str, Any]:
    """Retrieves hypothesis set metadata, active candidate IDs, and information gaps."""
    svc = get_hypothesis_service()
    hset = svc.get_hypothesis_set(set_id)
    if not hset:
        raise HTTPException(status_code=404, detail=f"HypothesisSet '{set_id}' not found.")
    return hset.to_dict()


@router.get("/hypothesis-sets/{set_id}/compare")
def compare_hypothesis_set(set_id: str) -> Dict[str, Any]:
    """Returns the side-by-side comparison matrix for competing explanations."""
    svc = get_hypothesis_service()
    try:
        return svc.get_side_by_side_comparison(set_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/hypothesis-sets/{set_id}/discriminators")
def get_set_discriminators(set_id: str) -> List[Dict[str, Any]]:
    """Retrieves discriminating observations capable of resolving uncertainty in this set."""
    svc = get_hypothesis_service()
    hset = svc.get_hypothesis_set(set_id)
    if not hset:
        raise HTTPException(status_code=404, detail=f"HypothesisSet '{set_id}' not found.")
    return [d.to_dict() for d in hset.discriminators]


@router.get("/hypothesis-sets/{set_id}/uncertainty")
def get_set_uncertainty_profile(set_id: str) -> Dict[str, Any]:
    """Exposes uncertainty resolution state, information gaps, and unresolved conflicts."""
    svc = get_hypothesis_service()
    hset = svc.get_hypothesis_set(set_id)
    if not hset:
        raise HTTPException(status_code=404, detail=f"HypothesisSet '{set_id}' not found.")
    hyps = svc.list_hypotheses(set_id)
    active = [h for h in hyps if h.hypothesis_id in hset.active_hypothesis_ids]

    avg_uncertainty = sum(h.confidence_profile.uncertainty for h in active) / max(1, len(active))
    return {
        "set_id": set_id,
        "is_resolved": hset.is_resolved,
        "resolution_summary": hset.resolution_summary,
        "average_uncertainty": round(avg_uncertainty, 3),
        "information_gaps": hset.information_gaps,
        "unresolved_conflicts": [c.to_dict() for c in hset.unresolved_conflicts],
        "active_candidates_count": len(active),
    }


@router.post("/hypothesis-sets/{set_id}/evidence", status_code=status.HTTP_201_CREATED)
def attach_evidence_to_set(set_id: str, req: AttachEvidenceRequest) -> Dict[str, Any]:
    """Ingests evidence, checks independence lineage, evaluates against all competing hypotheses, and updates state."""
    svc = get_hypothesis_service()
    try:
        ev = svc.attach_evidence_to_set(set_id, req.model_dump())
        return ev.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))


@router.post("/hypothesis-sets/{set_id}/split")
def split_hypothesis(set_id: str, req: SplitHypothesisRequest) -> List[Dict[str, Any]]:
    """Splits a broad hypothesis into specialized child hypotheses."""
    svc = get_hypothesis_service()
    try:
        children = svc.split_hypothesis(set_id, req.parent_hypothesis_id, req.child_specs)
        return [c.to_dict() for c in children]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/hypothesis-sets/{set_id}/merge")
def merge_hypotheses(set_id: str, req: MergeHypothesesRequest) -> Dict[str, Any]:
    """Merges equivalent hypotheses into a consolidated explanation."""
    svc = get_hypothesis_service()
    try:
        merged = svc.merge_hypotheses(set_id, req.source_hypothesis_ids, req.consolidated_statement)
        return merged.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Individual Hypotheses ---

@router.post("/hypotheses", status_code=status.HTTP_201_CREATED)
def create_hypothesis(req: CreateHypothesisRequest) -> Dict[str, Any]:
    """Adds a new candidate explanation into an existing set."""
    svc = get_hypothesis_service()
    try:
        hyp = svc.add_hypothesis_to_set(req.set_id, req.model_dump())
        return hyp.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/hypotheses")
def list_hypotheses(set_id: Optional[str] = Query(None, description="Optional filter by hypothesis set ID")) -> List[Dict[str, Any]]:
    """Lists candidate hypotheses."""
    svc = get_hypothesis_service()
    return [h.to_dict() for h in svc.list_hypotheses(set_id)]


@router.get("/hypotheses/{hypothesis_id}")
def get_hypothesis(hypothesis_id: str) -> Dict[str, Any]:
    """Gets detailed hypothesis record."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    return hyp.to_dict()


@router.get("/hypotheses/{hypothesis_id}/versions")
def get_hypothesis_versions(hypothesis_id: str) -> List[Dict[str, Any]]:
    """Returns version history of hypothesis."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    return [{"version": hyp.version, "updated_at": hyp.updated_at.isoformat(), "status": hyp.status.value}]


@router.get("/hypotheses/{hypothesis_id}/evidence")
def get_hypothesis_evidence(hypothesis_id: str) -> Dict[str, Any]:
    """Returns supporting, contradicting, and falsifying evidence for a hypothesis."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    return {
        "hypothesis_id": hypothesis_id,
        "supporting_evidence_ids": hyp.supporting_evidence_ids,
        "contradicting_evidence_ids": hyp.contradicting_evidence_ids,
        "falsifying_evidence_ids": hyp.falsifying_evidence_ids,
        "assessments": [a.to_dict() for a in hyp.assessments],
    }


@router.get("/hypotheses/{hypothesis_id}/predictions")
def get_hypothesis_predictions(hypothesis_id: str) -> List[Dict[str, Any]]:
    """Returns testable predictions and calibration outcomes."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    return [p.to_dict() for p in hyp.predictions]


@router.get("/hypotheses/{hypothesis_id}/falsification")
def get_hypothesis_falsification(hypothesis_id: str) -> List[Dict[str, Any]]:
    """Returns explicit, testable falsification conditions."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    return [f.to_dict() for f in hyp.falsification_conditions]


@router.get("/hypotheses/{hypothesis_id}/alternatives")
def get_hypothesis_alternatives(hypothesis_id: str) -> List[Dict[str, Any]]:
    """Returns competing alternative hypotheses for the same incident target."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    all_hyps = svc.list_hypotheses(hyp.set_id)
    alternatives = [h.to_dict() for h in all_hyps if h.hypothesis_id != hypothesis_id]
    return alternatives


@router.get("/hypotheses/{hypothesis_id}/conflicts")
def get_hypothesis_conflicts(hypothesis_id: str) -> List[Dict[str, Any]]:
    """Returns conflicts involving this hypothesis."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    hset = svc.get_hypothesis_set(hyp.set_id)
    if not hset:
        return []
    conflicts = [
        c.to_dict() for c in hset.unresolved_conflicts
        if c.hypothesis_a_id == hypothesis_id or c.hypothesis_b_id == hypothesis_id
    ]
    return conflicts


@router.get("/hypotheses/{hypothesis_id}/history")
def get_hypothesis_history(hypothesis_id: str) -> List[Dict[str, Any]]:
    """Returns audit history and state transitions."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    events = [e.to_dict() for e in svc._events if e.hypothesis_id == hypothesis_id]
    return events


@router.get("/hypotheses/{hypothesis_id}/snapshot")
def get_hypothesis_snapshot(hypothesis_id: str) -> Dict[str, Any]:
    """Captures and returns an immediate snapshot of the hypothesis and its set."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    snap = svc.create_snapshot(hyp.set_id, summary=f"Snapshot requested for hypothesis {hypothesis_id}")
    return snap.to_dict()


@router.post("/hypotheses/{hypothesis_id}/evaluate")
def evaluate_hypothesis_endpoint(hypothesis_id: str) -> Dict[str, Any]:
    """Forces re-evaluation of confidence dimensions and bias guards."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    hset = svc.get_hypothesis_set(hyp.set_id)
    if hset:
        svc.bias_guard_engine.check_and_apply_safeguards(
            hyp, hset, svc.list_hypotheses(hyp.set_id), list(svc._evidence.values())
        )
    return hyp.to_dict()


@router.post("/hypotheses/{hypothesis_id}/verify")
def verify_hypothesis_endpoint(hypothesis_id: str) -> Dict[str, Any]:
    """Evaluates whether hypothesis satisfies all verification invariants."""
    svc = get_hypothesis_service()
    try:
        return svc.verify_hypothesis(hypothesis_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))


@router.post("/hypotheses/{hypothesis_id}/feedback")
def submit_hypothesis_feedback(hypothesis_id: str, req: HypothesisFeedbackRequest) -> Dict[str, Any]:
    """Records reviewer or operator feedback."""
    svc = get_hypothesis_service()
    hyp = svc.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{hypothesis_id}' not found.")
    svc.record_feedback(hypothesis_id, req.model_dump())
    return {"status": "FEEDBACK_RECORDED", "hypothesis_id": hypothesis_id}

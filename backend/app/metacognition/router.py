"""FastAPI router for Kairo Self-Modeling & Metacognition Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.metacognition.schemas import (
    CapabilityState,
    LimitationCategory,
    LimitationSeverity,
)
from app.metacognition.service import MetacognitionService

router = APIRouter(prefix="/metacognition", tags=["metacognition"])

_service: Optional[MetacognitionService] = None


def get_metacognition_service() -> MetacognitionService:
    global _service
    if _service is None:
        _service = MetacognitionService()
    return _service


class CheckReadinessRequest(BaseModel):
    action_name: str
    required_capabilities: List[str] = []
    user_id: str = "default_user"
    required_permission: Optional[str] = None
    policy_rule: Optional[str] = None
    requires_approval: bool = False
    is_approved: bool = False
    preconditions: Dict[str, bool] = {}


class RegisterLimitationRequest(BaseModel):
    category: LimitationCategory
    description: str
    scope: str = "GLOBAL"
    severity: LimitationSeverity = LimitationSeverity.MEDIUM
    source: str = "SYSTEM"
    mitigation_suggestion: Optional[str] = None


class IntrospectRequest(BaseModel):
    question_type: str  # WHAT_CAN_YOU_DO, WHY_CANT_YOU, HOW_SURE, DID_YOU_DO_IT, WHAT_WENT_WRONG
    subject_or_action: Optional[str] = None


class RecordReflectionRequest(BaseModel):
    goal: str
    attempted: str
    worked: List[str] = []
    failed: List[str] = []
    verified: List[str] = []
    remaining_uncertainties: List[str] = []
    lessons: List[str] = []
    corrections_applied: List[str] = []


class ReconcileRequest(BaseModel):
    registered_tools: List[str] = []


@router.get("/health")
def metacognition_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "kairo_self_modeling_metacognition_engine",
        "is_operational_metadata_only": True,
    }


@router.get("/self-model")
def get_self_model(
    user_id: str = Query("default_user"),
    service: MetacognitionService = Depends(get_metacognition_service),
) -> Dict[str, Any]:
    return service.get_self_model(user_id=user_id).model_dump()


@router.get("/self-model/projection")
def get_user_facing_projection(
    user_id: str = Query("default_user"),
    service: MetacognitionService = Depends(get_metacognition_service),
) -> Dict[str, Any]:
    return service.get_user_facing_projection(user_id=user_id)


@router.get("/capabilities")
def list_capabilities(
    state: Optional[CapabilityState] = Query(None),
    service: MetacognitionService = Depends(get_metacognition_service),
) -> List[Dict[str, Any]]:
    caps = service.capabilities.list_capabilities(state=state)
    return [c.model_dump() for c in caps]


@router.get("/limitations")
def list_limitations(
    category: Optional[LimitationCategory] = Query(None),
    service: MetacognitionService = Depends(get_metacognition_service),
) -> List[Dict[str, Any]]:
    limits = service.limitations.list_active_limitations(category=category)
    return [l.model_dump() for l in limits]


@router.post("/limitations")
def register_limitation(
    req: RegisterLimitationRequest,
    service: MetacognitionService = Depends(get_metacognition_service),
) -> Dict[str, Any]:
    lim = service.limitations.register_limitation(
        category=req.category,
        description=req.description,
        scope=req.scope,
        severity=req.severity,
        source=req.source,
        mitigation_suggestion=req.mitigation_suggestion,
    )
    return lim.model_dump()


@router.post("/readiness")
def check_readiness(
    req: CheckReadinessRequest,
    service: MetacognitionService = Depends(get_metacognition_service),
) -> Dict[str, Any]:
    readiness = service.check_action_readiness(
        action_name=req.action_name,
        required_capabilities=req.required_capabilities,
        user_id=req.user_id,
        required_permission=req.required_permission,
        policy_rule=req.policy_rule,
        requires_approval=req.requires_approval,
        is_approved=req.is_approved,
        preconditions=req.preconditions,
    )
    return readiness.model_dump()


@router.post("/introspect")
def introspect(
    req: IntrospectRequest,
    service: MetacognitionService = Depends(get_metacognition_service),
) -> Dict[str, Any]:
    try:
        res = service.introspect(req.question_type, req.subject_or_action)
        return res.model_dump()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/reflection")
def record_reflection(
    req: RecordReflectionRequest,
    service: MetacognitionService = Depends(get_metacognition_service),
) -> Dict[str, Any]:
    rec = service.reflection.conduct_reflection(
        goal=req.goal,
        attempted=req.attempted,
        worked=req.worked,
        failed=req.failed,
        verified=req.verified,
        remaining_uncertainties=req.remaining_uncertainties,
        lessons=req.lessons,
        corrections_applied=req.corrections_applied,
    )
    return rec.model_dump()


@router.get("/metrics")
def get_metrics(
    service: MetacognitionService = Depends(get_metacognition_service),
) -> Dict[str, Any]:
    return service.evaluator.get_dimensional_report()


@router.post("/reconcile")
def reconcile(
    req: ReconcileRequest,
    service: MetacognitionService = Depends(get_metacognition_service),
) -> Dict[str, Any]:
    return service.reconcile(req.registered_tools)

"""FastAPI REST router for Kairo Autonomous Attention & Cognitive Resource Engine (Task 70)."""

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.attention.domain import (
    AttentionCandidate as AttentionCandidateT109,
    AttentionCandidateType,
    AttentionEvidence,
    AttentionFeedback,
    AttentionLifecycleState,
    AttentionScore as AttentionScoreT109,
    AttentionSnapshot as AttentionSnapshotT109,
    AttentionWatch,
    FocusSession,
    FocusSwitchReason,
    FocusTarget,
    InterruptionDecision,
    WaitingConditionType,
    gen_attn_id,
)
from app.attention.schemas import (
    AttentionCandidate,
    AttentionCandidateCreate,
    AttentionHealthMetrics,
    AttentionSnapshot,
)
from app.attention.service import AttentionEngineService

router = APIRouter(prefix="/attention", tags=["Autonomous Attention Engine"])


def get_service() -> AttentionEngineService:
    return AttentionEngineService.get_instance()


def get_tenant_id(x_tenant_id: Annotated[str | None, Header()] = None) -> str:
    if not x_tenant_id or not x_tenant_id.strip():
        return "default"

    return x_tenant_id.strip()


class ActionReasonRequest(BaseModel):
    reason: str = ""


class DelegateRequest(BaseModel):
    target_agent_id: str
    reason: str = ""
    scope: str = "full_investigation"


class ScoreAdjustRequest(BaseModel):
    delta: float = Field(default=0.15, ge=0.01, le=1.0)
    reason: str = ""


@router.post("/evaluate", response_model=AttentionCandidate, status_code=status.HTTP_201_CREATED)
async def evaluate_candidate(
    payload: AttentionCandidateCreate,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Evaluate signals/tasks into an explainable, scored attention candidate."""
    payload.tenant_id = tenant_id or payload.tenant_id
    service = get_service()
    return service.evaluate_candidate(payload)


@router.get("/current", response_model=AttentionCandidate | None)
async def get_current_focus(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate | None:
    """Retrieve the candidate currently in active ATTENDING focus."""
    service = get_service()
    return service.get_current_focus(tenant_id)


@router.get("/queue", response_model=list[AttentionCandidate])
async def get_attention_queue(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> list[AttentionCandidate]:
    """Retrieve active prioritized queue of attention items."""
    service = get_service()
    return service.get_queue(tenant_id)


@router.get("/snapshot", response_model=AttentionSnapshot)
async def get_snapshot(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionSnapshot:
    """Capture point-in-time snapshot of active attention focus, stack, and queue."""
    service = get_service()
    return service.create_snapshot(tenant_id)


@router.get("/health", response_model=AttentionHealthMetrics)
async def get_attention_health(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionHealthMetrics:
    """Retrieve telemetry metrics on attention performance, preemption, and resource usage."""
    service = get_service()
    return service.get_health(tenant_id)


@router.get("/metrics")
async def get_raw_metrics(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Retrieve granular attention and cognitive resource metrics."""
    service = get_service()
    health = service.get_health(tenant_id)
    return {
        "health": health.model_dump(),
        "resource_budget": service.resource_mgr.budget.model_dump(),
        "total_evaluations": service.total_evaluations,
        "total_interruptions": service.total_interruptions,
        "mode": service.mode.value,
    }


@router.get("/{attention_id}", response_model=AttentionCandidate)
async def get_candidate(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Retrieve a specific attention candidate by ID."""
    service = get_service()
    cand = service.get_candidate(attention_id, tenant_id)
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attention candidate '{attention_id}' not found.",
        )
    return cand


@router.post("/{attention_id}/focus")
async def focus_candidate(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Allocate active focus to candidate, preempting current work if justified."""
    service = get_service()
    try:
        cand, preemption = service.focus_candidate(attention_id, tenant_id)
        return {
            "status": "focused",
            "candidate": cand,
            "preemption": preemption,
        }
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/pause", response_model=AttentionCandidate)
async def pause_candidate(
    attention_id: str,
    req: ActionReasonRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Pause an attending candidate and release active cognitive resources."""
    service = get_service()
    reason = req.reason if req else ""
    try:
        return service.pause_candidate(attention_id, tenant_id, reason=reason)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/resume", response_model=AttentionCandidate)
async def resume_candidate(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Resume attention on a paused candidate."""
    service = get_service()
    try:
        return service.resume_candidate(attention_id, tenant_id)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/defer", response_model=AttentionCandidate)
async def defer_candidate(
    attention_id: str,
    req: ActionReasonRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Defer candidate for later scheduling."""
    service = get_service()
    reason = req.reason if req else ""
    try:
        return service.defer_candidate(attention_id, tenant_id, reason=reason)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/delegate", response_model=AttentionCandidate)
async def delegate_candidate(
    attention_id: str,
    req: DelegateRequest,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Delegate candidate to a specialized autonomous agent."""
    service = get_service()
    try:
        return service.delegate_candidate(
            attention_id,
            target_agent_id=req.target_agent_id,
            tenant_id=tenant_id,
            reason=req.reason,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/dismiss", response_model=AttentionCandidate)
async def dismiss_candidate(
    attention_id: str,
    req: ActionReasonRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Dismiss candidate from active scheduling."""
    service = get_service()
    reason = req.reason if req else ""
    try:
        return service.dismiss_candidate(attention_id, tenant_id, reason=reason)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/escalate", response_model=AttentionCandidate)
async def escalate_candidate(
    attention_id: str,
    req: ScoreAdjustRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """Escalate attention score based on new evidence or risk increase."""
    service = get_service()
    boost = req.delta if req else 0.15
    reason = req.reason if req else ""
    try:
        return service.escalate_candidate(attention_id, boost=boost, tenant_id=tenant_id, reason=reason)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/{attention_id}/deescalate", response_model=AttentionCandidate)
async def deescalate_candidate(
    attention_id: str,
    req: ScoreAdjustRequest | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidate:
    """De-escalate attention score when risk has been mitigated or verified."""
    service = get_service()
    reduction = req.delta if req else 0.15
    reason = req.reason if req else ""
    try:
        return service.deescalate_candidate(
            attention_id, reduction=reduction, tenant_id=tenant_id, reason=reason
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/{attention_id}/explanation")
async def get_candidate_explanation(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Retrieve explainable scoring and focus justification ('Why is/isn't Kairo focusing on this?')."""
    service = get_service()
    try:
        return service.get_explanation(attention_id, tenant_id)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/{attention_id}/history")
async def get_candidate_history(
    attention_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> list[dict[str, Any]]:
    """Retrieve full audit history for candidate."""
    service = get_service()
    return service.get_history(attention_id, tenant_id)


# ============================================================================
# Task 109 Endpoints
# ============================================================================


class CandidateIngestRequestT109(BaseModel):
    source: str
    type: AttentionCandidateType = AttentionCandidateType.USER_REQUEST
    target: str = "unspecified"


    title: str
    description: str = ""
    urgency: float = 0.5
    importance: float = 0.5
    risk: float = 0.3
    related_mission: str | None = None
    related_situation: str | None = None
    related_user_intent: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class FocusRequestT109(BaseModel):
    candidate_id: str
    target_id: str
    target_name: str
    reason: FocusSwitchReason = FocusSwitchReason.USER_REQUEST
    expected_duration_sec: int = 300
    interruption_policy: str = "NORMAL"


class FocusCompleteRequestT109(BaseModel):
    reason: str = "Objective accomplished"


class InterruptionEvalRequestT109(BaseModel):
    incoming_candidate_id: str
    source_is_emergency_stop: bool = False
    current_phase: str = "in_progress"
    is_current_shielded: bool = False


class WatchCreateRequestT109(BaseModel):
    candidate_id: str
    condition_type: WaitingConditionType = WaitingConditionType.WAITING_FOR_EXTERNAL_EVENT
    condition_expr: str
    reconsideration_trigger: str



class SignalEvalRequestT109(BaseModel):
    event_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class FeedbackRequestT109(BaseModel):
    candidate_id: str
    decision_type: str = "INTERRUPT"
    was_appropriate: bool = True
    missed_critical: bool = False
    unnecessary_interrupt: bool = False
    starvation_occurred: bool = False
    notes: str = ""


@router.post("/v2/candidates", response_model=AttentionCandidateT109, status_code=status.HTTP_201_CREATED)
async def ingest_candidate_v2(
    payload: CandidateIngestRequestT109,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidateT109:
    """Ingest, sanitize, evaluate 15-dimensional salience and queue candidate (Task 109)."""
    service = get_service()
    candidate = AttentionCandidateT109(
        source=payload.source,
        type=payload.type,
        target=payload.target,
        title=payload.title,
        description=payload.description,
        related_mission=payload.related_mission,
        related_situation=payload.related_situation,
        related_user_intent=payload.related_user_intent,
    )
    candidate.score.urgency = payload.urgency
    candidate.score.importance = payload.importance
    candidate.score.risk = payload.risk

    evidence_objs = [
        AttentionEvidence(
            candidate_id=candidate.candidate_id,
            source_uri=ev.get("source_uri", "signal://incoming"),
            source_type=ev.get("source_type", "INTERNAL_SIGNAL"),
            is_trusted=ev.get("is_trusted", True),
            credibility=ev.get("credibility", 0.8),
            claim=ev.get("claim", ""),
            raw_payload=ev.get("raw_payload", {}),
        )
        for ev in payload.evidence
    ]

    return service.ingest_candidate_t109(candidate, evidence_objs, tenant_id=tenant_id)


@router.get("/v2/candidates", response_model=list[AttentionCandidateT109])
async def list_candidates_v2(
    lifecycle: AttentionLifecycleState | None = None,
    candidate_type: AttentionCandidateType | None = None,
    limit: int = 50,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> list[AttentionCandidateT109]:
    """List attention candidates ordered by composite salience."""
    service = get_service()
    return service.list_candidates_t109(lifecycle=lifecycle, candidate_type=candidate_type, limit=limit)


@router.get("/v2/candidates/{candidate_id}", response_model=AttentionCandidateT109)
async def get_candidate_v2(
    candidate_id: str,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionCandidateT109:
    """Get single attention candidate details."""
    service = get_service()
    cand = service.get_candidate_t109(candidate_id)
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate {candidate_id} not found")
    return cand


@router.post("/v2/focus")
async def request_focus_v2(
    payload: FocusRequestT109,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Enter or transition active focus to candidate."""
    service = get_service()
    target = FocusTarget(target_id=payload.target_id, name=payload.target_name)
    try:
        session, transition = service.request_focus_t109(
            candidate_id=payload.candidate_id,
            target=target,
            reason=payload.reason,
            expected_duration_sec=payload.expected_duration_sec,
            interruption_policy=payload.interruption_policy,
            tenant_id=tenant_id,
        )
        return {
            "session": session.model_dump(),
            "transition": transition.model_dump() if transition else None,
        }
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except RuntimeError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err))


@router.post("/v2/focus/complete")
async def complete_focus_v2(
    payload: FocusCompleteRequestT109 | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Complete active focus session and pop resumed session from stack."""
    service = get_service()
    reason = payload.reason if payload else "Objective accomplished"
    completed, resumed = service.complete_focus_t109(reason=reason, tenant_id=tenant_id)
    return {
        "completed_session": completed.model_dump() if completed else None,
        "resumed_session": resumed.model_dump() if resumed else None,
    }


@router.post("/v2/focus/abort")
async def abort_focus_v2(
    payload: FocusCompleteRequestT109 | None = None,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Abort active focus session and pop resumed session from stack."""
    service = get_service()
    reason = payload.reason if payload else "Cancelled"
    completed, resumed = service.abort_focus_t109(reason=reason, tenant_id=tenant_id)
    return {
        "aborted_session": completed.model_dump() if completed else None,
        "resumed_session": resumed.model_dump() if resumed else None,
    }


@router.post("/v2/interruptions/evaluate", response_model=InterruptionDecision)
async def evaluate_interruption_v2(
    payload: InterruptionEvalRequestT109,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> InterruptionDecision:
    """Evaluate 6-tier interruption policy for incoming stimulus."""
    service = get_service()
    try:
        return service.evaluate_interruption_t109(
            incoming_candidate_id=payload.incoming_candidate_id,
            source_is_emergency_stop=payload.source_is_emergency_stop,
            current_phase=payload.current_phase,
            is_current_shielded=payload.is_current_shielded,
            tenant_id=tenant_id,
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/v2/watches", response_model=AttentionWatch, status_code=status.HTTP_201_CREATED)
async def create_watch_v2(
    payload: WatchCreateRequestT109,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionWatch:
    """Create a zero-cost condition watch."""
    service = get_service()
    try:
        return service.create_watch_t109(
            candidate_id=payload.candidate_id,
            condition_type=payload.condition_type,
            condition_expr=payload.condition_expr,
            trigger=payload.reconsideration_trigger,
            tenant_id=tenant_id,
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.post("/v2/signals/evaluate")
async def evaluate_signals_v2(
    payload: SignalEvalRequestT109,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Evaluate incoming external signal against active condition watches."""
    service = get_service()
    reactivated = service.evaluate_external_signal_t109(
        event_name=payload.event_name,
        payload=payload.payload,
        tenant_id=tenant_id,
    )
    return {"reactivated_candidate_ids": reactivated}


@router.post("/v2/fairness/sweep", response_model=list[AttentionCandidateT109])
async def run_fairness_sweep_v2(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> list[AttentionCandidateT109]:
    """Apply fairness aging boost across queued and deferred candidates."""
    service = get_service()
    return service.run_fairness_sweep_t109(tenant_id=tenant_id)


@router.get("/v2/health")
async def get_health_v2(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> dict[str, Any]:
    """Evaluate cognitive load, fragmentation, and attention health."""
    service = get_service()
    return service.get_health_status_t109(tenant_id=tenant_id)


@router.get("/v2/snapshot", response_model=AttentionSnapshotT109)
async def get_snapshot_v2(
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionSnapshotT109:
    """Capture point-in-time snapshot for Decision Intelligence."""
    service = get_service()
    return service.capture_snapshot_t109(tenant_id=tenant_id)


@router.post("/v2/feedback", response_model=AttentionFeedback, status_code=status.HTTP_201_CREATED)
async def record_feedback_v2(
    payload: FeedbackRequestT109,
    tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default",
) -> AttentionFeedback:
    """Record post-hoc evaluation telemetry."""
    service = get_service()
    return service.record_feedback_t109(
        candidate_id=payload.candidate_id,
        decision_type=payload.decision_type,
        was_appropriate=payload.was_appropriate,
        missed_critical=payload.missed_critical,
        unnecessary_interrupt=payload.unnecessary_interrupt,
        starvation_occurred=payload.starvation_occurred,
        notes=payload.notes,
    )


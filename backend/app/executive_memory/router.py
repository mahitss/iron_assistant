"""FastAPI Router for Kairo Executive Memory, Long-Horizon Context, and Continuity Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.executive_memory.schemas import (
    BlockerSchema,
    BlockerStatus,
    CheckpointSchema,
    ContinuityQueryRequest,
    ContinuityQueryResponse,
    ExecutiveBriefSchema,
    ExecutiveMemoryMetricsSchema,
    ExecutiveStateSchema,
    ExecutiveStateScope,
    MilestoneSchema,
    NextActionSchema,
    OpenLoopSchema,
    OpenLoopStatus,
    ReconciliationReportSchema,
    TimelineEventSchema,
    TimelineEventType,
)
from app.executive_memory.service import executive_memory_service

router = APIRouter(prefix="/api/v1/executive-memory", tags=["Executive Memory"])


# --------------------------------------------------------------------------
# Request Body Models
# --------------------------------------------------------------------------


class RecordTimelineEventRequest(BaseModel):
    event_type: TimelineEventType
    source: str
    description_reference: str
    project_id: str | None = None
    actor: str = "kairo"
    impact: str = "MEDIUM"
    timestamp: datetime | None = None
    provenance: dict[str, Any] | None = None


class SynthesizeStateRequest(BaseModel):
    scope: ExecutiveStateScope = ExecutiveStateScope.PROJECT
    scope_id: str | None = None
    authoritative_sources: dict[str, Any] | None = None


class CreateOpenLoopRequest(BaseModel):
    description: str
    owner: str = "kairo"
    source: str = "tasks"
    priority: str = "MEDIUM"
    due_at: datetime | None = None
    dependencies: list[str] | None = None
    scope: str = "PROJECT"
    project_id: str | None = None


class UpdateOpenLoopStatusRequest(BaseModel):
    status: OpenLoopStatus
    evidence: str | None = None


class CloseOpenLoopRequest(BaseModel):
    evidence: str


class CreateBlockerRequest(BaseModel):
    description: str
    affected_tasks: list[str]
    source: str
    severity: str = "MEDIUM"
    owner: str | None = None
    causality_evidence: str | None = None
    project_id: str | None = None


class ResolveBlockerRequest(BaseModel):
    resolution_evidence: str


class CreateMilestoneRequest(BaseModel):
    project_id: str
    criteria: str
    goal_id: str | None = None
    due_at: datetime | None = None


class AchieveMilestoneRequest(BaseModel):
    verification_evidence: str


class GenerateBriefRequest(BaseModel):
    current_status: str
    recent_progress: list[dict[str, Any]] | None = None
    open_work: list[dict[str, Any]] | None = None
    blockers: list[dict[str, Any]] | None = None
    decisions: list[dict[str, Any]] | None = None
    risks: list[dict[str, Any]] | None = None
    next_actions: list[dict[str, Any]] | None = None


class CreateCheckpointRequest(BaseModel):
    workflow_id: str
    goal: str
    state: dict[str, Any]
    progress: str
    dependencies: list[str]
    authorization: dict[str, Any]
    next_step: str


class ResumeCheckpointRequest(BaseModel):
    current_authoritative_state: dict[str, Any]


class ReconcileRequest(BaseModel):
    scope_id: str
    synthesized_state: dict[str, Any]
    authoritative_state: dict[str, Any]


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.post("/query", response_model=ContinuityQueryResponse)
def answer_continuity_query(req: ContinuityQueryRequest) -> ContinuityQueryResponse:
    """Answers one of the 8 canonical continuity questions grounded in authoritative state."""
    return executive_memory_service.answer_continuity_query(
        question_type=req.question_type,
        project_id=req.project_id,
        as_of=req.as_of,
        target_id=req.target_id,
        explicit_user_intent=req.explicit_user_intent,
    )


@router.get("/state", response_model=ExecutiveStateSchema | None)
def get_latest_state() -> ExecutiveStateSchema | None:
    """Returns the latest synthesized executive state."""
    state = executive_memory_service.get_latest_state()
    return state


@router.post("/state/synthesize", response_model=ExecutiveStateSchema)
def synthesize_state(req: SynthesizeStateRequest) -> ExecutiveStateSchema:
    """Derives and synthesizes current executive state from authoritative sources."""
    return executive_memory_service.synthesize_current_state(
        scope=req.scope,
        scope_id=req.scope_id,
        authoritative_sources=req.authoritative_sources,
    )


@router.get("/timeline", response_model=list[TimelineEventSchema])
def list_timeline_events(
    project_id: str | None = None,
    event_type: TimelineEventType | None = None,
    as_of: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[TimelineEventSchema]:
    """Lists chronological timeline events."""
    return executive_memory_service.list_timeline_events(
        project_id=project_id, event_type=event_type, as_of=as_of, limit=limit
    )


@router.post(
    "/timeline/events", response_model=TimelineEventSchema, status_code=status.HTTP_201_CREATED
)
def record_timeline_event(req: RecordTimelineEventRequest) -> TimelineEventSchema:
    """Records an authoritative timeline event with deduplication."""
    return executive_memory_service.record_timeline_event(
        event_type=req.event_type,
        source=req.source,
        description_reference=req.description_reference,
        project_id=req.project_id,
        actor=req.actor,
        impact=req.impact,
        timestamp=req.timestamp,
        provenance=req.provenance,
    )


@router.get("/timeline/as-of")
def reconstruct_as_of(
    as_of: datetime,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Reconstructs historical state as of a specified point in time."""
    return executive_memory_service.reconstruct_as_of(as_of=as_of, project_id=project_id)


@router.get("/open-loops", response_model=list[OpenLoopSchema])
def list_open_loops(
    project_id: str | None = None,
    status: OpenLoopStatus | None = None,
    include_stale: bool = True,
) -> list[OpenLoopSchema]:
    """Lists open loops with staleness detection."""
    return executive_memory_service.list_open_loops(
        project_id=project_id, status=status, include_stale=include_stale
    )


@router.post(
    "/open-loops", response_model=OpenLoopSchema, status_code=status.HTTP_201_CREATED
)
def create_open_loop(req: CreateOpenLoopRequest) -> OpenLoopSchema:
    """Creates a new open loop."""
    return executive_memory_service.create_open_loop(
        description=req.description,
        owner=req.owner,
        source=req.source,
        priority=req.priority,
        due_at=req.due_at,
        dependencies=req.dependencies,
        scope=req.scope,
        project_id=req.project_id,
    )


@router.patch("/open-loops/{loop_id}/status", response_model=OpenLoopSchema)
def update_open_loop_status(
    loop_id: str, req: UpdateOpenLoopStatusRequest
) -> OpenLoopSchema:
    """Updates the status of an open loop."""
    try:
        return executive_memory_service.update_open_loop_status(
            loop_id=loop_id, status=req.status, evidence=req.evidence
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Open loop {loop_id} not found"
        )


@router.post("/open-loops/{loop_id}/close", response_model=OpenLoopSchema)
def close_open_loop(loop_id: str, req: CloseOpenLoopRequest) -> OpenLoopSchema:
    """Closes an open loop with verified evidence."""
    try:
        return executive_memory_service.close_open_loop(
            loop_id=loop_id, evidence=req.evidence
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Open loop {loop_id} not found"
        )


@router.get("/blockers", response_model=list[BlockerSchema])
def list_blockers(
    project_id: str | None = None, active_only: bool = True
) -> list[BlockerSchema]:
    """Lists blockers with causal evidence."""
    return executive_memory_service.list_blockers(
        project_id=project_id, active_only=active_only
    )


@router.post("/blockers", response_model=BlockerSchema, status_code=status.HTTP_201_CREATED)
def create_blocker(req: CreateBlockerRequest) -> BlockerSchema:
    """Creates a blocker backed by causal evidence."""
    return executive_memory_service.create_blocker(
        description=req.description,
        affected_tasks=req.affected_tasks,
        source=req.source,
        severity=req.severity,
        owner=req.owner,
        causality_evidence=req.causality_evidence,
        project_id=req.project_id,
    )


@router.post("/blockers/{blocker_id}/resolve", response_model=BlockerSchema)
def resolve_blocker(blocker_id: str, req: ResolveBlockerRequest) -> BlockerSchema:
    """Resolves a blocker with evidence."""
    try:
        return executive_memory_service.resolve_blocker(
            blocker_id=blocker_id, resolution_evidence=req.resolution_evidence
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Blocker {blocker_id} not found"
        )


@router.get("/milestones", response_model=list[MilestoneSchema])
def list_milestones(project_id: str | None = None) -> list[MilestoneSchema]:
    """Lists milestones."""
    return executive_memory_service.list_milestones(project_id=project_id)


@router.post(
    "/milestones", response_model=MilestoneSchema, status_code=status.HTTP_201_CREATED
)
def create_milestone(req: CreateMilestoneRequest) -> MilestoneSchema:
    """Creates a milestone."""
    return executive_memory_service.create_milestone(
        project_id=req.project_id,
        criteria=req.criteria,
        goal_id=req.goal_id,
        due_at=req.due_at,
    )


@router.post("/milestones/{milestone_id}/achieve", response_model=MilestoneSchema)
def achieve_milestone(milestone_id: str, req: AchieveMilestoneRequest) -> MilestoneSchema:
    """Marks a milestone as achieved with required empirical evidence."""
    try:
        return executive_memory_service.achieve_milestone(
            milestone_id=milestone_id, verification_evidence=req.verification_evidence
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Milestone {milestone_id} not found",
        )


@router.get("/briefs/{project_id}", response_model=ExecutiveBriefSchema | None)
def get_executive_brief(project_id: str) -> ExecutiveBriefSchema | None:
    """Retrieves the latest executive brief for a project."""
    return executive_memory_service.get_executive_brief(project_id=project_id)


@router.post("/briefs/{project_id}", response_model=ExecutiveBriefSchema)
def generate_executive_brief(
    project_id: str, req: GenerateBriefRequest
) -> ExecutiveBriefSchema:
    """Generates an executive briefing containing CURRENT, RECENT, OPEN, BLOCKED, NEXT, RISKS, DECISIONS."""
    return executive_memory_service.generate_executive_brief(
        project_id=project_id,
        current_status=req.current_status,
        recent_progress=req.recent_progress,
        open_work=req.open_work,
        blockers=req.blockers,
        decisions=req.decisions,
        risks=req.risks,
        next_actions=req.next_actions,
    )


@router.get("/next-actions", response_model=list[NextActionSchema])
def get_next_actions(
    project_id: str | None = None,
    explicit_user_intent: str | None = None,
) -> list[NextActionSchema]:
    """Generates grounded next actions from open loops, respecting user intent supremacy."""
    return executive_memory_service.generate_next_actions(
        project_id=project_id, explicit_user_intent=explicit_user_intent
    )


@router.post(
    "/checkpoints", response_model=CheckpointSchema, status_code=status.HTTP_201_CREATED
)
def create_checkpoint(req: CreateCheckpointRequest) -> CheckpointSchema:
    """Captures a workflow checkpoint."""
    return executive_memory_service.create_checkpoint(
        workflow_id=req.workflow_id,
        goal=req.goal,
        state=req.state,
        progress=req.progress,
        dependencies=req.dependencies,
        authorization=req.authorization,
        next_step=req.next_step,
    )


@router.post("/checkpoints/{checkpoint_id}/resume")
def resume_checkpoint(checkpoint_id: str, req: ResumeCheckpointRequest) -> dict[str, Any]:
    """Validates and resumes an execution checkpoint."""
    try:
        return executive_memory_service.resume_checkpoint(
            checkpoint_id=checkpoint_id,
            current_authoritative_state=req.current_authoritative_state,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkpoint {checkpoint_id} not found",
        )


@router.post("/reconcile", response_model=ReconciliationReportSchema)
def reconcile_state(req: ReconcileRequest) -> ReconciliationReportSchema:
    """Reconciles synthesized state against source systems (source systems strictly win)."""
    return executive_memory_service.reconcile(
        scope_id=req.scope_id,
        synthesized_state=req.synthesized_state,
        authoritative_state=req.authoritative_state,
    )


@router.get("/metrics", response_model=ExecutiveMemoryMetricsSchema)
def get_metrics() -> ExecutiveMemoryMetricsSchema:
    """Retrieves executive memory operational metrics and false continuity tracking."""
    return executive_memory_service.get_metrics()

"""FastAPI REST API endpoints for Kairo Autonomous Goal Management & Mission Control (Task 66 & Task 100)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.missions.schemas import (
    AssumptionCreateRequest,
    AssumptionUpdateRequest,
    CheckpointCreateRequest,
    DependencyCreateRequest,
    MilestoneCreateRequest,
    MilestoneUpdateRequest,
    MilestoneVerifyRequest,
    MissionCreateRequest,
    MissionReviewRequest,
    MissionUpdateRequest,
    ObjectiveCreateRequest,
    ReviewType,
)
from app.missions.service import MissionService, mission_service

router = APIRouter(prefix="/missions", tags=["missions"])


def get_mission_service(db: Session = Depends(get_db)) -> MissionService:
    if db is not None:
        mission_service.db = db
        mission_service.auditor.db = db
    return mission_service


@router.get("/health", response_model=dict[str, Any])
def get_missions_health(
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Health check endpoint for Autonomous Goal Management & Mission Control."""
    return {
        "status": "ok",
        "engine": "Kairo Autonomous Mission Control Engine",
        "task": 66,
        "task_100": True,
        "audit_chain_intact": service.auditor.verify_integrity(),
    }


@router.post("/", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_mission(
    request: MissionCreateRequest,
    is_human_approved: bool = Query(default=False),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Normalize natural-language goal and instantiate an autonomous mission (Spec 2, 4, 9 & Task 100)."""
    try:
        mission, goal, val_status, ambiguity = service.create_mission(
            request=request,
            is_human_approved=is_human_approved,
        )
        return {
            "mission": mission.model_dump(),
            "goal": goal.model_dump(),
            "validation_status": val_status.value,
            "ambiguity_info": ambiguity,
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/", response_model=list[dict[str, Any]])
def list_missions(
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    """List all missions for tenant."""
    missions = service.list_missions(tenant_id=tenant_id)
    return [m.model_dump() for m in missions]


@router.get("/overview", response_model=dict[str, Any])
def get_mission_overview(
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Retrieve Mission Control Center aggregated telemetry (Spec 95 & Task 100)."""
    overview = service.get_overview(tenant_id=tenant_id)
    return overview.model_dump()


@router.get("/audit/verify", response_model=dict[str, Any])
def verify_audit_chain(
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Verify cryptographic SHA-256 hash-chain integrity across all mission logs."""
    is_valid = service.auditor.verify_integrity()
    return {"audit_chain_intact": is_valid}


@router.get("/{mission_id}", response_model=dict[str, Any])
def get_mission(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Get mission details by id."""
    try:
        mission = service.get_mission(mission_id, tenant_id=tenant_id)
        return mission.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{mission_id}", response_model=dict[str, Any])
def update_mission(
    mission_id: str,
    request: MissionUpdateRequest,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Update mutable attributes of a mission."""
    try:
        mission = service.update_mission(mission_id, request, tenant_id=tenant_id)
        return mission.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/start", response_model=dict[str, Any])
def start_mission(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Start autonomous execution of mission."""
    try:
        mission = service.start_mission(mission_id, tenant_id=tenant_id)
        return mission.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/pause", response_model=dict[str, Any])
def pause_mission(
    mission_id: str,
    reason: str = Query(default="Operator requested pause"),
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Pause mission execution (Spec 48, 73)."""
    try:
        mission = service.pause_mission(mission_id, reason=reason, tenant_id=tenant_id)
        return mission.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/resume", response_model=dict[str, Any])
def resume_mission(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Resume paused mission with revalidation (Spec 48, 49)."""
    try:
        mission = service.resume_mission(mission_id, tenant_id=tenant_id)
        return mission.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/cancel", response_model=dict[str, Any])
def cancel_mission(
    mission_id: str,
    reason: str = Query(default="User cancelled"),
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Cancel mission and release all resources."""
    try:
        mission = service.cancel_mission(mission_id, reason=reason, tenant_id=tenant_id)
        return mission.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/replan", response_model=dict[str, Any])
def replan_mission(
    mission_id: str,
    reason: str = Query(default="Strategy adjustment"),
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Trigger strategic replan for mission."""
    try:
        return service.replan_mission(mission_id, reason=reason, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/cycle", response_model=dict[str, Any])
def execute_supervisory_cycle(
    mission_id: str,
    telemetry: dict[str, Any] | None = None,
    recent_actions: list[str] | None = None,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Execute autonomous supervisory loop cycle (Spec 57)."""
    try:
        return service.execute_supervisory_cycle(
            mission_id=mission_id,
            telemetry=telemetry or {},
            recent_actions=recent_actions or [],
            tenant_id=tenant_id,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/orchestrate", response_model=dict[str, Any])
def run_orchestration_cycle(
    mission_id: str,
    world_state_entity_id: str | None = Query(default=None),
    expected_postconditions: dict[str, Any] | None = None,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Run one continuous mission control orchestration step (Task 100)."""
    try:
        return service.run_orchestration_cycle(
            mission_id=mission_id,
            world_state_entity_id=world_state_entity_id,
            expected_postconditions=expected_postconditions,
            tenant_id=tenant_id,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/complete", response_model=dict[str, Any])
def complete_mission(
    mission_id: str,
    what_worked: list[str] | None = None,
    lessons: list[str] | None = None,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Complete mission and record retrospective postmortem (Spec 75, 78)."""
    try:
        pm = service.complete_mission(
            mission_id=mission_id,
            what_worked=what_worked,
            lessons=lessons,
            tenant_id=tenant_id,
        )
        return pm.model_dump()
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# --- Task 100 Objective Endpoints ---


@router.get("/{mission_id}/objectives", response_model=list[dict[str, Any]])
def list_mission_objectives(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        objectives = service.list_objectives(mission_id, tenant_id=tenant_id)
        return [o.model_dump() for o in objectives]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.post("/{mission_id}/objectives", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def add_mission_objective(
    mission_id: str,
    request: ObjectiveCreateRequest,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        obj = service.add_objective(mission_id, request, tenant_id=tenant_id)
        return obj.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# --- Task 100 Milestone Endpoints ---


@router.get("/{mission_id}/milestones", response_model=list[dict[str, Any]])
def list_mission_milestones(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        milestones = service.list_milestones(mission_id, tenant_id=tenant_id)
        return [m.model_dump() for m in milestones]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.post("/{mission_id}/milestones", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def add_mission_milestone(
    mission_id: str,
    request: MilestoneCreateRequest,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        milestone = service.add_milestone(mission_id, request, tenant_id=tenant_id)
        return milestone.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/milestones/{milestone_id}", response_model=dict[str, Any])
def get_mission_milestone(
    mission_id: str,
    milestone_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        m = service.get_milestone(mission_id, milestone_id, tenant_id=tenant_id)
        return m.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Milestone '{milestone_id}' not found.")


@router.patch("/{mission_id}/milestones/{milestone_id}", response_model=dict[str, Any])
def update_mission_milestone(
    mission_id: str,
    milestone_id: str,
    request: MilestoneUpdateRequest,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        m = service.update_milestone(mission_id, milestone_id, request, tenant_id=tenant_id)
        return m.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Milestone '{milestone_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/milestones/{milestone_id}/verify", response_model=dict[str, Any])
def verify_mission_milestone(
    mission_id: str,
    milestone_id: str,
    request: MilestoneVerifyRequest,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.verify_milestone(mission_id, milestone_id, request, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Milestone '{milestone_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/milestones/{milestone_id}/regress", response_model=dict[str, Any])
def regress_mission_milestone(
    mission_id: str,
    milestone_id: str,
    reason: str = Query(default="World state drift invalidated completion"),
    evidence: list[str] | None = None,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        m = service.regress_milestone(mission_id, milestone_id, reason=reason, evidence=evidence, tenant_id=tenant_id)
        return m.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Milestone '{milestone_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# --- Task 100 Assumption Endpoints ---


@router.get("/{mission_id}/assumptions", response_model=list[dict[str, Any]])
def list_mission_assumptions(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        assumptions = service.list_assumptions(mission_id, tenant_id=tenant_id)
        return [a.model_dump() for a in assumptions]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.post("/{mission_id}/assumptions", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def add_mission_assumption(
    mission_id: str,
    request: AssumptionCreateRequest,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        a = service.add_assumption(mission_id, request, tenant_id=tenant_id)
        return a.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{mission_id}/assumptions/{assumption_id}", response_model=dict[str, Any])
def update_mission_assumption(
    mission_id: str,
    assumption_id: str,
    request: AssumptionUpdateRequest,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.update_assumption(mission_id, assumption_id, request, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Assumption '{assumption_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# --- Task 100 Dependency Endpoints ---


@router.get("/{mission_id}/dependencies", response_model=list[dict[str, Any]])
def list_mission_dependencies(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        deps = service.list_dependencies(mission_id, tenant_id=tenant_id)
        return [d.model_dump() for d in deps]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.post("/{mission_id}/dependencies", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def add_mission_dependency(
    mission_id: str,
    request: DependencyCreateRequest,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        dep = service.add_dependency(mission_id, request, tenant_id=tenant_id)
        return dep.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# --- Task 100 Situation & Plan Endpoints ---


@router.get("/{mission_id}/situations", response_model=list[str])
def list_mission_situations(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[str]:
    try:
        return service.list_situations(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.post("/{mission_id}/situations", response_model=dict[str, Any])
def link_mission_situation(
    mission_id: str,
    situation_id: str = Query(...),
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.link_situation(mission_id, situation_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/plans", response_model=list[dict[str, Any]])
def list_mission_plans(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        plans = service.list_plans(mission_id, tenant_id=tenant_id)
        return [p.model_dump() for p in plans]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


# --- Task 100 Reviews, Health & Checkpoints ---


@router.get("/{mission_id}/health", response_model=dict[str, Any])
@router.get("/{mission_id}/health_details", response_model=dict[str, Any])
def get_mission_health_details(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        data = service.get_mission_health(mission_id, tenant_id=tenant_id)
        if "health_dimensions" in data and "dimensions" not in data:
            data["dimensions"] = data["health_dimensions"]
        return data
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.post("/{mission_id}/reviews", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
@router.post("/{mission_id}/review", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def review_mission(
    mission_id: str,
    request: MissionReviewRequest | None = None,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        rev_type = request.review_type if request else ReviewType.TRIGGERED
        notes = request.notes if request else ""
        eval_score = request.evaluation_score if request else None
        obs = request.observations if request else None
        review = service.review_mission(
            mission_id,
            review_type=rev_type,
            notes=notes,
            evaluation_score=eval_score,
            observations=obs,
            tenant_id=tenant_id,
        )
        return review.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/checkpoints", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
@router.post("/{mission_id}/checkpoint", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_mission_checkpoint(
    mission_id: str,
    request: CheckpointCreateRequest | None = None,
    context_summary: str | None = Query(default=None),
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        label = request.label if request else ""
        summary = (request.context_summary if request and request.context_summary else context_summary) or "Manual checkpoint created"
        handoff = request.generate_handoff_manifest if request else False
        chk = service.create_checkpoint(
            mission_id,
            label=label,
            context_summary=summary,
            generate_handoff_manifest=handoff,
            tenant_id=tenant_id,
        )
        return chk.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/orchestrate", response_model=dict[str, Any])
def orchestrate_mission_cycle(
    mission_id: str,
    payload: dict[str, Any] | None = None,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.run_orchestration_cycle(
            mission_id=mission_id,
            expected_postconditions=payload,
            tenant_id=tenant_id,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc



# --- Preserved Query Endpoints ---


@router.get("/{mission_id}/goals", response_model=dict[str, Any])
def get_mission_goals(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.get_mission_goals(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/tasks", response_model=dict[str, Any])
def get_mission_tasks(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.get_mission_tasks(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/progress", response_model=dict[str, Any])
def get_mission_progress(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.get_mission_progress(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/blockers", response_model=list[dict[str, Any]])
def get_mission_blockers(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        return service.get_mission_blockers(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/timeline", response_model=dict[str, Any])
def get_mission_timeline(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.get_mission_timeline(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/decisions", response_model=list[dict[str, Any]])
def get_mission_decisions(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        return service.get_mission_decisions(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/risks", response_model=dict[str, Any])
def get_mission_risks(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.get_mission_risks(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/checkpoints", response_model=list[dict[str, Any]])
def get_mission_checkpoints(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        mission = service.get_mission(mission_id, tenant_id=tenant_id)
        return [c.model_dump() for c in mission.checkpoints]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/audit", response_model=list[dict[str, Any]])
def get_mission_audit(
    mission_id: str,
    tenant_id: str | None = Query(default=None),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    try:
        if tenant_id is not None:
            service.get_mission(mission_id, tenant_id=tenant_id)
        events = service.auditor.get_trail(mission_id=mission_id)
        return [e.model_dump() for e in events]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.get("/{mission_id}/postmortem", response_model=dict[str, Any])
def get_mission_postmortem(
    mission_id: str,
    tenant_id: str | None = Query(default=None),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        if tenant_id is not None:
            service.get_mission(mission_id, tenant_id=tenant_id)
        pm = service.supervisor.get_postmortem(mission_id)
        if not pm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Postmortem not yet recorded for mission '{mission_id}'.",
            )
        return pm.model_dump()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")


@router.post("/{mission_id}/reassess", response_model=dict[str, Any])
def reassess_mission(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.reassess_mission(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/verify", response_model=dict[str, Any])
def verify_mission(
    mission_id: str,
    telemetry: dict[str, Any] | None = None,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    try:
        return service.verify_mission(mission_id, telemetry=telemetry, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

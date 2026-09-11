"""FastAPI REST API endpoints for Kairo Autonomous Goal Management & Mission Engine (Task 66)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.missions.schemas import (
    MissionCreateRequest,
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
    """Health check endpoint for Autonomous Goal Management & Mission Engine."""
    return {
        "status": "ok",
        "engine": "Kairo Autonomous Mission Engine",
        "task": 66,
        "audit_chain_intact": service.auditor.verify_integrity(),
    }


@router.post("/", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_mission(
    request: MissionCreateRequest,
    is_human_approved: bool = Query(default=False),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Normalize natural-language goal and instantiate an autonomous mission (Spec 2, 4, 9)."""
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
    """Retrieve Mission Control Center aggregated telemetry (Spec 95)."""
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{mission_id}/start", response_model=dict[str, Any])
def start_mission(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Start mission execution."""
    try:
        mission = service.start_mission(mission_id, tenant_id=tenant_id)
        return mission.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/pause", response_model=dict[str, Any])
def pause_mission(
    mission_id: str,
    reason: str = Query(default="User requested pause"),
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Pause an active mission."""
    try:
        mission = service.pause_mission(mission_id, reason=reason, tenant_id=tenant_id)
        return mission.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/resume", response_model=dict[str, Any])
def resume_mission(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Resume a paused mission after revalidating world state (Spec 48, 49)."""
    try:
        mission = service.resume_mission(mission_id, tenant_id=tenant_id)
        return mission.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/cancel", response_model=dict[str, Any])
def cancel_mission(
    mission_id: str,
    reason: str = Query(default="User cancelled"),
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Gracefully cancel mission and teardown resources (Spec 74, 90)."""
    try:
        mission = service.cancel_mission(mission_id, reason=reason, tenant_id=tenant_id)
        return mission.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/replan", response_model=dict[str, Any])
def replan_mission(
    mission_id: str,
    reason: str = Query(default="Strategy adaptation"),
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Generate a new plan version for the mission (Spec 35, 36)."""
    try:
        new_plan = service.replan_mission(mission_id, reason=reason, tenant_id=tenant_id)
        return new_plan
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/cycle", response_model=dict[str, Any])
def execute_supervisory_cycle(
    mission_id: str,
    telemetry: dict[str, Any],
    recent_actions: list[str],
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Execute one autonomous supervisory loop cycle (Spec 57)."""
    try:
        cycle_result = service.execute_supervisory_cycle(
            mission_id=mission_id,
            telemetry=telemetry,
            recent_actions=recent_actions,
            tenant_id=tenant_id,
        )
        return cycle_result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/complete", response_model=dict[str, Any])
def complete_mission(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Close mission with structured postmortem (Spec 75, 78)."""
    try:
        postmortem = service.complete_mission(mission_id, tenant_id=tenant_id)
        return postmortem.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/audit", response_model=list[dict[str, Any]])
def get_mission_audit_trail(
    mission_id: str,
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    """Retrieve cryptographic SHA-256 audit records for mission."""
    records = service.auditor.get_trail(mission_id=mission_id)
    return [r.model_dump() for r in records]


@router.get("/{mission_id}/goals", response_model=dict[str, Any])
def get_mission_goals(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Retrieve goal hierarchy, constraints, and DAG dependencies for mission (Spec 3, 12, 13, 94)."""
    try:
        return service.get_mission_goals(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/tasks", response_model=dict[str, Any])
def get_mission_tasks(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Retrieve active planning tasks associated with mission (Spec 31, 32, 94)."""
    try:
        return service.get_mission_tasks(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/progress", response_model=dict[str, Any])
def get_mission_progress(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Retrieve multi-metric progress calculations, milestones, and sunk cost status (Spec 27, 28, 34, 94)."""
    try:
        return service.get_mission_progress(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/blockers", response_model=list[dict[str, Any]])
def get_mission_blockers(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    """Retrieve prioritized blockers halting mission progress (Spec 68, 69, 70, 94)."""
    try:
        return service.get_mission_blockers(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/timeline", response_model=dict[str, Any])
def get_mission_timeline(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Retrieve complete mission replay timeline and checkpoints (Spec 82, 83, 94, 96)."""
    try:
        return service.get_mission_timeline(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/decisions", response_model=list[dict[str, Any]])
def get_mission_decisions(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> list[dict[str, Any]]:
    """Retrieve decision engine trade-offs and alternatives evaluated (Spec 51, 94)."""
    try:
        return service.get_mission_decisions(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{mission_id}/risks", response_model=dict[str, Any])
def get_mission_risks(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Retrieve risk evaluation, failure conditions, and drift indicators (Spec 11, 19, 20, 94)."""
    try:
        return service.get_mission_risks(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/reassess", response_model=dict[str, Any])
def reassess_mission(
    mission_id: str,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Revalidate assumptions against World Model & Foresight (Spec 21, 22, 53, 94)."""
    try:
        return service.reassess_mission(mission_id, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{mission_id}/verify", response_model=dict[str, Any])
def verify_mission(
    mission_id: str,
    telemetry: dict[str, Any] | None = None,
    tenant_id: str = Query(default="default"),
    service: MissionService = Depends(get_mission_service),
) -> dict[str, Any]:
    """Empirically verify success criteria against telemetry (Spec 65, 75, 76, 94)."""
    try:
        return service.verify_mission(mission_id, telemetry=telemetry, tenant_id=tenant_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission '{mission_id}' not found."
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

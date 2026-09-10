"""FastAPI REST API router for Collective Intelligence & Swarm Reasoning Engine (Task 64)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.swarm.schemas import (
    AgentResult,
    CollectiveResult,
    DisagreementRecord,
    MinorityReport,
    PeerReview,
    SwarmActionRequest,
    SwarmAgentSpec,
    SwarmCreateRequest,
    SwarmSession,
    SwarmTaskNode,
)
from app.swarm.service import swarm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/swarm", tags=["Collective Intelligence & Swarm Reasoning"])


@router.get("/health", response_model=dict[str, Any])
async def swarm_health_check() -> dict[str, Any]:
    """Health and diagnostic endpoint for Swarm Reasoning Engine."""
    agents = swarm_service._engine.registry.list_agents()
    healthy_agents = [a for a in agents if a.health.value == "HEALTHY"]
    return {
        "status": "ok",
        "subsystem": "Collective Intelligence & Swarm Reasoning Engine",
        "version": "1.0.0",
        "registered_agents_count": len(agents),
        "healthy_agents_count": len(healthy_agents),
    }


@router.post("/", response_model=SwarmSession)
async def create_swarm_session(
    req: SwarmCreateRequest,
    db: AsyncSession | None = Depends(get_db),
) -> SwarmSession:
    """Launch a collective intelligence reasoning session toward a shared objective."""
    try:
        session = await swarm_service.create_and_execute_session(req, db=db)
        return session
    except Exception as exc:
        logger.error("Failed to execute swarm session: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Swarm session execution failed: {str(exc)}",
        )


@router.get("/", response_model=list[dict[str, Any]])
async def list_swarm_sessions(
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """List recent and active collective swarm reasoning sessions."""
    sessions = swarm_service.list_sessions(limit=limit)
    return [
        {
            "swarm_id": s.swarm_id,
            "goal": s.objective.goal,
            "topology": s.topology.value,
            "status": s.status.value,
            "agent_count": len(s.agents),
            "consensus_score": s.consensus.consensus_score if s.consensus else 0.0,
            "confidence": s.final_result.confidence if s.final_result else 0.0,
            "verification_status": s.final_result.verification_status if s.final_result else "UNVERIFIED",
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/audit/trail", response_model=list[dict[str, Any]])
async def get_swarm_audit_trail(
    swarm_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Retrieve append-only SHA-256 hash-chained audit trail records."""
    records = swarm_service.get_audit_trail(swarm_id=swarm_id, limit=limit)
    return [dict(r) for r in records]


@router.get("/{swarm_id}", response_model=SwarmSession)
async def get_swarm_session(swarm_id: str) -> SwarmSession:
    """Retrieve full details of an active or completed swarm session."""
    session = swarm_service.get_session(swarm_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Swarm session '{swarm_id}' not found."
        )
    return session


@router.get("/{swarm_id}/agents", response_model=list[SwarmAgentSpec])
async def list_swarm_agents(swarm_id: str) -> list[SwarmAgentSpec]:
    """Retrieve list of specialized agents recruited for the swarm."""
    session = swarm_service.get_session(swarm_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Swarm session '{swarm_id}' not found."
        )
    return session.agents


@router.get("/{swarm_id}/tasks", response_model=list[SwarmTaskNode])
async def list_swarm_tasks(swarm_id: str) -> list[SwarmTaskNode]:
    """Retrieve list of tasks and DAG nodes in the swarm session."""
    tasks = swarm_service.list_tasks(swarm_id)
    return tasks


@router.get("/{swarm_id}/results", response_model=list[AgentResult])
async def list_swarm_results(swarm_id: str) -> list[AgentResult]:
    """Retrieve independent agent results from the swarm session."""
    results = swarm_service.list_results(swarm_id)
    return results


@router.get("/{swarm_id}/reviews", response_model=list[PeerReview])
async def list_swarm_reviews(swarm_id: str) -> list[PeerReview]:
    """Retrieve independent peer reviews conducted across agent results."""
    reviews = swarm_service.list_reviews(swarm_id)
    return reviews


@router.get("/{swarm_id}/disagreements", response_model=list[DisagreementRecord])
async def list_swarm_disagreements(swarm_id: str) -> list[DisagreementRecord]:
    """Retrieve classified disagreements and contradictions detected in the swarm."""
    disagreements = swarm_service.list_disagreements(swarm_id)
    return disagreements


@router.get("/{swarm_id}/minorities", response_model=list[MinorityReport])
@router.get("/{swarm_id}/minority_reports", response_model=list[MinorityReport])
async def list_swarm_minority_reports(swarm_id: str) -> list[MinorityReport]:
    """Retrieve preserved minority positions and conditional failure scenarios."""
    reports = swarm_service.list_minority_reports(swarm_id)
    return reports


@router.get("/{swarm_id}/timeline", response_model=dict[str, Any])
async def get_swarm_timeline(swarm_id: str) -> dict[str, Any]:
    """Reconstruct historical swarm execution timeline and trace (Spec 68)."""
    try:
        return swarm_service.replay_session(swarm_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Swarm session '{swarm_id}' not found."
        )


@router.post("/{swarm_id}/pause", response_model=SwarmSession)
async def pause_swarm_session(swarm_id: str) -> SwarmSession:
    """Pause an active swarm reasoning session."""
    try:
        return swarm_service.pause_session(swarm_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Swarm session '{swarm_id}' not found."
        )


@router.post("/{swarm_id}/resume", response_model=SwarmSession)
async def resume_swarm_session(swarm_id: str) -> SwarmSession:
    """Resume a paused swarm reasoning session."""
    try:
        return swarm_service.resume_session(swarm_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Swarm session '{swarm_id}' not found."
        )


@router.post("/{swarm_id}/cancel", response_model=SwarmSession)
async def cancel_swarm_session(
    swarm_id: str,
    req: SwarmActionRequest | None = None,
) -> SwarmSession:
    """Cancel an active swarm reasoning session."""
    try:
        reason = req.reason if req else ""
        return swarm_service.cancel_session(swarm_id, reason=reason)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Swarm session '{swarm_id}' not found."
        )


@router.post("/{swarm_id}/synthesize", response_model=CollectiveResult)
async def synthesize_swarm_session(swarm_id: str) -> CollectiveResult:
    """Trigger or retrieve synthesized collective result for a session."""
    session = swarm_service.get_session(swarm_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Swarm session '{swarm_id}' not found."
        )
    if session.final_result:
        return session.final_result
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Session does not yet have completed results to synthesize.",
    )


@router.post("/{swarm_id}/verify", response_model=CollectiveResult)
async def verify_swarm_session(
    swarm_id: str,
    notes: str | None = Query(None),
) -> CollectiveResult:
    """Execute Truth Verification barrier on synthesized collective output."""
    try:
        return swarm_service.verify_session(swarm_id, notes=notes)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm session '{swarm_id}' not found or has no result.",
        )

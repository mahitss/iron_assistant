"""FastAPI router for Kairo Autonomous Multi-Agent Collaboration & Swarm Orchestration (Task 96)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.swarm.orchestration_domain import AgentRole
from app.swarm.orchestration_service import (
    SwarmOrchestrationService,
    get_swarm_orchestration_service,
)

logger = logging.getLogger("kairo.swarm.api")

swarms_router = APIRouter(prefix="/swarms", tags=["Swarm Orchestration Engine"])
agents_router = APIRouter(prefix="/agents", tags=["Agent Workers & Supervision"])


# ------------------------------------------------------------------------------
# Request / Response Schemas
# ------------------------------------------------------------------------------

class CreateSwarmRequest(BaseModel):
    objective: str = Field(..., description="High-level mission objective delegated to the swarm")
    max_depth: int = Field(default=3, description="Maximum delegation depth limit")
    max_agents: int = Field(default=10, description="Maximum active agent workers allowed")
    resource_budget: dict[str, Any] = Field(default_factory=dict, description="Allocated resource budget")
    correlation_id: str | None = None
    trace_id: str | None = None


class SpawnAgentRequest(BaseModel):
    session_id: str
    role: AgentRole
    parent_agent_id: str | None = None
    capability_scope: list[str] = Field(default_factory=list)
    context_scope: str = "PRIVATE_AGENT_CONTEXT"
    resource_scope: dict[str, Any] = Field(default_factory=dict)


class DelegateSubtaskRequest(BaseModel):
    objective: str
    role_needed: AgentRole
    allowed_capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    priority: str = "NORMAL"
    expected_output: str = "structured report"


class ExecuteAgentActionRequest(BaseModel):
    action_reference: str
    target: dict[str, Any]
    parameters: dict[str, Any] = Field(default_factory=dict)


class SubmitAgentResultRequest(BaseModel):
    task_id: str
    status: str = "COMPLETED"
    result_summary: str
    structured_output: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.9
    uncertainty: float = 0.1
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class ReassignAgentRequest(BaseModel):
    new_role: AgentRole


# ------------------------------------------------------------------------------
# Swarms Endpoints (Phase 40)
# ------------------------------------------------------------------------------

@swarms_router.get("", response_model=list[dict[str, Any]])
async def list_swarms(
    limit: int = Query(50, ge=1, le=100),
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """List all active and completed swarm collaboration sessions."""
    sessions = service.list_sessions(limit=limit)
    return [s.model_dump() for s in sessions]


@swarms_router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_swarm(
    req: CreateSwarmRequest,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Launch an autonomous multi-agent swarm collaboration session."""
    session = await service.create_swarm(
        objective=req.objective,
        max_depth=req.max_depth,
        max_agents=req.max_agents,
        resource_budget=req.resource_budget,
        correlation_id=req.correlation_id,
        trace_id=req.trace_id,
    )
    return session.model_dump()


@swarms_router.get("/{swarm_id}", response_model=dict[str, Any])
async def get_swarm(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Get swarm session details and topology."""
    session = service.get_session(swarm_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found.")
    return session.model_dump()


@swarms_router.get("/{swarm_id}/graph", response_model=dict[str, Any])
async def get_swarm_graph(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Get the full topology DAG for a swarm, including agent workers and task dependencies."""
    return service.get_swarm_graph(swarm_id)


@swarms_router.get("/{swarm_id}/agents", response_model=list[dict[str, Any]])
async def get_swarm_agents(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """List all agents operating within a specific swarm session."""
    agents = service.list_agents(session_id=swarm_id)
    return [a.to_dict() for a in agents]


@swarms_router.get("/{swarm_id}/results", response_model=list[dict[str, Any]])
async def get_swarm_results(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """Get all submitted agent results for a swarm session."""
    return service.get_swarm_results(swarm_id)


@swarms_router.get("/{swarm_id}/conflicts", response_model=list[dict[str, Any]])
async def get_swarm_conflicts(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """Get all detected disagreements and minority opinions among agents."""
    return service.get_swarm_conflicts(swarm_id)


@swarms_router.post("/{swarm_id}/pause", response_model=dict[str, Any])
async def pause_swarm(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Pause all running agent workers in a swarm session."""
    try:
        session = service.pause_swarm(swarm_id)
        return session.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found.")


@swarms_router.post("/{swarm_id}/resume", response_model=dict[str, Any])
async def resume_swarm(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Resume execution of paused agent workers in a swarm session."""
    try:
        session = service.resume_swarm(swarm_id)
        return session.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found.")


@swarms_router.post("/{swarm_id}/cancel", response_model=dict[str, Any])
async def cancel_swarm(
    swarm_id: str,
    reason: str = Query("Operator cancelled"),
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Cancel a swarm session and gracefully stop all associated workers."""
    try:
        session = await service.cancel_swarm(swarm_id, reason=reason)
        return session.model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found.")


@swarms_router.post("/{swarm_id}/reconcile", response_model=dict[str, Any])
async def reconcile_swarm(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Reconcile all dangling or stalled agent states within a swarm session."""
    try:
        return service.reconcile_swarm(swarm_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found.")


@swarms_router.post("/{swarm_id}/supervise", response_model=list[dict[str, Any]])
async def supervise_swarm(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """Run supervision checks, stall detection, and deadlock evaluation on a swarm."""
    try:
        stalls = await service.check_supervision(swarm_id)
        return [
            {
                "agent_id": a_id,
                "stall_state": state.value,
            }
            for a_id, state in stalls.items()
        ]
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found.")


@swarms_router.post("/{swarm_id}/synthesize", response_model=dict[str, Any])
async def synthesize_swarm(
    swarm_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Synthesize validated outputs from agents into a final verified collective result."""
    try:
        col_res = await service.synthesize_results(swarm_id)
        return col_res.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------------------
# Agents Endpoints (Phase 40)
# ------------------------------------------------------------------------------

@agents_router.get("", response_model=list[dict[str, Any]])
async def list_agents(
    session_id: str | None = None,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """List all agent worker instances."""
    agents = service.list_agents(session_id=session_id)
    return [a.to_dict() for a in agents]


@agents_router.post("/spawn", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def spawn_agent(
    req: SpawnAgentRequest,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Spawn a new bounded agent worker inside an authorized swarm session."""
    try:
        agent = await service.spawn_agent(
            session_id=req.session_id,
            role=req.role,
            parent_agent_id=req.parent_agent_id,
            capability_scope=req.capability_scope,
            context_scope=req.context_scope,
            resource_scope=req.resource_scope,
        )
        return agent.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@agents_router.get("/{agent_id}", response_model=dict[str, Any])
async def get_agent(
    agent_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Get detailed identity, capability scope, and state of an agent worker."""
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return agent.to_dict()


@agents_router.get("/{agent_id}/tasks", response_model=list[dict[str, Any]])
async def get_agent_tasks(
    agent_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """List tasks assigned to a specific agent worker."""
    tasks = service.get_agent_tasks(agent_id)
    return [
        {
            "task_id": t.task_id,
            "session_id": t.session_id,
            "objective": t.objective,
            "status": t.status,
            "priority": t.priority,
            "dependencies": t.dependencies,
            "required_capabilities": t.required_capabilities,
        }
        for t in tasks
    ]


@agents_router.get("/{agent_id}/messages", response_model=list[dict[str, Any]])
async def get_agent_messages(
    agent_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """Get typed audit log messages sent or received by this agent."""
    msgs = service.get_agent_messages(agent_id)
    return [
        {
            "message_id": m.message_id,
            "sender_id": m.sender_id,
            "recipient_id": m.recipient_id,
            "message_type": m.message_type.value,
            "payload": m.payload,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in msgs
    ]


@agents_router.get("/{agent_id}/health", response_model=dict[str, Any])
async def get_agent_health(
    agent_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Get operational health and lifecycle state of an agent."""
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return {
        "agent_id": agent.agent_id,
        "lifecycle_state": agent.lifecycle_state.value,
        "is_active": agent.is_active,
        "is_terminal": agent.is_terminal,
        "trust_score": agent.trust_score,
        "role": agent.role.value,
    }


@agents_router.get("/{agent_id}/history", response_model=list[dict[str, Any]])
async def get_agent_history(
    agent_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> list[dict[str, Any]]:
    """Get the immutable lifecycle state transition history for an agent."""
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return [
        {
            "from_state": t.from_state.value,
            "to_state": t.to_state.value,
            "timestamp": t.timestamp.isoformat(),
            "reason": t.reason,
        }
        for t in agent.history
    ]


@agents_router.post("/{agent_id}/delegate", response_model=dict[str, Any])
async def delegate_subtask(
    agent_id: str,
    req: DelegateSubtaskRequest,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Delegate a bounded subtask from a parent agent to a specialized child worker."""
    try:
        task = await service.delegate_subtask(
            parent_agent_id=agent_id,
            objective=req.objective,
            role_needed=req.role_needed,
            allowed_capabilities=req.allowed_capabilities,
            dependencies=req.dependencies,
            priority=req.priority,
            expected_output=req.expected_output,
        )
        return {
            "task_id": task.task_id,
            "parent_task_id": task.parent_task_id,
            "assigned_agent_id": task.assigned_agent_id,
            "status": task.status,
            "objective": task.objective,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@agents_router.post("/{agent_id}/action", response_model=dict[str, Any])
async def execute_agent_action(
    agent_id: str,
    req: ExecuteAgentActionRequest,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Execute a real-world side effect via mandatory Task 95 ActionTransaction pipeline."""
    try:
        txn = await service.execute_agent_action(
            agent_id=agent_id,
            action_reference=req.action_reference,
            target=req.target,
            parameters=req.parameters,
        )
        return txn.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@agents_router.post("/{agent_id}/result", response_model=dict[str, Any])
async def submit_agent_result(
    agent_id: str,
    req: SubmitAgentResultRequest,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Submit a structured AgentResult for validation and synthesis."""
    try:
        res = await service.submit_agent_result(
            agent_id=agent_id,
            task_id=req.task_id,
            status=req.status,
            result_summary=req.result_summary,
            structured_output=req.structured_output,
            evidence=req.evidence,
            confidence=req.confidence,
            uncertainty=req.uncertainty,
            assumptions=req.assumptions,
            warnings=req.warnings,
            provenance=req.provenance,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@agents_router.post("/{agent_id}/cancel", response_model=dict[str, Any])
async def cancel_agent(
    agent_id: str,
    reason: str = Query("Operator cancelled"),
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Cancel an individual agent worker."""
    try:
        agent = service.cancel_agent(agent_id, reason=reason)
        return agent.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")


@agents_router.post("/{agent_id}/retry", response_model=dict[str, Any])
async def retry_agent(
    agent_id: str,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Retry a failed agent worker."""
    try:
        agent = service.retry_agent(agent_id)
        return agent.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")


@agents_router.post("/{agent_id}/reassign", response_model=dict[str, Any])
async def reassign_agent(
    agent_id: str,
    req: ReassignAgentRequest,
    service: SwarmOrchestrationService = Depends(get_swarm_orchestration_service),
) -> dict[str, Any]:
    """Reassign an agent to a different operational role."""
    try:
        agent = service.reassign_agent(agent_id, new_role=req.new_role)
        return agent.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

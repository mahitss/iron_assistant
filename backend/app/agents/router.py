"""FastAPI REST API router for Kairo Multi-Agent Collaboration & Collective Intelligence Engine (Task 44)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Annotated, Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.agents.agent import Agent, AgentRole, AgentStatus
from app.agents.budgets import AgentBudget, BudgetExhaustedError
from app.agents.capabilities import AgentCapability, CapabilityRegistry, CapabilityType
from app.agents.collaboration import CollaborationCoordinator
from app.agents.consensus import ConsensusEngine, ConsensusStatus
from app.agents.contracts import AgentContract, ContractExpansionRequest, ContractScope, ContractStatus
from app.agents.delegation import DelegationManager
from app.agents.disagreement import Disagreement, DisagreementResolver, DisagreementStatus
from app.agents.evidence import CollaborativeEvidence, EvidencePool, FactType
from app.agents.isolation import AgentIsolationGuard
from app.agents.messages import AgentMessage, MessageBus, MessageType
from app.agents.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
    ProvenanceRelation,
)
from app.agents.registry import AgentRegistry, create_default_agent_registry
from app.agents.schemas import (
    AgentRegistrationRequest,
    AgentResponse,
    CollaborationSessionCreate,
    CollaborationSessionResponse,
    ConsensusCheckRequest,
    ConsensusResponse,
    ContractCreateRequest,
    ContractExpansionRequestSchema,
    ContractResponse,
    DelegationRequest,
    DelegationResponse,
    DisagreementCreateRequest,
    DisagreementResolveRequest,
    DisagreementResponse,
    EmergencyStopRequest,
    EmergencyStopResponse,
    EvidenceCreateRequest,
    EvidenceResponse,
    MessageResponse,
    SendMessageRequest,
    SynthesisRequest,
    SynthesisResponse,
)
from app.agents.synthesis import CollectiveSynthesisResult, SynthesisEngine, SynthesizedFinding

logger = logging.getLogger("kairo.agents.router")

router = APIRouter(prefix="/collaboration", tags=["Multi-Agent Collaboration Engine"])

# Global coordinator state for active collaboration sessions
_sessions: Dict[str, Dict[str, Any]] = {}
_agents: Dict[str, Agent] = {}
_contracts: Dict[str, AgentContract] = {}
_evidence_pool = EvidencePool()
_message_bus = MessageBus()
_disagreement_resolver = DisagreementResolver(_evidence_pool)
_consensus_engine = ConsensusEngine(_evidence_pool)
_synthesis_engine = SynthesisEngine(_evidence_pool)
_coordinator = CollaborationCoordinator()
_delegation_mgr = DelegationManager()
_isolation_guard = AgentIsolationGuard()
_provenance_graphs: Dict[str, ProvenanceGraph] = {}


def get_current_user_id(x_user_id: Annotated[Optional[str], Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


# ==================================================
# 1. Sessions
# ==================================================

@router.post("/sessions", response_model=CollaborationSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_collaboration_session(
    req: CollaborationSessionCreate,
    user_id: str = Depends(get_current_user_id),
) -> CollaborationSessionResponse:
    """Initialize a multi-agent collaboration session with bounded goal and scope."""
    session_id = f"collab_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()

    session_data = {
        "session_id": session_id,
        "goal": req.goal,
        "user_id": user_id,
        "project_id": req.project_id,
        "scope": req.scope,
        "risk_level": req.risk_level,
        "status": "ACTIVE",
        "agent_ids": [],
        "contract_ids": [],
        "created_at": created_at,
    }
    _sessions[session_id] = session_data

    # Initialize provenance graph
    prov_graph = ProvenanceGraph(session_id=session_id)
    goal_node_id = f"goal_{session_id}"
    prov_graph.add_node(
        node_id=goal_node_id,
        node_type=ProvenanceNodeType.GOAL,
        label=req.goal,
        metadata={"user_id": user_id, "project_id": req.project_id},
        verified=True,
    )
    _provenance_graphs[session_id] = prov_graph

    logger.info("Created collaboration session %s for user=%s goal='%s'", session_id, user_id, req.goal[:60])
    return CollaborationSessionResponse(
        session_id=session_id,
        goal=req.goal,
        user_id=user_id,
        project_id=req.project_id,
        status="ACTIVE",
        agents_count=0,
        created_at=created_at,
    )


@router.get("/sessions/{session_id}")
async def get_collaboration_session(session_id: str) -> Dict[str, Any]:
    """Retrieve detailed state of a collaboration session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")
    return session


# ==================================================
# 2. Agents & Registry
# ==================================================

@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(req: AgentRegistrationRequest) -> AgentResponse:
    """Register a new specialist agent with bounded role, capabilities, and resource budget."""
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"

    # Validate role
    role_enum = AgentRole.RESEARCHER
    try:
        role_enum = AgentRole(req.role.upper())
    except ValueError:
        pass

    agent = Agent(
        agent_id=agent_id,
        name=req.name,
        role=role_enum,
        capabilities=req.capabilities,
        status=AgentStatus.READY,
        model_profile=req.model_profile,
        permissions_scope=req.permissions_scope,
        tool_scope=req.tool_scope,
        resource_budget=AgentBudget(max_tokens=req.max_tokens, max_cost=req.max_cost),
    )
    _agents[agent_id] = agent
    logger.info("Registered agent %s (%s) role=%s", agent.name, agent_id, agent.role.value)

    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        role=agent.role.value,
        capabilities=agent.capabilities,
        status=agent.status.value,
        version=agent.version,
        health=agent.health,
        created_at=agent.created_at.isoformat(),
    )


@router.get("/agents", response_model=List[AgentResponse])
async def list_agents(
    role: Optional[str] = Query(None, description="Filter by role"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
) -> List[AgentResponse]:
    """Discover available specialist agents matching capability or role."""
    results = []
    for ag in _agents.values():
        if role and ag.role.value.upper() != role.upper():
            continue
        if capability and capability not in ag.capabilities:
            continue
        results.append(
            AgentResponse(
                agent_id=ag.agent_id,
                name=ag.name,
                role=ag.role.value,
                capabilities=ag.capabilities,
                status=ag.status.value,
                version=ag.version,
                health=ag.health,
                created_at=ag.created_at.isoformat(),
            )
        )
    return results


# ==================================================
# 3. Agent Contracts & Scope Boundaries
# ==================================================

@router.post("/contracts", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_contract(req: ContractCreateRequest) -> ContractResponse:
    """Issue a strictly bounded AgentContract governing permissions, scope, and budget."""
    agent = _agents.get(req.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {req.agent_id} not found")

    contract_id = f"ct_{uuid.uuid4().hex[:10]}"
    scope = ContractScope(
        resources=req.scope_resources,
        tools=req.scope_tools,
        data=req.scope_data,
        project_id=req.project_id,
    )
    budget = AgentBudget(
        max_tokens=req.token_budget,
        max_tool_calls=req.tool_budget,
        max_cost=req.cost_budget,
    )

    contract = AgentContract(
        contract_id=contract_id,
        agent_id=req.agent_id,
        parent_goal=req.parent_goal,
        assigned_objective=req.assigned_objective,
        scope=scope,
        budget=budget,
    )
    _contracts[contract_id] = contract

    logger.info("Created contract %s for agent %s: '%s'", contract_id, req.agent_id, req.assigned_objective[:60])
    return ContractResponse(
        contract_id=contract.contract_id,
        agent_id=contract.agent_id,
        assigned_objective=contract.assigned_objective,
        status=contract.status.value,
        scope=contract.scope.to_dict(),
        budget=contract.budget.to_dict(),
        created_at=contract.created_at.isoformat(),
    )


@router.post("/contracts/expand", response_model=ContractResponse)
async def expand_contract(req: ContractExpansionRequestSchema) -> ContractResponse:
    """Request and evaluate contract expansion. Agents cannot silently expand scope."""
    contract = _contracts.get(req.contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contract {req.contract_id} not found")

    expansion = ContractExpansionRequest(
        request_id=f"exp_{uuid.uuid4().hex[:8]}",
        contract_id=req.contract_id,
        reason=req.reason,
        requested_resources=req.requested_resources,
        requested_tools=req.requested_tools,
        requested_token_budget=req.requested_token_budget,
    )
    # Supervisor validates expansion
    approved = contract.apply_expansion(expansion)
    if not approved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract expansion rejected by supervisor")

    return ContractResponse(
        contract_id=contract.contract_id,
        agent_id=contract.agent_id,
        assigned_objective=contract.assigned_objective,
        status=contract.status.value,
        scope=contract.scope.to_dict(),
        budget=contract.budget.to_dict(),
        created_at=contract.created_at.isoformat(),
    )


@router.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: str) -> ContractResponse:
    """Retrieve details of an agent contract."""
    contract = _contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contract {contract_id} not found")
    return ContractResponse(
        contract_id=contract.contract_id,
        agent_id=contract.agent_id,
        assigned_objective=contract.assigned_objective,
        status=contract.status.value,
        scope=contract.scope.to_dict(),
        budget=contract.budget.to_dict(),
        created_at=contract.created_at.isoformat(),
    )


# ==================================================
# 4. Delegation & Ownership
# ==================================================

@router.post("/delegations", response_model=DelegationResponse, status_code=status.HTTP_201_CREATED)
async def delegate_subtask(req: DelegationRequest) -> DelegationResponse:
    """Supervisor delegates a subtask to an agent with single ownership and loop detection."""
    # Find or create agent matching role
    agent_id = req.target_agent_id
    if not agent_id:
        matching = [a for a in _agents.values() if a.role.value.upper() == req.agent_role.upper()]
        if matching:
            agent_id = matching[0].agent_id
        else:
            # Register on-demand specialist agent
            new_req = AgentRegistrationRequest(
                name=f"{req.agent_role.title()} Specialist",
                role=req.agent_role,
                capabilities=[req.agent_role.lower()],
            )
            created_ag = await register_agent(new_req)
            agent_id = created_ag.agent_id

    # Create contract for delegated subtask
    contract_req = ContractCreateRequest(
        agent_id=agent_id,
        parent_goal=req.parent_goal,
        assigned_objective=req.assigned_objective,
        scope_tools=req.required_tools,
    )
    contract_resp = await create_agent_contract(contract_req)

    # Record delegation with single ownership enforcement
    try:
        node = _delegation_mgr.delegate(
            parent_task_id=req.session_id,
            subtask_id=req.subtask_id,
            objective=req.assigned_objective,
            agent_id=agent_id,
            contract_id=contract_resp.contract_id,
            role=req.agent_role,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    # Link in provenance graph
    if req.session_id in _provenance_graphs:
        pg = _provenance_graphs[req.session_id]
        subtask_node_id = f"subtask_{req.subtask_id}"
        agent_node_id = f"agent_{agent_id}"
        contract_node_id = f"contract_{contract_resp.contract_id}"

        pg.add_node(subtask_node_id, ProvenanceNodeType.SUBTASK, req.assigned_objective)
        pg.add_node(agent_node_id, ProvenanceNodeType.AGENT, req.agent_role)
        pg.add_node(contract_node_id, ProvenanceNodeType.CONTRACT, contract_resp.contract_id)

        pg.add_edge(f"goal_{req.session_id}", subtask_node_id, ProvenanceRelation.DECOMPOSED_INTO)
        pg.add_edge(subtask_node_id, agent_node_id, ProvenanceRelation.DELEGATED_TO)
        pg.add_edge(agent_node_id, contract_node_id, ProvenanceRelation.BOUND_BY)

    return DelegationResponse(
        delegation_id=node.delegation_id,
        contract_id=contract_resp.contract_id,
        subtask_id=req.subtask_id,
        agent_id=agent_id,
        role=req.agent_role,
        status="DELEGATED",
    )


# ==================================================
# 5. Scoped Inter-Agent Messaging
# ==================================================

@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_agent_message(req: SendMessageRequest) -> MessageResponse:
    """Send an authenticated, scoped inter-agent message with deduplication."""
    try:
        msg_type = MessageType(req.message_type.upper())
    except ValueError:
        msg_type = MessageType.TASK

    msg = AgentMessage(
        message_id=f"msg_{uuid.uuid4().hex[:10]}",
        sender=req.sender_id,
        recipient=req.recipient_id,
        type=msg_type,
        payload=req.payload,
        evidence_refs=req.evidence_refs,
        contract_id=req.contract_id,
        priority=req.priority,
    )

    try:
        _message_bus.send(msg)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return MessageResponse(
        message_id=msg.message_id,
        sender_id=msg.sender,
        recipient_id=msg.recipient,
        message_type=msg.type.value,
        status="DELIVERED",
        timestamp=msg.timestamp.isoformat(),
    )


@router.get("/messages/{recipient_id}", response_model=List[MessageResponse])
async def get_agent_messages(recipient_id: str) -> List[MessageResponse]:
    """Retrieve all pending messages for an agent."""
    msgs = _message_bus.get_messages(recipient_id)
    return [
        MessageResponse(
            message_id=m.message_id,
            sender_id=m.sender,
            recipient_id=m.recipient,
            message_type=m.type.value,
            status="PENDING",
            timestamp=m.timestamp.isoformat(),
        )
        for m in msgs
    ]


# ==================================================
# 6. Evidence Sharing & Provenance
# ==================================================

@router.post("/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def submit_evidence(req: EvidenceCreateRequest) -> EvidenceResponse:
    """Publish a structured evidence item with provenance and classification (FACT/INFERENCE/HYPOTHESIS)."""
    try:
        fact_type = FactType(req.fact_type.upper())
    except ValueError:
        fact_type = FactType.INFERENCE

    evidence = CollaborativeEvidence(
        evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
        producer_agent_id=req.producer_agent_id,
        contract_id=req.contract_id,
        fact_type=fact_type,
        claim=req.claim,
        sources=req.sources,
        model_id=req.model_id,
        is_verified=req.is_verified,
        verification_source=req.verification_source,
    )
    _evidence_pool.add(evidence)

    # Link in session provenance graph if present
    if req.session_id in _provenance_graphs:
        pg = _provenance_graphs[req.session_id]
        ev_node_id = f"ev_{evidence.evidence_id}"
        pg.add_node(
            ev_node_id,
            ProvenanceNodeType.EVIDENCE,
            req.claim[:40],
            metadata={"fact_type": fact_type.value, "producer": req.producer_agent_id},
            verified=req.is_verified,
        )
        agent_node_id = f"agent_{req.producer_agent_id}"
        if agent_node_id in pg.nodes:
            pg.add_edge(agent_node_id, ev_node_id, ProvenanceRelation.PRODUCED)

    logger.info("Submitted evidence %s [%s] by agent %s: verified=%s", evidence.evidence_id, fact_type.value, req.producer_agent_id, evidence.is_verified)
    return EvidenceResponse(
        evidence_id=evidence.evidence_id,
        fact_type=evidence.fact_type.value,
        claim=evidence.claim,
        is_verified=evidence.is_verified,
        producer_agent_id=evidence.producer_agent_id,
        timestamp=evidence.timestamp.isoformat(),
    )


@router.get("/evidence", response_model=List[EvidenceResponse])
async def list_evidence() -> List[EvidenceResponse]:
    """Query evidence pool."""
    all_ev = _evidence_pool.get_all()
    return [
        EvidenceResponse(
            evidence_id=e.evidence_id,
            fact_type=e.fact_type.value,
            claim=e.claim,
            is_verified=e.is_verified,
            producer_agent_id=e.producer_agent_id,
            timestamp=e.timestamp.isoformat(),
        )
        for e in all_ev
    ]


# ==================================================
# 7. Disagreements & Blind Review
# ==================================================

@router.post("/disagreements", response_model=DisagreementResponse, status_code=status.HTTP_201_CREATED)
async def create_disagreement(req: DisagreementCreateRequest) -> DisagreementResponse:
    """Register an active disagreement between collaborating agents."""
    disagreement_id = f"disag_{uuid.uuid4().hex[:8]}"

    claims = {
        req.claimant_a: req.claim_a,
        req.claimant_b: req.claim_b,
    }
    evidence_map = {
        req.claimant_a: req.evidence_ids_a,
        req.claimant_b: req.evidence_ids_b,
    }

    disagreement = Disagreement(
        disagreement_id=disagreement_id,
        subject=req.subject,
        participants=[req.claimant_a, req.claimant_b],
        claims=claims,
        evidence=evidence_map,
        severity=req.severity,
        status=DisagreementStatus.OPEN,
    )
    _disagreement_resolver.register(disagreement)

    logger.warning("Disagreement recorded between %s and %s on '%s'", req.claimant_a, req.claimant_b, req.subject)
    return DisagreementResponse(
        disagreement_id=disagreement.disagreement_id,
        subject=disagreement.subject,
        severity=disagreement.severity,
        status=disagreement.status.value,
        participants=disagreement.participants,
    )


@router.post("/disagreements/resolve", response_model=DisagreementResponse)
async def resolve_disagreement(req: DisagreementResolveRequest) -> DisagreementResponse:
    """Resolve a disagreement using evidence-first analysis (verified empirical evidence wins)."""
    disagreement = _disagreement_resolver.get(req.disagreement_id)
    if not disagreement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Disagreement {req.disagreement_id} not found")

    res = _disagreement_resolver.resolve(disagreement)
    return DisagreementResponse(
        disagreement_id=res.disagreement_id,
        subject=res.subject,
        severity=res.severity,
        status=res.status.value,
        participants=res.participants,
        resolution_summary=res.resolution,
    )


# ==================================================
# 8. Consensus & Collective Synthesis
# ==================================================

@router.post("/consensus", response_model=ConsensusResponse)
async def check_consensus(req: ConsensusCheckRequest) -> ConsensusResponse:
    """Evaluate consensus on a topic. 1 verified evidence strictly defeats 3 unverified claims."""
    report = _consensus_engine.evaluate(topic=req.topic, evidence_ids=req.evidence_ids)
    return ConsensusResponse(
        topic=report.topic,
        status=report.status.value,
        claim_counts=report.claim_counts,
        verified_claim=report.verified_claim,
        total_evidence=report.total_evidence,
    )


@router.post("/synthesis", response_model=SynthesisResponse)
async def synthesize_findings(req: SynthesisRequest) -> SynthesisResponse:
    """Synthesize collective findings into a unified, evidence-linked result."""
    result = _synthesis_engine.synthesize(
        session_id=req.session_id,
        goal=req.goal,
        agent_result_ids=req.agent_result_ids,
    )

    # Link in provenance graph
    if req.session_id in _provenance_graphs:
        pg = _provenance_graphs[req.session_id]
        synth_node_id = f"synth_{result.synthesis_id}"
        pg.add_node(
            synth_node_id,
            ProvenanceNodeType.SYNTHESIS,
            f"Synthesis: {req.goal[:40]}",
            metadata={"findings_count": len(result.findings)},
            verified=result.is_verified,
        )
        pg.add_edge(f"goal_{req.session_id}", synth_node_id, ProvenanceRelation.CONTRIBUTED_TO)

    return SynthesisResponse(
        synthesis_id=result.synthesis_id,
        goal=result.goal,
        findings_count=len(result.findings),
        unresolved_conflicts_count=len(result.unresolved_conflicts),
        recommendation=result.recommendation,
        is_verified=result.is_verified,
    )


# ==================================================
# 9. Emergency Stop & Provenance
# ==================================================

@router.post("/emergency-stop", response_model=EmergencyStopResponse)
async def trigger_emergency_stop(req: EmergencyStopRequest) -> EmergencyStopResponse:
    """Halt all active agents and contracts in a session immediately."""
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {req.session_id} not found")

    session["status"] = "EMERGENCY_STOPPED"
    session["stopped_reason"] = req.reason

    # Cancel all active delegations and contracts for this session
    stopped_count = _delegation_mgr.cancel_session(req.session_id)
    logger.critical("EMERGENCY STOP executed on session %s: %s (stopped %d subtasks)", req.session_id, req.reason, stopped_count)

    return EmergencyStopResponse(
        session_id=req.session_id,
        stopped=True,
        reason=req.reason,
        stopped_agents_count=stopped_count,
    )


@router.get("/provenance/{session_id}")
async def get_session_provenance(session_id: str) -> Dict[str, Any]:
    """Retrieve full causal provenance DAG for a collaboration session."""
    pg = _provenance_graphs.get(session_id)
    if not pg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provenance graph for session {session_id} not found")
    return pg.to_dict()

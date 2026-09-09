"""Agents module for Kairo AI assistant.

Supports single-agent operations, multi-agent execution, contracts, evidence-based consensus,
disagreement resolution, and collective intelligence.
"""

from .core import (
    KAIRO_SYSTEM_PROMPT,
    AgentResponse,
    KairoAgent,
    ToolActivity,
    get_default_agent,
)
from .executor import MultiAgentExecutor
from .limits import AgentBudgetTracker
from .planner import AgentPlanner, PlanValidator
from .policies import AgentSecurityPolicy, AgentSecurityViolation
from .registry import AgentRegistry, create_default_agent_registry
from .runtime import AgentRuntime
from .schemas import (
    AgentCitation,
    AgentContext,
    AgentDefinition,
    AgentEvidence,
    AgentPlan,
    AgentResult,
    AgentStreamingEvent,
    AgentTaskCancelResponse,
    AgentTaskRead,
    AgentTaskSpec,
    CollaborationSessionCreate,
    CollaborationSessionResponse,
    ContractCreateRequest,
    ContractExpansionRequestSchema,
    ContractResponse,
    DelegationRequest,
    DelegationResponse,
    SendMessageRequest,
    MessageResponse,
    EvidenceCreateRequest,
    EvidenceResponse,
    DisagreementCreateRequest,
    DisagreementResolveRequest,
    DisagreementResponse,
    ConsensusCheckRequest,
    ConsensusResponse,
    SynthesisRequest,
    SynthesisResponse,
    EmergencyStopRequest,
    EmergencyStopResponse,
)
from .state import AgentTaskStatus, AgentType, EvidenceType
from .supervisor import SupervisorAgent

# Task 44 domain imports
from .agent import Agent, AgentRole, AgentStatus
from .capabilities import AgentCapability, CapabilityRegistry, CapabilityType
from .contracts import AgentContract, ContractScope, ContractStatus, ContractExpansionRequest
from .delegation import DelegationManager, DelegationTree, DelegationNode
from .collaboration import CollaborationCoordinator, ConflictResolutionStrategy
from .messages import AgentMessage, MessageType, MessageBus
from .workspace import AgentWorkspace, SharedTeamWorkspace, CollaborativeArtifact
from .evidence import CollaborativeEvidence, EvidencePool, FactType
from .disagreement import Disagreement, DisagreementStatus, DisagreementResolver
from .consensus import ConsensusEngine, ConsensusStatus, ConsensusReport
from .synthesis import SynthesisEngine, CollectiveSynthesisResult, SynthesizedFinding
from .routing import SpecialistRouter
from .budgets import AgentBudget, BudgetExhaustedError
from .isolation import AgentIsolationGuard
from .lifecycle import AgentLifecycleState, AgentLifecycleManager
from .health import AgentHealthState, AgentHealthRecord, AgentHealthMonitor
from .recovery import AgentRecoveryManager, AgentCheckpoint
from .evaluation import TeamEvaluator
from .provenance import (
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceEdge,
    ProvenanceNodeType,
    ProvenanceRelation,
)

__all__ = [
    "KAIRO_SYSTEM_PROMPT",
    "AgentBudgetTracker",
    "AgentCitation",
    "AgentContext",
    "AgentDefinition",
    "AgentEvidence",
    "AgentPlan",
    "AgentPlanner",
    "AgentRegistry",
    "AgentResponse",
    "AgentResult",
    "AgentRuntime",
    "AgentSecurityPolicy",
    "AgentSecurityViolation",
    "AgentStreamingEvent",
    "AgentTaskCancelResponse",
    "AgentTaskRead",
    "AgentTaskSpec",
    "AgentTaskStatus",
    "AgentType",
    "EvidenceType",
    "KairoAgent",
    "MultiAgentExecutor",
    "PlanValidator",
    "SupervisorAgent",
    "ToolActivity",
    "create_default_agent_registry",
    "get_default_agent",
    # Task 44
    "Agent",
    "AgentRole",
    "AgentStatus",
    "AgentCapability",
    "CapabilityRegistry",
    "CapabilityType",
    "AgentContract",
    "ContractScope",
    "ContractStatus",
    "ContractExpansionRequest",
    "DelegationManager",
    "DelegationTree",
    "DelegationNode",
    "CollaborationCoordinator",
    "ConflictResolutionStrategy",
    "AgentMessage",
    "MessageType",
    "MessageBus",
    "AgentWorkspace",
    "SharedTeamWorkspace",
    "CollaborativeArtifact",
    "CollaborativeEvidence",
    "EvidencePool",
    "FactType",
    "Disagreement",
    "DisagreementStatus",
    "DisagreementResolver",
    "ConsensusEngine",
    "ConsensusStatus",
    "ConsensusReport",
    "SynthesisEngine",
    "CollectiveSynthesisResult",
    "SynthesizedFinding",
    "SpecialistRouter",
    "AgentBudget",
    "BudgetExhaustedError",
    "AgentIsolationGuard",
    "AgentLifecycleState",
    "AgentLifecycleManager",
    "AgentHealthState",
    "AgentHealthRecord",
    "AgentHealthMonitor",
    "AgentRecoveryManager",
    "AgentCheckpoint",
    "TeamEvaluator",
    "ProvenanceGraph",
    "ProvenanceNode",
    "ProvenanceEdge",
    "ProvenanceNodeType",
    "ProvenanceRelation",
    "CollaborationSessionCreate",
    "CollaborationSessionResponse",
    "ContractCreateRequest",
    "ContractExpansionRequestSchema",
    "ContractResponse",
    "DelegationRequest",
    "DelegationResponse",
    "SendMessageRequest",
    "MessageResponse",
    "EvidenceCreateRequest",
    "EvidenceResponse",
    "DisagreementCreateRequest",
    "DisagreementResolveRequest",
    "DisagreementResponse",
    "ConsensusCheckRequest",
    "ConsensusResponse",
    "SynthesisRequest",
    "SynthesisResponse",
    "EmergencyStopRequest",
    "EmergencyStopResponse",
]

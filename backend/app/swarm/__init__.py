"""Kairo Collective Intelligence & Swarm Reasoning Engine (Task 64)."""

from app.swarm.agents import SwarmAgentRegistry, swarm_agent_registry
from app.swarm.analysis import IndependentAnalysisCoordinator
from app.swarm.audit import AuditRecord, SwarmAuditor, swarm_auditor
from app.swarm.calibration import ConfidenceCalibrator
from app.swarm.consensus import ConsensusEngine
from app.swarm.debate import DebateEngine
from app.swarm.decomposition import TaskDecomposer
from app.swarm.disagreement import DisagreementDetector
from app.swarm.engine import SwarmReasoningEngine, swarm_engine
from app.swarm.privacy import SwarmPrivacyManager, swarm_privacy_manager
from app.swarm.recovery import FailureRecoveryManager
from app.swarm.review import PeerReviewEngine
from app.swarm.router import router
from app.swarm.safety import (
    SwarmExecutionBoundaryError,
    SwarmSafetyError,
    SwarmSpawnLimitExceededError,
    block_direct_swarm_action,
    sanitize_agent_message,
    sanitize_swarm_directive,
    scrub_swarm_secrets,
)
from app.swarm.schemas import (
    AgentAssertion,
    AgentHealthState,
    AgentResult,
    CollectiveObjective,
    CollectiveResult,
    ConsensusOutcome,
    ConsensusResult,
    DebateRound,
    DebateSession,
    DebateStatus,
    DebateTurn,
    DisagreementRecord,
    DisagreementType,
    EpistemicType,
    EvidenceStrength,
    MinorityReport,
    PeerReview,
    SwarmActionRequest,
    SwarmAgentSpec,
    SwarmCreateRequest,
    SwarmSession,
    SwarmStatus,
    SwarmTaskNode,
    SwarmTopology,
    TaskDAG,
    TaskStatus,
)
from app.swarm.selection import AgentSelector
from app.swarm.service import SwarmService, swarm_service
from app.swarm.synthesis import CollectiveSynthesizer

__all__ = [
    "AgentAssertion",
    "AgentHealthState",
    "AgentResult",
    "AgentSelector",
    "AuditRecord",
    "CollectiveObjective",
    "CollectiveResult",
    "CollectiveSynthesizer",
    "ConfidenceCalibrator",
    "ConsensusEngine",
    "ConsensusOutcome",
    "ConsensusResult",
    "DebateEngine",
    "DebateRound",
    "DebateSession",
    "DebateStatus",
    "DebateTurn",
    "DisagreementDetector",
    "DisagreementRecord",
    "DisagreementType",
    "EpistemicType",
    "EvidenceStrength",
    "FailureRecoveryManager",
    "IndependentAnalysisCoordinator",
    "MinorityReport",
    "PeerReview",
    "PeerReviewEngine",
    "SwarmActionRequest",
    "SwarmAgentRegistry",
    "SwarmAgentSpec",
    "SwarmAuditor",
    "SwarmCreateRequest",
    "SwarmExecutionBoundaryError",
    "SwarmPrivacyManager",
    "SwarmReasoningEngine",
    "SwarmSafetyError",
    "SwarmService",
    "SwarmSession",
    "SwarmSpawnLimitExceededError",
    "SwarmStatus",
    "SwarmTaskNode",
    "SwarmTopology",
    "TaskDAG",
    "TaskDecomposer",
    "TaskStatus",
    "block_direct_swarm_action",
    "router",
    "sanitize_agent_message",
    "sanitize_swarm_directive",
    "scrub_swarm_secrets",
    "swarm_agent_registry",
    "swarm_auditor",
    "swarm_engine",
    "swarm_privacy_manager",
    "swarm_service",
]

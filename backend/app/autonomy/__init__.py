"""Kairo Autonomous Execution, Long-Horizon Agency, and Goal Completion Engine (Task 45)."""

from app.autonomy.budgets import AutonomousBudget, BudgetExhaustedError
from app.autonomy.checkpoints import AutonomousCheckpoint, CheckpointManager, CorruptCheckpointError
from app.autonomy.controller import RunController, StepExecutionResult, VerificationFailedError
from app.autonomy.deadlines import DeadlineExhaustedError, DeadlineTracker
from app.autonomy.engine import (
    AutonomousExecutionEngine,
    AutonomousRun,
    CompletionRecord,
    FalseCompletionError,
)
from app.autonomy.escalation import EscalationManager, EscalationReason, EscalationRequest
from app.autonomy.execution import (
    AutonomousExecutionLoop,
    DuplicateExecutionError,
    ExecutionResourceManager,
    IdempotencyRecord,
    OutcomeCertainty,
    ResourceLockConflictError,
    SideEffectRetryViolationError,
)
from app.autonomy.goals import AutonomousGoal, GoalDriftError, GoalManager
from app.autonomy.heartbeat import HeartbeatTracker
from app.autonomy.interruption import InterruptionHandler, InterruptionType
from app.autonomy.leases import ExecutionLease, ExecutionLeaseManager, SplitBrainConflictError
from app.autonomy.lifecycle import (
    InvalidStateTransitionError,
    RunLifecycleManager,
    WaitConditionType,
    WaitStateRecord,
)
from app.autonomy.persistence import AutonomyPersistenceManager, JournalTamperingError
from app.autonomy.policies import AutonomyPolicyEngine, DomainWorkflowType, PolicyDeniedError
from app.autonomy.progress import NoProgressLoopError, ProgressSnapshot, ProgressTracker
from app.autonomy.recovery import (
    RecoveryDecision,
    RecoveryEngine,
    RecoveryRevalidationError,
    StateRevalidationResult,
)
from app.autonomy.replanning import PlanDiff, ReplanningManager
from app.autonomy.router import router
from app.autonomy.safety import (
    ActionClassification,
    AutonomyLevel,
    AutonomySafetyGuard,
    SafetyViolationError,
)
from app.autonomy.scheduler import AutonomousScheduler, CorrelatedEvent, EventAuthenticityError
from app.autonomy.sessions import (
    AutonomousScope,
    AutonomousSession,
    ScopeViolationError,
    TenantIsolationError,
)
from app.autonomy.state import (
    VALID_STATE_TRANSITIONS,
    AutonomousRunState,
    can_transition,
)
from app.autonomy.watchdog import AutonomyWatchdog, WatchdogInspectionResult

__all__ = [
    "AutonomousExecutionEngine",
    "AutonomousRun",
    "AutonomousGoal",
    "AutonomousCheckpoint",
    "CompletionRecord",
    "AutonomousRunState",
    "AutonomyLevel",
    "ActionClassification",
    "VALID_STATE_TRANSITIONS",
    "can_transition",
    "GoalManager",
    "GoalDriftError",
    "CheckpointManager",
    "CorruptCheckpointError",
    "AutonomousBudget",
    "BudgetExhaustedError",
    "DeadlineTracker",
    "DeadlineExhaustedError",
    "ExecutionLease",
    "ExecutionLeaseManager",
    "SplitBrainConflictError",
    "HeartbeatTracker",
    "AutonomyWatchdog",
    "WatchdogInspectionResult",
    "RecoveryEngine",
    "RecoveryDecision",
    "StateRevalidationResult",
    "RecoveryRevalidationError",
    "ReplanningManager",
    "PlanDiff",
    "InterruptionHandler",
    "InterruptionType",
    "AutonomySafetyGuard",
    "SafetyViolationError",
    "ProgressTracker",
    "ProgressSnapshot",
    "NoProgressLoopError",
    "EscalationManager",
    "EscalationRequest",
    "EscalationReason",
    "RunController",
    "StepExecutionResult",
    "VerificationFailedError",
    "FalseCompletionError",
    "RunLifecycleManager",
    "WaitConditionType",
    "WaitStateRecord",
    "InvalidStateTransitionError",
    "AutonomousScheduler",
    "CorrelatedEvent",
    "EventAuthenticityError",
    "AutonomousExecutionLoop",
    "ExecutionResourceManager",
    "IdempotencyRecord",
    "OutcomeCertainty",
    "DuplicateExecutionError",
    "ResourceLockConflictError",
    "SideEffectRetryViolationError",
    "AutonomyPolicyEngine",
    "DomainWorkflowType",
    "PolicyDeniedError",
    "AutonomyPersistenceManager",
    "JournalTamperingError",
    "AutonomousSession",
    "AutonomousScope",
    "ScopeViolationError",
    "TenantIsolationError",
    "router",
]

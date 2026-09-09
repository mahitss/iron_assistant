"""Kairo Autonomous Task Engine Subsystem (Task 31)."""

from app.tasks.budget import BudgetExceededError, TaskBudgetEnforcer
from app.tasks.cancellation import (
    CancellationToken,
    EmergencyStopActiveError,
    TaskCancelledError,
    get_cancellation_manager,
)
from app.tasks.checkpoint import CheckpointService
from app.tasks.dependencies import (
    CircularDependencyError,
    DependencyResolver,
    MissingDependencyError,
)
from app.tasks.engine import AutonomousTaskEngine
from app.tasks.executor import StepExecutionError, StepExecutor
from app.tasks.models import (
    TaskCheckpointModel,
    TaskLockModel,
    TaskModel,
    TaskPlanModel,
    TaskStepModel,
)
from app.tasks.planner import InvalidPlanError, TaskPlanner
from app.tasks.policies import TaskPolicyEngine, TaskPolicyViolationError
from app.tasks.recovery import TaskRecoveryService
from app.tasks.registry import get_task_engine, get_task_engine_registry
from app.tasks.replanner import LoopDetectedError, TaskReplanner
from app.tasks.resolver import TaskContextResolver
from app.tasks.scheduler import (
    ResourceLockConflictError,
    TaskScheduler,
    get_task_scheduler,
)
from app.tasks.schemas import (
    ApprovalActionRequest,
    AutonomyLevel,
    FailureClassification,
    ResourceType,
    StepStatus,
    TaskApprovalRequest,
    TaskBudget,
    TaskCheckpointSchema,
    TaskCreateRequest,
    TaskPlanSchema,
    TaskPriority,
    TaskResource,
    TaskResponse,
    TaskResultSummary,
    TaskRiskLevel,
    TaskStatus,
    TaskStepResponse,
    TaskStepSchema,
    UserPromptResponse,
    VerificationCriterion,
)
from app.tasks.state import (
    InvalidStateTransitionError,
    StepStateMachine,
    TaskStateMachine,
)
from app.tasks.verifier import TaskVerifier, VerificationError

__all__ = [
    "AutonomousTaskEngine",
    "TaskPlanner",
    "StepExecutor",
    "TaskReplanner",
    "TaskVerifier",
    "TaskScheduler",
    "TaskPolicyEngine",
    "TaskBudgetEnforcer",
    "DependencyResolver",
    "CheckpointService",
    "TaskRecoveryService",
    "TaskContextResolver",
    "TaskStateMachine",
    "StepStateMachine",
    "CancellationToken",
    "get_cancellation_manager",
    "get_task_scheduler",
    "get_task_engine",
    "get_task_engine_registry",
    # Models
    "TaskModel",
    "TaskPlanModel",
    "TaskStepModel",
    "TaskCheckpointModel",
    "TaskLockModel",
    # Schemas
    "TaskStatus",
    "StepStatus",
    "TaskPriority",
    "TaskRiskLevel",
    "AutonomyLevel",
    "FailureClassification",
    "ResourceType",
    "TaskBudget",
    "TaskResource",
    "VerificationCriterion",
    "TaskStepSchema",
    "TaskPlanSchema",
    "TaskResultSummary",
    "TaskCreateRequest",
    "TaskResponse",
    "TaskStepResponse",
    "TaskApprovalRequest",
    "ApprovalActionRequest",
    "UserPromptResponse",
    "TaskCheckpointSchema",
    # Exceptions
    "InvalidStateTransitionError",
    "CircularDependencyError",
    "MissingDependencyError",
    "BudgetExceededError",
    "TaskCancelledError",
    "EmergencyStopActiveError",
    "TaskPolicyViolationError",
    "LoopDetectedError",
    "InvalidPlanError",
    "StepExecutionError",
    "VerificationError",
    "ResourceLockConflictError",
]

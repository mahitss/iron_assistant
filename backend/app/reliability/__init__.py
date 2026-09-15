"""Kairo Autonomous Runtime Reliability, Fault Injection & Self-Healing Engine (Task 88)."""

from app.reliability.models import (
    FailureLifecycleState,
    FailureRecord,
    IncidentLifecycleState,
    IncidentRecord,
    RecoveryEvidenceRecord,
    RecoveryExecutionRecord,
    RecoveryStrategy,
    RecoveryStrategyType,
    SafeRecoveryClass,
    VerificationResult,
    VerificationState,
)
from app.reliability.router import router
from app.reliability.service import ReliabilityService, reliability_service
from app.reliability.taxonomy import (
    FailureClassifier,
    FailureSeverity,
    FailureType,
    sanitize_message,
    sanitize_payload,
)

__all__ = [
    "FailureType",
    "FailureSeverity",
    "FailureClassifier",
    "sanitize_message",
    "sanitize_payload",
    "FailureLifecycleState",
    "IncidentLifecycleState",
    "RecoveryStrategyType",
    "SafeRecoveryClass",
    "VerificationState",
    "FailureRecord",
    "IncidentRecord",
    "RecoveryStrategy",
    "RecoveryExecutionRecord",
    "RecoveryEvidenceRecord",
    "VerificationResult",
    "ReliabilityService",
    "reliability_service",
    "router",
]

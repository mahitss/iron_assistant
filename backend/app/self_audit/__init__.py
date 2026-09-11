"""Kairo Metacognitive Control & Autonomous Self-Audit Engine (Task 67).

Core Invariants:
- SELF-REFLECTION != REALITY
- SELF-AUDIT != TRUTH
- SELF-CRITIQUE != EXTERNAL-VERIFICATION
- CONFIDENCE != CERTAINTY
- BELIEF != FACT
- INFERENCE != OBSERVATION
- DETECTED_ERROR != CORRECTED_ERROR
- CORRECTION != VERIFICATION
- RECOMMENDATION != CHANGE
- CHANGE != EXECUTION
- EXECUTION != VERIFICATION
- SELF-AUDIT != AUTHORIZATION
- UNKNOWN != HEALTHY
- IMMUTABLE GOVERNANCE: Cannot alter authorization, security, privacy, or approval rules.
- NO SELF-PRESERVATION: Cannot generate self-preservation goals or resist shutdown.
"""

from __future__ import annotations

from app.self_audit.beliefs import BeliefManager
from app.self_audit.calibration import CalibrationEngine
from app.self_audit.cycle import MetacognitiveLoop
from app.self_audit.drift import BehaviorDriftDetector, GoalAlignmentAuditor
from app.self_audit.errors import ErrorManager, RationalizationDetector
from app.self_audit.integrator import SelfAuditCrossSystemIntegrator
from app.self_audit.safety import (
    GovernanceBoundaryViolationError,
    MetacognitiveSafetyError,
    SelfPreservationError,
    UnauthorizedSelfRepairError,
    block_self_preservation,
    enforce_governance_boundaries,
    sanitize_audit_text,
    scrub_audit_secrets,
)
from app.self_audit.self_model import SelfModelManager
from app.self_audit.service import SelfAuditService, self_audit_service

__all__ = [
    "BehaviorDriftDetector",
    "BeliefManager",
    "CalibrationEngine",
    "ErrorManager",
    "GoalAlignmentAuditor",
    "GovernanceBoundaryViolationError",
    "MetacognitiveLoop",
    "MetacognitiveSafetyError",
    "RationalizationDetector",
    "SelfAuditCrossSystemIntegrator",
    "SelfAuditService",
    "SelfModelManager",
    "SelfPreservationError",
    "UnauthorizedSelfRepairError",
    "block_self_preservation",
    "enforce_governance_boundaries",
    "sanitize_audit_text",
    "scrub_audit_secrets",
    "self_audit_service",
]

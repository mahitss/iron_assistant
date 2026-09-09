"""Kairo Truth, Verification, Self-Correction & Confidence Engine (Task 42)."""

from app.verification.assertions import (
    VerificationContract,
    VerificationResult,
    VerificationStatus,
)
from app.verification.claims import Claim, ClaimType, TruthStatus
from app.verification.confidence import (
    ConfidenceCalibrator,
    ConfidenceLevel,
    ConfidenceReport,
    UncertaintyState,
)
from app.verification.contradictions import (
    Contradiction,
    ContradictionEngine,
    ContradictionType,
)
from app.verification.evaluators import (
    CitationValidationResult,
    CitationValidator,
    TestQualityAssessment,
    TestQualityEvaluator,
)
from app.verification.evidence import Evidence, EvidenceType
from app.verification.freshness import FreshnessEvaluation, FreshnessTracker
from app.verification.invariants import (
    InvariantEngine,
    InvariantRule,
    InvariantViolation,
)
from app.verification.provenance import ProvenanceChain, ProvenanceStep
from app.verification.reconciliation import ReconciliationAction, StateReconciler
from app.verification.router import router as verification_router
from app.verification.self_correction import (
    Correction,
    SelfCorrectionEngine,
)
from app.verification.service import VerificationService
from app.verification.strategies import (
    VerificationStrategyExecutor,
    VerificationStrategyType,
)
from app.verification.triangulation import (
    SourceTriangulator,
    TriangulationResult,
)
from app.verification.validators import (
    CodeChangeValidator,
    DatabaseMigrationValidator,
    DeploymentValidator,
    FileWriteValidator,
)

__all__ = [
    "Claim",
    "ClaimType",
    "TruthStatus",
    "Evidence",
    "EvidenceType",
    "ProvenanceChain",
    "ProvenanceStep",
    "VerificationContract",
    "VerificationResult",
    "VerificationStatus",
    "InvariantEngine",
    "InvariantRule",
    "InvariantViolation",
    "ContradictionEngine",
    "Contradiction",
    "ContradictionType",
    "SourceTriangulator",
    "TriangulationResult",
    "FreshnessTracker",
    "FreshnessEvaluation",
    "ConfidenceCalibrator",
    "ConfidenceLevel",
    "ConfidenceReport",
    "UncertaintyState",
    "SelfCorrectionEngine",
    "Correction",
    "CitationValidator",
    "CitationValidationResult",
    "TestQualityEvaluator",
    "TestQualityAssessment",
    "StateReconciler",
    "ReconciliationAction",
    "VerificationStrategyExecutor",
    "VerificationStrategyType",
    "DeploymentValidator",
    "CodeChangeValidator",
    "FileWriteValidator",
    "DatabaseMigrationValidator",
    "VerificationService",
    "verification_router",
]

"""Central Verification Service for Kairo (Task 42).

Coordinates Claims, Evidence, Invariant Rules, Contradiction Detection,
Source Triangulation, Freshness Decay, Calibrated Confidence, and Self-Correction.
Ensures zero unverified assertions, read-only safety, secret redaction, and strict
separation between model belief, tool reports, and independently verified truth.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.security.redaction import ArgumentSanitizer
from app.verification.assertions import VerificationContract, VerificationResult, VerificationStatus
from app.verification.claims import Claim, ClaimType, TruthStatus
from app.verification.confidence import ConfidenceCalibrator, ConfidenceLevel, ConfidenceReport
from app.verification.contradictions import Contradiction, ContradictionEngine
from app.verification.evaluators import CitationValidationResult, CitationValidator, TestQualityAssessment, TestQualityEvaluator
from app.verification.evidence import Evidence, EvidenceType
from app.verification.freshness import FreshnessEvaluation, FreshnessTracker
from app.verification.invariants import InvariantEngine, InvariantRule, InvariantViolation
from app.verification.provenance import ProvenanceChain
from app.verification.reconciliation import ReconciliationAction, StateReconciler
from app.verification.self_correction import Correction, SelfCorrectionEngine
from app.verification.strategies import VerificationStrategyExecutor, VerificationStrategyType
from app.verification.triangulation import SourceTriangulator, TriangulationResult
from app.verification.validators import (
    CodeChangeValidator,
    DatabaseMigrationValidator,
    DeploymentValidator,
    FileWriteValidator,
)

logger = logging.getLogger("kairo.verification.service")


class VerificationService:
    """Enterprise verification, contradiction detection, and self-correction coordinator."""

    def __init__(self) -> None:
        # In-memory primary registries (with DB persistence hook support)
        self._claims: dict[str, Claim] = {}
        self._evidence: dict[str, Evidence] = {}
        self._provenance_chains: dict[str, ProvenanceChain] = {}
        self._contracts: dict[str, VerificationContract] = {}
        self._results: dict[str, VerificationResult] = {}

        # Subsystems
        self.invariants = InvariantEngine()
        self.contradictions = ContradictionEngine()
        self.triangulator = SourceTriangulator()
        self.freshness = FreshnessTracker()
        self.confidence = ConfidenceCalibrator()
        self.self_correction = SelfCorrectionEngine()
        self.citation_validator = CitationValidator()
        self.strategy_executor = VerificationStrategyExecutor()
        self.reconciler = StateReconciler()

        # Metrics
        self._metrics = {
            "claims_created": 0,
            "claims_verified": 0,
            "claims_contradicted": 0,
            "evidence_registered": 0,
            "verifications_passed": 0,
            "verifications_failed": 0,
            "corrections_applied": 0,
            "oscillations_prevented": 0,
        }

    # =========================================================================
    # CLAIMS LIFECYCLE
    # =========================================================================

    def register_claim(
        self,
        statement: str,
        claim_type: ClaimType = ClaimType.MODEL_ASSERTION,
        subject: str | None = None,
        predicate: str | None = None,
        object_ref: str | None = None,
        source: str = "model",
        scope: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
        claim_id: str | None = None,
    ) -> Claim:
        """Register a new claim.
        
        Applies Deduplication (Spec 68) and Anti-Self-Attestation (Spec 19, 75).
        Model claims asserting "done", "fixed", "passed" without evidence remain UNVERIFIED.
        """
        cid = claim_id or f"clm-{uuid.uuid4().hex[:8]}"
        scope_dict = dict(scope or {})

        # Check deduplication
        for existing in self._claims.values():
            if (
                existing.subject == subject
                and existing.predicate == predicate
                and existing.object_ref == object_ref
                and existing.scope.get("project_id") == scope_dict.get("project_id")
                and existing.statement.strip().lower() == statement.strip().lower()
            ):
                logger.debug("Deduplicated equivalent claim: %s", existing.claim_id)
                return existing

        claim = Claim(
            claim_id=cid,
            statement=statement,
            claim_type=claim_type,
            subject=subject,
            predicate=predicate,
            object_ref=object_ref,
            source=source,
            scope=scope_dict,
            expires_at=expires_at,
            truth_status=TruthStatus.UNVERIFIED,
            confidence="LOW",
        )

        self._claims[cid] = claim
        self._provenance_chains[cid] = ProvenanceChain(claim_id=cid)
        self._metrics["claims_created"] += 1
        return claim

    def get_claim(self, claim_id: str) -> Claim | None:
        """Get claim by ID, with automatic freshness evaluation."""
        claim = self._claims.get(claim_id)
        if claim:
            self.freshness.mark_stale_if_expired(claim)
        return claim

    def list_claims(
        self,
        status: TruthStatus | None = None,
        claim_type: ClaimType | None = None,
        subject: str | None = None,
    ) -> list[Claim]:
        """List registered claims with optional filters."""
        claims = list(self._claims.values())
        if status:
            claims = [c for c in claims if c.truth_status == status]
        if claim_type:
            claims = [c for c in claims if c.claim_type == claim_type]
        if subject:
            claims = [c for c in claims if c.subject == subject]
        return claims

    # =========================================================================
    # EVIDENCE REGISTRATION & PROVENANCE
    # =========================================================================

    def register_evidence(
        self,
        source_type: EvidenceType,
        source_reference: str,
        observation: dict[str, Any] | str,
        claim_id: str | None = None,
        scope: dict[str, Any] | None = None,
        checksum: str | None = None,
        evidence_id: str | None = None,
    ) -> Evidence:
        """Register empirical evidence with secret redaction and provenance tracking."""
        eid = evidence_id or f"ev-{uuid.uuid4().hex[:8]}"

        # Secret Redaction (Spec 180, 181)
        if isinstance(observation, dict):
            sanitized_obs = ArgumentSanitizer.sanitize(observation)
        else:
            sanitized_obs = {"content": ArgumentSanitizer.redact_string(str(observation))}

        evidence = Evidence(
            evidence_id=eid,
            source_type=source_type,
            source_reference=source_reference,
            observation=sanitized_obs,
            scope=dict(scope or {}),
            checksum=checksum,
        )

        self._evidence[eid] = evidence
        self._metrics["evidence_registered"] += 1

        # Attach to claim & provenance chain if specified
        if claim_id and claim_id in self._claims:
            claim = self._claims[claim_id]
            if eid not in claim.evidence_refs:
                claim.evidence_refs.append(eid)

            chain = self._provenance_chains.get(claim_id)
            if chain:
                chain.add_step(
                    action=f"registered_evidence_{source_type.value}",
                    source=source_reference,
                    evidence_ref=eid,
                )

        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        return self._evidence.get(evidence_id)

    def get_provenance_chain(self, claim_id: str) -> ProvenanceChain | None:
        return self._provenance_chains.get(claim_id)

    # =========================================================================
    # VERIFICATION EXECUTION
    # =========================================================================

    def verify_claim_contract(
        self,
        claim_id: str,
        contract: VerificationContract,
        observed_data: dict[str, Any],
        strategy: VerificationStrategyType = VerificationStrategyType.DIRECT_CHECK,
    ) -> tuple[Claim, VerificationResult]:
        """Execute verification contract against observed data (Spec 49-53).
        
        Read-only safe, updates Claim truth_status and confidence, executes domain invariants.
        """
        claim = self.get_claim(claim_id)
        if not claim:
            raise ValueError(f"Claim '{claim_id}' does not exist")

        # Execute strategy
        result = self.strategy_executor.execute(strategy.value, contract, observed_data)
        self._results[claim_id] = result
        self._contracts[contract.contract_id] = contract

        # Evaluate Invariants
        violations = self.invariants.evaluate_all(observed_data)
        if violations:
            for v in violations:
                result.discrepancies.append(f"Invariant [{v.rule_id}]: {v.message}")
            if any(v.severity == "CRITICAL" for v in violations):
                result.status = VerificationStatus.FAIL

        # Register observed data as new Evidence piece
        evidence = self.register_evidence(
            source_type=EvidenceType.DIRECT_OBSERVATION,
            source_reference=f"verifier:{result.verifier}",
            observation=observed_data,
            claim_id=claim_id,
            scope=claim.scope,
        )
        result.evidence_ids.append(evidence.evidence_id)

        # Update Claim Truth Status
        if result.status == VerificationStatus.PASS:
            claim.truth_status = TruthStatus.VERIFIED
            claim.confidence = "HIGH"
            self._metrics["verifications_passed"] += 1
            self._metrics["claims_verified"] += 1
        elif result.status == VerificationStatus.PARTIAL:
            claim.truth_status = TruthStatus.SUPPORTED
            claim.confidence = "MEDIUM"
        elif result.status == VerificationStatus.TIMEOUT:
            claim.truth_status = TruthStatus.UNKNOWN
            claim.confidence = "LOW"
            self._metrics["verifications_failed"] += 1
        elif result.status in [VerificationStatus.FAIL, VerificationStatus.INCONCLUSIVE]:
            claim.truth_status = TruthStatus.CONTRADICTED if result.discrepancies else TruthStatus.UNKNOWN
            claim.confidence = "LOW"
            self._metrics["verifications_failed"] += 1

            # Trigger state reconciliation if safe (Spec 133, 134)
            self.reconciler.reconcile(
                target_resource=contract.target,
                verification_result=result,
                resource_authority="DERIVED",
            )

        return claim, result

    # =========================================================================
    # DOMAIN SPECIFIC VALIDATORS (Spec 23-27)
    # =========================================================================

    def verify_deployment(
        self,
        claim_id: str,
        api_response: dict[str, Any],
        health_response: dict[str, Any],
        expected_version: str,
    ) -> VerificationResult:
        """Verify deployment via independent status and health endpoints (Spec 23)."""
        res = DeploymentValidator.validate_deployment(api_response, health_response, expected_version)
        claim = self.get_claim(claim_id)
        if claim:
            claim.truth_status = TruthStatus.VERIFIED if res.status == VerificationStatus.PASS else TruthStatus.CONTRADICTED
            claim.confidence = res.confidence
        return res

    def verify_code_change(
        self,
        claim_id: str,
        test_results: dict[str, Any],
        lint_results: dict[str, Any],
        type_check_results: dict[str, Any],
    ) -> VerificationResult:
        """Verify code patch through tests, linting, and type check (Spec 25)."""
        res = CodeChangeValidator.validate_code_change(test_results, lint_results, type_check_results)
        claim = self.get_claim(claim_id)
        if claim:
            claim.truth_status = TruthStatus.VERIFIED if res.status == VerificationStatus.PASS else TruthStatus.CONTRADICTED
            claim.confidence = res.confidence
        return res

    def verify_file_write(
        self,
        claim_id: str,
        path: str,
        expected_content: str,
        file_system_probe: dict[str, Any],
    ) -> VerificationResult:
        """Verify file existence and content hash match (Spec 27)."""
        res = FileWriteValidator.validate_file(path, expected_content, file_system_probe)
        claim = self.get_claim(claim_id)
        if claim:
            claim.truth_status = TruthStatus.VERIFIED if res.status == VerificationStatus.PASS else TruthStatus.CONTRADICTED
            claim.confidence = res.confidence
        return res

    def verify_database_migration(
        self,
        claim_id: str,
        migration_output: dict[str, Any],
        schema_query_result: dict[str, Any],
        expected_tables: list[str],
    ) -> VerificationResult:
        """Verify database schema actually contains expected tables (Spec 26)."""
        res = DatabaseMigrationValidator.validate_migration(migration_output, schema_query_result, expected_tables)
        claim = self.get_claim(claim_id)
        if claim:
            claim.truth_status = TruthStatus.VERIFIED if res.status == VerificationStatus.PASS else TruthStatus.CONTRADICTED
            claim.confidence = res.confidence
        return res

    # =========================================================================
    # CONTRADICTION DETECTION & TRIANGULATION
    # =========================================================================

    def check_contradictions(self, claim_id: str) -> list[Contradiction]:
        """Check claim against other registered claims for direct or temporal conflict."""
        target_claim = self.get_claim(claim_id)
        if not target_claim:
            return []

        other_claims = [c for c in self._claims.values() if c.claim_id != claim_id]
        contradictions = self.contradictions.detect_conflicts(target_claim, other_claims)
        if contradictions:
            self._metrics["claims_contradicted"] += len(contradictions)
            if target_claim.truth_status == TruthStatus.VERIFIED:
                target_claim.truth_status = TruthStatus.CONTRADICTED
        return contradictions

    def triangulate(self, claim_id: str) -> TriangulationResult:
        """Cross-verify claim across all associated evidence pieces."""
        claim = self.get_claim(claim_id)
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found")

        evidences = [self._evidence[eid] for eid in claim.evidence_refs if eid in self._evidence]
        result = self.triangulator.triangulate(claim, evidences)
        claim.truth_status = result.status
        return result

    # =========================================================================
    # CONFIDENCE & CALIBRATION
    # =========================================================================

    def evaluate_confidence(self, claim_id: str) -> ConfidenceReport:
        """Compute calibrated confidence report for claim."""
        claim = self.get_claim(claim_id)
        if not claim:
            raise ValueError(f"Claim '{claim_id}' not found")

        evidences = [self._evidence[eid] for eid in claim.evidence_refs if eid in self._evidence]
        contradictions = self.check_contradictions(claim_id)
        last_result = self._results.get(claim_id)
        v_passed = (last_result.status == VerificationStatus.PASS) if last_result else None

        report = self.confidence.calibrate(
            claim=claim,
            evidences=evidences,
            has_contradictions=bool(contradictions),
            verification_passed=v_passed,
        )
        claim.confidence = report.level.value
        return report

    # =========================================================================
    # CITATIONS & EVALUATION (Spec 92-94)
    # =========================================================================

    def validate_citation(
        self,
        statement: str,
        citation_ref: str,
        excerpt: str | None = None,
    ) -> CitationValidationResult:
        """Verify citation points to a real source and corroborates claim."""
        return self.citation_validator.validate_citation(statement, citation_ref, excerpt)

    def register_known_source(self, source_ref: str, content: str) -> None:
        """Register known reference document for citation checking."""
        self.citation_validator.register_source(source_ref, content)

    # =========================================================================
    # SELF-CORRECTION (Spec 79-83, 135-144)
    # =========================================================================

    def execute_self_correction(
        self,
        original_claim_id: str,
        corrected_statement: str,
        supporting_evidence_ids: list[str],
        reason: str,
    ) -> Correction:
        """Correct a refuted claim, enforce boundaries, detect oscillation, format admission."""
        original_claim = self.get_claim(original_claim_id)
        if not original_claim:
            raise ValueError(f"Claim '{original_claim_id}' not found")

        evidences = [self._evidence[eid] for eid in supporting_evidence_ids if eid in self._evidence]
        correction = self.self_correction.attempt_correction(
            original_claim=original_claim,
            corrected_statement=corrected_statement,
            supporting_evidence=evidences,
            reason=reason,
        )

        if correction.status == "APPLIED":
            # Update claim statement and mark truth status
            original_claim.statement = corrected_statement
            original_claim.truth_status = TruthStatus.VERIFIED if evidences else TruthStatus.SUPPORTED
            self._metrics["corrections_applied"] += 1
        elif correction.status == "ESCALATED":
            self._metrics["oscillations_prevented"] += 1
            original_claim.truth_status = TruthStatus.CONTRADICTED

        return correction

    # =========================================================================
    # SUMMARY & METRICS
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Return verification engine summary statistics."""
        return {
            "metrics": dict(self._metrics),
            "total_claims": len(self._claims),
            "total_evidence": len(self._evidence),
            "total_contracts": len(self._contracts),
            "total_corrections": len(self.self_correction.get_all_corrections()),
            "calibration": self.confidence.get_calibration_stats(),
        }

"""Content Integrity Engine for Task 116.
Verifies content SHA-256 hashes, detects source drift, compares snapshots,
validates transformation pipelines, and defends against untrusted external content.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.claim_verification.domain import (
    EvidenceArtifact,
    EvidenceTransformation,
    IntegrityCheck,
    SourceSnapshot,
)


class ContentIntegrityEngine:
    """Calculates cryptographic hashes, verifies snapshot integrity, and detects drift/tampering."""

    # Prompt injection patterns in untrusted raw content
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s*:\s*you\s+are\s+now", re.IGNORECASE),
        re.compile(r"override\s+(security|governance|emergency_stop)", re.IGNORECASE),
        re.compile(r"authorized\s+bypass\s+granted", re.IGNORECASE),
        re.compile(r"<\|im_start\|>", re.IGNORECASE),
        re.compile(r"\[SYSTEM_DIRECTIVE\]", re.IGNORECASE),
    ]

    @classmethod
    def compute_sha256(cls, content: str | bytes) -> str:
        """Compute standard SHA-256 hexadecimal digest."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def sanitize_untrusted_content(cls, content: str) -> Tuple[str, List[str]]:
        """Sanitize raw untrusted text by disarming prompt injection and malicious instructions.
        Returns sanitized content and detected threat flags.
        """
        threat_flags: List[str] = []
        sanitized = content

        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            matches = pattern.findall(content)
            if matches:
                threat_flags.append(f"PROMPT_INJECTION_ATTEMPT: {pattern.pattern}")
                sanitized = pattern.sub("[DISARMED_UNTRUSTED_INSTRUCTION]", sanitized)

        return sanitized, threat_flags

    @classmethod
    def verify_snapshot_integrity(
        cls,
        snapshot: SourceSnapshot,
        current_content: Optional[str] = None,
    ) -> IntegrityCheck:
        """Verify SHA-256 integrity of snapshot against current content if provided, or stored hash."""
        check_id = f"integ_{uuid.uuid4().hex[:10]}"

        if current_content is not None:
            computed_hash = cls.compute_sha256(current_content)
            passed = (computed_hash == snapshot.content_hash)
            diff_summary = "" if passed else f"Hash mismatch: expected {snapshot.content_hash}, got {computed_hash}"
            return IntegrityCheck(
                check_id=check_id,
                target_type="SOURCE_SNAPSHOT",
                target_id=snapshot.snapshot_id,
                expected_hash=snapshot.content_hash,
                computed_hash=computed_hash,
                passed=passed,
                diff_summary=diff_summary,
                tamper_indicators=["CONTENT_DRIFT_DETECTED"] if not passed else [],
                checked_at=datetime.now(timezone.utc),
            )

        # Self-consistency check on snapshot preview
        computed_preview_hash = cls.compute_sha256(snapshot.content_preview)
        passed = (computed_preview_hash == snapshot.content_hash) if snapshot.content_preview else True
        return IntegrityCheck(
            check_id=check_id,
            target_type="SOURCE_SNAPSHOT",
            target_id=snapshot.snapshot_id,
            expected_hash=snapshot.content_hash,
            computed_hash=computed_preview_hash if snapshot.content_preview else snapshot.content_hash,
            passed=passed,
            diff_summary="" if passed else "Snapshot content preview hash does not match stored content hash",
            tamper_indicators=["PREVIEW_HASH_MISMATCH"] if not passed else [],
            checked_at=datetime.now(timezone.utc),
        )

    @classmethod
    def verify_artifact_integrity(
        cls,
        artifact: EvidenceArtifact,
        raw_text: Optional[str] = None,
    ) -> IntegrityCheck:
        """Verify content hash of evidence artifact."""
        check_id = f"integ_{uuid.uuid4().hex[:10]}"
        text_to_check = raw_text if raw_text is not None else artifact.content_text
        computed = cls.compute_sha256(text_to_check)
        passed = (computed == artifact.content_hash)

        # Also inspect for prompt injection / external untrusted markers
        _, threats = cls.sanitize_untrusted_content(text_to_check)

        return IntegrityCheck(
            check_id=check_id,
            target_type="EVIDENCE_ARTIFACT",
            target_id=artifact.evidence_id,
            expected_hash=artifact.content_hash,
            computed_hash=computed,
            passed=passed and (len(threats) == 0),
            diff_summary="" if passed else f"Artifact hash mismatch: expected {artifact.content_hash}, got {computed}",
            tamper_indicators=threats + (["ARTIFACT_HASH_TAMPERED"] if not passed else []),
            checked_at=datetime.now(timezone.utc),
        )

    @classmethod
    def verify_transformation_chain(
        cls,
        transformations: List[EvidenceTransformation],
        artifacts_by_id: Dict[str, EvidenceArtifact],
    ) -> Tuple[bool, List[str]]:
        """Verify that every step in the transformation graph has valid inputs and outputs.
        Ensures input hashes match prior outputs.
        """
        issues: List[str] = []

        for trans in transformations:
            # Check input artifacts exist
            for in_id in trans.input_artifact_ids:
                if in_id not in artifacts_by_id:
                    issues.append(f"Transformation {trans.transformation_id}: missing input artifact {in_id}")
                else:
                    in_art = artifacts_by_id[in_id]
                    if trans.input_hash and in_art.content_hash != trans.input_hash:
                        issues.append(
                            f"Transformation {trans.transformation_id}: input hash mismatch for {in_id}. Expected {trans.input_hash}, artifact has {in_art.content_hash}"
                        )

            # Check output artifact exists
            if trans.output_artifact_id not in artifacts_by_id:
                issues.append(f"Transformation {trans.transformation_id}: missing output artifact {trans.output_artifact_id}")
            else:
                out_art = artifacts_by_id[trans.output_artifact_id]
                if trans.output_hash and out_art.content_hash != trans.output_hash:
                    issues.append(
                        f"Transformation {trans.transformation_id}: output hash mismatch for {trans.output_artifact_id}. Expected {trans.output_hash}, artifact has {out_art.content_hash}"
                    )

        return (len(issues) == 0, issues)

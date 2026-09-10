"""Safety guards, invariant validators, and domain exceptions for Causal Reasoning (Task 55)."""

from __future__ import annotations

import re

from app.causal.schemas import CausalEvidence, CausalRelationshipType, EvidenceType


class CausalSafetyError(Exception):
    """Base exception for causal reasoning safety violations."""


class CorrelationAsCausationError(CausalSafetyError):
    """Raised when temporal precedence or correlation alone is asserted as verified causation."""


class ModelOutputAsEvidenceError(CausalSafetyError):
    """Raised when model reasoning or synthetic hallucinations are cited as empirical evidence."""


class UnverifiedRootCauseError(CausalSafetyError):
    """Raised when a root cause is declared verified without passing empirical verification thresholds."""


class UnauthorizedInterventionError(CausalSafetyError):
    """Raised when an intervention is attempted without policy, authorization, or approval."""


class HighRiskExperimentError(CausalSafetyError):
    """Raised when an unapproved or high-risk causal experiment is initiated autonomously."""


class CausalPoisoningError(CausalSafetyError):
    """Raised when untrusted external inputs attempt to inject or fabricate causal relationships."""


SECRET_KEY_PATTERNS = [
    re.compile(r".*(password|passwd|pwd).*", re.IGNORECASE),
    re.compile(r".*(secret|api_key|apikey|token|auth_token|bearer|jwt).*", re.IGNORECASE),
    re.compile(r".*(private_key|priv_key|ssh_key|cert_key).*", re.IGNORECASE),
]

SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----"),
    re.compile(r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+"),  # JWT
    re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{82})"),  # GitHub tokens
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
    re.compile(r"(password|passwd|pwd|secret|api_key|token|auth_token)\s*=\s*['\"]?[^\s,'\"&]+['\"]?", re.IGNORECASE),
]


class CausalSafetyGuard:
    """Enforces causal inference invariants, prevents fallacies, and protects production."""

    @staticmethod
    def scrub_text(text: str) -> str:
        """Prompt #144: Do not expose secrets in causal explanations or evidence."""
        scrubbed = text
        for pat in SECRET_VALUE_PATTERNS:
            scrubbed = pat.sub("[REDACTED_SECRET]", scrubbed)
        return scrubbed

    @staticmethod
    def validate_causal_claim(
        relationship: CausalRelationshipType,
        evidence_list: list[CausalEvidence],
    ) -> None:
        """Prompt #6, #8, #19, #26: Prevents confusing correlation or model output with causation."""
        if relationship in (CausalRelationshipType.CAUSES, CausalRelationshipType.CONTRIBUTES_TO):
            if not evidence_list:
                raise CorrelationAsCausationError(
                    f"Relationship '{relationship.value}' requires empirical causal evidence, not mere assertion."
                )

            # Prompt #19: Model-generated reasoning is hypothesis generation, NOT evidence
            for ev in evidence_list:
                src_lower = str(ev.source).lower()
                if "llm" in src_lower or "model_output" in src_lower or "assistant_thought" in src_lower:
                    raise ModelOutputAsEvidenceError(
                        "Model-generated reasoning cannot serve as empirical causal evidence. Use telemetry, traces, logs, or interventions."
                    )

            # If all evidence is only TEMPORAL_ORDER or CORRELATION without mechanism or telemetry
            non_temporal = [
                ev for ev in evidence_list
                if ev.type not in (EvidenceType.OBSERVATION, EvidenceType.HISTORICAL_PATTERN)
                or ev.strength.value in ("STRONG", "CRITICAL")
            ]
            if not non_temporal:
                raise CorrelationAsCausationError(
                    "Temporal sequence or historical correlation alone cannot establish verified causation (post hoc fallacy rejection)."
                )

    @staticmethod
    def validate_root_cause_claim(
        root_cause: str | None,
        is_verified: bool,
        evidence_list: list[CausalEvidence],
    ) -> None:
        """Prompt #33, #84, #164: Verified root cause requires explicit empirical evidence threshold."""
        if is_verified and root_cause:
            if not evidence_list:
                raise UnverifiedRootCauseError(
                    f"Root cause '{root_cause}' cannot be claimed as VERIFIED without empirical evidence."
                )

            # Check for strong or critical evidence
            has_strong = any(ev.strength.value in ("STRONG", "CRITICAL") for ev in evidence_list)
            if not has_strong:
                raise UnverifiedRootCauseError(
                    f"Root cause '{root_cause}' cannot be claimed as VERIFIED with only weak evidence. Must remain LIKELY or SUPPORTED."
                )

    @staticmethod
    def validate_intervention_safety(
        target: str,
        risk: str,
        is_production: bool,
        is_approved: bool,
    ) -> None:
        """Prompt #43, #44: Interventions cannot modify production without approval."""
        if is_production and not is_approved:
            raise UnauthorizedInterventionError(
                f"Intervention on production target '{target}' requires explicit operator approval."
            )

    @staticmethod
    def validate_experiment_safety(
        hypothesis_id: str,
        is_high_risk: bool,
        is_approved: bool,
    ) -> None:
        """Prompt #75, #76: High-risk experiments require approval."""
        if is_high_risk and not is_approved:
            raise HighRiskExperimentError(
                f"High-risk causal experiment for hypothesis '{hypothesis_id}' cannot run automatically without approval."
            )

"""Evidence Ingestion, Quality Classification, and Independence Discounting (Task 55, Prompts #13-#24)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.causal.provenance import generate_evidence_id
from app.causal.safety import ModelOutputAsEvidenceError
from app.causal.schemas import CausalEvidence, EvidenceStrength, EvidenceType
from app.causal.temporal import utc_now

AUTHORITATIVE_SOURCES = {
    "opentelemetry", "jaeger", "prometheus", "datadog", "kubernetes_api",
    "git_provider", "postgres_sys", "aws_cloudwatch", "systemd"
}


def create_causal_evidence(
    evidence_type: EvidenceType,
    source: str,
    observation: dict[str, Any],
    strength: EvidenceStrength = EvidenceStrength.MODERATE,
    independence: float = 1.0,
    timestamp: datetime | None = None,
) -> CausalEvidence:
    """Prompt #13, #15, #17, #19: Creates validated CausalEvidence with authority checks."""
    src_lower = source.lower()

    # Prompt #19: Model output cannot be evidence
    if "llm" in src_lower or "model_output" in src_lower or "assistant_thought" in src_lower:
        raise ModelOutputAsEvidenceError(
            f"Source '{source}' is model-generated reasoning, which is hypothesis generation, not evidence."
        )

    # Prompt #18: User reports are useful evidence but default to WEAK/MODERATE unless corroborated
    if evidence_type == EvidenceType.USER_REPORT and strength in (EvidenceStrength.STRONG, EvidenceStrength.CRITICAL):
        strength = EvidenceStrength.MODERATE

    # Authoritative sources get strength floor of MODERATE
    if any(auth in src_lower for auth in AUTHORITATIVE_SOURCES):
        if strength == EvidenceStrength.WEAK:
            strength = EvidenceStrength.MODERATE

    eid = generate_evidence_id(evidence_type.value, source, observation)
    return CausalEvidence(
        evidence_id=eid,
        type=evidence_type,
        source=source,
        observation=observation,
        strength=strength,
        independence=round(max(0.1, min(1.0, independence)), 2),
        timestamp=timestamp or utc_now(),
    )


def discount_correlated_evidence(evidences: list[CausalEvidence]) -> list[CausalEvidence]:
    """Prompt #16: Avoids counting correlated or redundant evidence multiple times."""
    seen_sources: dict[str, int] = {}
    adjusted: list[CausalEvidence] = []

    for ev in evidences:
        base_src = ev.source.split(":")[0].lower()
        seen_sources[base_src] = seen_sources.get(base_src, 0) + 1
        count = seen_sources[base_src]

        # If multiple pieces of evidence come from the exact same source, discount independence
        indep = ev.independence if count == 1 else round(ev.independence / (1.5 ** (count - 1)), 2)
        adjusted.append(
            CausalEvidence(
                evidence_id=ev.evidence_id,
                type=ev.type,
                source=ev.source,
                observation=ev.observation,
                strength=ev.strength,
                independence=indep,
                timestamp=ev.timestamp,
            )
        )
    return adjusted


create_evidence = create_causal_evidence


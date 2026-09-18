"""Provenance Engine for Task 110:
Maintains cryptographic lineage and provenance chains for context elements.

Strict Invariants:
- Untrusted content never gains authority by traveling through transformations.
- Complete lineage from acquisition through transformation to working set is preserved.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.context.working_set_domain import (
    ContextCandidate,
    ContextProvenance,
    TrustClassification,
    utc_now,
)


class ProvenanceEngine:
    """Builds and verifies verifiable provenance chains for context elements."""

    @classmethod
    def create_provenance(
        cls,
        candidate: ContextCandidate,
        lineage_step: str = "context_ingest",
    ) -> ContextProvenance:
        """Initialize provenance record from an upstream candidate."""
        now = utc_now()
        is_user = candidate.trust_label == TrustClassification.USER_AUTHORED
        is_ext = candidate.trust_label in (
            TrustClassification.EXTERNAL_UNTRUSTED,
            TrustClassification.WEB_UNTRUSTED,
            TrustClassification.TOOL_UNTRUSTED,
        )
        is_agent = candidate.trust_label == TrustClassification.AGENT_DERIVED
        is_gen = candidate.trust_label == TrustClassification.MODEL_DERIVED

        # Seed initial lineage path
        initial_lineage = [
            f"{candidate.source_subsystem}:{candidate.source_id}@{candidate.source_timestamp.isoformat()}",
            f"context_engine:{lineage_step}@{now.isoformat()}",
        ]

        # Generate deterministic fingerprint
        signature_material = f"{candidate.source_subsystem}:{candidate.source_id}:{candidate.raw_content[:200]}"
        signature = hashlib.sha256(signature_material.encode("utf-8")).hexdigest()[:16]

        return ContextProvenance(
            source_type=candidate.source_subsystem,
            source_id=candidate.source_id,
            source_version="1.0.0",
            originating_subsystem=candidate.source_subsystem,
            acquisition_timestamp=now,
            observation_timestamp=candidate.source_timestamp,
            trust_label=candidate.trust_label,
            user_originated=is_user,
            external_origin=is_ext,
            agent_originated=is_agent,
            generated_origin=is_gen,
            lineage_path=initial_lineage,
            signature=f"sig_{signature}",
        )

    @classmethod
    def append_transformation_step(
        cls,
        provenance: ContextProvenance,
        transformation_type: str,
        transformation_id: str,
    ) -> ContextProvenance:
        """Append an explicit transformation step to an existing provenance record."""
        updated_lineage = list(provenance.lineage_path)
        updated_lineage.append(f"transform:{transformation_type}:{transformation_id}@{utc_now().isoformat()}")

        return ContextProvenance(
            source_type=provenance.source_type,
            source_id=provenance.source_id,
            source_version=provenance.source_version,
            originating_subsystem=provenance.originating_subsystem,
            acquisition_timestamp=provenance.acquisition_timestamp,
            observation_timestamp=provenance.observation_timestamp,
            trust_label=provenance.trust_label,
            user_originated=provenance.user_originated,
            external_origin=provenance.external_origin,
            agent_originated=provenance.agent_originated,
            generated_origin=provenance.generated_origin,
            lineage_path=updated_lineage,
            signature=provenance.signature,
        )

"""Service layer for Task 116: Autonomous Claim Verification, Source Integrity & Evidence Provenance Engine.
Provides thread-safe state management, idempotency handling, pipeline execution,
and persistent DB synchronization with fallback.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.claim_verification.domain import (
    Claim,
    ContradictionRecord,
    CorroborationGroup,
    EvidenceArtifact,
    EvidenceQualityProfile,
    EvidenceTransformation,
    IntegrityCheck,
    ProvenanceLink,
    ProvenancePredicate,
    ReproducibilityStatus,
    ReproductionAttempt,
    Source,
    SourceCategory,
    SourceRelationship,
    SourceRelationshipType,
    SourceSnapshot,
    SourceTrustProfile,
    VerificationCase,
    VerificationCaseStatus,
    VerificationEvent,
    VerificationGap,
    VerificationResult,
    VerificationSnapshot,
)
from app.claim_verification.fragmentation_engine import ClaimFragmentationEngine
from app.claim_verification.integrity_engine import ContentIntegrityEngine
from app.claim_verification.pipeline import VerificationPipeline
from app.claim_verification.provenance_engine import ProvenanceEngine
from app.claim_verification.reproducibility_engine import ReproducibilityEngine
from app.claim_verification.schemas import CreateVerificationRequest
from app.claim_verification.staleness_and_cache import StalenessAndCacheEngine

logger = logging.getLogger(__name__)


class ClaimVerificationService:
    """Core singleton service managing claim verification cases, sources, evidence, and provenance."""

    _instance: Optional[ClaimVerificationService] = None

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # In-memory storage caches
        self._cases: Dict[str, VerificationCase] = {}
        self._claims: Dict[str, Claim] = {}
        self._sources: Dict[str, Source] = {}
        self._snapshots: Dict[str, SourceSnapshot] = {}
        self._evidence: Dict[str, EvidenceArtifact] = {}
        self._transformations: Dict[str, EvidenceTransformation] = {}
        self._links: List[ProvenanceLink] = []
        self._relationships: List[SourceRelationship] = []
        self._corroborations: Dict[str, CorroborationGroup] = {}
        self._contradictions: Dict[str, List[ContradictionRecord]] = {}
        self._reproductions: Dict[str, List[ReproductionAttempt]] = {}
        self._results: Dict[str, VerificationResult] = {}
        self._gaps: Dict[str, List[VerificationGap]] = {}
        self._events: Dict[str, List[VerificationEvent]] = {}
        self._explanations: Dict[str, Dict[str, Any]] = {}
        self._idempotency_map: Dict[str, str] = {}

        self.pipeline = VerificationPipeline(event_emitter=self._handle_event)

    @classmethod
    def get_instance(cls) -> ClaimVerificationService:
        if cls._instance is None:
            cls._instance = ClaimVerificationService()
        return cls._instance

    def _handle_event(self, event: VerificationEvent) -> None:
        """Record append-only verification events."""
        if event.case_id not in self._events:
            self._events[event.case_id] = []
        self._events[event.case_id].append(event)
        logger.info(f"VerificationEvent: [{event.event_type}] case={event.case_id} actor={event.actor}")

    async def create_verification(
        self,
        request: CreateVerificationRequest,
        session: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
    ) -> Tuple[VerificationCase, VerificationResult]:
        """Initiate or idempotently retrieve a verification case and execute the 25-step pipeline."""
        async with self._lock:
            # 1. Check idempotency
            if request.idempotency_key and request.idempotency_key in self._idempotency_map:
                existing_id = self._idempotency_map[request.idempotency_key]
                if existing_id in self._cases and existing_id in self._results:
                    return self._cases[existing_id], self._results[existing_id]

            case_id = f"case_{uuid.uuid4().hex[:12]}"
            claim_id = f"claim_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)

            # 2. Construct Sources
            sources_to_use: List[Source] = []
            snapshots_to_use: List[SourceSnapshot] = []

            for s_data in request.sources:
                s_id = s_data.get("source_id") or f"src_{uuid.uuid4().hex[:10]}"
                uri = s_data.get("uri", f"internal://source/{s_id}")
                cat = SourceCategory(s_data.get("category", "SYSTEM")) if s_data.get("category") in SourceCategory._value2member_map_ else SourceCategory.INTERNAL_SYSTEM
                publisher = s_data.get("publisher", "internal")
                owner = s_data.get("owner", "system")

                src = Source(
                    source_id=s_id,
                    version=1,
                    uri=uri,
                    category=cat,
                    origin="internal",
                    owner=owner,
                    publisher=publisher,
                    retrieval_location=uri,
                    retrieval_timestamp=now,
                    content_hash="",
                    auth_state="AUTHENTICATED",
                    trust_profile=SourceTrustProfile(
                        identity_confidence=0.9,
                        provenance_quality=0.85,
                        integrity_confidence=0.95,
                        reproducibility=0.9,
                        independence=0.8,
                    ),
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                self._sources[s_id] = src
                sources_to_use.append(src)

                # Snapshot if content provided
                if "content" in s_data:
                    raw_content = s_data["content"]
                    chash = ContentIntegrityEngine.compute_sha256(raw_content)
                    snap = SourceSnapshot(
                        snapshot_id=f"snap_{uuid.uuid4().hex[:10]}",
                        source_id=s_id,
                        content_hash=chash,
                        canonical_source_identifier=uri,
                        retrieval_time=now,
                        observed_version=1,
                        headers={},
                        content_metadata={},
                        content_preview=raw_content[:200],
                        parser_version="v1.0",
                        transformation_chain=[],
                        valid_at=now,
                        expired_at=now + timedelta(days=30),
                    )
                    self._snapshots[snap.snapshot_id] = snap
                    snapshots_to_use.append(snap)

            # Default source if none provided
            if not sources_to_use:
                def_src = Source(
                    source_id=f"src_default_{uuid.uuid4().hex[:8]}",
                    version=1,
                    uri="system://telemetry/default",
                    category=SourceCategory.TELEMETRY,
                    origin="system",
                    owner="kairo",
                    publisher="telemetry_engine",
                    retrieval_location="system://telemetry",
                    retrieval_timestamp=now,
                    content_hash="",
                    auth_state="AUTHENTICATED",
                    trust_profile=SourceTrustProfile(),
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                self._sources[def_src.source_id] = def_src
                sources_to_use.append(def_src)

            # 3. Construct Evidence Artifacts
            evidence_artifacts: List[EvidenceArtifact] = []
            for e_data in request.evidence:
                e_id = e_data.get("evidence_id") or f"ev_{uuid.uuid4().hex[:10]}"
                raw_text = e_data.get("content_text", "")
                src_id = e_data.get("source_id") or sources_to_use[0].source_id
                chash = e_data.get("content_hash") or ContentIntegrityEngine.compute_sha256(raw_text)

                art = EvidenceArtifact(
                    evidence_id=e_id,
                    source_id=src_id,
                    snapshot_id=e_data.get("snapshot_id"),
                    location=e_data.get("location", "default_location"),
                    offset_range=e_data.get("offset_range", "0:0"),
                    extraction_method="DIRECT",
                    extractor_version="1.0",
                    extraction_timestamp=now,
                    content_hash=chash,
                    content_text=raw_text,
                    parent_artifact_id=e_data.get("parent_artifact_id"),
                    transformation_chain=[],
                    quality_profile=EvidenceQualityProfile(
                        directness="DIRECT",
                        relevance=0.9,
                        specificity=0.85,
                        freshness=1.0,
                        completeness=0.8,
                        provenance_quality=0.9,
                        integrity=1.0,
                        reproducibility=0.9,
                        independence=0.8,
                    ),
                    direct_status=True,
                    is_synthetic=e_data.get("is_synthetic", False),
                    is_simulated=e_data.get("is_simulated", False),
                    is_counterfactual=e_data.get("is_counterfactual", False),
                    created_at=now,
                )
                self._evidence[e_id] = art
                evidence_artifacts.append(art)

            # 4. Construct Case
            title = request.title or f"Verify: {request.claim_text[:60]}"
            case = VerificationCase(
                case_id=case_id,
                version=1,
                title=title,
                claim_id=claim_id,
                status=VerificationCaseStatus.REQUESTED,
                scope=request.scope,
                assumptions=[],
                falsification_conditions=[],
                verification_requirements=[],
                resolution_summary="",
                idempotency_key=request.idempotency_key,
                correlation_id=request.correlation_id,
                created_at=now,
                updated_at=now,
            )
            self._cases[case_id] = case
            if request.idempotency_key:
                self._idempotency_map[request.idempotency_key] = case_id

            # 5. Run Pipeline
            result, explanation = self.pipeline.execute_pipeline(
                case=case,
                claim_text=request.claim_text,
                sources=sources_to_use,
                snapshots=snapshots_to_use,
                evidence_artifacts=evidence_artifacts,
                transformations=list(self._transformations.values()),
                existing_links=self._links,
                user_id=user_id,
            )

            # Save state
            self._results[case_id] = result
            self._explanations[case_id] = explanation
            if "claim" in explanation:
                # Save structured claim
                c_dict = explanation["claim"]
                self._claims[claim_id] = ClaimFragmentationEngine.decompose_claim(
                    text=request.claim_text,
                    temporal_scope=case.scope.get("temporal"),
                    spatial_scope=case.scope.get("spatial"),
                    entity_scope=case.scope.get("entities", []),
                    source_scope=case.scope.get("sources"),
                    claim_id=claim_id,
                )

            # Also persist to DB if session provided
            if session is not None:
                await self._persist_to_db(case, result, session)

            return case, result

    async def _persist_to_db(
        self,
        case: VerificationCase,
        result: VerificationResult,
        session: AsyncSession,
    ) -> None:
        """Synchronize case and result to Postgres DB using SQLAlchemy models."""
        try:
            from app.claim_verification.models import VerificationCaseModel, VerificationResultModel

            case_model = VerificationCaseModel(
                case_id=case.case_id,
                version=case.version,
                title=case.title,
                claim_id=case.claim_id,
                status=case.status.value,
                scope_json=case.scope,
                assumptions_json=case.assumptions,
                falsification_conditions_json=case.falsification_conditions,
                verification_requirements_json=case.verification_requirements,
                resolution_summary=case.resolution_summary,
                idempotency_key=case.idempotency_key,
                correlation_id=case.correlation_id,
                created_at=case.created_at,
                updated_at=case.updated_at,
            )
            session.add(case_model)

            res_model = VerificationResultModel(
                result_id=result.result_id,
                case_id=result.case_id,
                claim_id=result.claim_id,
                status=result.status.value,
                scope_json=result.scope,
                justification=result.justification,
                evidence_ids_json=result.evidence_ids,
                contradiction_ids_json=result.contradiction_ids,
                method_types_json=result.method_types,
                uncertainty_profile_json=result.uncertainty_profile,
                gaps_json=result.gaps,
                reproducibility_status=result.reproducibility_status.value,
                validity_window_start=result.validity_window_start,
                validity_window_end=result.validity_window_end,
                verified_at=result.verified_at,
                expires_at=result.expires_at,
            )
            session.add(res_model)
            await session.commit()
        except Exception as e:
            logger.warning(f"Could not persist verification to DB: {e}. In-memory state preserved.")

    async def get_verification(self, case_id: str) -> Optional[VerificationCase]:
        return self._cases.get(case_id)

    async def get_result_for_case(self, case_id: str) -> Optional[VerificationResult]:
        return self._results.get(case_id)

    async def list_verifications(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[VerificationCase]:
        cases = list(self._cases.values())
        if status:
            cases = [c for c in cases if c.status.value == status]
        cases.sort(key=lambda x: x.created_at, reverse=True)
        return cases[offset : offset + limit]

    async def cancel_verification(self, case_id: str) -> Optional[VerificationCase]:
        async with self._lock:
            case = self._cases.get(case_id)
            if not case:
                return None
            case.status = VerificationCaseStatus.CANCELLED
            case.resolution_summary = "Verification explicitly cancelled by user/agent."
            case.updated_at = datetime.now(timezone.utc)
            return case

    async def revalidate_verification(self, case_id: str) -> Optional[Tuple[VerificationCase, VerificationResult]]:
        async with self._lock:
            case = self._cases.get(case_id)
            if not case:
                return None
            claim = self._claims.get(case.claim_id)
            if not claim:
                return None

            sources = [s for s in self._sources.values()]
            snapshots = [sn for sn in self._snapshots.values()]
            arts = [a for a in self._evidence.values()]

            case.version += 1
            case.status = VerificationCaseStatus.REQUESTED
            case.updated_at = datetime.now(timezone.utc)

            result, explanation = self.pipeline.execute_pipeline(
                case=case,
                claim_text=claim.canonical_text,
                sources=sources,
                snapshots=snapshots,
                evidence_artifacts=arts,
                transformations=list(self._transformations.values()),
                existing_links=self._links,
            )
            self._results[case_id] = result
            self._explanations[case_id] = explanation
            return case, result

    async def get_claims_for_case(self, case_id: str) -> List[Claim]:
        case = self._cases.get(case_id)
        if not case:
            return []
        claim = self._claims.get(case.claim_id)
        return [claim] if claim else []

    async def get_evidence_for_case(self, case_id: str) -> List[EvidenceArtifact]:
        res = self._results.get(case_id)
        if not res:
            return []
        return [self._evidence[eid] for eid in res.evidence_ids if eid in self._evidence]

    async def get_provenance_graph(self, case_id: str) -> Dict[str, Any]:
        case = self._cases.get(case_id)
        if not case:
            return {"nodes": [], "edges": []}

        nodes = [
            {"id": case.case_id, "type": "VerificationCase", "label": case.title, "status": case.status.value},
            {"id": case.claim_id, "type": "Claim", "label": case.title},
        ]
        edges = [
            {"from": case.case_id, "to": case.claim_id, "predicate": "VERIFIES"},
        ]

        res = self._results.get(case_id)
        if res:
            for eid in res.evidence_ids:
                if eid in self._evidence:
                    art = self._evidence[eid]
                    nodes.append({"id": eid, "type": "EvidenceArtifact", "label": art.content_text[:30]})
                    edges.append({"from": eid, "to": case.claim_id, "predicate": "SUPPORTS"})
                    if art.source_id in self._sources:
                        src = self._sources[art.source_id]
                        nodes.append({"id": src.source_id, "type": "Source", "label": src.uri})
                        edges.append({"from": eid, "to": src.source_id, "predicate": "EXTRACTED_FROM"})

        return {"nodes": nodes, "edges": edges}

    async def get_contradictions_for_case(self, case_id: str) -> List[ContradictionRecord]:
        expl = self._explanations.get(case_id)
        if not expl or "contradictions" not in expl:
            return []
        return [ContradictionRecord.from_dict(c) for c in expl["contradictions"]]

    async def get_gaps_for_case(self, case_id: str) -> List[VerificationGap]:
        expl = self._explanations.get(case_id)
        if not expl or "unresolved_gaps" not in expl:
            return []
        return [VerificationGap.from_dict(g) for g in expl["unresolved_gaps"]]

    async def get_timeline_for_case(self, case_id: str) -> List[VerificationEvent]:
        return self._events.get(case_id, [])

    async def get_explanation(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self._explanations.get(case_id)

    async def get_source(self, source_id: str) -> Optional[Source]:
        return self._sources.get(source_id)

    async def get_source_history(self, source_id: str) -> List[SourceSnapshot]:
        return [s for s in self._snapshots.values() if s.source_id == source_id]

    async def get_source_relationships(self, source_id: str) -> List[SourceRelationship]:
        return [
            r for r in self._relationships
            if r.source_a_id == source_id or r.source_b_id == source_id
        ]

    async def get_evidence_lineage(self, evidence_id: str) -> List[Dict[str, Any]]:
        return ProvenanceEngine.trace_evidence_lineage(evidence_id, self._links)

    async def get_claim_verification_status(self, claim_id: str) -> Optional[Dict[str, Any]]:
        for cid, case in self._cases.items():
            if case.claim_id == claim_id:
                res = self._results.get(cid)
                return {
                    "claim_id": claim_id,
                    "case_id": cid,
                    "status": case.status.value,
                    "resolution_summary": case.resolution_summary,
                    "verified_at": res.verified_at.isoformat() if res else None,
                    "expires_at": res.expires_at.isoformat() if (res and res.expires_at) else None,
                }
        return None

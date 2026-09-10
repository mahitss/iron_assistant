"""Claim extraction, semantic classification, entity resolution, and temporal versioning (Task 63)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from app.research.schemas import Claim, ClaimType, ConfidenceLevel, DocumentChunk

logger = logging.getLogger(__name__)


class ClaimExtractor:
    """Extracts explicit assertions, classifies claim types, and manages temporal validity.

    Invariant 11 & 12: A reported claim is not equivalent to measured or verified fact.
    Invariant 16: Knowledge changes over time; claims support valid_from, valid_until, and superseded_by.
    """

    # Entity canonicalization map to prevent duplicate entities (Invariant 45 & 46)
    _ENTITY_CANONICAL_MAP: dict[str, str] = {
        "google cloud run": "Cloud Run",
        "cloud run": "Cloud Run",
        "gcp cloud run": "Cloud Run",
        "amazon web services": "AWS",
        "amazon aws": "AWS",
        "kairo assistant": "Kairo",
        "kairo ai": "Kairo",
        "kairo core": "Kairo",
    }

    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}

    def extract_claims_from_chunk(
        self,
        chunk: DocumentChunk,
        source_id: str,
        scope: str = "general",
    ) -> list[Claim]:
        """Extract subject-predicate-object assertions from a document chunk and classify their types."""
        extracted: list[Claim] = []
        sentences = self._split_sentences(chunk.content)

        for sent in sentences:
            if len(sent.split()) < 4:
                continue

            claim_type = self._classify_claim_type(sent)
            subj, pred, obj = self._parse_spo_triplet(sent)

            # Canonicalize subject if known alias exists
            subj_canonical = self.resolve_entity(subj)

            claim = Claim(
                subject=subj_canonical,
                predicate=pred,
                object=obj,
                claim_text=sent,
                claim_type=claim_type,
                source_id=source_id,
                document_id=chunk.document_id,
                confidence=ConfidenceLevel.HIGH
                if claim_type in (ClaimType.MEASURED, ClaimType.OBSERVED)
                else ConfidenceLevel.MODERATE,
                scope=scope,
                valid_from=datetime.now(timezone.utc),
            )
            self._claims[claim.claim_id] = claim
            extracted.append(claim)

        logger.info(
            "CLAIMS_EXTRACTED: chunk=%s count=%d",
            chunk.chunk_id,
            len(extracted),
        )
        return extracted

    def get_claim(self, claim_id: str) -> Claim | None:
        """Retrieve claim by ID."""
        return self._claims.get(claim_id)

    def list_claims(self, source_id: str | None = None) -> list[Claim]:
        """List extracted claims."""
        if source_id:
            return [c for c in self._claims.values() if c.source_id == source_id]
        return list(self._claims.values())

    def supersede_claim(
        self,
        old_claim_id: str,
        new_claim_id: str,
        reason: str = "Updated with newer evidence",
    ) -> Claim:
        """Mark an older claim as superseded with an explicit valid_until timestamp.

        Invariant 16: Do not overwrite history; represent temporal validity.
        """
        old_claim = self._claims.get(old_claim_id)
        if not old_claim:
            raise KeyError(f"Claim '{old_claim_id}' not found.")

        now = datetime.now(timezone.utc)
        old_claim.valid_until = now
        old_claim.superseded_by = new_claim_id
        old_claim.status = "SUPERSEDED"
        logger.info("CLAIM_SUPERSEDED: %s superseded_by %s (%s)", old_claim_id, new_claim_id, reason)
        return old_claim

    def canonicalize_entity(self, entity_text: str) -> str:
        """Canonicalize entity text to lowercase canonical identifier (Invariant 45 & 46)."""
        clean = entity_text.strip().lower()
        if "cloud run" in clean:
            return "google cloud run"
        if "aws" in clean or "amazon web services" in clean:
            return "amazon web services"
        if "kairo" in clean:
            return "kairo"
        return self._ENTITY_CANONICAL_MAP.get(clean, clean).lower()

    def resolve_entity(self, entity_text: str) -> str:
        """Canonicalize entity text while preventing false merges (Invariant 45 & 46)."""
        return self.canonicalize_entity(entity_text)

    def extract_from_text(
        self,
        text: str,
        source_id: str,
        document_id: str | None = None,
        scope: str = "general",
    ) -> list[Claim]:
        """Extract claims directly from unstructured text string."""
        import uuid

        chunk = DocumentChunk(
            document_id=document_id or f"doc_{uuid.uuid4().hex[:8]}",
            content=text,
        )
        return self.extract_claims_from_chunk(chunk, source_id=source_id, scope=scope)

    def create_claim(
        self,
        subject: str,
        predicate: str,
        object: str,
        claim_text: str,
        source_id: str,
        claim_type: ClaimType = ClaimType.REPORTED,
        supersedes_claim_id: str | None = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MODERATE,
        scope: str = "general",
    ) -> Claim:
        """Programmatically create a verified claim and register it."""
        claim = Claim(
            subject=self.resolve_entity(subject),
            predicate=predicate,
            object=object,
            claim_text=claim_text,
            claim_type=claim_type,
            source_id=source_id,
            confidence=confidence,
            scope=scope,
        )
        self._claims[claim.claim_id] = claim
        if supersedes_claim_id:
            self.supersede_claim(supersedes_claim_id, claim.claim_id)
        return claim

    def _classify_claim_type(self, sentence: str) -> ClaimType:
        """Classify statement into structured epistemological categories."""
        lowered = sentence.lower()

        # 1. Causal claims
        if any(
            term in lowered
            for term in ["caused by", "causes", "led to", "resulting in", "due to", "attributable to"]
        ):
            return ClaimType.CAUSAL

        # 2. Quantitative / Measured claims
        if (
            re.search(r"\b\d+(\.\d+)?\s*(ms|s|%|mb|gb|req/s|rps|usd|\$)\b", lowered)
            or "measured" in lowered
            or "benchmark" in lowered
        ):
            return ClaimType.MEASURED

        # 3. Forecast / Predicted claims
        if any(
            term in lowered
            for term in ["will increase", "will decrease", "projected to", "forecast", "by 202", "by 203"]
        ):
            return ClaimType.PREDICTED

        # 4. Hypothetical claims
        if (
            lowered.startswith("if ")
            or "hypothetically" in lowered
            or "supposing" in lowered
            or "assuming that" in lowered
        ):
            return ClaimType.HYPOTHETICAL

        # 5. Normative / Policy claims
        if any(
            term in lowered
            for term in ["should be", "ought to", "must follow", "mandatory", "required by policy"]
        ):
            return ClaimType.NORMATIVE

        # 6. Opinion / Subjective claims
        if any(
            term in lowered
            for term in ["in our view", "we believe", "superior to", "better than", "arguably", "preferred"]
        ):
            return ClaimType.OPINION

        # 7. Observed direct telemetry
        if any(term in lowered for term in ["observed", "detected", "logged", "telemetry shows"]):
            return ClaimType.OBSERVED

        return ClaimType.REPORTED

    def _parse_spo_triplet(self, sentence: str) -> tuple[str, str, str]:
        """Simple linguistic decomposition into Subject, Predicate, Object."""
        tokens = sentence.split()
        if len(tokens) >= 3:
            # First 1-3 words as subject, middle as predicate, rest as object
            subj = tokens[0]
            if len(tokens) > 4 and tokens[1].lower() in ("is", "was", "are", "were", "has", "have"):
                subj = tokens[0]
                pred = tokens[1]
                obj = " ".join(tokens[2:])
            elif len(tokens) > 5 and tokens[2].lower() in (
                "is",
                "was",
                "are",
                "were",
                "has",
                "have",
                "reduced",
                "increased",
            ):
                subj = f"{tokens[0]} {tokens[1]}"
                pred = tokens[2]
                obj = " ".join(tokens[3:])
            else:
                subj = tokens[0]
                pred = tokens[1]
                obj = " ".join(tokens[2:])
            return subj, pred, obj
        return "Unknown", "asserts", sentence

    def _split_sentences(self, text: str) -> list[str]:
        """Sentence splitter respecting punctuation boundaries."""
        raw_sents = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in raw_sents if s.strip()]


claim_extractor = ClaimExtractor()

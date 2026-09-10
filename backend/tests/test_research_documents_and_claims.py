"""Unit tests for Document Ingestion, Structural Chunking, and Claim Extraction/Versioning (Task 63)."""

from app.research.claims import ClaimExtractor
from app.research.documents import DocumentIngester
from app.research.schemas import ClaimStatus, ClaimType, IngestDocumentRequest, SourceType


def test_document_ingestion_formats_and_chunking():
    ingester = DocumentIngester()

    # Ingest Markdown with headings and paragraphs
    md_content = """# Architecture Evaluation
The distributed edge layer achieves 4ms latency.

## Memory Footprint
System utilizes 256MB of RAM under peak load.
| Metric | Value |
| Latency | 4ms |
| Memory | 256MB |
"""
    req_md = IngestDocumentRequest(
        title="Edge Arch Spec",
        source_type=SourceType.TECHNICAL_REPORT,
        content=md_content,
        format="markdown",
    )
    doc_md = ingester.ingest(req_md)
    assert doc_md.format == "markdown"
    assert len(doc_md.chunks) >= 2
    assert any("Architecture Evaluation" in c.section for c in doc_md.chunks)
    assert any("Memory Footprint" in c.section for c in doc_md.chunks)

    # Ingest JSON
    req_json = IngestDocumentRequest(
        title="Telemetry JSON",
        source_type=SourceType.STRUCTURED_API_DATA,
        content='{"p99_latency_ms": 14.2, "throughput_qps": 8500}',
        format="json",
    )
    doc_json = ingester.ingest(req_json)
    assert doc_json.format == "json"
    assert len(doc_json.chunks) >= 1
    assert any("8500" in c.text for c in doc_json.chunks)

    # Ingest CSV
    req_csv = IngestDocumentRequest(
        title="Benchmark CSV",
        source_type=SourceType.DATASET,
        content="timestamp,latency,cpu\n2026-09-01,15,45\n2026-09-02,14,42",
        format="csv",
    )
    doc_csv = ingester.ingest(req_csv)
    assert doc_csv.format == "csv"
    assert len(doc_csv.chunks) >= 1


def test_claim_extraction_and_classification():
    extractor = ClaimExtractor()
    text = (
        "Independent benchmark measured Model X latency at 12ms under load. "
        "Engineers observed zero dropped frames during stress tests. "
        "Routing changes caused most of the throughput degradation. "
        "We predict throughput will increase by 20% in Q4. "
        "The system should always validate authorization tokens before processing."
    )

    claims = extractor.extract_from_text(
        text=text,
        source_id="src_benchmark_001",
        document_id="doc_001",
    )
    assert len(claims) >= 3

    types = {c.claim_type for c in claims}
    assert ClaimType.MEASURED in types or ClaimType.OBSERVED in types
    assert ClaimType.CAUSAL in types or ClaimType.PREDICTED in types or ClaimType.NORMATIVE in types

    # Check that measured claims carry quantitative structure
    measured_claims = [c for c in claims if c.claim_type == ClaimType.MEASURED]
    if measured_claims:
        mc = measured_claims[0]
        assert mc.subject != ""
        assert mc.confidence in ["HIGH", "MODERATE", "VERY_HIGH"]


def test_entity_canonicalization():
    extractor = ClaimExtractor()
    # Canonicalize known aliases
    canon_1 = extractor.canonicalize_entity("Google Cloud Run")
    canon_2 = extractor.canonicalize_entity("Cloud Run")
    canon_3 = extractor.canonicalize_entity("Google's Cloud Run service")
    assert canon_1 == canon_2 == canon_3 == "google cloud run"

    # Ambiguous/unknown entity
    unknown = extractor.canonicalize_entity("X-Service-Proto")
    assert unknown == "x-service-proto"


def test_claim_temporal_versioning_and_superseding():
    extractor = ClaimExtractor()
    old_claim = extractor.create_claim(
        subject="Model X",
        predicate="supports",
        object="Feature A",
        claim_text="Model X supports Feature A in version 1.0.",
        source_id="src_v1_docs",
        claim_type=ClaimType.OBSERVED,
    )
    assert old_claim.status == ClaimStatus.ACTIVE
    assert old_claim.superseded_by is None

    # New version supersedes old claim
    new_claim = extractor.create_claim(
        subject="Model X",
        predicate="deprecates",
        object="Feature A",
        claim_text="Model X deprecates Feature A in version 2.0.",
        source_id="src_v2_docs",
        claim_type=ClaimType.OBSERVED,
        supersedes_claim_id=old_claim.claim_id,
    )

    updated_old = extractor.get_claim(old_claim.claim_id)
    assert updated_old.status == ClaimStatus.SUPERSEDED
    assert updated_old.superseded_by == new_claim.claim_id
    assert updated_old.valid_until is not None

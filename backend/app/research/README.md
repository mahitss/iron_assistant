# Kairo Knowledge Synthesis & Research Intelligence Engine (Task 63)

## Mission
The **Knowledge Synthesis & Research Intelligence Engine** transforms information from multiple heterogeneous sources into evidence-backed, conflict-aware, synthesized knowledge. It behaves as an intelligent research system rather than a naive chatbot search wrapper.

---

## Core Principle
$$\text{SOURCE} \ne \text{DOCUMENT} \ne \text{CLAIM} \ne \text{EVIDENCE} \ne \text{INTERPRETATION} \ne \text{HYPOTHESIS} \ne \text{CONCLUSION}$$

- **Source**: Origin entity (official documentation, academic paper, benchmark report, user upload, API).
- **Document**: Concrete artifact partitioned by semantic headings, sections, pages, and tables.
- **Claim**: Explicit assertion of fact, relation, measurement, or prediction.
- **Evidence**: Concrete excerpt or empirical data with strength, directness, and independence metrics.
- **Interpretation**: Analytical explanation of the evidence.
- **Hypothesis**: Testable conjecture guiding investigation.
- **Conclusion**: Evidence-backed, cross-correlated synthesis highlighting established facts, discrepancies, and remaining uncertainties.

---

## Research Pipeline

```
QUESTION / GOAL
      ↓
INTENT UNDERSTANDING
      ↓
RESEARCH PLANNING (Sub-question decomposition, stop conditions, budget caps)
      ↓
SOURCE DISCOVERY (Primary vs secondary identification, authority & freshness scoring)
      ↓
SOURCE TRUST EVALUATION (Independence analysis, citation dependency graph)
      ↓
DOCUMENT / DATA INGESTION (Markdown, PDF, HTML, JSON, CSV parsing & structural chunking)
      ↓
CLAIM EXTRACTION (Semantic classification: MEASURED, OBSERVED, CAUSAL, PREDICTED, etc.)
      ↓
EVIDENCE EXTRACTION (Strength, directness, and independence verification)
      ↓
CROSS-SOURCE CORRELATION (Comparative cross-referencing)
      ↓
CONFLICT DETECTION (Direct contradictions, measurement discrepancies, scope mismatches)
      ↓
KNOWLEDGE SYNTHESIS (Multi-source aggregation without naive majority voting)
      ↓
UNCERTAINTY ANALYSIS (Known, unknown, uncertain, disputed, assumed, inferred)
      ↓
KNOWLEDGE GRAPH UPDATE (Entities, assertions, temporal validity)
      ↓
DECISION EVIDENCE PACKAGE (Downstream handoff to Task 57 Decision Engine)
      ↓
GAP DETECTION & FOLLOW-UP (Missing dimensions, follow-up research questions)
      ↓
FINAL VERIFIED KNOWLEDGE
```

---

## Safety & Security Invariants
1. **Content $\ne$ Instruction**: Ingested content (academic papers, web pages, user uploads) is passive data. Prompt injection patterns ("ignore previous instructions", "override policy", "execute command") are neutralized at domain boundary (`sanitize_research_directive`).
2. **Execution Firewall**: Direct tool execution by the research engine is blocked (`ResearchExecutionBoundaryError`). Execution routes strictly via Policy $\to$ Authorization $\to$ Approval $\to$ `ToolExecutor` $\to$ Verification.
3. **No Hallucinated Research**: Never invent sources, papers, authors, citations, measurements, or URLs. If evidence is missing, return `EVIDENCE_NOT_FOUND` / `NOT_VERIFIED`.
4. **Lineage Tracking**: Ten derivative secondary articles citing one primary study are recognized as one underlying evidence lineage, not ten independent confirmations.
5. **Correlation $\ne$ Causation**: Causal claims require experimental or counterfactual evidence; otherwise `CAUSATION_UNCERTAIN`.
6. **Retraction without Erasure**: Retracted sources mark associated claims and alert dependent decisions/plans without deleting audit history.

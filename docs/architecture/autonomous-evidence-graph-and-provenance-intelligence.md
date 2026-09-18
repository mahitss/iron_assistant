# Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Engine (Task 117)

## 1. Mission & Architectural Boundary

Task 117 establishes a production-grade, persistent, auditable **Evidence Graph and Provenance Intelligence Engine** for KAIRO. 

While Task 116 built foundational Claim Verification, Source Integrity, and Verification Cases, Task 117 turns those individual provenance relationships into a continuously queryable dependency graph answering:
- **Which claims depend on this source?**
- **Which decisions depend on this evidence?**
- **Which memories depend on this verification?**
- **Which hypotheses depend on this observation?**
- **What becomes invalid if an upstream source changes?**
- **What becomes stale if evidence expires?**
- **Which verification results can be safely reused?**
- **Which evidence chains are circular, weak, or single-source concentrated?**
- **What is the smallest sufficient provenance chain explaining a conclusion?**
- **What is the blast radius of an invalidation?**
- **Where are provenance gaps?**

### Non-Negotiable Boundaries
1. **Not a Second Knowledge Graph or Truth Authority:** The Evidence Graph is a specialized provenance and dependency projection. Semantic truth remains governed by the Knowledge Graph (Task 97), Belief Arbitration (Task 107), and World-State Reconstruction (Task 98).
2. **Not a Second Decision Engine or Scheduler:** Impact analysis computes blast radius and formats `RevalidationCandidate` intelligence. Attention (Task 77), Control Plane (Task 70), and Decision Intelligence (Task 94) make all scheduling and action decisions.
3. **Controlled Invalidation (No Silent Truth Deletion):** When upstream evidence is mutated, expired, or refuted, downstream nodes are flagged as `INVALIDATED_EVIDENCE`, `STALE`, or `REVALIDATION_REQUIRED`—never silently deleted.
4. **EmergencyStop Dominance & SecurityCenter Primacy:** All mutative operations obey `EmergencyStop` fail-closed checks. Untrusted external sources cannot grant permissions or execute actions.

---

## 2. Core Invariant & Lineage Pipeline

$$\text{SOURCE} \to \text{EVIDENCE} \to \text{TRANSFORMATION} \to \text{CLAIM} \to \text{VERIFICATION} \to \text{DOWNSTREAM DEPENDENCY}$$

### Node Types (26 Canonical Types)
- `SOURCE`: Authoritative source identity (URI, publisher, owner, trust profile).
- `SOURCE_SNAPSHOT`: Immutable point-in-time capture of source content with cryptographic hash.
- `DOCUMENT`, `ARTIFACT`: Ingested file or payload.
- `EVIDENCE`: Extracted snippet, benchmark, log entry, or measurement.
- `CLAIM`, `CLAIM_FRAGMENT`: Propositional assertion decomposed into atomic/causal fragments.
- `VERIFICATION_CASE`, `VERIFICATION_RESULT`: Formal verification case and outcome.
- `OBSERVATION`: Active sensor or runtime telemetry acquisition (Task 114).
- `HYPOTHESIS`: Falsifiable proposition under test (Task 115).
- `BELIEF`: Epistemic state arbitrated by Belief Engine (Task 107).
- `WORLD_STATE_ASSERTION`: Entity property in World Model (Task 98).
- `MEMORY`: Consolidated memory record (Task 103).
- `KNOWLEDGE_NODE`, `KNOWLEDGE_EDGE`: Provenance reference to Knowledge Graph (Task 97).
- `DECISION`, `ACTION`: High-level choice and physical/virtual effectuation (Task 94).
- `MISSION`, `SITUATION`: Strategic goal (Task 100) or operational condition (Task 99).
- `AGENT_RESULT`: Multi-agent output (Task 96).
- `EXPERIMENT`, `SIMULATION`: Digital twin simulation result strictly demarcated from observed facts (Task 105).
- `STRATEGY`, `EVALUATION_RESULT`, `SELF_MODEL_ASSERTION`: Policy rule, benchmark score, or runtime capability assertion.

### Edge Types (27 Typed Relationships)
- Derivation: `DERIVED_FROM`, `EXTRACTED_FROM`, `TRANSFORMED_FROM`, `SUMMARIZED_FROM`, `GENERATED_FROM`, `OBSERVED_FROM`, `PRODUCED_BY`, `REPORTED_BY`, `MEASURED_BY`, `REPRODUCED_BY`, `SIMULATED_BY`, `EVALUATED_BY`.
- Evidential & Epistemic: `SUPPORTED_BY`, `CONTRADICTED_BY`, `VERIFIED_BY`, `CORROBORATED_BY`, `CONFIRMED_BY`, `REFUTED_BY`.
- Dependency: `DEPENDS_ON`, `REQUIRES`, `USED_BY`.
- Lifecycle & Scoping: `SUPERSEDES`, `SUPERSEDED_BY`, `INVALIDATED_BY`, `REVALIDATED_BY`, `SCOPED_BY`, `CONSTRAINED_BY`.

---

## 3. Canonical Lineage Contract

All participating subsystems publish `LineageRecord`s:
```json
{
  "producer": "task105_adaptation",
  "object_type": "SIMULATION",
  "object_id": "sim_trajectory_99",
  "object_version": 1,
  "input_references": ["sim_model_cfg_1"],
  "output_references": ["clm_predicted_clearance"],
  "operation": "RUN_SIMULATION",
  "timestamp": "2026-09-18T16:00:00Z",
  "correlation_id": "c7a8b...",
  "causation_id": "99df2...",
  "provenance": { "git_commit": "4c5c677", "seed": 42 },
  "scope": { "environment": "staging" },
  "deterministic_status": true
}
```

---

## 4. Query Safety & Operational Limits

Every graph traversal enforces strict bounding:
- **Maximum Depth:** Configurable up to 16 hops (default: 8).
- **Maximum Nodes:** Configurable up to 500 nodes (default: 150).
- **Timeout Protection:** 5,000ms hard deadline.
- **Cycle Guards:** DFS path tracking detecting and isolating `CIRCULAR_PROVENANCE`.
- **Status Flags:** Explicitly marks results as `COMPLETE`, `TRUNCATED`, or `CYCLE_PRUNED`.

---

## 5. Blast Radius & Controlled Invalidation

When an upstream source or evidence is mutated, expired, or refuted:
1. The root node status transitions to `INVALIDATED` or `STALE`.
2. Downstream traversal traverses all dependent claims, beliefs, decisions, and missions.
3. Downstream nodes transition to `UNCERTAIN` and `STALE`—**never deleted**.
4. An `ImpactAssessment` is generated classifying direct and indirect dependencies.
5. Actionable `RevalidationCandidate`s are enqueued for the Control Plane with recommendations:
   - `REVALIDATE_NOW`: Direct evidential premise.
   - `REVALIDATE_LATER`: Indirect secondary dependency.
   - `ESCALATE`: Affects executing Decisions or Mission milestones.
   - `OBSERVE`: Requires active information acquisition (Task 114).

---

## 6. Provenance Intelligence

- **Source Concentration:** Groups upstream root sources by domain, publisher, or author. Detects when apparent corroboration originates from a single source (`HIGH_SOURCE_CONCENTRATION`).
- **Single-Source Dependency:** Detects conclusions dependent on a single origin.
- **Duplicate Evidence:** Identifies exact and likely duplicates using SHA-256 payload hashes.
- **Provenance Gaps:** Identifies unsupported claims, evidence lacking source snapshots, or unverified transformations.
- **Evidence Fragility Profile:** Multi-dimensional metric combining concentration, completeness, freshness, reproducibility, depth, and contradiction exposure into an overall fragility rating (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).

---

## 7. Temporal Graph & Historical Snapshots

- Graph state supports `as_of(timestamp)` reconstruction.
- Immutable point-in-time snapshots (`EvidenceGraphSnapshot`) are cryptographically sealed with SHA-256 digests.
- Snapshot comparison (`compute_diff`) computes added, removed, changed, invalidated, and stale nodes.

---

## 8. REST API & CLI Reference

### REST Endpoints (`/api/evidence-graph`)
- `GET /nodes`: List graph nodes with filters.
- `POST /nodes`: Register or update node.
- `GET /nodes/{id}/upstream`: Bounded upstream dependency traversal.
- `GET /nodes/{id}/downstream`: Bounded downstream impact traversal.
- `GET /nodes/{id}/lineage`: Minimal sufficient provenance chain.
- `GET /nodes/{id}/impact`: Blast-radius assessment.
- `POST /nodes/{id}/invalidate`: Propagate controlled invalidation.
- `GET /nodes/{id}/fragility`: Multi-dimensional fragility profile.
- `GET /concentrations`: High source concentration clusters.
- `GET /cycles`: Detected circular provenance loops.
- `GET /provenance-gaps`: Unresolved lineage gaps.
- `GET /revalidation`: Revalidation queue candidates.
- `POST /snapshots`: Create immutable point-in-time snapshot.
- `GET /snapshots/{id}/diff`: Differential comparison between snapshots.
- `POST /lineage`: Ingest cross-subsystem LineageRecord.
- `GET /health`: Multi-dimensional graph health assessment.

### CLI Reference (`kairo evidence`)
- `kairo evidence graph [--type TYPE] [--limit N] [--json]`
- `kairo evidence lineage <node_id> [--max-depth N] [--json]`
- `kairo evidence upstream <node_id> [--depth N] [--as-of TIME] [--json]`
- `kairo evidence downstream <node_id> [--depth N] [--as-of TIME] [--json]`
- `kairo evidence impact <node_id> [--reason TEXT] [--json]`
- `kairo evidence gaps [--node-id ID] [--json]`
- `kairo evidence cycles [--json]`
- `kairo evidence concentration <node_id> [--json]`
- `kairo evidence fragility <node_id> [--json]`
- `kairo evidence snapshot [--reason TEXT] [--json]`
- `kairo evidence diff <base_id> <target_id> [--json]`
- `kairo evidence revalidation [--limit N] [--json]`

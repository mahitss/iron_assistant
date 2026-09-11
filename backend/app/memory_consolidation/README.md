# Kairo Autonomous Knowledge & Memory Consolidation Engine (Task 68)

## Core Cognitive Invariants
- `memory != truth`
- `memory != evidence`
- `summary != source`
- `repetition != independent evidence`
- `retrieval != verification`
- `prediction != event`
- `simulation != experience`
- `agent output != fact`
- `historical memory != current state`
- `user preference != authorization`
- `private memory != public knowledge`

## Architecture Overview
1. **Cognitive Distinctions**: Strict typing separating observations, events, experiences, claims, predictions, simulations, decisions, outcomes, summaries, and derived knowledge.
2. **Deterministic Lifecycle**: 14-state machine (`CAPTURED` -> `CLASSIFIED` -> `VALIDATING` -> `ACTIVE` -> `CONSOLIDATING` -> `CONSOLIDATED` -> `PROMOTED` -> `STALE`/`SUPERSEDED` -> `EXPIRED` -> `FORGOTTEN`/`DELETED`, plus `QUARANTINED` and `CONFLICTED`).
3. **Capture Pipeline**: Secret scrubbing, prompt-injection defense, initial trust scoring, and temporal boundary assignment.
4. **Lineage Provenance**: Complete DAG tracking parents, derived entities, source references, and self-reinforcement defense.
5. **Deduplication Engine**: Exact hash and near-duplicate token overlap with canonical reference linking.
6. **Consolidation & Hierarchical Abstraction**: Clustering of episodic memories into higher-level semantic abstractions (`RAW_OBSERVATION` -> `EPISODE` -> `PATTERN` -> `GENERALIZED_KNOWLEDGE` -> `EXECUTIVE_INSIGHT`).
7. **Contradiction Engine**: Non-destructive evaluation of opposing assertions with temporal and environmental contextualization.
8. **Temporal Validity**: Configurable type-specific decay rates and historical point-in-time validity checking.
9. **Compliance Forgetting**: Safe forgetting with auditable tombstones and cascade updates to indexes and graph edges.
10. **Explainable Retrieval & Context Assembler**: Multi-factor scoring justifications and token-budgeted cognitive context partitioning.

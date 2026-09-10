# Kairo Executive Memory, Long-Horizon Context, and Continuity Subsystem

## Overview
Executive Memory provides Kairo with coherent long-term project continuity across sessions, tasks, goals, decisions, outcomes, blockers, and open loops. It serves as a **grounded synthesis layer** that reconstructs historical states, tracks active work, and answers core continuity questions without competing with canonical authoritative systems.

```
HISTORY → EVENTS → STATE CHANGES → DECISIONS → OUTCOMES → CURRENT STATE → OPEN LOOPS → NEXT OBJECTIVES
```

## The 8 Canonical Continuity Questions
1. **"What were we doing?" / "Where did we stop?"**: Reconstructs recent activity and active open loops from verified task and project state.
2. **"Why did we do it?"**: Traces decision rationales, goals, and evidence without fabricating purpose.
3. **"What changed?"**: Compares historical states and snapshots to summarize verified differences.
4. **"What is currently happening?"**: Synthesizes current operational state directly from authoritative subsystems.
5. **"What remains unfinished?"**: Enumerates active open loops and uncompleted tasks.
6. **"What should happen next?"**: Generates grounded next actions from open loops with user intent supremacy.
7. **"What was true at that time?"**: Performs as-of historical reconstruction bounded by timestamp $T \le X$ with zero future leakage.
8. **"What is blocking us?" / "What are we waiting for?"**: Surfaces evidence-backed blockers and waiting dependencies without speculation.

## Core Invariants & Safety Guarantees
- **No Memory-Only State (Invariant 6)**: Projects and tasks cannot be declared completed simply because memory or conversational context says so; authoritative proof is mandatory.
- **Strict Temporal Isolation (Invariants 20, 21)**: As-of historical reconstruction uses strictly events $\le X$, raising `TemporalLeakageError` if future data is introduced.
- **No Hallucinated Continuity (Invariants 25, 26, 87, 195-201)**: Returns `UNKNOWN` whenever causal provenance, decision rationale, or historical evidence is missing.
- **Authoritative System Supremacy (Invariants 123, 204)**: When conflicts occur between synthesized executive memory and source systems (Projects, Tasks, Goals, World Model), source systems strictly win.
- **User Intent & Priority Supremacy (Invariants 71, 214)**: Current explicit user intent strictly overrides algorithmic recommendations and learned priorities.
- **Safety & Authorization Boundary (Invariants 76, 216-220)**: Executive memory is advisory and cannot execute or authorize actions. Policy, Authorization, Approval, and Verification subsystems remain strictly authoritative.
- **Privacy & Isolation (Invariants 107-112, 187-192)**: Enforces strict tenant, project, and user isolation, and redacts sensitive credentials/tokens from summaries.

## Architecture & Module Layout
- `schemas.py`: Domain data models and enums.
- `models.py`: SQLAlchemy database models.
- `safety.py`: `ExecutiveSafetyGuard` enforcing strict invariants.
- `temporal.py`: Authoritative UTC timestamping and conflict preservation.
- `provenance.py`: Audit tracking and citation of source systems.
- `timeline.py`: Event ingestion, deduplication, and chronological queries.
- `state_reconstruction.py`: Time-travel as-of state reconstruction.
- `projects.py`, `goals.py`, `tasks.py`: Continuity managers for work structures.
- `decisions.py`, `outcomes.py`, `history.py`: Decision lineage and attempt tracking.
- `milestones.py`, `commitments.py`: Verifiable milestone and commitment trackers.
- `open_loops.py`, `blockers.py`: Unfinished work and blocker causality engines.
- `priorities.py`, `next_actions.py`: Grounded action engines respecting user intent.
- `summaries.py`, `snapshots.py`, `checkpoints.py`: Briefings, snapshots, and recovery checkpoints.
- `reconciliation.py`: Divergence detection with source system override.
- `privacy.py`: Cross-context leak prevention and secret redaction.
- `evaluation.py`: Continuous measurement of false continuity rates and latency.
- `service.py`: `ExecutiveMemoryService` central orchestrator.
- `router.py`: REST API endpoints under `/api/v1/executive-memory`.

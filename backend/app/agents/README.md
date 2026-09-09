# Kairo Multi-Agent Collaboration & Collective Intelligence Engine (Task 44)

## Overview

The **Kairo Multi-Agent Collaboration Engine** enables multiple specialist agents to cooperate on complex goals while enforcing strict structural boundaries:
- **Agents are collaborators, NOT independent authorities.**
- **No agent may bypass Policy, Authorization, ToolExecutor, Verification, or Audit.**
- **Capability $\neq$ Authorization.** An agent being technically capable of a tool or deployment does not grant authorization.
- **Contract Principle.** Agents operate strictly within their active `AgentContract` (resources, tools, budget, data).
- **No Silent Scope Expansion.** Discovered needs require an explicit expansion request reviewed by the supervisor.
- **Evidence-First Truth.** 1 verified empirical evidence point defeats 3 unverified votes. Majority vote is never a substitute for empirical verification.
- **Consensus $\neq$ Verification.** Consensus is a derived observation, not an authority.
- **Parallelism & Locks.** Read-only workloads execute in parallel; shared mutable resources require coordinated serialization via read leases and write locks.
- **Blind Review.** Disagreements strip agent identities to prevent halo and authority bias during resolution.

```
GOAL
  ↓
SUPERVISOR
  ↓
DECOMPOSE
  ↓
DELEGATE
  ↓
SPECIALISTS (Bounded by AgentContracts)
  ↓
EVIDENCE (FACT, INFERENCE, HYPOTHESIS, RECOMMENDATION)
  ↓
SYNTHESIS (Conflict Preservation & Provenance)
  ↓
VERIFY (Independent Verifier)
  ↓
RESULT
```

---

## Core Architecture

```
backend/app/agents/
├── agent.py          # Specialist Agent model, 14 roles, resource budgets, health
├── capabilities.py   # Fine-grained capability definitions; Capability != Authorization
├── contracts.py      # Bounded AgentContract, scope validation, expansion requests
├── delegation.py     # Task delegation tree, 1 primary owner, loop detection, spawn limits
├── collaboration.py  # Resource leases, write locks, 3-way structured diff merges
├── messages.py       # Scoped inter-agent messaging, hash deduplication, priority queues
├── workspace.py      # Isolated agent workspaces, shared team artifacts with versioning
├── evidence.py       # EvidencePool, fact classification, source and model diversity
├── disagreement.py   # Evidence-first disagreement resolver, blind review formatting
├── consensus.py      # Derived consensus evaluator, prevents false consensus & collusion
├── synthesis.py      # SynthesisEngine, conflict-preserving collective intelligence
├── routing.py        # Domain specialist routing; policy constraints dominate
├── budgets.py        # Token, tool, time, and cost budgets; BLOCKED/BUDGET_EXHAUSTED
├── isolation.py      # Cross-user/project tenant isolation, prompt injection defense
├── lifecycle.py      # 9-state formal lifecycle management & transition validation
├── health.py         # Agent health states, heartbeat monitors, quarantine governance
├── recovery.py       # Checkpoints, authorized handoffs, human escalation triggers
├── evaluation.py     # Risk-based team composition, minimal team principle
├── provenance.py     # Full causal provenance DAG (Goal -> Supervisor -> Subtask -> Contract -> Agent -> Evidence -> Result)
├── schemas.py        # Pydantic request/response models for all collaboration APIs
├── router.py         # FastAPI REST endpoints under /api/v1/collaboration
└── registry.py       # Agent discovery, capability & version lookups, health checks
```

---

## Key Invariants

1. **Task Ownership:** Every delegated subtask has exactly 1 primary owner. Collaborative contributors publish evidence to the shared workspace rather than concurrently mutating the primary resource.
2. **Backpressure & Loop Protection:** Spawning depth is bounded (default depth $\le 4$) and concurrent active agents are capped (default $\le 10$). Circular delegation ($A \to B \to A$) is detected and halted.
3. **Emergency Stop:** A supervisor or operator emergency stop halts all active agents, contracts, and subtasks across the session immediately.
4. **Tenant Isolation:** Cross-user and cross-project data leakage is rejected by default.
5. **No Self-Approval:** An agent cannot approve its own privileged actions or grant permissions to peers.

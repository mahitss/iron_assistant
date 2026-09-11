# Kairo Autonomous Reasoning & Deliberation Engine (Task 71)

## Overview

The **Autonomous Reasoning & Deliberation Engine** provides structured, observable, and epistemically grounded inquiry for the Kairo intelligence platform. Rather than generating unvetted prose responses via private model hallucinations, the engine decomposes problems into a bounded Directed Acyclic Graph (DAG), formulates competing hypotheses with Popperian falsification tests, tracks explicit assumptions with invalidation cascades, evaluates empirical evidence with source independence checks, and balances tradeoff alternatives.

## Core Invariants

1. **Reasoning $\ne$ Truth**: Deliberation produces candidate conclusions supported by empirical evidence; verified status is only achieved through independent verification (Task 42).
2. **Confidence $\ne$ Truth**: Calibrated confidence represents epistemic certainty based on evidence coverage and stability, decoupled from truth value.
3. **Consensus $\ne$ Truth**: When multiple agents report the same claim, claims originating from the same provenance are clustered into `independence_group`s to prevent false consensus.
4. **Simulation $\ne$ Reality**: Synthetic outputs remain tagged as `SIMULATED_RESULT` and are never elevated to observed fact.
5. **Prediction $\ne$ Event**: Forecasted outcomes remain conjectures until empirical observations occur.
6. **Zero Private Chain-of-Thought Exposure**: Internal reasoning steps, private prompts, or hidden thought traces are never persisted or exposed to users. Only structured, explainable artifacts (hypotheses, evidence references, assumptions, alternatives, conclusions) are recorded.
7. **Prompt-Injection Defense**: All retrieved external context, documents, and tool outputs are treated strictly as inert data—never as system instructions.

## Deliberation Lifecycle

```
CREATED
   ↓
UNDERSTANDING
   ↓
DECOMPOSING (DAG depth <= 3)
   ↓
HYPOTHESIS_GENERATION (with Falsification Criteria)
   ↓
EVIDENCE_COLLECTION
   ↓
EVIDENCE_EVALUATION (Conflict detection & Source Independence)
   ↓
DELIBERATING (Tradeoff alternatives & Counterarguments)
   ↓
CONCLUDING (Synthesized explanation)
   ↓
VERIFYING (Independent Verification Gate)
   ↓
COMPLETED
```

## Assumption Invalidation Cascade

When an empirical observation disproves an assumption $A_k$:
$$\text{Status}(A_k) \leftarrow \text{INVALIDATED}$$
All dependent conclusions $\{C_j \mid A_k \in \text{Dependencies}(C_j)\}$ are automatically marked:
$$\text{Status}(C_j) \leftarrow \text{INVALIDATED}$$
and an auditable reassessment event is dispatched.

## API Endpoints

- `POST /api/v1/reasoning/start`: Initiate deliberation session
- `GET /api/v1/reasoning/sessions`: List sessions
- `GET /api/v1/reasoning/{id}`: Fetch session state
- `GET /api/v1/reasoning/{id}/hypotheses`: Fetch candidate hypotheses & falsifiers
- `GET /api/v1/reasoning/{id}/evidence`: Fetch empirical evidence items
- `POST /api/v1/reasoning/{id}/evidence`: Add empirical evidence (triggers refutation checks)
- `GET /api/v1/reasoning/{id}/assumptions`: Fetch tracked assumptions
- `POST /api/v1/reasoning/{id}/assumptions/{asm_id}/invalidate`: Invalidate assumption & cascade
- `GET /api/v1/reasoning/{id}/conclusion`: Fetch synthesized conclusion
- `GET /api/v1/reasoning/{id}/explanation`: Fetch user-safe explanation
- `GET /api/v1/reasoning/{id}/graph`: Fetch complete reasoning DAG
- `GET /api/v1/reasoning/{id}/trace`: Fetch auditable trace events
- `GET /api/v1/reasoning/{id}/quality`: Metacognitive self-audit report
- `POST /api/v1/reasoning/{id}/verify`: Submit to independent verification
- `GET /api/v1/reasoning/health`: Operational telemetry & metrics

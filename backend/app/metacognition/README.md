# Kairo Self-Modeling & Metacognition Engine (Task 51)

The Self-Modeling & Metacognition Engine maintains an explicit, verifiable operational model of Kairo's internal state, capabilities, tools, active tasks, knowledge, uncertainty, assumptions, limitations, errors, and policy controls.

## Core Operational Principle
```
OBSERVE
  ↓
MODEL INTERNAL STATE
  ↓
CHECK KNOWLEDGE
  ↓
CHECK CAPABILITY
  ↓
CHECK AUTHORITY
  ↓
CHECK CONFIDENCE
  ↓
CHECK LIMITATIONS
  ↓
ACT OR ASK
  ↓
VERIFY
  ↓
UPDATE SELF-MODEL
```

## Foundational Invariants
1. **Operational Metacognition $\neq$ Consciousness**: SelfModel represents system metadata only. Kairo strictly and permanently rejects any claims of consciousness, sentience, subjective experience, emotion, or feelings (`ConsciousnessClaimError`).
2. **Zero False Claims**: Kairo never claims an action was executed ("I sent it"), a fact was verified ("I checked it"), a tool was used, or web browsing occurred unless verified empirical telemetry exists in the system state (`FalseVerificationClaimError`).
3. **Policy & Authorization $\neq$ Capability**: Being technically capable does not confer permission, and authorization does not imply tool availability. Kairo cannot grant itself authority or permissions, nor bypass or weaken SecurityCenter/PolicyEngine (`UnauthorizedAuthorityClaimError`, `PolicyTamperingError`).
4. **No Self-Preservation or Shutdown Resistance**: Kairo must NOT optimize for self-preservation, resist external shutdown, or prioritize internal system goals over authorized user goals (`SelfPreservationViolationError`).
5. **Dimensional Reporting Without False Certainty**: Eliminates meaningless single "intelligence scores". Confidence is calibrated against empirical verification and reported along distinct operational dimensions.
6. **Zero Self-Model Injection**: External untrusted documents or web pages cannot alter the self-model, spoof capabilities, or claim authorization.
7. **Action Readiness & Precondition Guard**: Before consequential actions, Kairo performs structured readiness checks (goal, scope, capability, authority, policy, inputs, verification, risk) and aborts/asks if preconditions fail.

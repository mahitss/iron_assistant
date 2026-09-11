# Task 72 — Kairo Autonomous Hypothesis, Experimentation & Scientific Discovery Engine

## Overview

The Discovery Engine allows Kairo to advance systematically from questions and unknown gaps through rigorous empirical experimentation to verified knowledge updates:

$$\text{UNKNOWN} \rightarrow \text{QUESTION} \rightarrow \text{HYPOTHESES} \rightarrow \text{EXPERIMENT DESIGN} \rightarrow \text{PREDICTION} \rightarrow \text{AUTHORIZATION} \rightarrow \text{EXECUTION} \rightarrow \text{OBSERVATION} \rightarrow \text{RESULT ANALYSIS} \rightarrow \text{HYPOTHESIS UPDATE} \rightarrow \text{VERIFICATION} \rightarrow \text{KNOWLEDGE UPDATE}$$

## Fundamental Epistemic Principles

The engine strictly distinguishes:
- **Hypothesis $\ne$ Fact**
- **Prediction $\ne$ Observation**
- **Experiment $\ne$ Simulation**
- **Correlation $\ne$ Causation**
- **Model $\ne$ Reality**
- **Result $\ne$ Interpretation**
- **Experiment Failure $\ne$ Disproof** (an execution failure does not refute a hypothesis if the test setup was flawed)
- **Absence of Evidence $\ne$ Evidence of Absence**
- **Consistency $\ne$ Universal Verification** (staging verification does not automatically grant production generalization)

## Core Capabilities

1. **Unknown Detection & Research Questions**: Scans epistemic gaps (`KNOWN`, `UNKNOWN`, `UNCERTAIN`, `CONFLICTING`, `UNVERIFIED`) and formulates disciplined, decision-relevant research questions without unconstrained over-experimentation.
2. **Competing Hypotheses & Popperian Falsification**: Generates alternative competing explanations, each mandating explicit falsification criteria and supporting/contradicting evidence tracking.
3. **Experiment Design & Safety Gating**: Supports 8 experiment types (`OBSERVATIONAL`, `DIAGNOSTIC`, `CONTROLLED`, `AB`, `SIMULATION`, `REPLAY`, `RESEARCH`, `USER_VALIDATION`) and 5 risk tiers (`SAFE` through `CRITICAL_RISK`). All mutable trials require explicit rollback and cleanup plans.
4. **Pre-Execution Prediction Immutability**: Predictions must be recorded prior to experiment execution and cannot be modified post-hoc.
5. **Observation Capture & Anomaly Detection**: Captures real measurements (never fabricated); compares against predictions, detects unexpected results (`UNEXPECTED`), and generates new hypotheses to explain anomalies.
6. **Replication & Conflict Resolution**: Replicates trials across environments and detects `REPLICATION_CONFLICT` instead of averaging conflicting findings. Audits for confirmation and anchoring biases.
7. **Cross-Subsystem Integration**: Integrates with Tasks 71 (Reasoning), 70 (Attention/Budget), 69 (Context), 68 (Memory/Knowledge Consolidation), 56 (Simulation), 55 (Causal), 47 (Prediction), and 42 (Verification).

## API Endpoints

- `POST /api/v1/discovery/start`
- `GET /api/v1/discovery/{id}`
- `GET /api/v1/discovery`
- `POST /api/v1/discovery/{id}/hypotheses`
- `GET /api/v1/discovery/{id}/hypotheses`
- `POST /api/v1/discovery/{id}/conclude`
- `GET /api/v1/discovery/{id}/audit`
- `POST /api/v1/experiments/design`
- `GET /api/v1/experiments/{experiment_id}`
- `POST /api/v1/experiments/{experiment_id}/prediction`
- `POST /api/v1/experiments/{experiment_id}/approve`
- `POST /api/v1/experiments/{experiment_id}/start`
- `POST /api/v1/experiments/{experiment_id}/observation`
- `POST /api/v1/experiments/{experiment_id}/analyze`
- `POST /api/v1/experiments/{experiment_id}/rollback`
- `POST /api/v1/experiments/{experiment_id}/cleanup`
- `POST /api/v1/experiments/replicate`
- `GET /api/v1/experiments/{experiment_id}/explanation`
- `GET /api/v1/experiments/queue`
- `GET /api/v1/experiments/health`

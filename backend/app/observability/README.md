# Kairo Unified Observability & System Intelligence

## Core Purpose
The Observability layer answers **WHAT HAPPENED** across the entire lifecycle of commands, intents, policies, autonomous tasks, multi-agent operations, tools, and model providers.

### Absolute Separation of Concerns
- **Observability**: Explains *WHAT HAPPENED* (latency, traces, errors, execution graph).
- **Audit**: Explains *WHAT MUST BE ACCOUNTABLE* (immutable security log).
- **Policy**: Explains *WHAT WAS ALLOWED* (governance rules, risk tiers, approvals).
- **Model**: Explains *WHAT IT PROPOSED* (candidate intents, plans).
- **Task Engine**: Explains *WHAT IT EXECUTED* (task steps, state transitions).

---

## Architectural Components

1. **Distributed Tracing (`tracing.py`, `spans.py`, `correlation.py`)**:
   - Trace hierarchy: `COMMAND` $\rightarrow$ `INTENT` $\rightarrow$ `POLICY` $\rightarrow$ `TASK` $\rightarrow$ `AGENT` $\rightarrow$ `TOOL` $\rightarrow$ `VERIFICATION`.
   - `contextvars` context propagation ensuring parent-child span integrity across asynchronous coroutines.
2. **Telemetry Sanitizer (`sanitization.py`)**:
   - Automatic secret scrubbing (API keys, bearer tokens, passwords, cookies).
   - Log injection defense (newline and control character escaping).
   - Prompt hash and token counts preserved without retaining raw user prompts.
3. **Structured Logging (`logs.py`)**:
   - Structured JSON logging with trace and span correlation.
4. **Metrics & Cardinality Defense (`metrics.py`)**:
   - Thread-safe collector for counters, gauges, and histograms.
   - Strict cardinality bounds preventing label bloat.
5. **Sampling & Backpressure (`sampling.py`, `exporters.py`)**:
   - 100% error and security event capture.
   - Non-blocking export isolation ensuring telemetry failures never halt core application logic.
6. **Root-Cause Analysis (`root_cause.py`)**:
   - Evidence-backed RCA requiring concrete observable metrics.
   - Diagnostic only — never performs automated remediation.
7. **Operational Incidents (`incidents.py`)**:
   - Automated correlation of related component failures into single incidents.
   - Evidence-backed resolution requirement.
8. **Dynamic Service Map (`dependencies.py`)**:
   - Live topology graph generated from actual span telemetry.

# Changelog

All notable changes to Kairo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-08

### Added
- **Core Architecture Convergence**:
  - FastAPI asynchronous backend with centralized model routing and tool orchestration.
  - Single-source-of-truth `ModelRouter` with fallback capability cascades and latency/cost optimization.
  - Centralized `ToolRegistry` and `ToolExecutor` governing all built-in, developer, browser, and research tools.
  - Multi-tiered long-term memory architecture combining pgvector semantic embeddings, PostgreSQL relational storage, and LRU cache.
  - Ephemeral Redis cache layer for rate limiting, distributed lock coordination, and transient session caches (zero authoritative state in Redis).
- **Security Center & Policy Engine**:
  - Authoritative `SecurityCenter` enforcing pre-execution gates, risk classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and human-in-the-loop approvals.
  - Cryptographic action fingerprinting to prevent approval reuse, race conditions, or parameter tampering.
  - Time-bounded, user-scoped approval requests with automatic expiration.
  - Global and user-scoped Emergency Stop kill switch that immediately halts side-effecting operations across all agents, tools, and workflows.
  - Immutable, append-only security audit log recording every tool authorization, approval, denial, and emergency stop.
- **Multi-Agent Orchestration**:
  - `SupervisorAgent` with query complexity classification, task decomposition, and dynamic DAG planner.
  - Specialized worker agents: `ResearcherAgent`, `DeveloperAgent`, `AnalystAgent`, and `BrowserAgent`.
  - Evidence classification taxonomy strictly segregating `OBSERVED` facts, `INFERRED` hypotheses, and `UNKNOWN` variables.
  - Explicit delegation depth limits (max depth 1) preventing recursive or runaway agent loops.
  - Verification and citation preservation with bracketed numeric citations (`[1]`, `[2]`).
- **Automation & Workflow Engine**:
  - Scheduled and event-driven automation engine with timezone-aware cron triggers.
  - Deterministic idempotency key generator (`sched_{workflow_id}_{timestamp}`) preventing duplicate side effects across distributed workers.
  - Condition evaluation engine for branching workflows without dynamic code execution or `eval()`.
  - Human approval gating on high-risk workflow steps.
- **Proactive Intelligence**:
  - Continuous event monitor for CI check failures, pending approvals, and scheduled workflow degradations.
  - SHA-256 candidate insight fingerprinting and 24-hour deduplication window.
  - User preference filters, priority thresholds, quiet hours, and rate-limited notification dispatch.
- **Controlled Interaction Channels**:
  - Local-only voice pipeline featuring wake-word detection, STT transcription, and TTS synthesis with explicit mic session gating.
  - Vision processing pipeline supporting image validation, resolution limits, and temporary disk cleanup.
  - Local desktop computer interaction gated behind explicit user configuration, capability toggles, and human approval.
- **Developer Intelligence**:
  - Git repository inspection tools (`git_status`, `git_branches`, `git_log`, `git_diff`, `code_search`, `code_read_file`, `code_analyze`).
  - Gated test runner (`test_runner`) with strict argument sanitization, no shell execution, and SecurityCenter authorization.
- **Cloud Infrastructure & Release Engineering**:
  - Production containerization with multi-stage Docker build, unprivileged `kairo` user (`uid 10001`), and read-only container root support.
  - Nginx reverse proxy configuration with TLS 1.3, CSP, HSTS, rate limiting zones, and SSE streaming buffer disabling (`X-Accel-Buffering: no`).
  - GitHub Actions CI/CD workflows for linting, typing, 427-test automated suite, security vulnerability scanning, and Docker builds.
  - Comprehensive operational documentation: deployment, staging, rollback, incident response, operations, and security threat model.

### Changed
- Standardized API endpoints to semantic `/api/v1/` routes.
- Unified model capability resolution across single-agent and multi-agent workflows.
- Configured Circuit Breaker (`CircuitBreaker`) on external LLM providers to fail-fast during provider outages and prevent thread pool exhaustion.
- Enforced strict user data isolation across database queries, vector memory, approvals, and notifications.

### Security
- **Untrusted Input Sanitization**: Implemented `AgentSecurityPolicy.sanitize_untrusted_input` disarming prompt injection and system override attempts in external web pages, repository files, issue bodies, and DOM text.
- **Credential Scrubbing**: Integrated `MemorySanitizer` redacting API keys, Bearer tokens, AWS keys, GitHub PATs, and passwords before long-term memory storage.
- **Subprocess Hardening**: Guaranteed all external processes (`git`, `pytest`) run via `asyncio.create_subprocess_exec` with explicit argument lists and `shell=False`.
- **Secret Redaction**: Configured audit logging, error handlers, and HTTP response formatters to scrub sensitive credentials and environment variables.

### Infrastructure
- Automated database migration management via Alembic.
- Health check endpoints (`/health/live`, `/health/ready`, `/health/startup`, `/health/version`) exposing semantic version, git commit SHA, and database/Redis liveness without credential exposure.
- Zero-downtime rolling update deployment workflows with automated smoke validation and rollback automation.

### Bug Fixes
- Fixed approval validation race condition by enforcing single-use action fingerprints.
- Fixed scheduler double-execution bug on distributed worker restarts using atomic Redis locks with deterministic fallback.
- Fixed streaming SSE buffer termination under reverse proxies by propagating explicit header directives.

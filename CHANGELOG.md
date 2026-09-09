# Changelog

All notable changes to Kairo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-09-09

### Added
- **Personal Context Engine**:
  - Centralized `ContextEngine` managing active user context, project affinity, recent working history, and relevant semantic memories.
  - Multi-tier ranking algorithm combining semantic relevance, recency decay, and importance scoring.
  - Explainable provenance tracking: every injected context snippet provides clear user-inspectable provenance and confidence without exposing internal weights.
  - Risk-aware context disambiguation: when user instructions are ambiguous across multiple project workspaces, Kairo prompts for explicit clarification rather than guessing.
  - Context preference controls: granular user toggles for memory retrieval, project context injection, active git context, and recent history depth.
- **Project Workspaces**:
  - Full project workspace management with dedicated tables (`projects`, `project_repositories`, `project_workflows`, `project_conversations`).
  - Strict user-level tenant isolation: users can only inspect, modify, link, or archive projects they own.
  - Repository linking with primary branch detection and primary repository flags.
  - Workflow and conversation association linking automations directly to projects.
  - Project archival and deletion cascading with foreign key constraints.
- **Unified Command Center UI**:
  - Cohesive single-window interface unifying Chat, Personal Context, Projects, Automations, Activity & Audit Logs, Security Center, Memory Management, and System Status.
  - Command Palette (`Ctrl+K` / `Cmd+K`) for fast, keyboard-driven navigation, project switching, and action execution.
  - Real-time reactive state store with centralized event dispatch and persistent preferences.
  - Context Inspector drawer allowing users to inspect active memory provenance, tokens, and relevance scores.
  - Global Security Banner & Emergency Stop accessible from any view with visual feedback.
  - Mobile-responsive navigation and WCAG 2.1 AA accessible keyboard navigation and ARIA landmarks.
- **Comprehensive Integration, Stress Testing & Hardening**:
  - Full end-to-end integration test suite (`test_v1_1_integration_stress.py`) verifying schema integrity, auth lifecycle, tenant isolation, streaming SSE, prompt injection defenses, emergency stop blocking, and multi-agent cancellation.
  - Concurrency and load testing verifying zero race conditions under 10, 25, and 50 concurrent requests.
  - Deterministic 20-step verification demo (`scripts/demo_v1_1_scenario.py`).

- **Release Engineering & Operations Automation**:
  - Authoritative unified application versioning (`1.1.0`) exposed safely at `GET /health/version` without credential leakage.
  - Full Operations Dashboard endpoint at `GET /health/operations` reporting uptime, request counts, error rates, average latency, and health statuses for all 8 subsystems (database, redis, model, automations, agents, security, github, browser).
  - Structured Incident Identifier generator (`generate_incident_id`) generating format `INC-YYYYMMDDHHMM-<uuid>` for correlated log, metric, trace, and audit event triage.
  - Automated smoke test suite (`scripts/smoke_test.py`) with support for live staging/production probes and in-process TestClient execution.
  - Complete 14-step release simulation suite (`scripts/release_simulation.py`) enforcing canonical release pipeline: `CODE -> CI -> TEST -> SECURITY SCAN -> BUILD -> STAGING -> SMOKE TEST -> APPROVAL -> PRODUCTION -> HEALTH -> MONITOR -> ROLLBACK IF NECESSARY`.
  - Automated Software Bill of Materials generator (`scripts/generate_sbom.py`) generating CycloneDX-compatible dependency manifests.

### Changed
- **CI/CD Pipeline Separation**:
  - Modularized GitHub Actions into discrete single-responsibility workflows: `ci.yml` (PR tests and builds), `security.yml` (SAST, secret scanning, dependency audit), `build.yml` (immutable Docker artifact builds with Git SHA & version tags), `staging.yml` (staging deployment and automated smoke tests), and `release.yml` (production deployment gated by manual environment approval).
  - Production deployments strictly consume exact staging-tested container artifacts; image rebuilding between staging and production is prohibited.

### Fixed
- **Release Verification & Schema Health**:
  - Enforced expand/contract database migration pattern across releases, guaranteeing application rollbacks to previous immutable artifacts remain compatible without destructive database downgrades.
  - Fixed sys.path resolution in release scripts and test runners.

### Security
- **Strict Multi-Tenant Isolation & Audit Operations**:
  - Enforced `user_id` authorization scoping across all long-term memory CRUD endpoints (`/api/v1/memory`, `/api/v1/internal/memories`).
  - Added user ownership validation on all Project CRUD, repository linking, and workflow association endpoints.
  - Cross-user approval hijacking prevention: decisions made on approvals owned by other users are rejected with `TenantIsolationError`.
  - Zero secrets exposure verified across all telemetry, operations dashboard, and release manifests.

### Infrastructure
- **Operational Runbooks & Incident Response**:
  - Created 13 operational runbooks under `docs/runbooks/`: `deploy.md`, `rollback.md`, `api-down.md`, `database-down.md`, `redis-down.md`, `provider-outage.md`, `high-error-rate.md`, `high-latency.md`, `workflow-failures.md`, `agent-failures.md`, `auth-incident.md`, `secret-compromise.md`, and `emergency-stop.md`.
  - Standardized `docs/release-checklist.md` with explicit CODE, BUILD, STAGING, DATABASE, PRODUCTION, and ROLLBACK verification gates.
- **Database Migration 0006**:
  - Added Alembic migration `0006_personal_context_and_projects.py` registering all project and context tables, indexes, and foreign keys.
  - Base metadata synchronized across all 23 database tables ensuring clean zero-state setup.
- **Circular Dependency Elimination**:
  - Decoupled `app.context` from `app.agents` import graph, eliminating module initialization race conditions.
- **Memory Service Signature Alignment**:
  - Aligned `MemoryService.create_memory` with caller contracts, ensuring robust multi-tenant memory creation.

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

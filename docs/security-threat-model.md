# Kairo Security Threat Model & Risk Analysis

This document outlines the 16 core threat categories analyzed for Kairo, identifying attack surfaces, potential impacts, implemented architectural mitigations, and residual risk management strategies.

---

## Threat Matrix Overview

| ID | Threat Category | Severity | Primary Defense | Residual Risk |
|---|---|---|---|---|
| TM-01 | Prompt Injection & Jailbreaking | High | Tool Schema Enforcement, Security Center | Untrusted external text |
| TM-02 | Server-Side Request Forgery (SSRF) | High | URL Sanitization & IP Blacklisting | Dynamic DNS rebinding |
| TM-03 | Arbitrary Code Execution | Critical | Sandboxing, Human-in-the-Loop Approval | Malicious approved commands |
| TM-04 | Browser Hijacking & DOM Exploits | High | Headless Isolation, Download Blockers | Zero-day browser vulnerabilities |
| TM-05 | Git / GitHub Credential Leakage | Critical | Scoped Tokens, Secret Redaction, Read-Only Defaults | User committing tokens |
| TM-06 | Denial of Service (DoS) & Request Floods | High | Sliding-Window Rate Limiting, Body Size Limits | Distributed volumetric floods |
| TM-07 | Unauthorized Privilege Escalation | Critical | Role-Based Access Control, Session Verification | Compromised admin session |
| TM-08 | IDOR on Workflows & Agent Tasks | High | User-Scoped Authorization Checks | Cross-tenant scoping errors |
| TM-09 | Sensitive Data Exposure in Logs | Medium | StructuredJsonFormatter Redaction Engine | Novel unmodeled secret formats |
| TM-10 | Memory & Vector Store Poisoning | Medium | Input Sanitizer, Memory Scrubbing Layer | Subtle semantic bias |
| TM-11 | Stolen Session Tokens & Replay Attacks | High | PBKDF2 Hashes, Idle Timeout, Absolute TTL | Compromised client machine |
| TM-12 | Database Connection Pool Exhaustion | Medium | Connection Pooling, Health Pre-Ping, Recycle | Extremely high concurrency spikes |
| TM-13 | LLM Provider Outage / Failures | High | Circuit Breaker, Exponential Jitter Retries | Extended upstream outage |
| TM-14 | Uncontrolled Notification Storms | Medium | Proactive Deduplication & Rate Throttling | Misconfigured alert rules |
| TM-15 | Orphaned Background Agents / Runaway Tasks | High | Startup Stale Recovery, Step & Budget Limits | Host node hard power loss |
| TM-16 | Emergency Stop Bypass / Invalidation | Critical | Authoritative Security Center, Rate Limit Exemption | Kernel-level process freeze |

---

## Detailed Threat Category Analysis

### TM-01: Prompt Injection & Jailbreaking
- **Attack Surface:** User chat input, external web research content, parsed Git commit messages, issue descriptions, and browser DOM text ingested into the prompt context.
- **Potential Impact:** LLM model hijacked into executing unauthorized tools, leaking private conversations, or bypassing safety guardrails.
- **Implemented Mitigations:**
  - Strict separation of system instructions and untrusted content blocks.
  - LLMs cannot directly execute actions; all actions must resolve to structured Pydantic tool schemas validated by `ToolRegistry`.
  - Authoritative `SecurityCenter` intercepts every tool execution regardless of LLM confidence or formatting.
- **Residual Risk & Recommendations:** Untrusted web text may mislead the model into requesting high-risk tool calls. Mitigated by strict human approval requirements on high-risk operations.

### TM-02: Server-Side Request Forgery (SSRF)
- **Attack Surface:** Web research tool (`research_web`), web fetch tool, and Playwright navigation targeting internal cloud metadata endpoints (e.g., `169.254.169.254`, `localhost`, private subnets `10.0.0.0/8`, `192.168.0.0/16`).
- **Potential Impact:** Extraction of cloud instance credentials, internal service discovery, or unauthenticated internal API invocation.
- **Implemented Mitigations:**
  - URL scheme restricted strictly to `http` and `https`.
  - Hostname resolution validation blocking loopback and RFC 1918 private IP addresses.
  - Cloud metadata IP ranges (`169.254.169.254`) explicitly blocked before network dispatch.
- **Residual Risk & Recommendations:** DNS rebinding attacks where a public domain resolves to a private IP after initial inspection. Recommend network-level egress filtering (e.g., AWS Security Group / iptables) blocking container egress to link-local metadata addresses.

### TM-03: Arbitrary Code Execution (Computer Control & Shell Execution)
- **Attack Surface:** Developer tools (`execute_command`, `git_push`), local terminal execution, and controlled computer interaction.
- **Potential Impact:** Unauthorized host filesystem modification, ransomware deployment, privilege compromise, or data destruction.
- **Implemented Mitigations:**
  - Computer control toggle is disabled by default (`COMPUTER_CONTROL_ENABLED=false`).
  - Terminal commands are restricted to pre-approved developer tool lists.
  - High-risk operations mandate explicit human approval through `SecurityCenter` with a 10-minute timeout defaulting to `DENIED`.
  - Emergency stop immediately terminates running subprocesses.
- **Residual Risk & Recommendations:** A human operator might blindly approve a dangerous command. Enforce least-privilege containerization so commands execute only in sandboxed environments.

### TM-04: Browser Hijacking & Malicious DOM Execution
- **Attack Surface:** Playwright headless browser navigating to untrusted third-party websites during research or automation.
- **Potential Impact:** Cross-site scripting (XSS), drive-by downloads, crypto-mining, or browser escape exploits.
- **Implemented Mitigations:**
  - Headless Chromium runs in an isolated ephemeral context with disabled file downloads.
  - Strict per-navigation timeouts (15 seconds).
  - Navigation restricted to view/extract text without persisting cookies, local storage, or session credentials across unrelated tasks.
- **Residual Risk & Recommendations:** Zero-day Chromium sandbox escape vulnerabilities. Keep Playwright/Chromium versions continuously updated via automated CI dependency scanning.

### TM-05: Git & GitHub Credential Leakage & Malicious Manipulation
- **Attack Surface:** Local Git operations (`git status`, `git commit`, `git push`), GitHub API integration (`inspect_prs`, `inspect_issues`), and GitHub PAT tokens.
- **Potential Impact:** Unauthorized commit tampering, accidental push of secrets to public repositories, or exposure of GitHub tokens.
- **Implemented Mitigations:**
  - Read-only operations allowed by default; write/push operations classified as high-risk requiring human approval.
  - Tokens stored in environment/secret provider abstractions, never logged.
  - `StructuredJsonFormatter` redacts GitHub PAT patterns (`ghp_...`, `github_pat_...`) from output logs.
- **Residual Risk & Recommendations:** User accidentally tells Kairo to write a private key into a tracked file. Pre-commit hooks with secret scanning (e.g., Gitleaks) should be enforced locally.

### TM-06: Denial of Service (DoS) & Request Flooding
- **Attack Surface:** Public REST API endpoints (`/api/v1/chat`, `/api/v1/auth/login`, `/api/v1/workflows`).
- **Potential Impact:** System unavailability, CPU/memory starvation, database connection starvation, and excessive LLM API billing.
- **Implemented Mitigations:**
  - Sliding-window in-memory rate limiting (`RateLimiter`) with configurable requests per minute.
  - Request body size capped at 10 MB (`ContentLengthLimitMiddleware`).
  - Strict payload validation with Pydantic rejecting malformed schemas early.
- **Residual Risk & Recommendations:** Distributed volumetric DDoS attacks overwhelming the host. Upstream reverse proxy (Cloudflare, AWS CloudFront, or Nginx) must provide edge rate-limiting and DDoS mitigation.

### TM-07: Unauthorized Privilege Escalation
- **Attack Surface:** Multi-user environments where standard users attempt to access administrative tools, toggle capabilities, or access Security Center settings.
- **Potential Impact:** Standard user enabling computer control or approving their own high-risk actions.
- **Implemented Mitigations:**
  - Explicit role-based access control (`UserRole.ADMIN`, `UserRole.USER`).
  - Administrative routes require `RoleChecker([UserRole.ADMIN])` dependency verification.
  - Capability toggles (`COMPUTER_CONTROL_ENABLED`) can only be modified with admin authority and audited.
- **Residual Risk & Recommendations:** Stolen admin credentials. Recommend multi-factor authentication (MFA) on production deployment layers.

### TM-08: Insecure Direct Object References (IDOR)
- **Attack Surface:** Workflow endpoints (`/api/v1/workflows/{id}`), Agent task endpoints (`/api/v1/agents/tasks/{id}`), and Audit log queries.
- **Potential Impact:** Unauthorized users viewing, modifying, or cancelling workflows or agent tasks belonging to other users.
- **Implemented Mitigations:**
  - All database queries and operations enforce user scoping: `filter_by(user_id=current_user.id)`.
  - Administrative users require explicit permission overrides to inspect cross-user tasks.
- **Residual Risk & Recommendations:** Flaws in newly added custom endpoints. Automated authorization test suites verify cross-user isolation across all resource types.

### TM-09: Sensitive Data Exposure in Structured Logs
- **Attack Surface:** Application standard output, error messages, exception tracebacks, and Prometheus metric labels.
- **Potential Impact:** LLM API keys, passwords, bearer tokens, or user PII written to centralized log management (e.g., Datadog, CloudWatch).
- **Implemented Mitigations:**
  - `StructuredJsonFormatter` intercepts all log records, recursively masking sensitive keys (`password`, `token`, `secret`, `api_key`, `authorization`).
  - Regex pattern matching masks bearer tokens, OpenRouter keys (`sk-or-v1-...`), and GitHub tokens.
  - Production exception handler intercepts unhandled errors and returns generic message IDs without leaking stack traces or SQL snippets.
- **Residual Risk & Recommendations:** Custom multi-line user inputs containing embedded credentials in novel formats. Encourage use of ephemeral session tokens and dedicated secret managers.

### TM-10: Memory & Vector Store Poisoning
- **Attack Surface:** Conversation memory ingestion, long-term memory extraction, and pgvector embeddings.
- **Potential Impact:** Malicious prompts injected into long-term memory to influence future agent behaviors persistently across sessions.
- **Implemented Mitigations:**
  - Input sanitizer scrubs raw instructions before memory extraction.
  - Memory extraction requires structured validation.
  - Users can view, inspect, and delete individual memory entities via memory management APIs.
- **Residual Risk & Recommendations:** Subtly deceptive facts recorded as true user preferences. Regular memory pruning and user-facing memory audit interfaces.

### TM-11: Stolen Session Tokens & Replay Attacks
- **Attack Surface:** Bearer tokens passed over HTTP headers.
- **Potential Impact:** Attacker intercepting token impersonating authenticated user.
- **Implemented Mitigations:**
  - Cryptographically secure token generation (`secrets.token_urlsafe(32)`).
  - Strict idle timeout (30 minutes) and absolute session lifetime (24 hours).
  - Logging out immediately revokes session and invalidates all pending human approvals.
  - HTTPS / HSTS enforced in production preventing unencrypted transit.
- **Residual Risk & Recommendations:** Compromised client browser storing token in local storage. Recommend secure HTTP-only cookies with `SameSite=Strict` for browser-based web clients.

### TM-12: Database Connection Pool Exhaustion
- **Attack Surface:** High concurrent API requests or long-running streaming LLM sessions holding database connections.
- **Potential Impact:** Database connection timeouts, cascading HTTP 500 errors, and total system hang.
- **Implemented Mitigations:**
  - Async SQLAlchemy connection pool with `pool_size=20`, `max_overflow=10`, `pool_timeout=30s`.
  - Connections recycled every 1800s to avoid stale server drops.
  - `pool_pre_ping=True` proactively validates connections before checkout.
  - Streaming endpoints release DB session before entering long-running LLM stream loops.
- **Residual Risk & Recommendations:** Long unindexed database queries blocking connection pool. Monitor Prometheus `kairo_db_pool_utilization` metric.

### TM-13: LLM Provider Outage & Failover Failures
- **Attack Surface:** OpenRouter upstream API latency spikes, rate limit exhaustion (HTTP 429), or complete service outage.
- **Potential Impact:** Entire application hangs, background workflows stall, proactive intelligence freezes.
- **Implemented Mitigations:**
  - `CircuitBreaker` trips to `OPEN` state after 5 consecutive failures, failing fast to prevent thread/connection exhaustion.
  - Exponential backoff with random jitter for transient errors.
  - Automated fallback models configured in `ModelRouter`.
- **Residual Risk & Recommendations:** Extended multi-hour provider outage. Recommend multi-provider fallback configuration (e.g., secondary direct provider key).

### TM-14: Uncontrolled Notification Storms
- **Attack Surface:** Proactive intelligence engine detecting high-frequency background events (e.g., CI polling, flaky web monitors).
- **Potential Impact:** Alert fatigue, UI spam, excessive notification processing overhead.
- **Implemented Mitigations:**
  - Proactive intelligence deduplication window (events with identical fingerprint throttled within 30 minutes).
  - Configurable maximum proactive alerts per hour.
  - User quiet hours and priority filtering.
- **Residual Risk & Recommendations:** Misconfigured background monitors. Enforce minimum monitoring intervals (e.g., no faster than every 5 minutes).

### TM-15: Orphaned Background Agents & Runaway Tasks
- **Attack Surface:** Multi-agent workflows, recursive subtask decomposition, or unexpected server crashes during execution.
- **Potential Impact:** Unbounded agent execution loops, memory leaks, runaway API cost accumulation.
- **Implemented Mitigations:**
  - Hard caps on subtask depth (max 3 levels) and step execution budget (max 25 tool calls per task).
  - Startup recovery routine (`recover_stale_tasks_on_startup`) scans database on boot and marks orphaned `RUNNING`/`PENDING` tasks as `FAILED`.
  - Comprehensive cancellation support propagating `SIGINT`/cancellation tokens through all sub-agents.
- **Residual Risk & Recommendations:** Extremely long-running single tool call. Enforce strict subprocess and HTTP timeouts (max 60 seconds per tool execution).

### TM-16: Emergency Stop Bypass / Invalidation
- **Attack Surface:** Flawed security architecture where tools execute outside SecurityCenter authority, or where emergency stop endpoint is rate-limited.
- **Potential Impact:** Inability to stop rogue agent actions or runaway automation.
- **Implemented Mitigations:**
  - Centralized SecurityCenter is the sole, authoritative gateway for all tool execution; no secondary or direct execution paths exist.
  - Emergency stop endpoint is explicitly exempt from API rate limiting.
  - Emergency stop sets atomic global flag, invalidates all pending approvals, and immediately aborts active background runners.
  - Comprehensive unit tests verify that emergency stop cannot be bypassed.
- **Residual Risk & Recommendations:** Physical host operating system crash or hardware freeze outside container process space. Out-of-band server power management (IPMI/cloud instance stop) as fallback.

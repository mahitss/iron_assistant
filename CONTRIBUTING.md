# Contributing to Kairo

Thank you for your interest in contributing to Kairo! This document outlines our development guidelines, architecture principles, testing standards, and contribution workflow.

---

## Architecture Principles

When contributing to Kairo, adhere to our core tenets:
1. **One Coherent Assistant**: Every capability converges on `Kairo Core`, `SecurityCenter`, `ModelRouter`, and `ToolRegistry`. Never create duplicate permission systems, duplicate model routers, or competing schedulers.
2. **Security Center as Single Authority**: No tool, agent, or workflow may bypass `SecurityCenter`. Destructive and high-risk actions must strictly require human-in-the-loop approval.
3. **Defense-in-Depth & Untrusted Data**: All external data (web documents, GitHub issues, pull requests, repository source files, browser DOM) is untrusted. Never allow external text to override system instructions or alter permissions.
4. **No Arbitrary Code Execution**: Never invoke `eval()`, `exec()`, or `shell=True`. All subprocesses must use safe argument vectors.
5. **Authoritative PostgreSQL**: PostgreSQL is the single authoritative source of truth. Redis is strictly ephemeral (locks, caches, transient queues).

---

## Development Environment Setup

### Prerequisites
- Python 3.12+ (or Python 3.13)
- Node.js 20+
- PostgreSQL 16+ with `pgvector`
- Redis 7+

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\Activate on Windows
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
```

### Frontend Setup
```bash
cd frontend
npm install
```

---

## Running Tests & Quality Gates

Before submitting a pull request, all automated checks must pass cleanly:

### Backend Testing & Linting
```bash
# Run backend unit and integration tests (402+ tests)
pytest backend/tests -ra -q

# Run code linter and formatting
ruff check backend
ruff format --check backend
```

### Frontend Testing & Build
```bash
cd frontend

# Run frontend tests (25 tests)
npm test

# Build frontend distribution
npm run build
```

---

## Pull Request Guidelines

1. **Feature Branches**: Create focused branches off `main` (e.g. `feat/memory-dedup-tuning` or `fix/circuit-breaker-timeout`).
2. **Atomic Commits**: Write clear, descriptive commit messages following the Conventional Commits format (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`).
3. **Test Coverage**: Every new tool, policy check, or endpoint must be accompanied by comprehensive tests.
4. **Clean Git Tree**: Do not commit `.env`, secrets, credentials, or generated files.

---

## Security Reporting

If you discover a potential security vulnerability in Kairo, please **do NOT** create a public issue.
Follow our responsible disclosure procedure outlined in [SECURITY.md](SECURITY.md).

# Kairo Policy & Governance Engine (Task 36)

## Overview
The Kairo Policy & Governance Engine provides **ONE centralized policy decision layer** that coordinates governance rules, risk levels, human approval requirements, environment guardrails, and autonomy boundaries across all Kairo subsystems.

### Core Principle
- **Policy**: *"Under these conditions, what is permitted?"*
- **Authorization**: *"Is this identity allowed?"* (`SecurityCenter`)
- **Approval**: *"Has the required human approval been granted?"* (`ApprovalManager`)
- **Execution**: *"How do we perform it?"* (`ToolExecutor`, `TaskEngine`)

The Policy Engine **does not replace** `Authentication`, `SecurityCenter`, `ApprovalManager`, or `TaskEngine`. Instead, it provides unified governance coordination and defense-in-depth enforcement.

---

## 5-Tier Deterministic Risk Taxonomy
1. **R0 — READ_ONLY**: Inspect, status, query, list, search, metric lookups.
2. **R1 — LOW**: Navigation, local draft preparation, non-mutating UI observations.
3. **R2 — MODERATE**: Interactive operations, branch creation, local file staging.
4. **R3 — HIGH**: Remote pushes, PR creation, form submissions, system reboot, staging deploy.
5. **R4 — CRITICAL**: Deletions, production deployments, IAM/security modifications, financial transactions, credential access.

*Risk factor escalation rule*: If any factor elevates risk (e.g. production target, blast radius, irreversibility), the **highest** applicable risk tier is chosen. Risk is never averaged.

---

## Conflict Resolution & Precedence
When multiple policies match an operational context, decisions are resolved using deterministic precedence:
1. `DENY` strictly overrides any `ALLOW` across all policies, regardless of priority.
2. `REQUIRE_STEP_UP_AUTH` / `REQUIRE_APPROVAL` take precedence over `ALLOW`.
3. `REQUIRE_CONFIRMATION` takes precedence over simple `ALLOW`.
4. `ALLOW_WITH_LIMITS` merges limits.
5. `ALLOW` permits execution within scope.
6. `DEFER` pauses execution for budget/resource review.

---

## REST API Endpoints
- `POST /api/v1/policy/evaluate`: Evaluate policy context and return deterministic `PolicyDecision`.
- `POST /api/v1/policy/simulate`: Simulate policy evaluation with detailed execution trace without enforcing.
- `GET /api/v1/policy/decision/{evaluation_id}`: Retrieve decision provenance record.
- `GET /api/v1/policy/status`: Health metrics, active freeze status, and policy counts.
- `GET /api/v1/admin/policies`: List governance policies (Admin only).
- `POST /api/v1/admin/policies`: Create new governance rule (Admin only).
- `PUT /api/v1/admin/policies/{id}`: Increment version and update rule (Admin only).
- `POST /api/v1/admin/policies/{id}/rollback`: Roll back policy to previous version (Admin only).
- `POST /api/v1/admin/freeze`: Activate/deactivate environment change freeze (Admin only).
- `POST /api/v1/admin/safemode`: Toggle system safe mode (Admin only).

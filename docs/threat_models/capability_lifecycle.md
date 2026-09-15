# Threat Model: Autonomous Capability Lifecycle, Versioning & Safe Evolution Engine (Task 91)

## 1. Overview & Trust Boundaries

The Capability Lifecycle subsystem discovers, validates, tests, and promotes capabilities. Because autonomous capability evolution introduces vectors for privilege escalation, supply-chain contamination, and resource denial-of-service, strict security boundaries are established:

```
[ UNTRUSTED INPUTS: Web, LLM Prompts, External Repos, Tool Payloads ]
                               |
                               v
               +-------------------------------+
               | Capability Validation Pipeline|
               | (Syntactic, Schema & Envelopes)
               +---------------+---------------+
                               |
                   [ Security Boundary 1: Authorization ]
                               v
                 +---------------------------+
                 |   SecurityCenter Sole     | <--- Sole authority for permissions
                 |   Authorization Gateway   |
                 +-------------+-------------+
                               |
                   [ Security Boundary 2: Policy & Approvals ]
                               v
                 +---------------------------+
                 |  Governance Constitution  | <--- Policy invariants
                 |  & ApprovalRegistry       | <--- Mandatory human approvals
                 +-------------+-------------+
                               |
                   [ Security Boundary 3: Operational Containment ]
                               v
                 +---------------------------+
                 |  EmergencyStop Override   | <--- Preempts all mutating actions
                 +---------------------------+
```

---

## 2. Threat Analysis & Mitigations

### Threat 1: Self-Authorized Privilege Escalation
- **Description:** A newly discovered or updated capability requests `DESTRUCTIVE` or `EXTERNAL` permissions and attempts to promote itself to `ACTIVE` automatically.
- **Impact:** Unauthorized access or data destruction.
- **Mitigation:**
  - `AUTONOMOUS EVOLUTION ≠ AUTONOMOUS AUTHORIZATION`.
  - Gate 5 requires `SecurityCenter` authorization.
  - Gate 11 requires `ApprovalRegistry` human sign-off for `CRITICAL_INFRASTRUCTURE` and `DESTRUCTIVE` capabilities.
  - Validation alone never grants permissions.

### Threat 2: Active Version Mutation (Supply-Chain Tampering)
- **Description:** An attacker modifies bytecode or schema of an existing `ACTIVE` version without incrementing SemVer.
- **Impact:** Stale cache, untracked changes, unvetted behavior in production.
- **Mitigation:**
  - `CapabilityVersionRecord.is_active` locks the version as immutable.
  - `CapabilityFingerprinter.verify_fingerprint_integrity()` calculates SHA-256 digests (`cfp_`, `ifp_`, `dfp_`, `cmp_`).
  - Any material modification requires an incremented SemVer version and full gate re-evaluation.

### Threat 3: Unchecked Blast-Radius Cascades
- **Description:** A buggy version is promoted directly to 100% production traffic, causing catastrophic cascading failure.
- **Impact:** System-wide outage.
- **Mitigation:**
  - Gate 8 enforces Task 89 digital twin simulation ($\le 40\%$ blast radius).
  - Gate 10 enforces progressive canary rollout (e.g. 5% $\to$ 10% $\to$ 20%).
  - Automated anomaly abort triggers if error rate $> 5\%$ or latency $> 500$ ms, transitioning state to `DEGRADED`.

### Threat 4: Zombie Retirement & Broken Consumer Workflows
- **Description:** A capability is retired while critical active workflows still depend on it.
- **Impact:** Silent workflow crashes and missing dependencies.
- **Mitigation:**
  - `CapabilityDeprecationManager.retire_capability()` performs reverse dependency impact analysis.
  - Retirement is blocked fail-closed if active dependents exist, unless administrative `force_retirement=True` is provided.

### Threat 5: Malicious Evasion during Emergency Stop
- **Description:** An adversary triggers automated capability promotion or rollout while an operator has initiated an emergency stop.
- **Impact:** Circumvention of operator kill-switch.
- **Mitigation:**
  - `EmergencyStopService.is_stopped()` is checked fail-closed at the entry of every mutating method (`register_discovered_capability`, `validate_capability`, `start_canary`, `promote_capability`, `rollback_capability`).
  - All mutating requests immediately abort with `RuntimeError` or `BLOCKED` state.

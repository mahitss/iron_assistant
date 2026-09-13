# Operational Runbook: Native Resource Enforcement & Execution Economy

## Purpose & Scope

This runbook covers operational alerts, incident triage, and remediation procedures for low-level resource violations, capacity saturation, and native runtime execution economy issues within Kairo.

---

## 1. Quick Diagnostic Commands

### Query Economy Status via CLI
```bash
python -m backend.app.native.cli economy
```
Sample Output:
```
Native Execution Economy Status:
  Saturation:       12.5%
  State:            HEALTHY
  Allocations:      1 active
  Native Memory:    14336.0 / 16384.0 MB available
  Native CPU:       7.0 / 8.0 Cores available
  Native Workspace: 92160.0 / 102400.0 MB available
```

### Query Low-Level Health & Capabilities
```bash
python -m backend.app.native.cli status
```

### Inspect Recent Violations in Event Stream
```bash
# In Python shell or logs:
# Filter for 'runtime.economy.violation' or 'runtime.economy.backpressure'
```

---

## 2. Common Alert Conditions & Triage

### Alert: `runtime.economy.violation` (`MEMORY_EXCEEDED`)

- **Symptom**: Sandbox execution fails with `ResourceViolationType.MEMORY_EXCEEDED` and `EnforcementAction.TERMINATED`. Process was killed by the OS kernel / Job Object.
- **Root Cause**: The workload attempted to allocate more memory than `max_memory_bytes` defined in the capability or request `ResourceBudget`.
- **Action**:
  1. Inspect the workload request ID and capability ID.
  2. Verify if the allocation limit was appropriately sized for the workload (e.g., standard tasks need 64-128 MB, memory-heavy data tasks may need 512 MB).
  3. If the task is malicious or leaking, keep strict limits. If legitimate, tune `max_memory_bytes` in the registered capability definition.
  4. Confirm that the resource reservation was returned cleanly: `python -m backend.app.native.cli economy`.

---

### Alert: `runtime.economy.backpressure` (`SATURATED` or `CRITICAL`)

- **Symptom**: Inbound sandbox requests are denied with `Insufficient capacity for Native Host Substrate`.
- **Root Cause**: Host saturation exceeded safe operational thresholds, or active parallel workloads have reserved the available pool.
- **Action**:
  1. Run `python -m backend.app.native.cli economy` to view active allocations and capacity pools.
  2. If allocations are orphaned due to an unhandled crash or network partition, force a reconciliation cycle:
     ```python
     from backend.app.native.service import get_native_runtime_service
     service = get_native_runtime_service()
     status = service.get_resource_economy_status()
     ```
  3. Under high system load, scale the host memory pool or lower the concurrency ceiling in `backend/app/config/settings.py`.

---

### Alert: `runtime.economy.violation` (`WORKSPACE_EXCEEDED`)

- **Symptom**: Workload terminated or flagged with `WORKSPACE_EXCEEDED` due to exceeding `max_disk_bytes` (10 GiB) or `max_file_count` (100,000 files).
- **Root Cause**: Workload script flooded the temporary isolated workspace with temporary files or large artifacts.
- **Action**:
  1. Sandboxed workspaces are automatically wiped upon process termination by `WorkspaceManager.cleanup()`.
  2. Verify that the disk directory under `%TEMP%\kairo_sandbox_*` has been deleted.
  3. Review the capability script for unbounded file generation loops or disk floods.

---

## 3. Emergency Containment Procedures

### Activating Global Emergency Stop
If native workloads are behaving adversarially or destabilizing the host system:
```bash
python -m backend.app.governance.cli stop --reason "Suspected native substrate resource exhaustion"
```
Or via Python:
```python
from backend.app.governance.emergency_stop import get_emergency_stop_manager
get_emergency_stop_manager().activate("Host resource containment")
```

### Verification After Emergency Stop
1. Check that all native runtime executions are immediately blocked (`BLOCKED_BY_EMERGENCY_STOP`).
2. Verify that all reservations are 100% returned with 0 active allocations:
   ```bash
   python -m backend.app.native.cli economy
   ```
3. Once the environment is verified safe, deactivate emergency stop:
   ```bash
   python -m backend.app.governance.cli resume
   ```

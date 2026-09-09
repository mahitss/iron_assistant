# Incident Runbook: Workflow & Automation Failures

**Incident Type**: Background Automation Anomaly  
**Severity**: P2 / Medium (P1 if automated financial/critical sync jobs fail)  
**Target**: Kairo Automation Engine & Celery/Worker Scheduler  

---

## Symptoms
- Alert firing: `WorkflowFailureSpike` or `WorkflowStuckRunDetected`.
- Operations Dashboard reflects `automations: "DEGRADED"` or `"UNAVAILABLE"`.
- Scheduled workflows not triggering at defined cron intervals, or repeating continuously in an infinite loop.
- Duplicate execution detected across multiple worker replicas.

---

## Checks
1. **Worker Process Health**:
   ```bash
   kubectl get pods -l app=kairo-worker
   kubectl logs -l app=kairo-worker --tail=200
   ```
2. **Scheduler Leader Election / Distributed Lock**:
   - Check Redis distributed lock key for the scheduler:
     ```bash
     redis-cli get "kairo:scheduler:leader_lock"
     ```
   - Verify that only one scheduler replica holds the leader lock. If two workers believe they are leader, duplicate executions will occur.
3. **Stuck Workflow Runs**:
   - Query database for runs stuck in `RUNNING` state beyond max execution timeout (e.g. > 15 minutes):
     ```sql
     SELECT id, workflow_id, status, started_at 
     FROM workflow_runs 
     WHERE status = 'RUNNING' AND started_at < NOW() - INTERVAL '30 minutes';
     ```
4. **External API Idempotency & Rate Limits**:
   - Check if automated actions (webhook POSTs, GitHub PR comments, email sends) are failing due to upstream rate limits or missing idempotency keys.

---

## Safe Actions
- **Do Not** mass-delete workflow runs from the database without recording their execution IDs.
- **Do Not** disable distributed locking: multiple replicas executing the same cron schedule causes duplicate external side effects.
- Pause problematic individual workflows via UI or database without shutting down the entire worker engine.

---

## Recovery
1. **If Stuck Runs Blocking Workers**:
   - Mark zombie runs as `FAILED` with a timeout reason:
     ```sql
     UPDATE workflow_runs 
     SET status = 'FAILED', error_message = 'Terminated by timeout watchdog' 
     WHERE status = 'RUNNING' AND started_at < NOW() - INTERVAL '30 minutes';
     ```
2. **If Scheduler Duplicate Lock Contention**:
   - Restart the scheduler leader pod so the distributed lock is cleanly released and reacquired by a single instance:
     ```bash
     kubectl delete pod -l app=kairo-scheduler
     ```
3. **If Infinite Retry Loop**:
   - Enforce max retries (max 3) with exponential backoff on failed workflow steps.

---

## Verification
- Confirm worker logs show normal task consumption without duplicate claim errors.
- Trigger a test workflow and verify it transitions: `PENDING` -> `RUNNING` -> `COMPLETED`.
- Verify Operations Dashboard shows `automations: "HEALTHY"`.

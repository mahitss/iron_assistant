# Incident Runbook: API Down

**Incident Type**: Core Service Outage  
**Severity**: P0 / Critical  
**Target**: Kairo API Gateway (`https://kairo.ai/health/*`)  

---

## Symptoms
- Ingress/Load balancer returning HTTP 502 Bad Gateway, 503 Service Unavailable, or 504 Gateway Timeout.
- Monitoring alert firing: `KairoApiDown` or probe failure on `/health/live`.
- Zero active incoming requests reaching application logs.
- Client applications displaying connection failure or timeout errors.

---

## Checks
1. **Pod / Container Status**:
   ```bash
   kubectl get pods -l app=kairo-api -o wide
   # Or docker ps / systemctl status
   ```
   Check for `CrashLoopBackOff`, `OOMKilled`, or `ImagePullBackOff`.
2. **Container Logs**:
   ```bash
   kubectl logs -l app=kairo-api --tail=100 --prefix
   ```
   Look for uncaught fatal startup exceptions, database connection refused, or missing mandatory environment variables.
3. **Ingress / Load Balancer Health**:
   ```bash
   curl -Iv https://kairo.ai/health/live
   ```
   Determine if the TLS certificate expired or ingress target group shows 0 healthy instances.
4. **Node Resource Saturation**:
   ```bash
   kubectl top pods -l app=kairo-api
   kubectl top nodes
   ```
   Check if CPU or RAM limit was reached causing container termination.

---

## Safe Actions
- **Do Not** modify database schemas or delete configuration secrets in response to an API crash.
- **Do Not** execute arbitrary shell commands inside dying containers without capturing stack traces first.
- Restart pods in a rolling fashion if deadlocked:
  ```bash
  kubectl rollout restart deployment/kairo-api
  ```
- Scale up replica count if down due to request load:
  ```bash
  kubectl scale deployment/kairo-api --replicas=6
  ```

---

## Recovery
1. **If OOMKilled**: Increase container memory limits in deployment spec (e.g. from 1Gi to 2Gi) and re-apply.
2. **If Bad Configuration / Fatal Code Bug**: Revert immediately to the previous immutable release artifact:
   ```bash
   kubectl rollout undo deployment/kairo-api
   ```
3. **If Database Connectivity Failure**: Follow `database-down.md` runbook to restore PostgreSQL connectivity.
4. **If Load Balancer Routing Failure**: Re-register healthy target groups with AWS ALB / Cloud Ingress.

---

## Verification
- Probe `/health/live` and `/health/ready`:
  ```bash
  curl -fsS https://kairo.ai/health/live
  curl -fsS https://kairo.ai/health/ready
  ```
  Must return HTTP 200 `{"status":"ready"}`.
- Run smoke test:
  ```bash
  python scripts/smoke_test.py --base-url "https://kairo.ai" --env production
  ```
- Verify ingress metrics show 0% 5xx errors and traffic routing resumes normally.

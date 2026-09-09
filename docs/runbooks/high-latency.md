# Incident Runbook: High Latency

**Incident Type**: Performance Degradation  
**Severity**: P2 / Medium (P1 if p99 > 3,000ms)  
**Target**: Kairo API & Downstream Pipelines  

---

## Symptoms
- Alert firing: `HighP99Latency` (p99 duration > 2,000ms over 5 minutes).
- Operations Dashboard shows `latency_ms` elevated above baseline.
- Streaming responses experiencing token delivery stalls.
- Client requests timing out at the load balancer / reverse proxy layer.

---

## Checks
1. **Deconstruct Latency by Pipeline Subsystem**:
   - Determine which subsystem is introducing delay:
     - **Database Query Latency**: Check pgvector cosine similarity search durations and index usage (`HNSW` / `IVFFlat`).
     - **Redis Latency**: Check Redis roundtrip ping and slowlog.
     - **Model Provider TTFT (Time-To-First-Token)**: Check upstream provider streaming response start times.
     - **Context Engine / Memory Retrieval**: Check document chunking and reranking execution time.
2. **CPU and Worker Contention**:
   ```bash
   kubectl top pods -l app=kairo-api
   ```
   Check if the Python GIL or event loop is blocked by synchronous CPU-bound operations.
3. **Database Connection Queue**:
   - Verify if requests are spending hundreds of milliseconds simply waiting to acquire a connection from the SQLAlchemy async connection pool.
4. **Network / Ingress Congestion**:
   - Inspect edge CDN or ingress controller latency metrics.

---

## Safe Actions
- **Do Not** reduce token budgets blindly without verifying if the delay is algorithmic or upstream.
- Ensure event loop is not starved: identify any blocking synchronous I/O or file system operations run in async routes.

---

## Recovery
1. **If Database Vector Search Delay**:
   - Re-index pgvector collections: `REINDEX INDEX CONCURRENTLY idx_memory_embeddings;`
   - Increase `work_mem` or pgvector probe limits.
2. **If Event Loop / CPU Starvation**:
   - Scale out API replicas to distribute load across more worker processes:
     ```bash
     kubectl scale deployment/kairo-api --replicas=8
     ```
3. **If Upstream Model Latency**:
   - Switch active router preference to faster low-latency models (e.g. Claude 3.5 Haiku or GPT-4o-mini) for simple queries.
4. **If Connection Pool Starvation**:
   - Adjust `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW` in environment configuration.

---

## Verification
- Confirm p99 latency returns to baseline (< 400ms for standard API, < 1,500ms TTFT for streaming).
- Verify `/health/operations` reflects normalized average latency.
- Run latency baseline probe using `python scripts/smoke_test.py`.

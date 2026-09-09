# Incident Runbook: Redis Down

**Incident Type**: Caching & Coordination Outage  
**Severity**: P1 / High  
**Target**: Redis Cache & Distributed Lock Store  

---

## Symptoms
- `/health/ready` returns HTTP 200 (degraded) or HTTP 503 with `"redis": "unhealthy"`.
- Backend logs show `redis.exceptions.ConnectionError: Error connecting to redis` or `TimeoutError`.
- Operations Dashboard reports `redis: "UNAVAILABLE"` or `"DEGRADED"`.
- Rate limiting, real-time WebSocket connection state, distributed locks, and temporary session caches fail or fall back to in-memory mode.

---

## Checks
1. **Redis Server Status**:
   ```bash
   redis-cli -h redis-host -p 6379 ping
   # Expected response: PONG
   ```
2. **Memory & Eviction Policy**:
   ```bash
   redis-cli -h redis-host info memory
   ```
   Check `used_memory_human` vs `maxmemory`. If max memory reached and `maxmemory-policy` is `noeviction`, Redis will reject write operations with `OOM command not allowed`.
3. **Client Connections**:
   ```bash
   redis-cli -h redis-host info clients
   ```
   Check `connected_clients` against `maxclients`.
4. **Slowlog & CPU Usage**:
   ```bash
   redis-cli -h redis-host slowlog get 10
   ```
   Check if heavy `KEYS *` or huge pipeline requests are blocking the single-threaded Redis execution loop.

---

## Safe Actions
- **Do Not** issue `FLUSHALL` or `FLUSHDB` in production without explicit Incident Commander sign-off.
- Allow Kairo's graceful degradation logic to operate: non-critical rate-limiting operations fail-open safely without crashing API endpoints.
- If Redis is unresponsive, trigger a managed failover to the replica instance.

---

## Recovery
1. **If Memory Exhausted**:
   - Set eviction policy to `volatile-lru` or `allkeys-lru`:
     ```bash
     redis-cli config set maxmemory-policy volatile-lru
     ```
   - Scale instance memory tier.
2. **If Blocked on Huge Keys / CPU Spike**:
   - Identify offending long-running commands in `slowlog`.
   - Terminate rogue client connection if a task is flooding the connection.
3. **If Redis Crashed**:
   - Restart the Redis service or container:
     ```bash
     kubectl rollout restart statefulset/redis
     ```
   - Verify AOF/RDB persistence loaded successfully.

---

## Verification
- Run `redis-cli ping` to verify `PONG`.
- Verify `/health/ready` reports HTTP 200 with `"redis": "healthy"`.
- Check Operations Dashboard (`/health/operations`) to confirm `redis: "HEALTHY"`.

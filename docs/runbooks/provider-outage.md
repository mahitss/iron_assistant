# Incident Runbook: Model Provider Outage

**Incident Type**: Third-Party Dependency Degradation  
**Severity**: P1 / High  
**Target**: OpenRouter, Anthropic, OpenAI, or Secondary LLM Providers  

---

## Symptoms
- Operations Dashboard (`/health/operations`) shows `model: "DEGRADED"` or `"UNAVAILABLE"`.
- Chat stream requests failing with user-friendly error: `"AI provider is temporarily unavailable. Please retry shortly."`
- Prometheus alerts firing: `CircuitBreakerTripped` or `ModelProviderErrorSpike`.
- Upstream HTTP 429 (Rate Limited), 500/503 (Provider Internal Server Error), or 30-second read timeouts.

---

## Checks
1. **Model Router Circuit Breaker Status**:
   - Check application logs for circuit breaker trip events:
     ```bash
     kubectl logs -l app=kairo-api --tail=200 | grep "circuit_breaker"
     ```
   - Determine if the primary provider (`openrouter`) has tripped to OPEN state.
2. **Provider Public Status Pages**:
   - OpenRouter status: `https://status.openrouter.ai`
   - Anthropic status: `https://status.anthropic.com`
   - OpenAI status: `https://status.openai.com`
3. **Upstream Response Codes**:
   - Analyze Prometheus metrics for `kairo_model_provider_requests_total{status_code=~"429|500|502|503"}`.
   - Note: Never log or expose raw bearer API tokens or user prompt data.
4. **Token Budget & Quota**:
   - Verify if upstream provider organization credits or usage tiers have been exhausted.

---

## Safe Actions
- **Do Not** disable circuit breakers or set retries to infinity; this causes request thread pileups and exacerbates 429 rate limits.
- **Do Not** expose raw socket or upstream traceback errors to frontend users. Return structured friendly error responses.
- The ModelRouter automatically attempts fallbacks to secondary configured models (e.g. Claude -> GPT-4o -> DeepSeek) if enabled.

---

## Recovery
1. **If Primary Provider Experiencing Full Outage**:
   - Switch active default model or provider via environment variable or runtime config:
     ```bash
     # Example: Switch primary model provider fallback
     kubectl set env deployment/kairo-api DEFAULT_CHAT_MODEL="openai/gpt-4o"
     ```
2. **If Upstream 429 Rate Limit Exhaustion**:
   - Temporarily throttle concurrent multi-agent and automated workflow runs:
     ```bash
     kubectl set env deployment/kairo-api WORKFLOW_MAX_CONCURRENCY="2"
     ```
3. **If Provider Resolved**:
   - The circuit breaker transitions from OPEN -> HALF-OPEN -> CLOSED automatically after the cooldown duration (typically 60s).
   - Verify incoming probe queries succeed.

---

## Verification
- Run a safe model probe:
  ```bash
  curl -fsS -X POST https://kairo.ai/api/v1/chat/completions \
    -H "Authorization: Bearer $TEST_USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"ping"}],"stream":false}'
  ```
- Verify Operations Dashboard reflects `model: "HEALTHY"`.
- Confirm circuit breaker metric resets to CLOSED (`state=0`).

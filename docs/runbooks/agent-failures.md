# Incident Runbook: Agent Failures & Loop Detection

**Incident Type**: Multi-Agent Orchestration Anomaly  
**Severity**: P2 / Medium (P1 if uncontrolled tool loop or budget depletion)  
**Target**: Kairo Multi-Agent Supervisor & Tool Execution Engine  

---

## Symptoms
- Alert firing: `AgentExecutionSpike`, `AgentToolCallExplosion`, or `AgentBudgetExceeded`.
- Operations Dashboard reflects `agents: "DEGRADED"` or `"UNAVAILABLE"`.
- Multi-agent tasks hanging indefinitely in planning or execution loops.
- Rapid token consumption triggering model provider budget alerts.

---

## Checks
1. **Agent Task Metrics**:
   - Inspect Prometheus metrics:
     - `kairo_agent_tasks_active`
     - `kairo_agent_tool_calls_total`
     - `kairo_agent_loop_iterations_total`
   - Check if any agent has executed more than 15 consecutive tool iterations without producing an answer.
2. **Active Subagent Graph**:
   - Check for recursive subagent spawning loops (e.g. Supervisor -> Researcher -> Analyst -> Supervisor).
   - Ensure the max delegation depth (default: 3) is strictly enforced.
3. **Token Budget Enforcement**:
   - Verify if per-agent or per-task token budgets (default: 32,000 tokens) are halting execution when exceeded.
4. **Tool Timeouts**:
   - Determine if agents are blocked waiting on slow web scraping or browser navigation tasks.

---

## Safe Actions
- **Do Not** disable agent depth or iteration limits to "let the agent finish".
- Use the Security Center or Emergency Stop capability to immediately halt running rogue agent workflows:
  ```bash
  # Trigger emergency stop via API:
  curl -X POST https://kairo.ai/api/v1/security/emergency-stop \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d '{"scope": "agents", "reason": "Uncontrolled tool recursion detected"}'
  ```

---

## Recovery
1. **Terminate Runaway Tasks**:
   - Cancel all active agent tasks exceeding max iteration thresholds or execution time limits (> 10 minutes).
2. **Enforce Hard Circuit Breakers**:
   - Set max tool calls per task to 20:
     ```bash
     kubectl set env deployment/kairo-api AGENT_MAX_TOOL_CALLS="20"
     ```
3. **Reset Agent State**:
   - Flush corrupted short-term scratchpad memory for the affected task session.

---

## Verification
- Verify `kairo_agent_tasks_active` drops to normal operational levels.
- Confirm token consumption rate normalizes.
- Execute a controlled multi-agent test task (e.g. standard research query) and verify clean termination within 5 iterations.
- Verify Operations Dashboard reflects `agents: "HEALTHY"`.

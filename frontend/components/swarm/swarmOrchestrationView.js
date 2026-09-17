/**
 * KAIRO Autonomous Multi-Agent Collaboration, Delegation, Supervision & Swarm Orchestration Console (Task 96).
 *
 * Exposes:
 * 1. Swarm Overview (collaboration sessions, topologies, resource allocations)
 * 2. Agent Worker Pool (scoped identities, 14-state lifecycles, capabilities, trust)
 * 3. Task DAG & Dependencies (dependency states, ready/blocked execution)
 * 4. Supervision & Stall Monitor (stall detection, deadlocks, health states)
 * 5. Inter-Agent Messages & Bounded Blackboard (typed audit log, shared validated facts)
 * 6. Results, Disagreements & Synthesis (Agent Result vs Validated Result vs Final Verified Result)
 */

export class SwarmOrchestrationView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api || this._createDefaultApi();
    this.state = {
      activeTab: 'overview', // 'overview' | 'agents' | 'dag' | 'supervision' | 'blackboard' | 'synthesis'
      swarms: [],
      selectedSwarmId: null,
      selectedSwarm: null,
      swarmGraph: null,
      agents: [],
      selectedAgentId: null,
      selectedAgent: null,
      tasks: [],
      messages: [],
      conflicts: [],
      results: [],
      stalls: [],
      isLoading: false,
      error: null,
    };
  }

  _createDefaultApi() {
    return {
      listSwarms: async (limit = 50) => (await fetch(`/api/v1/swarms?limit=${limit}`)).json(),
      getSwarm: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}`)).json(),
      getSwarmGraph: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/graph`)).json(),
      getSwarmAgents: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/agents`)).json(),
      getSwarmResults: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/results`)).json(),
      getSwarmConflicts: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/conflicts`)).json(),
      superviseSwarm: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/supervise`, { method: 'POST' })).json(),
      synthesizeSwarm: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/synthesize`, { method: 'POST' })).json(),
      pauseSwarm: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/pause`, { method: 'POST' })).json(),
      resumeSwarm: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/resume`, { method: 'POST' })).json(),
      cancelSwarm: async (id, reason = 'Operator cancelled') =>
        (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/cancel?reason=${encodeURIComponent(reason)}`, { method: 'POST' })).json(),
      reconcileSwarm: async (id) => (await fetch(`/api/v1/swarms/${encodeURIComponent(id)}/reconcile`, { method: 'POST' })).json(),

      listAgents: async (sessionId = null) => {
        const url = sessionId ? `/api/v1/agents?session_id=${encodeURIComponent(sessionId)}` : '/api/v1/agents';
        return (await fetch(url)).json();
      },
      getAgent: async (id) => (await fetch(`/api/v1/agents/${encodeURIComponent(id)}`)).json(),
      getAgentTasks: async (id) => (await fetch(`/api/v1/agents/${encodeURIComponent(id)}/tasks`)).json(),
      getAgentMessages: async (id) => (await fetch(`/api/v1/agents/${encodeURIComponent(id)}/messages`)).json(),
      getAgentHealth: async (id) => (await fetch(`/api/v1/agents/${encodeURIComponent(id)}/health`)).json(),
      getAgentHistory: async (id) => (await fetch(`/api/v1/agents/${encodeURIComponent(id)}/history`)).json(),
      cancelAgent: async (id, reason = 'Operator cancelled') =>
        (await fetch(`/api/v1/agents/${encodeURIComponent(id)}/cancel?reason=${encodeURIComponent(reason)}`, { method: 'POST' })).json(),
      retryAgent: async (id) => (await fetch(`/api/v1/agents/${encodeURIComponent(id)}/retry`, { method: 'POST' })).json(),
    };
  }

  async render() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="swarm-orchestration-view">
        <header class="swarm-header">
          <div class="swarm-title-area">
            <h2>Swarm Orchestration & Multi-Agent Collaboration</h2>
            <p class="subtitle">Autonomous Worker Coordination • Strict Scope Fences • Supervised Synthesis</p>
          </div>
          <div class="swarm-header-actions">
            <button class="btn btn-secondary" id="btn-refresh-swarm">↻ Refresh Data</button>
            <button class="btn btn-primary" id="btn-create-swarm">+ Launch Swarm</button>
          </div>
        </header>

        <nav class="swarm-tabs">
          <button class="tab-btn ${this.state.activeTab === 'overview' ? 'active' : ''}" data-tab="overview">
            🌐 Swarm Overview
          </button>
          <button class="tab-btn ${this.state.activeTab === 'agents' ? 'active' : ''}" data-tab="agents">
            🤖 Agent Workers (${this.state.agents.length})
          </button>
          <button class="tab-btn ${this.state.activeTab === 'dag' ? 'active' : ''}" data-tab="dag">
            📊 Task DAG & Dependencies
          </button>
          <button class="tab-btn ${this.state.activeTab === 'supervision' ? 'active' : ''}" data-tab="supervision">
            🛡️ Supervision & Stalls
          </button>
          <button class="tab-btn ${this.state.activeTab === 'blackboard' ? 'active' : ''}" data-tab="blackboard">
            📋 Messages & Blackboard
          </button>
          <button class="tab-btn ${this.state.activeTab === 'synthesis' ? 'active' : ''}" data-tab="synthesis">
            ⚖️ Disagreements & Synthesis
          </button>
        </nav>

        <main class="swarm-content" id="swarm-tab-content">
          <div class="loading-spinner">Loading swarm orchestration data...</div>
        </main>
      </div>
    `;

    this._bindEvents();
    await this.loadData();
  }

  _bindEvents() {
    this.container.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.dataset.tab;
        this.switchTab(tab);
      });
    });

    const refreshBtn = this.container.querySelector('#btn-refresh-swarm');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    const createBtn = this.container.querySelector('#btn-create-swarm');
    if (createBtn) {
      createBtn.addEventListener('click', () => this.promptCreateSwarm());
    }
  }

  async switchTab(tabName) {
    this.state.activeTab = tabName;
    this.container.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    this._renderActiveTab();
  }

  async loadData() {
    try {
      this.state.isLoading = true;
      const swarms = await this.api.listSwarms(50);
      this.state.swarms = Array.isArray(swarms) ? swarms : [];

      if (this.state.swarms.length > 0 && !this.state.selectedSwarmId) {
        this.state.selectedSwarmId = this.state.swarms[0].session_id;
      }

      if (this.state.selectedSwarmId) {
        await this.loadSwarmDetails(this.state.selectedSwarmId);
      } else {
        const agents = await this.api.listAgents();
        this.state.agents = Array.isArray(agents) ? agents : [];
      }

      this.state.isLoading = false;
      this._renderActiveTab();
    } catch (err) {
      console.error('Failed to load swarm orchestration state:', err);
      this.state.error = err.message;
      this.state.isLoading = false;
      this._renderError(err.message);
    }
  }

  async loadSwarmDetails(swarmId) {
    try {
      const [swarm, graph, agents, results, conflicts] = await Promise.all([
        this.api.getSwarm(swarmId),
        this.api.getSwarmGraph(swarmId),
        this.api.getSwarmAgents(swarmId),
        this.api.getSwarmResults(swarmId),
        this.api.getSwarmConflicts(swarmId),
      ]);
      this.state.selectedSwarm = swarm;
      this.state.swarmGraph = graph;
      this.state.agents = Array.isArray(agents) ? agents : [];
      this.state.results = Array.isArray(results) ? results : [];
      this.state.conflicts = Array.isArray(conflicts) ? conflicts : [];
    } catch (e) {
      console.warn('Error fetching swarm details:', e);
    }
  }

  _renderActiveTab() {
    const content = this.container.querySelector('#swarm-tab-content');
    if (!content) return;

    switch (this.state.activeTab) {
      case 'overview':
        content.innerHTML = this._renderOverviewTab();
        break;
      case 'agents':
        content.innerHTML = this._renderAgentsTab();
        break;
      case 'dag':
        content.innerHTML = this._renderDagTab();
        break;
      case 'supervision':
        content.innerHTML = this._renderSupervisionTab();
        break;
      case 'blackboard':
        content.innerHTML = this._renderBlackboardTab();
        break;
      case 'synthesis':
        content.innerHTML = this._renderSynthesisTab();
        break;
      default:
        content.innerHTML = this._renderOverviewTab();
    }
    this._bindTabActions();
  }

  _renderOverviewTab() {
    const s = this.state.selectedSwarm;
    return `
      <div class="overview-grid">
        <section class="card swarm-selector-pane">
          <h3>Active & Historical Swarms</h3>
          <div class="swarms-list">
            ${
              this.state.swarms.length === 0
                ? '<div class="empty-state">No active swarm collaboration sessions found.</div>'
                : this.state.swarms
                    .map(
                      (item) => `
              <div class="swarm-card-item ${item.session_id === this.state.selectedSwarmId ? 'selected' : ''}" data-id="${item.session_id}">
                <div class="swarm-card-head">
                  <span class="status-badge status-${(item.status || 'unknown').toLowerCase()}">${item.status}</span>
                  <span class="swarm-date">${new Date(item.created_at).toLocaleTimeString()}</span>
                </div>
                <div class="swarm-objective">${this._escapeHtml(item.objective?.goal || 'No objective')}</div>
                <div class="swarm-meta">ID: ${item.session_id.slice(0, 8)}... • Topology: ${item.topology}</div>
              </div>
            `
                    )
                    .join('')
            }
          </div>
        </section>

        <section class="card swarm-detail-pane">
          ${
            !s
              ? '<div class="empty-state">Select a swarm session from the left to view details.</div>'
              : `
            <div class="detail-header">
              <div>
                <h3>${this._escapeHtml(s.objective?.goal || 'Swarm Session')}</h3>
                <span class="session-id-pill">Session: ${s.session_id}</span>
              </div>
              <div class="action-btn-group">
                ${
                  s.status === 'EXECUTING'
                    ? `<button class="btn btn-sm btn-warning" id="btn-pause-swarm" data-id="${s.session_id}">⏸ Pause</button>`
                    : s.status === 'PAUSED'
                    ? `<button class="btn btn-sm btn-success" id="btn-resume-swarm" data-id="${s.session_id}">▶ Resume</button>`
                    : ''
                }
                <button class="btn btn-sm btn-danger" id="btn-cancel-swarm" data-id="${s.session_id}">⏹ Cancel</button>
                <button class="btn btn-sm btn-secondary" id="btn-reconcile-swarm" data-id="${s.session_id}">🧹 Reconcile</button>
                <button class="btn btn-sm btn-primary" id="btn-synthesize-swarm" data-id="${s.session_id}">✨ Synthesize</button>
              </div>
            </div>

            <div class="metrics-row">
              <div class="metric-card">
                <span class="metric-val">${this.state.agents.length}</span>
                <span class="metric-lbl">Active Agents</span>
              </div>
              <div class="metric-card">
                <span class="metric-val">${s.task_dag?.nodes ? Object.keys(s.task_dag.nodes).length : 0}</span>
                <span class="metric-lbl">DAG Tasks</span>
              </div>
              <div class="metric-card">
                <span class="metric-val">${this.state.results.length}</span>
                <span class="metric-lbl">Submitted Results</span>
              </div>
              <div class="metric-card">
                <span class="metric-val ${this.state.conflicts.length > 0 ? 'text-warning' : ''}">${this.state.conflicts.length}</span>
                <span class="metric-lbl">Conflicts Detected</span>
              </div>
            </div>

            <div class="info-section">
              <h4>Objective & Constraints</h4>
              <p><strong>Success Criteria:</strong> ${this._escapeHtml(s.objective?.success_criteria?.join(', ') || 'N/A')}</p>
              <p><strong>Max Agents:</strong> ${s.objective?.max_agents || 10} • <strong>Depth Limit:</strong> ≤ 4</p>
            </div>

            ${
              s.final_result
                ? `
              <div class="verified-result-banner">
                <div class="banner-head">
                  <span class="badge-verified">FINAL VERIFIED RESULT</span>
                  <span class="status-indicator">${s.final_result.verification_status}</span>
                </div>
                <div class="result-summary">${this._escapeHtml(s.final_result.summary)}</div>
                <ul class="result-findings">
                  ${(s.final_result.key_findings || []).map((f) => `<li>${this._escapeHtml(f)}</li>`).join('')}
                </ul>
              </div>
            `
                : ''
            }
          `
          }
        </section>
      </div>
    `;
  }

  _renderAgentsTab() {
    return `
      <div class="agents-grid">
        <section class="card agents-table-card">
          <div class="card-head">
            <h3>Agent Workers Registry</h3>
            <span class="badge">${this.state.agents.length} Registered</span>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Agent ID</th>
                <th>Role</th>
                <th>Parent</th>
                <th>Lifecycle State</th>
                <th>Context Scope</th>
                <th>Trust</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${
                this.state.agents.length === 0
                  ? '<tr><td colspan="7" class="text-center">No agent workers active.</td></tr>'
                  : this.state.agents
                      .map(
                        (a) => `
                <tr class="${a.agent_id === this.state.selectedAgentId ? 'selected-row' : ''}">
                  <td><code>${a.agent_id.slice(0, 10)}...</code></td>
                  <td><span class="role-badge role-${a.role?.toLowerCase()}">${a.role}</span></td>
                  <td>${a.parent_agent_id ? `<code>${a.parent_agent_id.slice(0, 8)}...</code>` : '<span class="text-muted">Root</span>'}</td>
                  <td><span class="state-badge state-${a.lifecycle_state?.toLowerCase()}">${a.lifecycle_state}</span></td>
                  <td><small>${a.context_scope}</small></td>
                  <td><strong>${(a.trust_score * 100).toFixed(0)}%</strong></td>
                  <td>
                    <button class="btn btn-xs btn-outline btn-agent-inspect" data-id="${a.agent_id}">Inspect</button>
                    ${
                      a.lifecycle_state === 'FAILED'
                        ? `<button class="btn btn-xs btn-warning btn-agent-retry" data-id="${a.agent_id}">Retry</button>`
                        : ''
                    }
                    ${
                      ['RUNNING', 'WAITING', 'INITIALIZING'].includes(a.lifecycle_state)
                        ? `<button class="btn btn-xs btn-danger btn-agent-cancel" data-id="${a.agent_id}">Stop</button>`
                        : ''
                    }
                  </td>
                </tr>
              `
                      )
                      .join('')
              }
            </tbody>
          </table>
        </section>
      </div>
    `;
  }

  _renderDagTab() {
    const graph = this.state.swarmGraph;
    return `
      <div class="dag-view">
        <section class="card">
          <div class="card-head">
            <h3>Task Graph & Worker Dependencies</h3>
            <span class="badge">Strict Kahn's Cycle Rejection • Depth Limit ≤ 4</span>
          </div>
          <div class="dag-graph-canvas" id="dag-canvas">
            ${
              !graph || graph.nodes.length === 0
                ? '<div class="empty-state">No graph nodes available for this session.</div>'
                : `
              <div class="dag-nodes-grid">
                ${graph.nodes
                  .map(
                    (node) => `
                  <div class="dag-node-card node-${node.type} state-${node.state?.toLowerCase()}">
                    <div class="node-header">
                      <span class="node-type-pill">${node.type}</span>
                      <span class="node-state-pill">${node.state}</span>
                    </div>
                    <div class="node-title">${this._escapeHtml(node.label)}</div>
                    <div class="node-id"><code>${node.id.slice(0, 10)}</code></div>
                  </div>
                `
                  )
                  .join('')}
              </div>
              <div class="dag-edges-list">
                <h4>Active Dependency Edges:</h4>
                <ul>
                  ${graph.edges
                    .map(
                      (e) => `
                    <li><code>${e.source.slice(0, 8)}</code> ──[${e.type}]──> <code>${e.target.slice(0, 8)}</code></li>
                  `
                    )
                    .join('')}
                </ul>
              </div>
            `
            }
          </div>
        </section>
      </div>
    `;
  }

  _renderSupervisionTab() {
    return `
      <div class="supervision-view">
        <section class="card">
          <div class="card-head">
            <h3>Supervision Engine & Stall Detector</h3>
            <button class="btn btn-sm btn-primary" id="btn-trigger-supervision">🔍 Run Stall Assessment</button>
          </div>
          <p class="section-desc">Evaluates worker progress, runaway recursion, deadlocks, and repeatedly failing tasks.</p>
          <div class="stalls-grid">
            ${
              this.state.agents.length === 0
                ? '<div class="empty-state">No active agents to monitor.</div>'
                : this.state.agents
                    .map(
                      (a) => `
              <div class="stall-card state-${a.lifecycle_state?.toLowerCase()}">
                <div class="stall-card-header">
                  <strong>${a.role} (${a.agent_id.slice(0, 8)})</strong>
                  <span class="state-badge">${a.lifecycle_state}</span>
                </div>
                <div class="stall-card-body">
                  <p><strong>Context Scope:</strong> ${a.context_scope}</p>
                  <p><strong>Capabilities:</strong> ${a.capability_scope?.join(', ') || 'READ-ONLY'}</p>
                  <p><strong>Last Transition:</strong> ${a.history?.length > 0 ? a.history[a.history.length - 1].reason || 'None' : 'Initial'}</p>
                </div>
              </div>
            `
                    )
                    .join('')
            }
          </div>
        </section>
      </div>
    `;
  }

  _renderBlackboardTab() {
    return `
      <div class="blackboard-view">
        <section class="card">
          <div class="card-head">
            <h3>Inter-Agent Typed Communication Audit & Shared Blackboard</h3>
            <span class="badge">Bounded Fact Store (≤500 entries)</span>
          </div>
          <div class="audit-log">
            ${
              this.state.results.length === 0
                ? '<div class="empty-state">No recorded agent messages or facts for this session.</div>'
                : this.state.results
                    .map(
                      (r) => `
              <div class="message-card">
                <div class="message-head">
                  <span class="badge-role">AGENT RESULT</span>
                  <span class="text-muted">Agent: ${r.agent_id ? r.agent_id.slice(0, 8) : 'unknown'}</span>
                  <span class="badge-validation status-${(r.validation_status || 'unvalidated').toLowerCase()}">${r.validation_status || 'UNVALIDATED'}</span>
                </div>
                <div class="message-body">${this._escapeHtml(r.summary || r.result_summary || 'No summary')}</div>
                ${r.evidence?.length > 0 ? `<div class="message-evidence"><strong>Evidence:</strong> ${r.evidence.join('; ')}</div>` : ''}
              </div>
            `
                    )
                    .join('')
            }
          </div>
        </section>
      </div>
    `;
  }

  _renderSynthesisTab() {
    const s = this.state.selectedSwarm;
    return `
      <div class="synthesis-view">
        <section class="card">
          <div class="card-head">
            <h3>Disagreements, Minority Reports & Consensus Synthesis</h3>
            <button class="btn btn-sm btn-primary" id="btn-run-synthesis">✨ Synthesize Final Result</button>
          </div>
          <p class="section-desc">Consensus is evidence-aware. Disagreements and minority positions are explicitly preserved rather than majority-voted away.</p>

          ${
            this.state.conflicts.length > 0
              ? `
            <div class="conflicts-container">
              <h4>⚠️ Active Disagreements (${this.state.conflicts.length})</h4>
              ${this.state.conflicts
                .map(
                  (c) => `
                <div class="conflict-card">
                  <div class="conflict-head">
                    <span class="conflict-type">${c.disagreement_type || 'CONTRADICTION'}</span>
                    <span>Issue: ${this._escapeHtml(c.issue || 'Assertion conflict')}</span>
                  </div>
                  <div class="conflict-agents">Involved: ${(c.involved_agents || []).join(', ')}</div>
                </div>
              `
                )
                .join('')}
            </div>
          `
              : '<div class="banner-success">✓ No unhandled contradictions or deadlocked claims detected.</div>'
          }

          <div class="results-comparison">
            <h4>Output Verification Pipeline:</h4>
            <div class="pipeline-step step-raw">
              <span class="step-num">1</span>
              <div>
                <strong>AGENT RESULT (Worker Output)</strong>
                <p>Untrusted, unvalidated claims produced by individual worker agents.</p>
              </div>
            </div>
            <div class="pipeline-step step-validated">
              <span class="step-num">2</span>
              <div>
                <strong>VALIDATED RESULT (Empirical Verification)</strong>
                <p>Checked against schema, provenance, and deterministic policy gates.</p>
              </div>
            </div>
            <div class="pipeline-step step-verified">
              <span class="step-num">3</span>
              <div>
                <strong>FINAL VERIFIED RESULT (Authoritative Synthesis)</strong>
                <p>Integrated collective outcome with minority reports and uncertainty bounds.</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    `;
  }

  _bindTabActions() {
    // Swarm selection click
    this.container.querySelectorAll('.swarm-card-item').forEach((el) => {
      el.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        this.state.selectedSwarmId = id;
        await this.loadSwarmDetails(id);
        this._renderActiveTab();
      });
    });

    // Pause / Resume / Cancel / Synthesize Swarm buttons
    const pauseBtn = this.container.querySelector('#btn-pause-swarm');
    if (pauseBtn) {
      pauseBtn.addEventListener('click', async (e) => {
        await this.api.pauseSwarm(e.currentTarget.dataset.id);
        await this.loadData();
      });
    }

    const resumeBtn = this.container.querySelector('#btn-resume-swarm');
    if (resumeBtn) {
      resumeBtn.addEventListener('click', async (e) => {
        await this.api.resumeSwarm(e.currentTarget.dataset.id);
        await this.loadData();
      });
    }

    const cancelBtn = this.container.querySelector('#btn-cancel-swarm');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', async (e) => {
        if (confirm('Cancel this swarm and all its child workers?')) {
          await this.api.cancelSwarm(e.currentTarget.dataset.id);
          await this.loadData();
        }
      });
    }

    const synthBtn = this.container.querySelector('#btn-synthesize-swarm') || this.container.querySelector('#btn-run-synthesis');
    if (synthBtn) {
      synthBtn.addEventListener('click', async () => {
        if (!this.state.selectedSwarmId) return;
        try {
          await this.api.synthesizeSwarm(this.state.selectedSwarmId);
          await this.loadData();
          alert('Collective synthesis completed!');
        } catch (e) {
          alert('Synthesis error: ' + e.message);
        }
      });
    }

    const superviseBtn = this.container.querySelector('#btn-trigger-supervision');
    if (superviseBtn) {
      superviseBtn.addEventListener('click', async () => {
        if (!this.state.selectedSwarmId) return;
        try {
          const stalls = await this.api.superviseSwarm(this.state.selectedSwarmId);
          alert(`Supervision assessment completed for ${stalls.length} workers.`);
          await this.loadData();
        } catch (e) {
          alert('Supervision error: ' + e.message);
        }
      });
    }

    // Agent actions: Cancel / Retry
    this.container.querySelectorAll('.btn-agent-cancel').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        if (confirm(`Halt agent ${id}?`)) {
          await this.api.cancelAgent(id);
          await this.loadData();
        }
      });
    });

    this.container.querySelectorAll('.btn-agent-retry').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        await this.api.retryAgent(id);
        await this.loadData();
      });
    });
  }

  async promptCreateSwarm() {
    const objective = prompt('Enter the high-level objective for this autonomous swarm:');
    if (!objective) return;
    try {
      const res = await fetch('/api/v1/swarms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          objective,
          max_depth: 3,
          max_agents: 10,
        }),
      });
      const data = await res.json();
      this.state.selectedSwarmId = data.session_id;
      await this.loadData();
      alert(`Swarm '${data.session_id}' successfully initiated!`);
    } catch (e) {
      alert('Failed to launch swarm: ' + e.message);
    }
  }

  _escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  _renderError(msg) {
    const content = this.container.querySelector('#swarm-tab-content');
    if (content) {
      content.innerHTML = `<div class="banner-error">Error loading swarm orchestration data: ${this._escapeHtml(msg)}</div>`;
    }
  }
}

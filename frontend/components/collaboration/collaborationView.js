/**
 * Kairo Multi-Agent Collaboration & Collective Intelligence View (Task 44)
 * Displays Specialist Rosters, Agent Contracts, Evidence Provenance,
 * Disagreement Resolution, Consensus Scoring, and Collective Synthesis.
 */

import { Endpoints } from '../../lib/api/endpoints.js';

export class CollaborationView {
  constructor(container) {
    this.container = container;
    this.sessions = [];
    this.agents = [];
    this.contracts = [];
    this.evidenceList = [];
    this.disagreements = [];
    this.activeSession = null;
    this.activeTab = 'agents';
    this.isLoading = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="collaboration-view">
        <header class="section-header">
          <div>
            <div class="badge-tag">Task 44 • Collective Intelligence</div>
            <h1 class="page-title">Multi-Agent Collaboration & Governance</h1>
            <p class="page-subtitle">Specialist orchestration, bounded contracts, evidence provenance, disagreement resolution, and supervisor oversight.</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-danger" id="emergency-stop-btn" title="Halt all active agents and contracts across the session">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              Emergency Stop
            </button>
            <button class="btn btn-secondary" id="refresh-collab-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="new-session-btn">
              + New Session
            </button>
          </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">Active Specialists</div>
            <div class="metric-value" id="kpi-agents-count">0</div>
            <div class="metric-subtext">Bounded by contract</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Active Contracts</div>
            <div class="metric-value" id="kpi-contracts-count">0</div>
            <div class="metric-subtext">Zero silent scope expansion</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Evidence Items</div>
            <div class="metric-value" id="kpi-evidence-count">0</div>
            <div class="metric-subtext">Facts, inferences & proofs</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Resolved Disagreements</div>
            <div class="metric-value" id="kpi-disagreements-count">0</div>
            <div class="metric-subtext">Evidence-first resolution</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs-nav" role="tablist">
          <button class="tab-item active" data-tab="agents" id="tab-agents">Specialists & Teams</button>
          <button class="tab-item" data-tab="contracts" id="tab-contracts">Contracts & Scopes</button>
          <button class="tab-item" data-tab="evidence" id="tab-evidence">Evidence Pool</button>
          <button class="tab-item" data-tab="disagreements" id="tab-disagreements">Disagreements & Consensus</button>
          <button class="tab-item" data-tab="synthesis" id="tab-synthesis">Collective Synthesis</button>
        </div>

        <!-- Tab Content Container -->
        <div class="tab-content" id="collab-tab-content">
          <div class="loading-state">Loading collaboration state...</div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  }

  bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-collab-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    const emergencyBtn = this.container.querySelector('#emergency-stop-btn');
    if (emergencyBtn) {
      emergencyBtn.addEventListener('click', () => this.handleEmergencyStop());
    }

    const newSessionBtn = this.container.querySelector('#new-session-btn');
    if (newSessionBtn) {
      newSessionBtn.addEventListener('click', () => this.promptNewSession());
    }

    const tabs = this.container.querySelectorAll('.tab-item');
    tabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        tabs.forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.activeTab = e.currentTarget.dataset.tab;
        this.renderTabContent();
      });
    });
  }

  async loadData() {
    this.isLoading = true;
    try {
      const [agentsRes, evidenceRes] = await Promise.all([
        Endpoints.listCollaborationAgents().catch(() => []),
        Endpoints.listCollaborationEvidence().catch(() => []),
      ]);

      this.agents = Array.isArray(agentsRes) ? agentsRes : [];
      this.evidenceList = Array.isArray(evidenceRes) ? evidenceRes : [];

      this.updateKPIs();
      this.renderTabContent();
    } catch (err) {
      console.error('Failed to load collaboration data:', err);
    } finally {
      this.isLoading = false;
    }
  }

  updateKPIs() {
    const agEl = this.container.querySelector('#kpi-agents-count');
    const evEl = this.container.querySelector('#kpi-evidence-count');
    const ctEl = this.container.querySelector('#kpi-contracts-count');
    const dgEl = this.container.querySelector('#kpi-disagreements-count');

    if (agEl) agEl.textContent = this.agents.length.toString();
    if (evEl) evEl.textContent = this.evidenceList.length.toString();
    if (ctEl) ctEl.textContent = this.contracts.length.toString();
    if (dgEl) dgEl.textContent = this.disagreements.length.toString();
  }

  renderTabContent() {
    const content = this.container.querySelector('#collab-tab-content');
    if (!content) return;

    switch (this.activeTab) {
      case 'agents':
        this.renderAgentsTab(content);
        break;
      case 'contracts':
        this.renderContractsTab(content);
        break;
      case 'evidence':
        this.renderEvidenceTab(content);
        break;
      case 'disagreements':
        this.renderDisagreementsTab(content);
        break;
      case 'synthesis':
        this.renderSynthesisTab(content);
        break;
      default:
        content.innerHTML = `<div class="empty-state">Select a tab above.</div>`;
    }
  }

  renderAgentsTab(content) {
    if (this.agents.length === 0) {
      content.innerHTML = `
        <div class="empty-state-card">
          <h3>No Registered Specialists</h3>
          <p>Register specialist agents with explicit roles, capabilities, and budgets.</p>
          <button class="btn btn-primary" id="add-agent-btn">+ Register Specialist</button>
        </div>
      `;
      const btn = content.querySelector('#add-agent-btn');
      if (btn) btn.addEventListener('click', () => this.promptRegisterAgent());
      return;
    }

    const cards = this.agents.map(a => `
      <div class="specialist-card ${a.health === 'HEALTHY' ? 'healthy' : 'degraded'}">
        <div class="card-header">
          <div class="agent-title">
            <strong>${a.name}</strong>
            <span class="role-pill">${a.role}</span>
          </div>
          <span class="health-status ${a.health.toLowerCase()}">${a.health}</span>
        </div>
        <div class="card-body">
          <div class="prop-row">
            <span class="prop-name">Version:</span>
            <span class="prop-val">${a.version}</span>
          </div>
          <div class="prop-row">
            <span class="prop-name">Status:</span>
            <span class="prop-val">${a.status}</span>
          </div>
          <div class="capabilities-list">
            ${(a.capabilities || []).map(c => `<span class="cap-tag">${c}</span>`).join('')}
          </div>
        </div>
        <div class="card-footer">
          <button class="btn btn-xs btn-secondary" onclick="window.issueContractFor('${a.agent_id}')">Issue Contract</button>
        </div>
      </div>
    `).join('');

    content.innerHTML = `
      <div class="agents-grid">
        ${cards}
      </div>
    `;
  }

  renderContractsTab(content) {
    content.innerHTML = `
      <div class="contracts-panel">
        <div class="panel-intro">
          <h3>Agent Contracts & Scope Boundaries</h3>
          <p>Agents operate strictly within contract scope (resources, tools, budget). Silent scope expansion is blocked by the Supervisor.</p>
        </div>
        <div class="contracts-list">
          <div class="contract-card">
            <div class="contract-header">
              <span class="contract-id">CT-DEMO-01</span>
              <span class="contract-status active">ACTIVE</span>
            </div>
            <div class="contract-objective">
              <strong>Objective:</strong> Perform AST security audit and dependency scan
            </div>
            <div class="contract-scopes">
              <div class="scope-item"><strong>Tools:</strong> code_read_file, code_search</div>
              <div class="scope-item"><strong>Budget:</strong> 25,000 tokens • $0.50 max</div>
              <div class="scope-item"><strong>Scope:</strong> Isolated to backend/app/auth/</div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderEvidenceTab(content) {
    if (this.evidenceList.length === 0) {
      content.innerHTML = `
        <div class="empty-state-card">
          <h3>No Evidence Published Yet</h3>
          <p>Specialists publish verified facts, inferences, hypotheses, and recommendations to this shared pool.</p>
        </div>
      `;
      return;
    }

    const items = this.evidenceList.map(e => `
      <div class="evidence-item ${e.is_verified ? 'verified-evidence' : ''}">
        <div class="evidence-header">
          <span class="fact-pill ${e.fact_type.toLowerCase()}">${e.fact_type}</span>
          ${e.is_verified ? '<span class="verified-badge">✓ Independently Verified</span>' : '<span class="unverified-badge">Unverified</span>'}
          <span class="evidence-time">${new Date(e.timestamp).toLocaleTimeString()}</span>
        </div>
        <div class="evidence-claim">
          ${e.claim}
        </div>
        <div class="evidence-footer">
          <span class="producer-tag">Producer: ${e.producer_agent_id}</span>
        </div>
      </div>
    `).join('');

    content.innerHTML = `<div class="evidence-stream">${items}</div>`;
  }

  renderDisagreementsTab(content) {
    content.innerHTML = `
      <div class="disagreements-panel">
        <div class="panel-intro">
          <h3>Disagreement Resolution & Consensus Arena</h3>
          <p><strong>Evidence-First Truth:</strong> 1 verified empirical evidence point strictly defeats 3 unverified claims. Majority voting does not override verified evidence.</p>
        </div>

        <div class="consensus-demo-card">
          <h4>Consensus Status: <span class="status-evidence-supported">EVIDENCE_SUPPORTED</span></h4>
          <div class="claim-comparison">
            <div class="claim-box rejected">
              <div class="claim-header">Claim A (3 unverified votes)</div>
              <p>"Memory leak caused by circular Python references."</p>
              <div class="claim-votes">Votes: Agent 1, Agent 2, Agent 3 (Unverified)</div>
            </div>
            <div class="vs-divider">VS</div>
            <div class="claim-box accepted">
              <div class="claim-header">Claim B (1 verified proof) ★ WINNER</div>
              <p>"Memory leak caused by unclosed DB connection pool in middleware."</p>
              <div class="claim-votes">Proof: Verified heap dump & reproduction test (Empirical)</div>
            </div>
          </div>
          <div class="resolution-notes">
            <strong>Supervisor Ruling:</strong> Verified empirical trace defeats unverified consensus. Claim B adopted.
          </div>
        </div>
      </div>
    `;
  }

  renderSynthesisTab(content) {
    content.innerHTML = `
      <div class="synthesis-panel">
        <div class="panel-intro">
          <h3>Collective Synthesis & Provenance Lineage</h3>
          <p>Synthesizes specialist findings while preserving conflicts, uncertainties, and full causal provenance from the root goal.</p>
        </div>
        <div class="synthesis-card">
          <div class="synthesis-header">
            <h4>Synthesis Result</h4>
            <span class="verified-badge">Verified Synthesis</span>
          </div>
          <div class="synthesis-body">
            <p class="synthesis-text">All specialists completed assigned contracts. Code changes passed independent verification and policy gates.</p>
            <div class="provenance-trail">
              <span class="prov-node">Goal</span> →
              <span class="prov-node">Supervisor</span> →
              <span class="prov-node">Decomposition</span> →
              <span class="prov-node">Specialists</span> →
              <span class="prov-node">Evidence</span> →
              <span class="prov-node">Verification</span> →
              <span class="prov-node verified">Adopted</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  async handleEmergencyStop() {
    const confirmStop = window.confirm('EMERGENCY STOP: Halt all active agents, contracts, and subtasks across the session immediately?');
    if (!confirmStop) return;

    try {
      await Endpoints.triggerEmergencyStop({
        session_id: this.activeSession?.session_id || 'default_session',
        reason: 'Operator triggered emergency stop',
        triggered_by: 'OPERATOR',
      });
      alert('Emergency stop executed successfully. All agents and subtasks halted.');
      await this.loadData();
    } catch (err) {
      alert('Emergency stop failed: ' + err.message);
    }
  }

  promptNewSession() {
    const goal = window.prompt('Enter high-level goal for multi-agent collaboration:');
    if (!goal) return;

    Endpoints.createCollaborationSession({
      goal: goal.trim(),
      project_id: 'default_project',
    }).then(res => {
      this.activeSession = res;
      alert(`Collaboration session created: ${res.session_id}`);
      this.loadData();
    }).catch(err => {
      alert('Failed to create session: ' + err.message);
    });
  }

  promptRegisterAgent() {
    const name = window.prompt('Enter agent name (e.g., "Security Specialist"):');
    if (!name) return;
    const role = window.prompt('Enter role (RESEARCHER, CODER, TESTER, VERIFIER, SECURITY_ANALYST):', 'SECURITY_ANALYST');
    if (!role) return;

    Endpoints.registerCollaborationAgent({
      name: name.trim(),
      role: role.trim().toUpperCase(),
      capabilities: [role.toLowerCase(), 'analysis'],
    }).then(() => {
      this.loadData();
    }).catch(err => {
      alert('Failed to register agent: ' + err.message);
    });
  }
}

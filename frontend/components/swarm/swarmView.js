/**
 * Collective Intelligence & Swarm Reasoning Engine View (Task 64)
 * Glassmorphic multi-agent swarm reasoning dashboard.
 */

import { swarmApi } from '../../lib/api/endpoints.js';

export class SwarmView {
  constructor(containerId) {
    this.container = typeof document !== 'undefined' ? (typeof containerId === 'string' ? document.getElementById(containerId) : containerId) : null;
    this.activeTab = 'active_swarms'; // active_swarms, agent_board, reasoning, debate, disagreements, consensus, verification_audit
    this.sessions = [];
    this.selectedSession = null;
    this.agents = [];
    this.tasks = [];
    this.results = [];
    this.reviews = [];
    this.disagreements = [];
    this.minorityReports = [];
    this.debates = [];
    this.consensus = null;
    this.selectedAgent = null;
    this.selectedDisagreement = null;
    this.auditTrail = [];
    this.isLoading = false;
  }

  async init() {
    if (!this.container) return;
    this.renderSkeleton();
    await this.loadSessions();
  }

  async loadSessions() {
    this.isLoading = true;
    try {
      this.sessions = await swarmApi.listSessions(20);
      if (this.sessions && this.sessions.length > 0 && !this.selectedSession) {
        await this.selectSession(this.sessions[0].swarm_id);
      }
    } catch (err) {
      console.error('Failed to load swarm sessions:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async selectSession(swarmOrId) {
    if (typeof swarmOrId === 'object' && swarmOrId !== null) {
      this.selectedSession = swarmOrId;
      if (this.container) this.render();
      return;
    }
    const swarmId = swarmOrId;
    this.isLoading = true;
    try {
      this.selectedSession = await swarmApi.getSession(swarmId);
      this.agents = await swarmApi.getAgents(swarmId);
      this.tasks = await swarmApi.getTasks(swarmId);
      this.results = await swarmApi.getResults(swarmId);
      this.reviews = await swarmApi.getReviews(swarmId);
      this.disagreements = await swarmApi.getDisagreements(swarmId);
      this.minorityReports = await swarmApi.getMinorities(swarmId);
      this.debates = this.selectedSession?.debates || [];
      this.timeline = await swarmApi.getTimeline(swarmId);
      this.auditTrail = await swarmApi.getAudit(swarmId, 50);
    } catch (err) {
      console.error('Failed to load swarm details:', err);
    } finally {
      this.isLoading = false;
      if (this.container) this.render();
    }
  }

  selectAgent(agent) {
    this.selectedAgent = agent;
    if (this.container) this.render();
  }

  selectDisagreement(disagreement) {
    this.selectedDisagreement = disagreement;
    if (this.container) this.render();
  }

  switchTab(tabName) {
    this.activeTab = tabName;
    if (this.container) this.render();
  }

  setTab(tabName) {
    this.switchTab(tabName);
  }

  renderSkeleton() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="swarm-container glass-panel">
        <header class="swarm-header">
          <div class="header-titles">
            <h1 class="text-gradient">Collective Intelligence & Swarm Reasoning Engine</h1>
            <p class="subtitle">Multi-Agent Specialization • Dialectical Debate • Evidence-Weighted Consensus • Minority Reports</p>
          </div>
          <div class="swarm-invariants-banner">
            <span class="inv-tag">AGENT AGREEMENT ≠ TRUTH</span>
            <span class="inv-tag">CONSENSUS ≠ FACT</span>
            <span class="inv-tag">MAJORITY ≠ EVIDENCE</span>
            <span class="inv-tag">CAPABILITY ≠ AUTHORIZATION</span>
            <span class="inv-tag">UNKNOWN ≠ HEALTHY</span>
          </div>
        </header>
        <nav class="swarm-nav">
          <button class="nav-tab ${this.activeTab === 'active_swarms' ? 'active' : ''}" data-tab="active_swarms">Active Swarms</button>
          <button class="nav-tab ${this.activeTab === 'agent_board' ? 'active' : ''}" data-tab="agent_board">Agent Board</button>
          <button class="nav-tab ${this.activeTab === 'reasoning' ? 'active' : ''}" data-tab="reasoning">Reasoning & Evidence</button>
          <button class="nav-tab ${this.activeTab === 'debate' ? 'active' : ''}" data-tab="debate">Dialectical Debate</button>
          <button class="nav-tab ${this.activeTab === 'disagreements' ? 'active' : ''}" data-tab="disagreements">Disagreements & Taxonomy</button>
          <button class="nav-tab ${this.activeTab === 'consensus' ? 'active' : ''}" data-tab="consensus">Consensus & Minority Reports</button>
          <button class="nav-tab ${this.activeTab === 'verification_audit' ? 'active' : ''}" data-tab="verification_audit">Verification & Audit</button>
        </nav>
        <main class="swarm-content" id="swarm-content-area">
          <div class="loading-spinner">Loading Collective Reasoning Center...</div>
        </main>
      </div>
    `;
    this.attachNavEvents();
  }

  attachNavEvents() {
    if (!this.container) return;
    const tabs = this.container.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        const target = e.currentTarget.getAttribute('data-tab');
        this.switchTab(target);
      });
    });
  }

  render() {
    if (!this.container) return;
    const contentArea = this.container.querySelector('#swarm-content-area');
    if (!contentArea) {
      this.renderSkeleton();
      return;
    }

    // Update active nav button
    this.container.querySelectorAll('.nav-tab').forEach(tab => {
      if (tab.getAttribute('data-tab') === this.activeTab) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    switch (this.activeTab) {
      case 'active_swarms':
        contentArea.innerHTML = this.renderActiveSwarmsTab();
        break;
      case 'agent_board':
        contentArea.innerHTML = this.renderAgentBoardTab();
        break;
      case 'reasoning':
        contentArea.innerHTML = this.renderReasoningTab();
        break;
      case 'debate':
        contentArea.innerHTML = this.renderDebateTab();
        break;
      case 'disagreements':
        contentArea.innerHTML = this.renderDisagreementsTab();
        break;
      case 'consensus':
        contentArea.innerHTML = this.renderConsensusTab();
        break;
      case 'verification_audit':
        contentArea.innerHTML = this.renderVerificationAuditTab();
        break;
      default:
        contentArea.innerHTML = this.renderActiveSwarmsTab();
    }
  }

  renderActiveSwarmsTab() {
    const sessionListHtml = this.sessions.length > 0 ? this.sessions.map(s => `
      <div class="session-card ${this.selectedSession && this.selectedSession.swarm_id === s.swarm_id ? 'selected' : ''}" data-id="${s.swarm_id}">
        <div class="session-header">
          <span class="session-topology badge-${s.topology.toLowerCase()}">${s.topology}</span>
          <span class="session-status status-${s.status.toLowerCase()}">${s.status}</span>
        </div>
        <h4 class="session-goal">${s.goal}</h4>
        <div class="session-meta">
          <span>Agents: ${s.agent_count}</span>
          <span>Consensus: ${(s.consensus_score * 100).toFixed(0)}%</span>
          <span>Confidence: ${(s.confidence * 100).toFixed(0)}%</span>
        </div>
        <div class="verification-badge badge-${s.verification_status.toLowerCase()}">${s.verification_status}</div>
      </div>
    `).join('') : '<div class="empty-state">No swarm reasoning sessions found. Launch a new collective session.</div>';

    const selectedDetailsHtml = this.selectedSession ? `
      <div class="session-detail-panel glass-card">
        <h3>Swarm Session: ${this.selectedSession.swarm_id}</h3>
        <p class="goal-highlight"><strong>Objective:</strong> ${this.selectedSession.objective.goal}</p>
        <div class="detail-kpis">
          <div class="kpi-box">
            <span class="kpi-val">${this.selectedSession.topology}</span>
            <span class="kpi-lbl">Topology</span>
          </div>
          <div class="kpi-box">
            <span class="kpi-val">${(this.selectedSession.consensus ? this.selectedSession.consensus.consensus_score * 100 : 0).toFixed(0)}%</span>
            <span class="kpi-lbl">Consensus Score</span>
          </div>
          <div class="kpi-box">
            <span class="kpi-val">${(this.selectedSession.final_result ? this.selectedSession.final_result.confidence * 100 : 0).toFixed(0)}%</span>
            <span class="kpi-lbl">Calibrated Confidence</span>
          </div>
          <div class="kpi-box">
            <span class="kpi-val status-${this.selectedSession.status.toLowerCase()}">${this.selectedSession.status}</span>
            <span class="kpi-lbl">Lifecycle Status</span>
          </div>
        </div>

        <div class="executive-summary-section">
          <h4>Executive Collective Summary</h4>
          <p>${this.selectedSession.final_result ? this.selectedSession.final_result.summary : 'Reasoning in progress...'}</p>
        </div>

        <div class="session-action-bar">
          <button class="btn btn-primary" id="btn-verify-swarm">Verify Outcome</button>
          <button class="btn btn-secondary" id="btn-pause-swarm">Pause</button>
          <button class="btn btn-secondary" id="btn-resume-swarm">Resume</button>
          <button class="btn btn-danger" id="btn-cancel-swarm">Cancel</button>
        </div>
      </div>
    ` : '<div class="empty-detail">Select a session to view details.</div>';

    return `
      <div class="tab-active-swarms grid-2col">
        <div class="session-list-column">
          <div class="column-header">
            <h3>Swarm Reasoning Sessions</h3>
            <button class="btn btn-accent btn-sm" id="btn-new-swarm">+ New Swarm</button>
          </div>
          <div class="session-items">${sessionListHtml}</div>
        </div>
        <div class="session-detail-column">${selectedDetailsHtml}</div>
      </div>
    `;
  }

  renderAgentBoardTab() {
    if (!this.agents || this.agents.length === 0) {
      return '<div class="empty-state">No agents currently assigned to this swarm.</div>';
    }

    const agentCards = this.agents.map(ag => `
      <div class="agent-card glass-card">
        <div class="agent-card-header">
          <span class="agent-role-badge badge-${ag.role.toLowerCase()}">${ag.role}</span>
          <span class="agent-health-badge health-${ag.health.toLowerCase()}">${ag.health}</span>
        </div>
        <h4 class="agent-name">${ag.name}</h4>
        <p class="agent-desc">${ag.description || 'Specialist reasoning agent.'}</p>
        <div class="agent-capabilities">
          <strong>Capabilities:</strong>
          <div class="chip-row">${ag.capabilities.map(c => `<span class="chip">${c}</span>`).join('')}</div>
        </div>
        <div class="agent-limitations">
          <strong>Limitations:</strong>
          <div class="chip-row chip-warn">${ag.limitations.map(l => `<span class="chip chip-limit">${l}</span>`).join('')}</div>
        </div>
        <div class="agent-specs-footer">
          <span>Trust: ${(ag.trust_level * 100).toFixed(0)}%</span>
          <span>Cost Profile: ${ag.cost_profile}x</span>
          <span>Latency: ${ag.latency_profile_ms}ms</span>
        </div>
      </div>
    `).join('');

    return `
      <div class="tab-agent-board">
        <div class="board-header">
          <h3>Swarm Specialist Agent Board</h3>
          <p>Each agent declares explicit capabilities, limitations, and operational boundaries. Capability ≠ Authorization.</p>
        </div>
        <div class="agent-grid">${agentCards}</div>
      </div>
    `;
  }

  renderReasoningTab() {
    if (!this.results || this.results.length === 0) {
      return '<div class="empty-state">No independent reasoning results available yet.</div>';
    }

    const resultCards = this.results.map(r => `
      <div class="reasoning-card glass-card">
        <div class="reasoning-card-header">
          <span class="agent-role-badge badge-${r.role.toLowerCase()}">${r.role}</span>
          <span class="confidence-tag">Confidence: ${(r.confidence * 100).toFixed(0)}%</span>
        </div>
        <h4 class="reasoning-answer">${r.answer}</h4>
        <div class="assertions-block">
          <strong>Atomic Epistemic Assertions:</strong>
          <div class="assertion-list">
            ${r.claims.map(c => `
              <div class="assertion-item">
                <span class="epistemic-type type-${c.epistemic_type.toLowerCase()}">${c.epistemic_type}</span>
                <span class="assertion-text">${c.text}</span>
                <span class="assertion-confidence">${(c.confidence * 100).toFixed(0)}%</span>
              </div>
            `).join('')}
          </div>
        </div>
        <div class="evidence-block">
          <strong>Supporting Evidence:</strong>
          <ul>
            ${r.evidence.map(e => `<li><strong>${e.type || 'Evidence'}:</strong> ${e.finding || e.source || JSON.stringify(e)}</li>`).join('')}
          </ul>
        </div>
      </div>
    `).join('');

    return `
      <div class="tab-reasoning">
        <div class="reasoning-header">
          <h3>Independent Specialist Reasoning & Evidence Collection</h3>
          <p>Initial analysis executed independently to prevent premature herd bias. Observation ≠ Claim ≠ Inference.</p>
        </div>
        <div class="reasoning-grid">${resultCards}</div>
      </div>
    `;
  }

  renderDebateTab() {
    if (!this.debates || this.debates.length === 0) {
      return '<div class="empty-state">No dialectical debates triggered for this session. (Consensus reached without unresolved dispute).</div>';
    }

    const debateCards = this.debates.map(d => `
      <div class="debate-session-card glass-card">
        <div class="debate-header">
          <h4>Debate Topic: ${d.topic}</h4>
          <span class="debate-status status-${d.status.toLowerCase()}">${d.status}</span>
        </div>
        <p class="debate-outcome"><strong>Outcome:</strong> ${d.outcome || 'Debate ongoing...'}</p>
        <div class="rounds-container">
          ${d.rounds.map(rnd => `
            <div class="round-card">
              <h5>Round ${rnd.round_number}</h5>
              <div class="turns-list">
                ${rnd.turns.map(trn => `
                  <div class="turn-item">
                    <span class="agent-role-badge badge-${trn.role.toLowerCase()}">${trn.role}</span>
                    <p class="turn-statement">${trn.statement}</p>
                    <small>Citations: ${trn.evidence_cited.join(', ')}</small>
                  </div>
                `).join('')}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');

    return `
      <div class="tab-debate">
        <div class="debate-page-header">
          <h3>Controlled Dialectical Debates</h3>
          <p>Strictly bounded argument rounds (max rounds ≤ 3) to challenge assumptions without infinite agent loops.</p>
        </div>
        <div class="debates-list">${debateCards}</div>
      </div>
    `;
  }

  renderDisagreementsTab() {
    if (!this.disagreements || this.disagreements.length === 0) {
      return '<div class="empty-state">No active contradictions or disagreements detected.</div>';
    }

    const disagreementCards = this.disagreements.map(dis => `
      <div class="disagreement-card glass-card">
        <div class="disagreement-header">
          <span class="taxonomy-badge category-${dis.category.toLowerCase()}">${dis.category}</span>
          <span class="severity-badge severity-${dis.severity.toLowerCase()}">${dis.severity}</span>
        </div>
        <h4 class="disagreement-issue">${dis.issue}</h4>
        <p class="root-cause"><strong>Root Cause Analysis:</strong> ${dis.root_cause_explanation}</p>
        <div class="positions-comparison">
          ${Object.entries(dis.positions).map(([agentId, pos]) => `
            <div class="position-bubble">
              <strong>Agent ${agentId}:</strong>
              <p>${pos}</p>
            </div>
          `).join('')}
        </div>
        <div class="resolution-footer">
          <span class="status-badge status-${dis.status.toLowerCase()}">${dis.status}</span>
          <span>${dis.resolution || 'Pending dialectical resolution'}</span>
        </div>
      </div>
    `).join('');

    return `
      <div class="tab-disagreements">
        <div class="disagreements-header">
          <h3>10-Class Disagreement Taxonomy</h3>
          <p>Kairo does not simply vote. The system isolates the fundamental reason for divergence.</p>
        </div>
        <div class="disagreements-grid">${disagreementCards}</div>
      </div>
    `;
  }

  renderConsensusTab() {
    const consensus = this.selectedSession ? this.selectedSession.consensus : null;
    const minorities = this.minorityReports || [];

    const consensusHtml = consensus ? `
      <div class="consensus-hero glass-card">
        <div class="consensus-badge-row">
          <span class="outcome-badge outcome-${consensus.outcome.toLowerCase()}">${consensus.outcome}</span>
          <span class="score-badge">Consensus Score: ${(consensus.consensus_score * 100).toFixed(0)}%</span>
        </div>
        <h3 class="majority-alignment">Majority Position: ${consensus.majority_opinion}</h3>
        <p class="consensus-rationale"><strong>Rationale:</strong> ${consensus.rationale}</p>
        <div class="agents-breakdown">
          <span><strong>Supporting Agents:</strong> ${consensus.supporting_agents.join(', ')}</span>
          <span><strong>Dissenting Agents:</strong> ${consensus.dissenting_agents.join(', ') || 'None'}</span>
        </div>
      </div>
    ` : '<div class="empty-state">Consensus evaluation pending.</div>';

    const minoritiesHtml = minorities.length > 0 ? minorities.map(m => `
      <div class="minority-card glass-card">
        <div class="minority-header">
          <span class="agent-role-badge badge-${m.dissenting_role.toLowerCase()}">Minority: ${m.dissenting_role}</span>
          <span class="confidence-tag">Confidence: ${(m.confidence * 100).toFixed(0)}%</span>
        </div>
        <h4 class="minority-position">${m.position}</h4>
        <p><strong>Reasoning:</strong> ${m.reasoning}</p>
        <div class="failure-conditions">
          <strong>Failure Scenario Conditions:</strong>
          <div class="chip-row chip-warn">${m.failure_scenario_conditions.map(c => `<span class="chip">${c}</span>`).join('')}</div>
        </div>
        <p class="divergence"><strong>Divergence from Majority:</strong> ${m.divergence_from_majority}</p>
      </div>
    `).join('') : '<div class="empty-state">No dissenting minority reports preserved (Unanimous agreement).</div>';

    return `
      <div class="tab-consensus">
        <div class="consensus-header">
          <h3>Evidence-Weighted Consensus & Preserved Minority Reports</h3>
          <p>Consensus ≠ Fact. Minority opinions are preserved as first-class failure safeguards.</p>
        </div>
        ${consensusHtml}
        <div class="minority-reports-section">
          <h4>Preserved Minority Reports & Failure Mode Contingencies</h4>
          <div class="minorities-grid">${minoritiesHtml}</div>
        </div>
      </div>
    `;
  }

  renderVerificationAuditTab() {
    const finalResult = this.selectedSession ? this.selectedSession.final_result : null;

    const verifStatusHtml = finalResult ? `
      <div class="verification-hero glass-card">
        <div class="verif-status-badge badge-${finalResult.verification_status.toLowerCase()}">${finalResult.verification_status}</div>
        <h3>Verification Gate: ${finalResult.verification_status === 'VERIFIED' ? 'Passed Ground Truth & Policy Invariants' : 'Pending Formal Truth Verification'}</h3>
        <p>Consensus ≠ Verification. Execution requires explicit Policy → Authorization → Approval → ToolExecutor.</p>
      </div>
    ` : '';

    const auditItemsHtml = this.auditTrail.length > 0 ? this.auditTrail.map(rec => `
      <div class="audit-timeline-item">
        <div class="audit-seq">#${rec.sequence_number}</div>
        <div class="audit-body">
          <div class="audit-title-row">
            <strong>${rec.event_type}</strong>
            <span class="audit-time">${rec.timestamp}</span>
          </div>
          <div class="audit-hash-row">
            <code>Hash: ${rec.hash || rec.entry_hash}</code>
            <code>Prev: ${rec.previous_hash}</code>
          </div>
        </div>
      </div>
    `).join('') : '<div class="empty-state">No audit records logged.</div>';

    return `
      <div class="tab-verification-audit">
        ${verifStatusHtml}
        <div class="audit-section glass-card">
          <h4>Cryptographic SHA-256 Tamper-Evident Audit Trail</h4>
          <div class="audit-timeline">${auditItemsHtml}</div>
        </div>
      </div>
    `;
  }
}

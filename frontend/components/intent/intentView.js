/**
 * Kairo Intent Understanding, Goal Extraction & Safe Motivation Engine View (Task 48)
 * Visualizes Understood Intents, Goal vs Task Separation, Discovered Constraints,
 * Consequence-Aware Ambiguity Gating, Clarifications, and Functional Motivations.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class IntentView {
  constructor(container) {
    this.container = container;
    this.intents = [];
    this.goals = [];
    this.clarifications = [];
    this.health = null;
    this.activeTab = 'intents';
    this.isLoading = false;
  }

  formatDate(isoStr) {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  getStatusBadgeClass(status) {
    switch (status) {
      case 'INTERPRETED':
      case 'CONFIRMED':
      case 'COMPLETED':
        return 'badge-success';
      case 'NEEDS_CLARIFICATION':
      case 'WAITING_USER':
        return 'badge-warning';
      case 'REJECTED':
      case 'CANCELLED':
        return 'badge-danger';
      case 'EXECUTING':
        return 'badge-primary';
      default:
        return 'badge-neutral';
    }
  }

  async render() {
    this.container.innerHTML = `
      <div class="intent-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Intent Understanding & Goal Extraction Engine</h1>
            <p class="page-subtitle">Distinguishing user requests from inferences, objective modeling, constraint discovery & safe motivation</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-intent-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="parse-intent-modal-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Parse Human Input
            </button>
          </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">Parsed Intents</div>
            <div class="metric-value" id="kpi-intents-total">${this.intents.length}</div>
            <div class="metric-delta">Tracked in session</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Active Goals</div>
            <div class="metric-value text-accent" id="kpi-goals-active">${this.goals.length}</div>
            <div class="metric-delta">Distinct from tasks</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Pending Clarifications</div>
            <div class="metric-value text-warning" id="kpi-pending-clarifications">${this.clarifications.length}</div>
            <div class="metric-delta">Zero guessing on risk</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Calibration Ratio</div>
            <div class="metric-value text-success" id="kpi-calibration-ratio">
              ${this.health ? this.health.calibration_ratio : '1.00'}
            </div>
            <div class="metric-delta">Confidence accuracy</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs-nav">
          <button class="tab-btn ${this.activeTab === 'intents' ? 'active' : ''}" data-tab="intents">
            Intents (${this.intents.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'goals' ? 'active' : ''}" data-tab="goals">
            Goals & Objectives (${this.goals.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'clarifications' ? 'active' : ''}" data-tab="clarifications">
            Clarifications (${this.clarifications.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'tradeoffs' ? 'active' : ''}" data-tab="tradeoffs">
            Tradeoffs & Motivations
          </button>
        </div>

        <!-- Tab Content Panes -->
        <div class="tab-content" id="intent-tab-panes">
          ${this.renderActiveTab()}
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  }

  renderActiveTab() {
    if (this.activeTab === 'intents') return this.renderIntentsTab();
    if (this.activeTab === 'goals') return this.renderGoalsTab();
    if (this.activeTab === 'clarifications') return this.renderClarificationsTab();
    if (this.activeTab === 'tradeoffs') return this.renderTradeoffsTab();
    return '';
  }

  renderIntentsTab() {
    if (this.intents.length === 0) {
      return `
        <div class="empty-state">
          <p class="empty-text">No user intents recorded yet. Enter a natural language request above.</p>
        </div>
      `;
    }

    return `
      <div class="items-list">
        ${this.intents.map(intent => `
          <div class="item-card" data-id="${intent.intent_id}">
            <div class="item-header">
              <div class="item-title-row">
                <span class="badge ${this.getStatusBadgeClass(intent.status)}">${intent.status}</span>
                <span class="badge badge-outline">${intent.intent_type}</span>
                <span class="badge badge-subtle">Urgency: ${intent.urgency || 'NORMAL'}</span>
                <span class="item-timestamp">${this.formatDate(intent.created_at)}</span>
              </div>
              <div class="item-actions">
                <button class="btn btn-sm btn-outline correct-btn" data-id="${intent.intent_id}">Correct ("Not what I meant")</button>
                <button class="btn btn-sm btn-danger-outline revoke-btn" data-id="${intent.intent_id}">Revoke</button>
              </div>
            </div>
            <div class="item-body">
              <p><strong>Raw Input:</strong> <em>"${intent.raw_input}"</em></p>
              <p><strong>Understood Objective:</strong> ${intent.normalized_intent}</p>
              ${intent.assumptions && intent.assumptions.length > 0 ? `
                <div class="assumptions-box">
                  <strong>Assumptions (Transparent):</strong>
                  <ul>
                    ${intent.assumptions.map(a => `<li>[${a.source}] ${a.statement} (Impact: ${a.impact})</li>`).join('')}
                  </ul>
                </div>
              ` : ''}
              ${intent.constraints && intent.constraints.length > 0 ? `
                <div class="constraints-box">
                  <strong>Constraints:</strong> ${intent.constraints.map(c => `${c.category}:${c.value}`).join(', ')}
                </div>
              ` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderGoalsTab() {
    if (this.goals.length === 0) {
      return `
        <div class="empty-state">
          <p class="empty-text">No active goals found. Goals represent desired outcomes distinct from execution tasks.</p>
        </div>
      `;
    }

    return `
      <div class="items-list">
        ${this.goals.map(goal => `
          <div class="item-card" data-id="${goal.goal_id}">
            <div class="item-header">
              <span class="badge ${this.getStatusBadgeClass(goal.status)}">${goal.status}</span>
              <span class="badge badge-outline">Priority: ${goal.priority}</span>
              <span class="item-timestamp">${this.formatDate(goal.created_at)}</span>
            </div>
            <div class="item-body">
              <h4>${goal.description}</h4>
              <p><strong>Goal ID:</strong> <code>${goal.goal_id}</code> | <strong>Intent ID:</strong> <code>${goal.intent_id}</code></p>
              <div class="success-criteria-box">
                <strong>Success Criteria:</strong>
                <ul>
                  ${(goal.success_criteria || []).map(sc => `<li>${sc.description || JSON.stringify(sc)}</li>`).join('') || '<li>None explicitly specified (Safe default completion).</li>'}
                </ul>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderClarificationsTab() {
    if (this.clarifications.length === 0) {
      return `
        <div class="empty-state">
          <p class="empty-text">No pending clarifications. All active intents are safely resolved.</p>
        </div>
      `;
    }

    return `
      <div class="items-list">
        ${this.clarifications.map(cl => `
          <div class="item-card card-warning" data-id="${cl.clarification_id}">
            <div class="item-header">
              <span class="badge badge-warning">AMBIGUITY GATE</span>
              <span class="badge badge-outline">Decision: ${cl.affected_decision}</span>
            </div>
            <div class="item-body">
              <p class="clarification-question"><strong>${cl.question}</strong></p>
              <p class="clarification-reason"><small>${cl.reason}</small></p>
              ${cl.options && cl.options.length > 0 ? `
                <div class="options-container">
                  ${cl.options.map(opt => `
                    <button class="btn btn-sm btn-secondary answer-opt-btn" data-cid="${cl.clarification_id}" data-val="${opt}">
                      ${opt}
                    </button>
                  `).join('')}
                </div>
              ` : ''}
              <div class="custom-answer-row">
                <input type="text" class="input-text custom-answer-input" placeholder="Type clarification answer..." id="answer-input-${cl.clarification_id}">
                <button class="btn btn-sm btn-primary submit-answer-btn" data-cid="${cl.clarification_id}">Submit Answer</button>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderTradeoffsTab() {
    return `
      <div class="tradeoffs-container">
        <h3>Safe Motivation & Tradeoff Analysis</h3>
        <p class="text-subtle">Surface explicit tradeoffs between competing goals (e.g. speed vs quality, cost vs security) without psychological profiling.</p>
        
        <div class="tradeoff-form-card">
          <div class="form-row">
            <input type="text" id="tradeoff-goal-a" class="input-text" placeholder="Goal A (e.g. Fast In-Memory Processing)">
            <input type="text" id="tradeoff-goal-b" class="input-text" placeholder="Goal B (e.g. Durable Disk Persistence)">
          </div>
          <div class="form-row">
            <input type="number" id="tradeoff-cost-a" class="input-text" placeholder="Cost A" value="10">
            <input type="number" id="tradeoff-cost-b" class="input-text" placeholder="Cost B" value="50">
          </div>
          <button class="btn btn-primary" id="analyze-tradeoff-btn">Evaluate Tradeoff</button>
        </div>

        <div id="tradeoff-results-box" class="results-box hidden"></div>
      </div>
    `;
  }

  bindEvents() {
    // Tab switching
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.activeTab = e.currentTarget.dataset.tab;
        this.container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const pane = this.container.querySelector('#intent-tab-panes');
        if (pane) pane.innerHTML = this.renderActiveTab();
        this.bindTabEvents();
      });
    });

    // Refresh button
    const refreshBtn = this.container.querySelector('#refresh-intent-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    // Modal Parse button
    const parseModalBtn = this.container.querySelector('#parse-intent-modal-btn');
    if (parseModalBtn) {
      parseModalBtn.addEventListener('click', () => this.promptParseModal());
    }

    this.bindTabEvents();
  }

  bindTabEvents() {
    // Clarification option selection
    this.container.querySelectorAll('.answer-opt-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const cid = e.currentTarget.dataset.cid;
        const val = e.currentTarget.dataset.val;
        await this.submitClarification(cid, val);
      });
    });

    // Clarification text submission
    this.container.querySelectorAll('.submit-answer-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const cid = e.currentTarget.dataset.cid;
        const input = this.container.querySelector(`#answer-input-${cid}`);
        if (input && input.value.trim()) {
          await this.submitClarification(cid, input.value.trim());
        }
      });
    });

    // Correct button ("That's not what I meant")
    this.container.querySelectorAll('.correct-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const intentId = e.currentTarget.dataset.id;
        const correction = prompt("What did you mean? (Non-defensive correction):");
        if (correction && correction.trim()) {
          await this.submitCorrection(intentId, correction.trim());
        }
      });
    });

    // Revoke button
    this.container.querySelectorAll('.revoke-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const intentId = e.currentTarget.dataset.id;
        const reason = prompt("Reason for revoking this intent (optional):");
        await this.revokeIntent(intentId, reason);
      });
    });

    // Tradeoff analysis
    const analyzeBtn = this.container.querySelector('#analyze-tradeoff-btn');
    if (analyzeBtn) {
      analyzeBtn.addEventListener('click', async () => {
        const ga = this.container.querySelector('#tradeoff-goal-a')?.value || 'Goal A';
        const gb = this.container.querySelector('#tradeoff-goal-b')?.value || 'Goal B';
        const ca = parseFloat(this.container.querySelector('#tradeoff-cost-a')?.value || '10');
        const cb = parseFloat(this.container.querySelector('#tradeoff-cost-b')?.value || '50');
        await this.runTradeoffAnalysis(ga, gb, ca, cb);
      });
    }
  }

  async loadData() {
    try {
      const [intentsRes, goalsRes, healthRes] = await Promise.all([
        Endpoints.listIntents().catch(() => []),
        Endpoints.listGoals().catch(() => []),
        Endpoints.getIntentHealth().catch(() => null),
      ]);

      this.intents = Array.isArray(intentsRes) ? intentsRes : [];
      this.goals = Array.isArray(goalsRes) ? goalsRes : [];
      this.health = healthRes;

      // Filter pending clarifications
      this.clarifications = this.intents
        .filter(i => i.clarification_request && i.status === 'NEEDS_CLARIFICATION')
        .map(i => i.clarification_request);

      const pane = this.container.querySelector('#intent-tab-panes');
      if (pane) pane.innerHTML = this.renderActiveTab();

      // Update KPIs
      const kpiIntents = this.container.querySelector('#kpi-intents-total');
      if (kpiIntents) kpiIntents.textContent = this.intents.length;
      const kpiGoals = this.container.querySelector('#kpi-goals-active');
      if (kpiGoals) kpiGoals.textContent = this.goals.length;
      const kpiClarifications = this.container.querySelector('#kpi-pending-clarifications');
      if (kpiClarifications) kpiClarifications.textContent = this.clarifications.length;
      const kpiCalib = this.container.querySelector('#kpi-calibration-ratio');
      if (kpiCalib && this.health) kpiCalib.textContent = this.health.calibration_ratio;

      this.bindTabEvents();
    } catch (err) {
      console.error("Failed to load intent engine data:", err);
    }
  }

  async promptParseModal() {
    const text = prompt("Enter natural-language instruction or goal:");
    if (!text || !text.trim()) return;

    try {
      const result = await Endpoints.parseIntent({
        raw_text: text.trim(),
        environment: 'DEVELOPMENT',
      });
      alert(`Intent Understood: [${result.intent_type}] Status: ${result.status}`);
      await this.loadData();
    } catch (err) {
      alert(`Failed to parse intent: ${err.message || err}`);
    }
  }

  async submitClarification(clarificationId, answer) {
    try {
      await Endpoints.answerClarification({
        clarification_id: clarificationId,
        answer: answer,
      });
      alert("Clarification submitted. Intent confirmed!");
      await this.loadData();
    } catch (err) {
      alert(`Failed to answer clarification: ${err.message || err}`);
    }
  }

  async submitCorrection(intentId, correctionText) {
    try {
      await Endpoints.applyUserCorrection({
        session_id: 'default_session',
        intent_id: intentId,
        correction_text: correctionText,
      });
      alert("Correction accepted non-defensively. Revised intent recorded!");
      await this.loadData();
    } catch (err) {
      alert(`Failed to apply correction: ${err.message || err}`);
    }
  }

  async revokeIntent(intentId, reason) {
    try {
      await Endpoints.revokeIntent({
        intent_id: intentId,
        reason: reason || 'User requested cancellation',
      });
      alert("Intent and planned goals revoked.");
      await this.loadData();
    } catch (err) {
      alert(`Failed to revoke intent: ${err.message || err}`);
    }
  }

  async runTradeoffAnalysis(goalA, goalB, costA, costB) {
    try {
      const result = await Endpoints.analyzeTradeoffs({
        goal_a: goalA,
        goal_b: goalB,
        cost_a: costA,
        cost_b: costB,
      });
      const box = this.container.querySelector('#tradeoff-results-box');
      if (box) {
        box.classList.remove('hidden');
        box.innerHTML = `
          <h4>Tradeoff Assessment</h4>
          <p><strong>Recommendation:</strong> ${result.recommendation}</p>
          <p><strong>Preferred Goal:</strong> <code>${result.preferred_goal}</code></p>
          <p><strong>Cost Difference:</strong> ${result.cost_difference}</p>
          <p><strong>Benefit Difference:</strong> ${result.benefit_difference}</p>
        `;
      }
    } catch (err) {
      alert(`Tradeoff evaluation error: ${err.message || err}`);
    }
  }
}

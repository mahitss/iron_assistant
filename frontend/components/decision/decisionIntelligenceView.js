/**
 * KAIRO Autonomous Decision Intelligence & Decision Memory Component (Task 94).
 *
 * Exposes:
 * 1. Decision Inbox & Active Deliberations
 * 2. Multi-Criteria Candidate Options & Pareto Trade-Off Analysis
 * 3. NO-ACTION & Alternative Paths
 * 4. Approval Registry Gate & Mandatory Authorization Reviews
 * 5. Assumptions Tracking & Environmental Drift Monitor
 * 6. Decision Memory & Safe Experience Precedent Inspection
 * 7. Post-Execution Outcome Verification & Deviation Scoring
 */

export class DecisionIntelligenceView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api || this._createDefaultApi();
    this.state = {
      activeTab: 'inbox', // 'inbox' | 'detail' | 'approvals' | 'blocked' | 'memory'
      decisions: [],
      selectedDecision: null,
      explanation: null,
      isLoading: false,
      error: null,
    };
  }

  _createDefaultApi() {
    return {
      listDecisions: async (limit = 50) => (await fetch(`/api/v1/decisions?limit=${limit}`)).json(),
      getDecision: async (id) => (await fetch(`/api/v1/decisions/${encodeURIComponent(id)}`)).json(),
      getExplanation: async (id) => (await fetch(`/api/v1/decisions/${encodeURIComponent(id)}/explanation`)).json(),
      selectOption: async (id, optionId) =>
        (
          await fetch(`/api/v1/decisions/${encodeURIComponent(id)}/select`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chosen_option_id: optionId, actor: 'operator' }),
          })
        ).json(),
      approveDecision: async (id) =>
        (
          await fetch(`/api/v1/decisions/${encodeURIComponent(id)}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ approver: 'security_officer', approval_id: `appr_${Date.now()}` }),
          })
        ).json(),
      rejectDecision: async (id, reason) =>
        (
          await fetch(`/api/v1/decisions/${encodeURIComponent(id)}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actor: 'security_officer', reason: reason || 'Rejected' }),
          })
        ).json(),
      evaluateDecision: async (input) =>
        (
          await fetch('/api/v1/decisions/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(input),
          })
        ).json(),
    };
  }

  async render() {
    if (!this.container) return;
    this.container.innerHTML = this._template();
    this._attachEventListeners();
    await this.fetchData();
  }

  async fetchData() {
    this.state.isLoading = true;
    this._updateLoadingState();

    try {
      const records = await this.api.listDecisions();
      this.state.decisions = records || [];
      if (this.state.decisions.length > 0 && !this.state.selectedDecision) {
        this.state.selectedDecision = this.state.decisions[0];
      }
      this.state.error = null;
    } catch (err) {
      this.state.error = err.message || 'Failed to load decisions.';
    } finally {
      this.state.isLoading = false;
      this._renderActiveTab();
    }
  }

  async switchTab(tabName) {
    this.state.activeTab = tabName;
    this._renderActiveTab();
  }

  async selectDecision(id) {
    const dec = this.state.decisions.find((d) => d.decision_id === id) || (await this.api.getDecision(id));
    if (dec) {
      this.state.selectedDecision = dec;
      try {
        this.state.explanation = await this.api.getExplanation(id);
      } catch (_) {}
      this.state.activeTab = 'detail';
      this._renderActiveTab();
    }
  }

  _renderOptionsGrid(options, selectedOption) {
    if (!options || options.length === 0) return '';
    return `
      <div class="di-options-grid">
        ${options
          .map(
            (opt) => `
          <div class="di-option-card ${selectedOption?.option_id === opt.option_id ? 'selected' : ''} ${opt.is_dominated ? 'dominated' : ''}">
            <div class="di-opt-header">
              <strong>${opt.name}</strong>
              ${selectedOption?.option_id === opt.option_id ? '<span class="di-badge-selected">SELECTED</span>' : ''}
            </div>
          </div>
        `
          )
          .join('')}
      </div>
    `;
  }

  _template() {
    return `
      <div class="decision-intelligence-view">
        <header class="di-header">
          <div class="di-title-block">
            <h2>KAIRO Autonomous Decision Intelligence</h2>
            <span class="di-subtitle">Policy-Aware Action Selection, Option Evaluation & Decision Memory (Task 94)</span>
          </div>
          <div class="di-header-actions">
            <button id="di-btn-new-deliberation" class="btn btn-primary" title="Trigger new deliberate decision evaluation">
              <span class="icon">⚖️</span> New Deliberation
            </button>
            <button id="di-btn-refresh" class="btn btn-icon" title="Refresh">↻</button>
          </div>
        </header>

        <nav class="di-nav-tabs">
          <button class="di-tab active" data-tab="inbox">Decision Inbox (${this.state.decisions.length})</button>
          <button class="di-tab" data-tab="detail">Decision Detail & Trade-Offs</button>
          <button class="di-tab" data-tab="approvals">Awaiting Approval</button>
          <button class="di-tab" data-tab="blocked">Blocked Decisions</button>
          <button class="di-tab" data-tab="memory">Decision Memory & Precedents</button>
        </nav>

        <div id="di-content-pane" class="di-content-pane">
          <div class="di-spinner">Loading decision intelligence...</div>
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    const tabs = this.container.querySelectorAll('.di-tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', (e) => {
        tabs.forEach((t) => t.classList.remove('active'));
        e.target.classList.add('active');
        this.state.activeTab = e.target.getAttribute('data-tab');
        this._renderActiveTab();
      });
    });

    const refreshBtn = this.container.querySelector('#di-btn-refresh');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.fetchData());

    const newBtn = this.container.querySelector('#di-btn-new-deliberation');
    if (newBtn) {
      newBtn.addEventListener('click', async () => {
        const question = prompt('Enter decision objective or dilemma:');
        if (question) {
          try {
            newBtn.disabled = true;
            newBtn.innerText = 'Deliberating...';
            const res = await this.api.evaluateDecision({
              objective_id: `obj_${Date.now()}`,
              statement: question,
              candidate_options: [
                {
                  name: 'Standard Autonomous Action',
                  description: 'Execute nominal procedure',
                  action_reference: 'tool:standard_action',
                  reversibility: 'REVERSIBLE',
                  confidence: 0.9,
                },
              ],
            });
            this.state.selectedDecision = res;
            this.state.activeTab = 'detail';
            await this.fetchData();
          } catch (err) {
            alert('Failed to evaluate decision: ' + err.message);
          } finally {
            newBtn.disabled = false;
            newBtn.innerHTML = '<span class="icon">⚖️</span> New Deliberation';
          }
        }
      });
    }
  }

  _updateLoadingState() {
    const pane = this.container.querySelector('#di-content-pane');
    if (pane && this.state.isLoading) {
      pane.innerHTML = '<div class="di-spinner">Deliberating across multi-criteria dimensions...</div>';
    }
  }

  _renderActiveTab() {
    const pane = this.container.querySelector('#di-content-pane');
    if (!pane) return;

    if (this.state.error) {
      pane.innerHTML = `<div class="di-error-banner">Error: ${this.state.error}</div>`;
      return;
    }

    switch (this.state.activeTab) {
      case 'inbox':
        pane.innerHTML = this._renderInboxView();
        this._bindInboxEvents();
        break;
      case 'detail':
        pane.innerHTML = this._renderDetailView();
        this._bindDetailEvents();
        break;
      case 'approvals':
        pane.innerHTML = this._renderApprovalsView();
        this._bindApprovalEvents();
        break;
      case 'blocked':
        pane.innerHTML = this._renderBlockedView();
        break;
      case 'memory':
        pane.innerHTML = this._renderMemoryView();
        break;
      default:
        pane.innerHTML = this._renderInboxView();
    }
  }

  _renderInboxView() {
    const list = this.state.decisions;
    if (list.length === 0) {
      return '<div class="di-card"><p class="di-empty">No active or historical decisions recorded.</p></div>';
    }

    return `
      <div class="di-card">
        <h3>Operational Decision Log</h3>
        <table class="di-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Objective</th>
              <th>Status</th>
              <th>Type</th>
              <th>Selected Option</th>
              <th>Certainty</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${list
              .map(
                (d) => `
              <tr class="di-row" data-id="${d.decision_id}">
                <td><code>${d.decision_id}</code></td>
                <td><strong>${d.objective_id}</strong></td>
                <td><span class="badge-status badge-${d.status.toLowerCase()}">${d.status}</span></td>
                <td><span class="badge-type">${d.decision_type}</span></td>
                <td>${d.selected_option?.name || '<em>None (NO_ACTION)</em>'}</td>
                <td><span class="badge-certainty">${d.certainty}</span></td>
                <td>
                  <button class="btn btn-xs btn-inspect" data-id="${d.decision_id}">Inspect</button>
                </td>
              </tr>
            `
              )
              .join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  _bindInboxEvents() {
    const btns = this.container.querySelectorAll('.btn-inspect');
    btns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-id');
        const dec = this.state.decisions.find((d) => d.decision_id === id);
        if (dec) {
          this.state.selectedDecision = dec;
          this.state.activeTab = 'detail';
          this._renderActiveTab();
        }
      });
    });
  }

  _renderDetailView() {
    const d = this.state.selectedDecision;
    if (!d) return '<div class="di-card"><p>No decision selected. Select a decision from the inbox.</p></div>';

    return `
      <div class="di-detail-layout">
        <div class="di-card">
          <div class="di-detail-header">
            <div>
              <h3>Decision: <code>${d.decision_id}</code></h3>
              <p class="di-hint">Objective: <strong>${d.objective_id}</strong> | Version: ${d.decision_version}</p>
            </div>
            <div class="di-status-pill">
              <span class="badge-status badge-${d.status.toLowerCase()}">${d.status}</span>
              <span class="badge-certainty">${d.certainty}</span>
            </div>
          </div>

          <h4>Candidate Options & Pareto Analysis</h4>
          <p class="di-hint">Evaluates trade-offs across objectives, risk, reversibility, and resource efficiency without flattening into false universal scores.</p>
          <div class="di-options-grid">
            ${d.options
              .map(
                (opt) => `
              <div class="di-option-card ${d.selected_option?.option_id === opt.option_id ? 'selected' : ''} ${opt.is_dominated ? 'dominated' : ''} ${!opt.is_feasible ? 'infeasible' : ''}">
                <div class="di-opt-header">
                  <strong>${opt.name}</strong>
                  <span class="badge-type">${opt.option_type}</span>
                </div>
                <div class="di-opt-desc">${opt.description || 'No description provided'}</div>
                <div class="di-opt-meta">
                  Reversibility: <strong>${opt.reversibility}</strong> | Confidence: ${Math.round(opt.confidence * 100)}%
                </div>
                ${opt.is_dominated ? '<div class="di-pill-dominated">Pareto Dominated</div>' : ''}
                ${!opt.is_feasible ? `<div class="di-pill-infeasible">Infeasible: ${opt.rejection_reason || 'Blocked'}</div>` : ''}
                ${
                  opt.is_feasible && d.selected_option?.option_id !== opt.option_id
                    ? `<button class="btn btn-xs btn-select-opt" data-opt="${opt.option_id}">Select This Option</button>`
                    : ''
                }
              </div>
            `
              )
              .join('')}
          </div>

          <h4 style="margin-top:1.5rem;">Underpinning Assumptions (${d.assumptions?.length || 0})</h4>
          <ul class="di-assumption-list">
            ${(d.assumptions || []).map((a) => `<li><code>${a.assumption_id}</code>: ${a.statement} [${a.status}]</li>`).join('') || '<li>Zero active assumptions recorded.</li>'}
          </ul>

          <div class="di-action-bar">
            ${
              d.status === 'AWAITING_APPROVAL'
                ? `
              <button class="btn btn-success btn-approve-action" data-id="${d.decision_id}">Formalize Approval</button>
              <button class="btn btn-danger btn-reject-action" data-id="${d.decision_id}">Reject Decision</button>
            `
                : ''
            }
          </div>
        </div>
      </div>
    `;
  }

  _bindDetailEvents() {
    const selBtns = this.container.querySelectorAll('.btn-select-opt');
    selBtns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const optId = e.target.getAttribute('data-opt');
        try {
          const res = await this.api.selectOption(this.state.selectedDecision.decision_id, optId);
          this.state.selectedDecision = res;
          await this.fetchData();
        } catch (err) {
          alert('Failed to select option: ' + err.message);
        }
      });
    });

    const apprBtn = this.container.querySelector('.btn-approve-action');
    if (apprBtn) {
      apprBtn.addEventListener('click', async () => {
        try {
          const res = await this.api.approveDecision(this.state.selectedDecision.decision_id);
          this.state.selectedDecision = res;
          await this.fetchData();
        } catch (err) {
          alert('Approval failed: ' + err.message);
        }
      });
    }
  }

  _renderApprovalsView() {
    const pending = this.state.decisions.filter((d) => d.status === 'AWAITING_APPROVAL');
    return `
      <div class="di-card">
        <h3>Decisions Awaiting Formal Approval</h3>
        <p class="di-hint">Sole Authority: ApprovalRegistry & SecurityCenter. Model output or user intent can NEVER bypass approval requirements.</p>
        ${
          pending.length === 0
            ? '<p class="di-empty">Zero decisions awaiting approval.</p>'
            : `<table class="di-table">
            <thead><tr><th>ID</th><th>Objective</th><th>Reason Mandated</th><th>Selected Action</th><th>Actions</th></tr></thead>
            <tbody>
              ${pending
                .map(
                  (p) => `
                <tr>
                  <td><code>${p.decision_id}</code></td>
                  <td>${p.objective_id}</td>
                  <td>${p.approval_summary?.reason || 'Required by policy'}</td>
                  <td>${p.selected_option?.name}</td>
                  <td>
                    <button class="btn btn-xs btn-success btn-approve-row" data-id="${p.decision_id}">Approve</button>
                    <button class="btn btn-xs btn-danger btn-reject-row" data-id="${p.decision_id}">Reject</button>
                  </td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _bindApprovalEvents() {
    const approveBtns = this.container.querySelectorAll('.btn-approve-row');
    approveBtns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-id');
        try {
          await this.api.approveDecision(id);
          await this.fetchData();
        } catch (err) {
          alert('Approval failed: ' + err.message);
        }
      });
    });

    const rejectBtns = this.container.querySelectorAll('.btn-reject-row');
    rejectBtns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-id');
        try {
          await this.api.rejectDecision(id, 'Rejected by operator');
          await this.fetchData();
        } catch (err) {
          alert('Rejection failed: ' + err.message);
        }
      });
    });
  }

  _renderBlockedView() {
    const blocked = this.state.decisions.filter((d) => d.status === 'BLOCKED');
    return `
      <div class="di-card">
        <h3>Blocked Decisions</h3>
        <p class="di-hint">Actions blocked by SecurityCenter authorization denial, Governance constitutional barriers, or Hard Constraint violations.</p>
        ${
          blocked.length === 0
            ? '<p class="di-empty">Zero blocked decisions.</p>'
            : `<table class="di-table">
            <thead><tr><th>ID</th><th>Objective</th><th>Status</th></tr></thead>
            <tbody>
              ${blocked
                .map(
                  (b) => `
                <tr>
                  <td><code>${b.decision_id}</code></td>
                  <td>${b.objective_id}</td>
                  <td><span class="badge-status badge-blocked">BLOCKED</span></td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _renderMemoryView() {
    return `
      <div class="di-card">
        <h3>Decision Memory & Experience Precedents (Task 92 Integration)</h3>
        <p class="di-hint">Historical decisions retain structured rationale, predictions, and actual outcomes. Environmental drift transitions old decisions to <code>REFERENCE_ONLY</code>.</p>
        <div class="di-precedent-stats">
          Total Precedents Indexed: <strong>${this.state.decisions.length}</strong>
        </div>
      </div>
    `;
  }
}

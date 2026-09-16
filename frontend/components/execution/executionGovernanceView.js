/**
 * KAIRO Autonomous Execution Governance & Action Transaction Console (Task 95).
 *
 * Exposes:
 * 1. Execution Inbox (all active/historical transactions)
 * 2. 18-Gate Pre-Flight Validation Inspector
 * 3. Approval Registry Gate & Authorization Controls
 * 4. Real-time Observations & Post-Condition Verifier
 * 5. Rollback Compensation & Saga Orchestration
 * 6. Crash State Reconciliation & Unknown Outcome Resolver
 */

export class ExecutionGovernanceView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api || this._createDefaultApi();
    this.state = {
      activeTab: 'inbox', // 'inbox' | 'preflight' | 'approvals' | 'running' | 'recovery' | 'history'
      transactions: [],
      selectedTransaction: null,
      isLoading: false,
      error: null,
    };
  }

  _createDefaultApi() {
    return {
      listTransactions: async (limit = 50) => (await fetch(`/api/v1/actions?limit=${limit}`)).json(),
      getTransaction: async (id) => (await fetch(`/api/v1/actions/${encodeURIComponent(id)}`)).json(),
      getPreflight: async (id) => (await fetch(`/api/v1/actions/${encodeURIComponent(id)}/preflight`)).json(),
      getObservations: async (id) => (await fetch(`/api/v1/actions/${encodeURIComponent(id)}/observations`)).json(),
      getVerification: async (id) => (await fetch(`/api/v1/actions/${encodeURIComponent(id)}/verification`)).json(),
      getOutcome: async (id) => (await fetch(`/api/v1/actions/${encodeURIComponent(id)}/outcome`)).json(),
      runPreflight: async (id) =>
        (await fetch(`/api/v1/actions/${encodeURIComponent(id)}/preflight`, { method: 'POST' })).json(),
      executeAction: async (id, approvalId = null) =>
        (
          await fetch(`/api/v1/actions/${encodeURIComponent(id)}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ approval_id: approvalId }),
          })
        ).json(),
      cancelAction: async (id, reason = 'Operator cancelled') =>
        (
          await fetch(`/api/v1/actions/${encodeURIComponent(id)}/cancel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason }),
          })
        ).json(),
      rollbackAction: async (id, reason = 'Operator rollback') =>
        (
          await fetch(`/api/v1/actions/${encodeURIComponent(id)}/rollback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason }),
          })
        ).json(),
      reconcileAction: async (id) =>
        (await fetch(`/api/v1/actions/${encodeURIComponent(id)}/reconcile`, { method: 'POST' })).json(),
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
      const records = await this.api.listTransactions();
      this.state.transactions = records || [];
      if (this.state.transactions.length > 0 && !this.state.selectedTransaction) {
        this.state.selectedTransaction = this.state.transactions[0];
      }
      this.state.error = null;
    } catch (err) {
      this.state.error = err.message || 'Failed to load action transactions.';
    } finally {
      this.state.isLoading = false;
      this._renderActiveTab();
    }
  }

  async switchTab(tabName) {
    this.state.activeTab = tabName;
    this._renderActiveTab();
  }

  async selectTransaction(id) {
    const txn = this.state.transactions.find((t) => t.transaction_id === id) || (await this.api.getTransaction(id));
    if (txn) {
      this.state.selectedTransaction = txn;
      this._renderActiveTab();
    }
  }

  _template() {
    return `
      <div class="execution-governance-view">
        <header class="eg-header">
          <div class="eg-title-block">
            <h2>⚡ KAIRO Autonomous Execution Governance</h2>
            <span class="eg-subtitle">Action Transactions, Pre-Flight Validation, Commit/Rollback & Verified Outcomes (Task 95)</span>
          </div>
          <div class="eg-header-actions">
            <button id="eg-btn-refresh" class="btn btn-icon" title="Refresh">↻</button>
          </div>
        </header>

        <nav class="eg-nav-tabs">
          <button class="eg-tab active" data-tab="inbox">Execution Inbox (${this.state.transactions.length})</button>
          <button class="eg-tab" data-tab="preflight">Pre-Flight Gates (18)</button>
          <button class="eg-tab" data-tab="approvals">Awaiting Approval</button>
          <button class="eg-tab" data-tab="running">Running & Observation</button>
          <button class="eg-tab" data-tab="recovery">Rollback & Unknown Recovery</button>
          <button class="eg-tab" data-tab="history">Verified Outcomes</button>
        </nav>

        <div id="eg-content-pane" class="eg-content-pane">
          <div class="eg-spinner">Loading execution governance telemetry...</div>
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    const tabs = this.container.querySelectorAll('.eg-tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', (e) => {
        tabs.forEach((t) => t.classList.remove('active'));
        e.target.classList.add('active');
        this.state.activeTab = e.target.getAttribute('data-tab');
        this._renderActiveTab();
      });
    });

    const refreshBtn = this.container.querySelector('#eg-btn-refresh');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.fetchData());
  }

  _updateLoadingState() {
    const pane = this.container.querySelector('#eg-content-pane');
    if (pane && this.state.isLoading) {
      pane.innerHTML = '<div class="eg-spinner">Processing action transaction telemetry...</div>';
    }
  }

  _renderActiveTab() {
    const pane = this.container.querySelector('#eg-content-pane');
    if (!pane) return;

    if (this.state.error) {
      pane.innerHTML = `<div class="eg-error-banner">Error: ${this.state.error}</div>`;
      return;
    }

    switch (this.state.activeTab) {
      case 'inbox':
        pane.innerHTML = this._renderInboxView();
        this._bindInboxEvents();
        break;
      case 'preflight':
        pane.innerHTML = this._renderPreflightView();
        break;
      case 'approvals':
        pane.innerHTML = this._renderApprovalsView();
        this._bindApprovalEvents();
        break;
      case 'running':
        pane.innerHTML = this._renderRunningView();
        break;
      case 'recovery':
        pane.innerHTML = this._renderRecoveryView();
        this._bindRecoveryEvents();
        break;
      case 'history':
        pane.innerHTML = this._renderHistoryView();
        break;
      default:
        pane.innerHTML = this._renderInboxView();
    }
  }

  _renderInboxView() {
    const list = this.state.transactions;
    if (list.length === 0) {
      return '<div class="eg-card"><p class="eg-empty">No active or historical action transactions recorded.</p></div>';
    }

    return `
      <div class="eg-card">
        <h3>Action Transaction Registry</h3>
        <table class="eg-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Decision ID</th>
              <th>Status</th>
              <th>Capability</th>
              <th>Target</th>
              <th>Verification</th>
              <th>Outcome</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${list
              .map(
                (t) => `
              <tr class="eg-row" data-id="${t.transaction_id}">
                <td><code>${t.transaction_id}</code></td>
                <td><strong>${t.decision_id}</strong></td>
                <td><span class="badge-status badge-${t.status.toLowerCase()}">${t.status}</span></td>
                <td><span class="badge-cap">${t.capability_id} (${t.capability_version})</span></td>
                <td><code>${t.target?.target_id || 'unbound'}</code></td>
                <td><span class="badge-ver">${t.verification_state}</span></td>
                <td><span class="badge-outcome">${t.outcome_type || 'PENDING'}</span></td>
                <td>
                  <button class="btn btn-xs btn-inspect-txn" data-id="${t.transaction_id}">Inspect</button>
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
    const btns = this.container.querySelectorAll('.btn-inspect-txn');
    btns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-id');
        await this.selectTransaction(id);
      });
    });
  }

  _renderPreflightView() {
    const t = this.state.selectedTransaction;
    if (!t) return '<div class="eg-card"><p>Select a transaction from the inbox to inspect pre-flight gates.</p></div>';

    const checks = t.preflight_checks || [];
    return `
      <div class="eg-card">
        <h3>18-Gate Pre-Flight Validation: <code>${t.transaction_id}</code></h3>
        <p class="eg-hint">All 18 mandatory gates must pass before low-level execution dispatch. Status: <strong>${t.status}</strong></p>
        <div class="eg-gates-grid">
          ${checks.length === 0 ? '<p>Pre-flight check not yet executed.</p>' : ''}
          ${checks
            .map(
              (c) => `
            <div class="eg-gate-card ${c.passed ? 'passed' : 'failed'}">
              <div class="eg-gate-header">
                <strong>${c.gate_name}</strong>
                <span class="eg-pill ${c.passed ? 'eg-pill-success' : 'eg-pill-danger'}">${c.passed ? 'PASSED' : 'BLOCKED'}</span>
              </div>
              <p class="eg-gate-reason">${c.reason}</p>
              <span class="eg-gate-latency">${c.latency_ms}ms</span>
            </div>
          `
            )
            .join('')}
        </div>
      </div>
    `;
  }

  _renderApprovalsView() {
    const pending = this.state.transactions.filter((t) => t.status === 'AWAITING_APPROVAL');
    return `
      <div class="eg-card">
        <h3>Awaiting Human Authorization (${pending.length})</h3>
        <p class="eg-hint">High-risk, irreversible, or destructive actions suspended pending explicit approval.</p>
        ${
          pending.length === 0
            ? '<p class="eg-empty">Zero transactions awaiting approval.</p>'
            : `
          <table class="eg-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Capability</th>
                <th>Target</th>
                <th>Action</th>
                <th>Authorization Control</th>
              </tr>
            </thead>
            <tbody>
              ${pending
                .map(
                  (t) => `
                <tr>
                  <td><code>${t.transaction_id}</code></td>
                  <td>${t.capability_id}</td>
                  <td>${t.target?.target_id}</td>
                  <td>${t.action_reference}</td>
                  <td>
                    <button class="btn btn-xs btn-primary btn-approve-txn" data-id="${t.transaction_id}">Approve & Execute</button>
                    <button class="btn btn-xs btn-danger btn-cancel-txn" data-id="${t.transaction_id}">Cancel</button>
                  </td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>
        `
        }
      </div>
    `;
  }

  _bindApprovalEvents() {
    const approveBtns = this.container.querySelectorAll('.btn-approve-txn');
    approveBtns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-id');
        try {
          await this.api.executeAction(id, `appr_${Date.now()}`);
          await this.fetchData();
        } catch (err) {
          alert('Approval execution failed: ' + err.message);
        }
      });
    });

    const cancelBtns = this.container.querySelectorAll('.btn-cancel-txn');
    cancelBtns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-id');
        try {
          await this.api.cancelAction(id, 'User rejected approval');
          await this.fetchData();
        } catch (err) {
          alert('Cancellation failed: ' + err.message);
        }
      });
    });
  }

  _renderRunningView() {
    const t = this.state.selectedTransaction;
    if (!t) return '<div class="eg-card"><p>Select a transaction to inspect running observations.</p></div>';

    const obs = t.observations || [];
    return `
      <div class="eg-card">
        <h3>Execution Observations & Post-Condition Probes: <code>${t.transaction_id}</code></h3>
        <p class="eg-hint">Status: <strong>${t.status}</strong> | Verification: <strong>${t.verification_state}</strong></p>

        <h4>Empirical Observations</h4>
        ${obs.length === 0 ? '<p>No observations recorded yet.</p>' : ''}
        ${obs
          .map(
            (o) => `
          <div class="eg-obs-box">
            <strong>Source: ${o.source}</strong> (Exit Code: ${o.exit_code})
            <pre class="eg-code-snippet">${o.raw_snippet || '(Empty snippet)'}</pre>
          </div>
        `
          )
          .join('')}
      </div>
    `;
  }

  _renderRecoveryView() {
    const recoveryItems = this.state.transactions.filter((t) =>
      ['FAILED', 'UNKNOWN', 'ROLLING_BACK', 'ROLLED_BACK', 'RECOVERING', 'RECOVERED'].includes(t.status)
    );

    return `
      <div class="eg-card">
        <h3>Rollback Compensation & Unknown Outcome Recovery</h3>
        <p class="eg-hint">Strict separation: UNKNOWN ≠ FAILED ≠ SUCCESS. Reconcile or execute compensation where defined.</p>
        ${
          recoveryItems.length === 0
            ? '<p class="eg-empty">No transactions currently in failure or recovery state.</p>'
            : `
          <table class="eg-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Status</th>
                <th>Target</th>
                <th>Compensation</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${recoveryItems
                .map(
                  (t) => `
                <tr>
                  <td><code>${t.transaction_id}</code></td>
                  <td><span class="badge-status badge-${t.status.toLowerCase()}">${t.status}</span></td>
                  <td>${t.target?.target_id}</td>
                  <td>${t.compensation_action || 'None'}</td>
                  <td>
                    ${
                      t.status === 'UNKNOWN'
                        ? `<button class="btn btn-xs btn-primary btn-reconcile-txn" data-id="${t.transaction_id}">Reconcile State</button>`
                        : ''
                    }
                    ${
                      t.status === 'FAILED' && t.compensation_action
                        ? `<button class="btn btn-xs btn-warning btn-rollback-txn" data-id="${t.transaction_id}">Rollback</button>`
                        : ''
                    }
                  </td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>
        `
        }
      </div>
    `;
  }

  _bindRecoveryEvents() {
    const reconcileBtns = this.container.querySelectorAll('.btn-reconcile-txn');
    reconcileBtns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-id');
        try {
          await this.api.reconcileAction(id);
          await this.fetchData();
        } catch (err) {
          alert('Reconciliation failed: ' + err.message);
        }
      });
    });

    const rollbackBtns = this.container.querySelectorAll('.btn-rollback-txn');
    rollbackBtns.forEach((b) => {
      b.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-id');
        try {
          await this.api.rollbackAction(id);
          await this.fetchData();
        } catch (err) {
          alert('Rollback failed: ' + err.message);
        }
      });
    });
  }

  _renderHistoryView() {
    const completed = this.state.transactions.filter((t) =>
      ['SUCCEEDED', 'FAILED', 'ROLLED_BACK', 'RECOVERED'].includes(t.status)
    );

    return `
      <div class="eg-card">
        <h3>Verified Outcomes History</h3>
        <p class="eg-hint">Outcomes verified empirically against target reality. SUCCESSFUL OUTCOME ≠ VERIFIED OUTCOME.</p>
        <table class="eg-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Outcome Type</th>
              <th>Deviation Score</th>
              <th>Regret Score</th>
              <th>Completed At</th>
            </tr>
          </thead>
          <tbody>
            ${completed
              .map(
                (t) => `
              <tr>
                <td><code>${t.transaction_id}</code></td>
                <td><span class="badge-status badge-${t.status.toLowerCase()}">${t.status}</span></td>
                <td><strong>${t.outcome_type || 'N/A'}</strong></td>
                <td><code>${t.deviation_score}</code></td>
                <td><code>${t.regret_score}</code></td>
                <td>${t.completed_at || t.updated_at}</td>
              </tr>
            `
              )
              .join('')}
          </tbody>
        </table>
      </div>
    `;
  }
}

/**
 * Autonomous Intent Understanding, Goal Inference & Request Semantics Console View (Task 108)
 * Comprehensive UI for Multi-Intent DAG Decomposition, Goal Hypotheses,
 * Explicit/Implicit Constraints, Non-Goals, Consequence-Aware Ambiguity Gating,
 * Provenance-Backed Evidence, and Immutable Epistemic Snapshots.
 */

import { intentApi } from '../../lib/api/endpoints.js';

export class IntentView {
  constructor(options = {}) {
    if (options && (options.nodeType || options.innerHTML !== undefined)) {
      this.container = options;
      this.activeTab = 'intents';
    } else {
      this.container = (options && options.container) || (typeof document !== 'undefined' ? document.getElementById('main-content-viewport') : null);
      this.activeTab = (options && options.activeTab) || 'intents';
    }
    this.dashboardData = null;
    this.requests = [];
    this.intents = [];
    this.clarifications = [];
    this.selectedIntentId = null;
    this.selectedIntent = null;
    this.selectedSnapshot = null;
    this.evidenceList = [];
    this.versions = [];
    this.corrections = [];
    this.loading = false;
    this.error = null;
    this.filterCategory = 'ALL';
    this.filterStatus = 'ALL';
  }

  async init() {
    this.renderContainer();
    await this.loadData();
  }

  async render() {
    this.renderContainer();
    this.renderCurrentTab();
  }

  renderContainer() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="intent-console" id="intent-console-root">
        <!-- Header -->
        <header class="console-header">
          <div class="header-left">
            <div class="header-badge">TASK 108</div>
            <h1 class="console-title">Autonomous Intent Understanding & Request Semantics</h1>
            <p class="console-sub">Transforms raw user input and environmental triggers into structured, uncertainty-aware intent representations.</p>
          </div>
          <div class="header-right">
            <div id="estop-indicator" class="estop-pill safe">
              <span class="pulse-dot"></span>
              <span id="estop-text">EmergencyStop Disengaged</span>
            </div>
            <button id="btn-refresh-intent" class="btn btn-secondary btn-sm">
              <span class="icon">↻</span> Refresh
            </button>
            <button id="btn-submit-request-modal" class="btn btn-primary btn-sm">
              <span class="icon">+</span> Submit Request
            </button>
          </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <section class="metrics-ribbon" id="intent-metrics-ribbon">
          <div class="metric-card">
            <div class="metric-label">Total Requests</div>
            <div class="metric-value" id="metric-total-requests">0</div>
            <div class="metric-trend text-muted">Direct user instructions</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Understood Intents</div>
            <div class="metric-value accent" id="metric-total-intents">0</div>
            <div class="metric-trend text-muted">Decomposed DAG nodes</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Pending Clarifications</div>
            <div class="metric-value warning" id="metric-pending-clarifications">0</div>
            <div class="metric-trend text-muted">Gated for high-consequence ambiguity</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Unresolved Ambiguities</div>
            <div class="metric-value" id="metric-unresolved-ambiguities">0</div>
            <div class="metric-trend text-muted">Tracked across 10 categories</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">External Effect Flagged</div>
            <div class="metric-value danger" id="metric-external-effect">0</div>
            <div class="metric-trend text-muted">External side-effects possible</div>
          </div>
        </section>

        <!-- Navigation Tabs -->
        <nav class="console-nav">
          <button class="nav-tab active" data-tab="dashboard">Dashboard</button>
          <button class="nav-tab" data-tab="requests">Requests (<span id="tab-cnt-requests">0</span>)</button>
          <button class="nav-tab" data-tab="intents">Intents (<span id="tab-cnt-intents">0</span>)</button>
          <button class="nav-tab" data-tab="clarifications">Clarification Queue (<span id="tab-cnt-clarifications">0</span>)</button>
          <button class="nav-tab" data-tab="ambiguities">Ambiguity Center</button>
          <button class="nav-tab" data-tab="corrections">Corrections & Lineage</button>
          <button class="nav-tab" data-tab="detail">Detail & Epistemic Snapshot</button>
        </nav>

        <!-- Dynamic Body Viewport -->
        <main class="console-body" id="intent-console-body">
          <div class="loading-spinner">Loading Intent Engine...</div>
        </main>
      </div>

      <!-- Submit Request Modal -->
      <div id="modal-submit-request" class="modal-backdrop hidden">
        <div class="modal-dialog">
          <div class="modal-header">
            <h3>Submit User Request</h3>
            <button class="btn-close" id="btn-close-request-modal">×</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Raw User Instruction / Request</label>
              <textarea id="input-request-raw" class="form-textarea" rows="4" placeholder="e.g. Analyze this repo, fix the bugs without changing the API, test, and prepare a PR."></textarea>
            </div>
            <div class="form-group">
              <label>Source Type</label>
              <select id="input-request-source" class="form-select">
                <option value="DIRECT_USER">DIRECT_USER (Direct human prompt)</option>
                <option value="VOICE">VOICE (Voice transcript)</option>
                <option value="API">API (Automated agent trigger)</option>
                <option value="UNTRUSTED_EXTERNAL">UNTRUSTED_EXTERNAL (Data payload - firewall protected)</option>
              </select>
            </div>
            <div class="form-group">
              <label>Execution Scope</label>
              <input id="input-request-scope" class="form-input" value="DEFAULT" />
            </div>
          </div>
          <div class="modal-footer">
            <button id="btn-cancel-request-modal" class="btn btn-secondary">Cancel</button>
            <button id="btn-confirm-submit-request" class="btn btn-primary">Parse & Understand</button>
          </div>
        </div>
      </div>

      <!-- Clarification Answer Modal -->
      <div id="modal-answer-clarification" class="modal-backdrop hidden">
        <div class="modal-dialog">
          <div class="modal-header">
            <h3>Answer Clarification Query</h3>
            <button class="btn-close" id="btn-close-clr-modal">×</button>
          </div>
          <div class="modal-body">
            <p id="clr-question-text" class="clarification-callout"></p>
            <p id="clr-rationale-text" class="text-muted small"></p>
            <div class="form-group">
              <label>Your Response</label>
              <input id="input-clarification-answer" class="form-input" placeholder="Enter clarification or select option..." />
            </div>
          </div>
          <div class="modal-footer">
            <button id="btn-cancel-clr-modal" class="btn btn-secondary">Cancel</button>
            <button id="btn-confirm-answer-clr" class="btn btn-primary">Submit Answer</button>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    const root = this.container;
    if (!root) return;

    // Tab buttons
    root.querySelectorAll('.nav-tab').forEach((tab) => {
      tab.addEventListener('click', (e) => {
        const target = e.currentTarget.dataset.tab;
        this.switchTab(target);
      });
    });

    // Refresh
    const refreshBtn = root.querySelector('#btn-refresh-intent');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    // Modals
    const openSubmitBtn = root.querySelector('#btn-submit-request-modal');
    const modalSubmit = root.querySelector('#modal-submit-request');
    const closeSubmitBtn = root.querySelector('#btn-close-request-modal');
    const cancelSubmitBtn = root.querySelector('#btn-cancel-request-modal');
    const confirmSubmitBtn = root.querySelector('#btn-confirm-submit-request');

    if (openSubmitBtn && modalSubmit) {
      openSubmitBtn.addEventListener('click', () => modalSubmit.classList.remove('hidden'));
    }
    if (closeSubmitBtn && modalSubmit) {
      closeSubmitBtn.addEventListener('click', () => modalSubmit.classList.add('hidden'));
    }
    if (cancelSubmitBtn && modalSubmit) {
      cancelSubmitBtn.addEventListener('click', () => modalSubmit.classList.add('hidden'));
    }
    if (confirmSubmitBtn) {
      confirmSubmitBtn.addEventListener('click', () => this.handleSubmitRequest());
    }

    // Clarification modal
    const modalClr = root.querySelector('#modal-answer-clarification');
    const closeClrBtn = root.querySelector('#btn-close-clr-modal');
    const cancelClrBtn = root.querySelector('#btn-cancel-clr-modal');
    const confirmClrBtn = root.querySelector('#btn-confirm-answer-clr');

    if (closeClrBtn && modalClr) {
      closeClrBtn.addEventListener('click', () => modalClr.classList.add('hidden'));
    }
    if (cancelClrBtn && modalClr) {
      cancelClrBtn.addEventListener('click', () => modalClr.classList.add('hidden'));
    }
    if (confirmClrBtn) {
      confirmClrBtn.addEventListener('click', () => this.handleAnswerClarification());
    }
  }

  async loadData() {
    this.loading = true;
    try {
      if (intentApi && typeof intentApi.getDashboard === 'function') {
        const res = await intentApi.getDashboard();
        this.dashboardData = res && res.data ? res.data : res;
      }
      if (intentApi && typeof intentApi.listRequests === 'function') {
        const reqRes = await intentApi.listRequests();
        this.requests = (reqRes && reqRes.data ? reqRes.data : reqRes) || [];
      }
      if (intentApi && typeof intentApi.listIntents === 'function') {
        const intRes = await intentApi.listIntents();
        this.intents = (intRes && intRes.data ? intRes.data : intRes) || [];
      }
      this.updateMetrics();
      this.renderCurrentTab();
    } catch (err) {
      console.error('Failed to load intent data:', err);
      this.error = err.message || 'Failed to load intent engine data';
      this.renderCurrentTab();
    } finally {
      this.loading = false;
    }
  }

  updateMetrics() {
    const root = this.container;
    if (!root) return;

    const data = this.dashboardData || {};
    const totalRequests = data.total_requests ?? this.requests.length;
    const totalIntents = data.total_intents ?? this.intents.length;
    const pendingClrs = data.pending_clarifications ?? 0;
    const unresolvedAmbs = data.unresolved_ambiguities ?? 0;
    const extEffect = data.external_effect_flagged ?? 0;

    const elReq = root.querySelector('#metric-total-requests');
    if (elReq) elReq.textContent = totalRequests;
    const elInt = root.querySelector('#metric-total-intents');
    if (elInt) elInt.textContent = totalIntents;
    const elClr = root.querySelector('#metric-pending-clarifications');
    if (elClr) elClr.textContent = pendingClrs;
    const elAmb = root.querySelector('#metric-unresolved-ambiguities');
    if (elAmb) elAmb.textContent = unresolvedAmbs;
    const elExt = root.querySelector('#metric-external-effect');
    if (elExt) elExt.textContent = extEffect;

    const tReq = root.querySelector('#tab-cnt-requests');
    if (tReq) tReq.textContent = totalRequests;
    const tInt = root.querySelector('#tab-cnt-intents');
    if (tInt) tInt.textContent = totalIntents;
    const tClr = root.querySelector('#tab-cnt-clarifications');
    if (tClr) tClr.textContent = pendingClrs;
  }

  switchTab(tabName) {
    this.activeTab = tabName;
    const root = this.container;
    if (!root) return;
    root.querySelectorAll('.nav-tab').forEach((tab) => {
      if (tab.dataset.tab === tabName) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });
    this.renderCurrentTab();
  }

  renderCurrentTab() {
    const body = this.container ? this.container.querySelector('#intent-console-body') : null;
    if (!body) return;

    switch (this.activeTab) {
      case 'dashboard':
        body.innerHTML = this.renderDashboardTab();
        break;
      case 'requests':
        body.innerHTML = this.renderRequestsTab();
        this.bindRequestsEvents();
        break;
      case 'intents':
        body.innerHTML = this.renderIntentsTab();
        this.bindIntentsEvents();
        break;
      case 'clarifications':
        body.innerHTML = this.renderClarificationsTab();
        this.bindClarificationsEvents();
        break;
      case 'ambiguities':
        body.innerHTML = this.renderAmbiguitiesTab();
        break;
      case 'corrections':
        body.innerHTML = this.renderCorrectionsTab();
        break;
      case 'detail':
        body.innerHTML = this.renderDetailTab();
        this.bindDetailEvents();
        break;
      default:
        body.innerHTML = `<div class="p-4">Unknown tab: ${this.activeTab}</div>`;
    }
  }

  renderDashboardTab() {
    const data = this.dashboardData || {};
    const epSummary = data.epistemic_summary || { explicit: 0, inferred: 0, unknown: 0, confirmed: 0 };
    const cats = data.categories_breakdown || {};
    const recentRequests = data.recent_requests || this.requests.slice(-5).reverse();

    return `
      <div class="intent-dashboard-grid">
        <!-- Epistemic Grounding Card -->
        <div class="card p-4">
          <h3 class="card-title">Epistemic Status Breakdown</h3>
          <p class="text-muted small mb-3">Distinguishes literal explicit instructions, inferred goals, safe assumptions, and unknown facts.</p>
          <div class="epistemic-badges-grid">
            <div class="epistemic-stat-box">
              <span class="badge badge-explicit">EXPLICIT</span>
              <div class="stat-num">${epSummary.explicit || 0}</div>
              <div class="stat-desc">Literal user commands</div>
            </div>
            <div class="epistemic-stat-box">
              <span class="badge badge-inferred">INFERRED</span>
              <div class="stat-num">${epSummary.inferred || 0}</div>
              <div class="stat-desc">Derived goal hypotheses</div>
            </div>
            <div class="epistemic-stat-box">
              <span class="badge badge-unknown">UNKNOWN</span>
              <div class="stat-num">${epSummary.unknown || 0}</div>
              <div class="stat-desc">Missing facts (never guessed)</div>
            </div>
            <div class="epistemic-stat-box">
              <span class="badge badge-confirmed">CONFIRMED</span>
              <div class="stat-num">${epSummary.confirmed || 0}</div>
              <div class="stat-desc">User clarified & confirmed</div>
            </div>
          </div>
        </div>

        <!-- Intent Categories Card -->
        <div class="card p-4">
          <h3 class="card-title">Intent Category Distribution</h3>
          <p class="text-muted small mb-3">Taxonomy of operational goals decomposed from user input.</p>
          <div class="category-bars">
            ${Object.entries(cats)
              .map(([cat, count]) => `
                <div class="category-row">
                  <span class="cat-name">${cat}</span>
                  <div class="cat-bar-track">
                    <div class="cat-bar-fill" style="width: ${Math.min(100, count * 20)}%;"></div>
                  </div>
                  <span class="cat-count">${count}</span>
                </div>
              `)
              .join('')}
          </div>
        </div>

        <!-- Recent Requests Flow -->
        <div class="card p-4 col-span-2">
          <h3 class="card-title">Recent Input Requests</h3>
          <p class="text-muted small mb-3">Incoming raw instructions processed through the Prompt Injection Firewall and Decomposition DAG.</p>
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Raw Instruction</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${recentRequests.length === 0 ? `<tr><td colspan="5" class="text-center text-muted">No requests submitted yet. Click "Submit Request" to begin.</td></tr>` : ''}
                ${recentRequests
                  .map((r) => `
                    <tr>
                      <td class="font-mono">${r.request_id}</td>
                      <td class="truncate-cell" title="${r.raw_text}">${r.raw_text}</td>
                      <td><span class="badge ${r.source === 'DIRECT_USER' ? 'badge-primary' : 'badge-neutral'}">${r.source}</span></td>
                      <td><span class="badge ${this.getStatusBadgeClass(r.status)}">${r.status}</span></td>
                      <td>
                        <button class="btn btn-xs btn-secondary btn-inspect-req" data-req-id="${r.request_id}">Inspect</button>
                      </td>
                    </tr>
                  `)
                  .join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  renderRequestsTab() {
    return `
      <div class="card p-4">
        <div class="card-header-bar">
          <div>
            <h3 class="card-title">User Requests Explorer</h3>
            <p class="text-muted small">Input streams, prompt injection defense logs, and multi-intent decomposition.</p>
          </div>
        </div>
        <div class="table-wrapper mt-3">
          <table class="data-table">
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Raw Instruction</th>
                <th>Source</th>
                <th>Scope</th>
                <th>External Data</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              ${this.requests.length === 0 ? `<tr><td colspan="7" class="text-center text-muted">No user requests found.</td></tr>` : ''}
              ${this.requests
                .map((r) => `
                  <tr>
                    <td class="font-mono">${r.request_id}</td>
                    <td>${r.raw_text}</td>
                    <td><span class="badge ${r.source === 'DIRECT_USER' ? 'badge-primary' : 'badge-neutral'}">${r.source}</span></td>
                    <td>${r.scope || 'DEFAULT'}</td>
                    <td>${r.is_external_content ? '<span class="badge badge-danger">DATA_ONLY</span>' : '<span class="badge badge-success">USER_AUTH</span>'}</td>
                    <td><span class="badge ${this.getStatusBadgeClass(r.status)}">${r.status}</span></td>
                    <td class="text-muted small">${new Date(r.created_at).toLocaleTimeString()}</td>
                  </tr>
                `)
                .join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  renderIntentsTab() {
    return `
      <div class="card p-4">
        <div class="card-header-bar">
          <div>
            <h3 class="card-title">Autonomous Structured Intents</h3>
            <p class="text-muted small">Decomposed intent nodes with component-wise confidence calibration and non-goals.</p>
          </div>
        </div>
        <div class="table-wrapper mt-3">
          <table class="data-table">
            <thead>
              <tr>
                <th>Intent ID</th>
                <th>Category</th>
                <th>Summary</th>
                <th>Target</th>
                <th>Epistemic</th>
                <th>Non-Goals</th>
                <th>External Effect</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${this.intents.length === 0 ? `<tr><td colspan="10" class="text-center text-muted">No intents available.</td></tr>` : ''}
              ${this.intents
                .map((i) => `
                  <tr>
                    <td class="font-mono">${i.intent_id}</td>
                    <td><span class="badge badge-category">${i.category}</span></td>
                    <td>${i.summary}</td>
                    <td class="font-mono">${i.target}</td>
                    <td><span class="badge badge-${(i.target_epistemic || 'EXPLICIT').toLowerCase()}">${i.target_epistemic || 'EXPLICIT'}</span></td>
                    <td>${(i.non_goals || []).length > 0 ? `<span class="badge badge-warning">${i.non_goals.length} non-goals</span>` : '<span class="text-muted">-</span>'}</td>
                    <td>${i.external_effect === 'EXTERNAL_EFFECT_POSSIBLE' ? '<span class="badge badge-danger">EXTERNAL</span>' : '<span class="badge badge-neutral">INTERNAL</span>'}</td>
                    <td><span class="confidence-pill">${Math.round((i.overall_confidence || 1.0) * 100)}%</span></td>
                    <td><span class="badge ${this.getStatusBadgeClass(i.status)}">${i.status}</span></td>
                    <td>
                      <button class="btn btn-xs btn-primary btn-select-intent" data-intent-id="${i.intent_id}">Inspect</button>
                    </td>
                  </tr>
                `)
                .join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  renderClarificationsTab() {
    const queue = (this.dashboardData && this.dashboardData.clarification_queue) || [];
    return `
      <div class="card p-4">
        <h3 class="card-title">Consequence-Aware Clarification Queue</h3>
        <p class="text-muted small mb-3">Minimal, targeted questions generated only when ambiguity materially impacts safety, authorization, destructive consequences, or privacy.</p>
        <div class="clarification-list">
          ${queue.length === 0 ? `<div class="empty-state text-muted">No pending clarifications. All active intents are sufficiently understood.</div>` : ''}
          ${queue
            .map((c) => `
              <div class="clarification-card">
                <div class="clr-header">
                  <span class="badge badge-warning">CLARIFICATION REQUIRED</span>
                  <span class="font-mono small">Intent: ${c.intent_id}</span>
                </div>
                <div class="clr-question">${c.question}</div>
                <div class="clr-rationale text-muted small">Rationale: ${c.rationale}</div>
                <div class="clr-options mt-2">
                  ${(c.options || [])
                    .map((opt) => `
                      <button class="btn btn-xs btn-secondary btn-quick-opt" data-clr-id="${c.clarification_id}" data-opt="${opt}">${opt}</button>
                    `)
                    .join('')}
                  <button class="btn btn-xs btn-primary btn-open-clr-modal" data-clr-id="${c.clarification_id}" data-q="${c.question}" data-r="${c.rationale}">Custom Answer</button>
                </div>
              </div>
            `)
            .join('')}
        </div>
      </div>
    `;
  }

  renderAmbiguitiesTab() {
    return `
      <div class="card p-4">
        <h3 class="card-title">Ambiguity Center</h3>
        <p class="text-muted small mb-3">Classification across 10 categories: lexical, scope, target, temporal, quantity, quality, authorization, priority, environment, output format.</p>
        <div class="ambiguity-grid">
          <div class="amb-category-pill"><span class="cat-label">Target Ambiguity:</span> Identifies vague pronouns ('it', 'them') on consequential operations.</div>
          <div class="amb-category-pill"><span class="cat-label">Environment Ambiguity:</span> Never assumes production when unclear.</div>
          <div class="amb-category-pill"><span class="cat-label">Quantity Ambiguity:</span> Gates thresholds ('clean old files' -> how old?).</div>
          <div class="amb-category-pill"><span class="cat-label">Scope Ambiguity:</span> Defines exact workspace boundaries.</div>
          <div class="amb-category-pill"><span class="cat-label">Temporal Ambiguity:</span> Resolves relative times ('now', 'later') safely.</div>
        </div>
      </div>
    `;
  }

  renderCorrectionsTab() {
    return `
      <div class="card p-4">
        <h3 class="card-title">User Corrections & Supersession Lineage</h3>
        <p class="text-muted small mb-3">Immutable version history (v1 -> v2) on corrections ('No, I meant staging') and supersession ('Actually, forget that').</p>
        <div class="timeline">
          <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
              <strong>Non-Destructive Versioning:</strong> Every material interpretation revision generates a new immutable snapshot.
            </div>
          </div>
          <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
              <strong>Supersession Principle:</strong> A superseded intent is immediately terminated so downstream execution halts.
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderDetailTab() {
    if (!this.selectedIntent) {
      return `
        <div class="card p-4 text-center text-muted">
          <p>No intent selected. Select an intent from the "Intents" tab to inspect its Goal Hypotheses, Constraints, Non-Goals, and Decision Snapshot.</p>
        </div>
      `;
    }

    const intent = this.selectedIntent;
    const snap = this.selectedSnapshot || {};

    return `
      <div class="intent-detail-layout">
        <!-- Main Intent Card -->
        <div class="card p-4">
          <div class="detail-header">
            <div>
              <span class="badge badge-category">${intent.category}</span>
              <h2 class="detail-title mt-1">${intent.summary}</h2>
            </div>
            <div>
              <span class="badge ${this.getStatusBadgeClass(intent.status)}">${intent.status}</span>
            </div>
          </div>

          <div class="detail-grid mt-4">
            <div class="detail-field">
              <label>Target Entity</label>
              <div class="field-val font-mono">${intent.target} (${intent.target_epistemic || 'EXPLICIT'})</div>
            </div>
            <div class="detail-field">
              <label>Scope</label>
              <div class="field-val">${intent.scope || 'DEFAULT'}</div>
            </div>
            <div class="detail-field">
              <label>External Effect Risk</label>
              <div class="field-val">${intent.external_effect}</div>
            </div>
            <div class="detail-field">
              <label>Overall Confidence</label>
              <div class="field-val">${Math.round((intent.overall_confidence || 1.0) * 100)}%</div>
            </div>
          </div>

          <!-- Non-Goals Block -->
          <div class="non-goals-box mt-4">
            <h4>Explicit Non-Goals (Preserved Boundaries)</h4>
            ${(intent.non_goals || []).length === 0 ? '<p class="text-muted small">No explicit non-goals declared.</p>' : ''}
            <ul>
              ${(intent.non_goals || []).map((ng) => `<li>${ng}</li>`).join('')}
            </ul>
          </div>

          <!-- Actions -->
          <div class="detail-actions mt-4">
            <button class="btn btn-secondary btn-sm btn-correct-intent" data-intent-id="${intent.intent_id}">Apply Correction</button>
            <button class="btn btn-danger btn-sm btn-cancel-intent" data-intent-id="${intent.intent_id}">Cancel Intent</button>
          </div>
        </div>

        <!-- Snapshot & Lineage -->
        <div class="card p-4">
          <h3 class="card-title">Decision-Time Snapshot</h3>
          <p class="text-muted small mb-3">Immutable epistemic record referenced by Decision Intelligence (Task 94) and Goal Management (Task 100).</p>
          <pre class="json-code-block">${JSON.stringify(snap, null, 2)}</pre>
        </div>
      </div>
    `;
  }

  bindRequestsEvents() {
    const root = this.container;
    if (!root) return;
    root.querySelectorAll('.btn-inspect-req').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const reqId = e.currentTarget.dataset.reqId;
        const matchingIntents = this.intents.filter((i) => i.request_id === reqId);
        if (matchingIntents.length > 0) {
          this.selectIntent(matchingIntents[0].intent_id);
        } else {
          this.switchTab('requests');
        }
      });
    });
  }

  bindIntentsEvents() {
    const root = this.container;
    if (!root) return;
    root.querySelectorAll('.btn-select-intent').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.dataset.intentId;
        this.selectIntent(id);
      });
    });
  }

  bindClarificationsEvents() {
    const root = this.container;
    if (!root) return;
    root.querySelectorAll('.btn-quick-opt').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const clrId = e.currentTarget.dataset.clrId;
        const opt = e.currentTarget.dataset.opt;
        await this.answerClarification(clrId, opt);
      });
    });

    root.querySelectorAll('.btn-open-clr-modal').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const clrId = e.currentTarget.dataset.clrId;
        const q = e.currentTarget.dataset.q;
        const r = e.currentTarget.dataset.r;
        const modal = root.querySelector('#modal-answer-clarification');
        if (modal) {
          modal.dataset.currentClrId = clrId;
          const qEl = modal.querySelector('#clr-question-text');
          if (qEl) qEl.textContent = q;
          const rEl = modal.querySelector('#clr-rationale-text');
          if (rEl) rEl.textContent = r;
          modal.classList.remove('hidden');
        }
      });
    });
  }

  bindDetailEvents() {
    const root = this.container;
    if (!root) return;
    const correctBtn = root.querySelector('.btn-correct-intent');
    if (correctBtn) {
      correctBtn.addEventListener('click', async () => {
        const feedback = prompt('Enter correction (e.g. "No, I meant staging" or "Archive instead of delete"):');
        if (feedback && this.selectedIntent) {
          try {
            await intentApi.correctRequest(this.selectedIntent.request_id, {
              correction_text: feedback,
              scope_affected: 'CURRENT_PROJECT',
            });
            await this.loadData();
            if (this.selectedIntentId) {
              await this.selectIntent(this.selectedIntentId);
            }
          } catch (err) {
            alert('Failed to apply correction: ' + err.message);
          }
        }
      });
    }

    const cancelBtn = root.querySelector('.btn-cancel-intent');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', async () => {
        if (confirm('Are you sure you want to cancel this intent?') && this.selectedIntent) {
          try {
            await intentApi.cancelRequest(this.selectedIntent.request_id, {
              reason: 'User cancelled via console',
            });
            await this.loadData();
            this.switchTab('intents');
          } catch (err) {
            alert('Failed to cancel intent: ' + err.message);
          }
        }
      });
    }
  }

  async selectIntent(intentId) {
    this.selectedIntentId = intentId;
    this.selectedIntent = this.intents.find((i) => i.intent_id === intentId) || null;
    try {
      if (intentApi && typeof intentApi.getSnapshot === 'function') {
        const snapRes = await intentApi.getSnapshot(intentId);
        this.selectedSnapshot = (snapRes && snapRes.data ? snapRes.data : snapRes) || null;
      }
    } catch {
      this.selectedSnapshot = null;
    }
    this.switchTab('detail');
  }

  async handleSubmitRequest() {
    const root = this.container;
    if (!root) return;
    const rawInput = root.querySelector('#input-request-raw');
    const sourceInput = root.querySelector('#input-request-source');
    const scopeInput = root.querySelector('#input-request-scope');
    const modal = root.querySelector('#modal-submit-request');

    const text = rawInput ? rawInput.value.trim() : '';
    if (!text) {
      alert('Please enter a request.');
      return;
    }

    try {
      const payload = {
        raw_text: text,
        source: sourceInput ? sourceInput.value : 'DIRECT_USER',
        scope: scopeInput ? scopeInput.value : 'DEFAULT',
      };
      await intentApi.submitRequest(payload);
      if (modal) modal.classList.add('hidden');
      if (rawInput) rawInput.value = '';
      await this.loadData();
      this.switchTab('intents');
    } catch (err) {
      alert('Submission rejected: ' + err.message);
    }
  }

  async handleAnswerClarification() {
    const root = this.container;
    if (!root) return;
    const modal = root.querySelector('#modal-answer-clarification');
    const input = root.querySelector('#input-clarification-answer');
    const clrId = modal ? modal.dataset.currentClrId : null;
    const answer = input ? input.value.trim() : '';

    if (!clrId || !answer) {
      alert('Please provide an answer.');
      return;
    }

    await this.answerClarification(clrId, answer);
    if (modal) modal.classList.add('hidden');
    if (input) input.value = '';
  }

  async answerClarification(clarificationId, answer) {
    try {
      await intentApi.answerClarification(clarificationId, { answer });
      await this.loadData();
      this.switchTab('clarifications');
    } catch (err) {
      alert('Failed to submit clarification: ' + err.message);
    }
  }

  getStatusBadgeClass(status) {
    switch (status) {
      case 'UNDERSTOOD':
      case 'CONFIRMED':
        return 'badge-success';
      case 'CLARIFICATION_REQUIRED':
      case 'AMBIGUOUS':
        return 'badge-warning';
      case 'SUPERSEDED':
        return 'badge-neutral';
      case 'CANCELLED':
      case 'REJECTED':
        return 'badge-danger';
      case 'PARSING':
      case 'INTERPRETING':
        return 'badge-primary';
      default:
        return 'badge-neutral';
    }
  }
}

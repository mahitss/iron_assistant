/**
 * Strategy & Adaptive Operating Policy Console View (Task 106)
 * Comprehensive UI for Knowledge-to-Action Learning, Strategy Synthesis,
 * Applicability Evaluation, Counterexample Tracking, and Governed Strategy Evolution.
 */

import { strategyApi, endpoints } from '../../lib/api/endpoints.js';

export class StrategyView {
  constructor(options = {}) {
    this.container = options.container || (typeof document !== 'undefined' ? document.getElementById('main-content-viewport') : null);
    this.activeTab = 'dashboard';
    this.dashboardData = null;
    this.strategies = [];
    this.selectedStrategyId = null;
    this.selectedStrategy = null;
    this.applicabilityResult = null;
    this.conflicts = [];
    this.proposals = [];
    this.loading = false;
    this.error = null;
    this.filterCategory = 'ALL';
    this.filterStatus = 'ALL';
  }

  async init() {
    this.renderContainer();
    await this.loadData();
  }

  renderContainer() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="strategy-console" id="strategy-console-root">
        <!-- Header -->
        <header class="console-header">
          <div class="header-left">
            <div class="header-badge">TASK 106</div>
            <h1 class="console-title">Autonomous Strategy Synthesis & Operating Policy</h1>
            <p class="console-sub">Transforming verified experience into reusable, bounded, evidence-backed operational strategies.</p>
          </div>
          <div class="header-right">
            <div id="estop-indicator" class="estop-pill safe">
              <span class="pulse-dot"></span>
              <span id="estop-text">EmergencyStop Disengaged</span>
            </div>
            <button id="btn-refresh-strategy" class="btn btn-secondary btn-sm">
              <span class="icon">↻</span> Refresh
            </button>
            <button id="btn-new-strategy" class="btn btn-primary btn-sm">
              <span class="icon">+</span> New Strategy
            </button>
          </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="console-tabs" role="tablist">
          <button class="tab-btn active" data-tab="dashboard">Dashboard</button>
          <button class="tab-btn" data-tab="explorer">Strategy Explorer</button>
          <button class="tab-btn" data-tab="detail">Strategy Detail</button>
          <button class="tab-btn" data-tab="applicability">Applicability Tester</button>
          <button class="tab-btn" data-tab="conflicts">Conflict Explorer</button>
          <button class="tab-btn" data-tab="coverage">Coverage & Drift</button>
          <button class="tab-btn" data-tab="proposals">Proposals & Review</button>
        </nav>

        <!-- Tab Content Viewport -->
        <main class="console-body" id="strategy-tab-viewport">
          <div class="loading-spinner">Loading Strategy Engine data...</div>
        </main>
      </div>
    `;

    this._bindEvents();
  }

  _bindEvents() {
    if (!this.container) return;

    // Tab buttons
    const tabBtns = this.container.querySelectorAll('.tab-btn');
    tabBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        tabBtns.forEach((b) => b.classList.remove('active'));
        e.target.classList.add('active');
        this.activeTab = e.target.dataset.tab;
        this.renderActiveTab();
      });
    });

    // Refresh button
    const refreshBtn = this.container.querySelector('#btn-refresh-strategy');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }
  }

  async loadData() {
    this.loading = true;
    try {
      if (typeof strategyApi !== 'undefined') {
        const [dashRes, stratRes] = await Promise.all([
          strategyApi.getDashboard().catch(() => null),
          strategyApi.listStrategies().catch(() => []),
        ]);
        if (dashRes && dashRes.data) this.dashboardData = dashRes.data;
        if (stratRes && stratRes.data) this.strategies = stratRes.data;
      }
    } catch (err) {
      this.error = err.message || 'Failed to load strategy data';
    } finally {
      this.loading = false;
      this.renderActiveTab();
    }
  }

  renderActiveTab() {
    const viewport = this.container ? this.container.querySelector('#strategy-tab-viewport') : null;
    let html = '';

    switch (this.activeTab) {
      case 'dashboard':
        html = this.renderDashboardTab();
        break;
      case 'explorer':
        html = this.renderExplorerTab();
        break;
      case 'detail':
        html = this.renderDetailTab();
        break;
      case 'applicability':
        html = this.renderApplicabilityTab();
        break;
      case 'conflicts':
        html = this.renderConflictsTab();
        break;
      case 'coverage':
        html = this.renderCoverageTab();
        break;
      case 'proposals':
        html = this.renderProposalsTab();
        break;
      default:
        html = this.renderDashboardTab();
    }

    if (viewport) {
      viewport.innerHTML = html;
      this._bindTabEvents(viewport);
    }
    return html;
  }

  // ---------------------------------------------------------------------------
  // Tab 1: Dashboard
  // ---------------------------------------------------------------------------
  renderDashboardTab() {
    const d = this.dashboardData || {
      total_strategies: this.strategies.length,
      available_count: this.strategies.filter((s) => s.lifecycle_status === 'AVAILABLE').length,
      candidate_count: this.strategies.filter((s) => s.lifecycle_status === 'CANDIDATE').length,
      validating_count: this.strategies.filter((s) => s.lifecycle_status === 'VALIDATING').length,
      stale_count: this.strategies.filter((s) => s.is_stale).length,
      suspended_count: this.strategies.filter((s) => s.lifecycle_status === 'SUSPENDED').length,
      conflicted_count: this.strategies.filter((s) => s.lifecycle_status === 'CONFLICTED').length,
      revalidation_queue_count: this.strategies.filter((s) => s.is_stale).length,
      proposals_pending_count: 0,
      emergency_stop_active: false,
    };

    return `
      <div class="dashboard-grid">
        <!-- 9 KPI Metric Cards -->
        <div class="kpi-card highlight">
          <div class="kpi-label">TOTAL STRATEGIES</div>
          <div class="kpi-value">${d.total_strategies}</div>
          <div class="kpi-sub">Across 17 categories</div>
        </div>
        <div class="kpi-card success">
          <div class="kpi-label">AVAILABLE (VALIDATED)</div>
          <div class="kpi-value">${d.available_count}</div>
          <div class="kpi-sub">Ready for decision selection</div>
        </div>
        <div class="kpi-card info">
          <div class="kpi-label">CANDIDATES</div>
          <div class="kpi-value">${d.candidate_count}</div>
          <div class="kpi-sub">Awaiting verification</div>
        </div>
        <div class="kpi-card warning">
          <div class="kpi-label">VALIDATING</div>
          <div class="kpi-value">${d.validating_count}</div>
          <div class="kpi-sub">Active benchmarks</div>
        </div>
        <div class="kpi-card danger">
          <div class="kpi-label">STALE / EXPIRED</div>
          <div class="kpi-value">${d.stale_count}</div>
          <div class="kpi-sub">Exceeded validity window</div>
        </div>
        <div class="kpi-card alert">
          <div class="kpi-label">SUSPENDED</div>
          <div class="kpi-value">${d.suspended_count}</div>
          <div class="kpi-sub">Safety or regression flag</div>
        </div>
        <div class="kpi-card warning">
          <div class="kpi-label">CONFLICTED</div>
          <div class="kpi-value">${d.conflicted_count}</div>
          <div class="kpi-sub">Tactical divergence</div>
        </div>
        <div class="kpi-card info">
          <div class="kpi-label">REVALIDATION QUEUE</div>
          <div class="kpi-value">${d.revalidation_queue_count}</div>
          <div class="kpi-sub">Scheduled renewals</div>
        </div>
        <div class="kpi-card primary">
          <div class="kpi-label">PENDING PROPOSALS</div>
          <div class="kpi-value">${d.proposals_pending_count}</div>
          <div class="kpi-sub">Under governance review</div>
        </div>
      </div>

      <!-- Architectural Invariants Notice -->
      <div class="notice-panel">
        <div class="notice-title">🛡️ NON-NEGOTIABLE SAFETY INVARIANTS</div>
        <div class="notice-body">
          <code>LEARNED STRATEGY != POLICY AUTHORITY</code> &bull;
          <code>LEARNED STRATEGY != SECURITY AUTHORITY</code> &bull;
          <code>LEARNED STRATEGY != DECISION</code> &bull;
          <code>STRATEGY != ACTION</code> &bull;
          <code>EMERGENCY_STOP ABSOLUTE PRIMACY</code>
        </div>
      </div>

      <!-- Recent Strategies -->
      <section class="section-card">
        <h2 class="section-title">Recent Strategies</h2>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID / Name</th>
                <th>Category</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Success Rate</th>
                <th>Staleness</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${
                this.strategies.length === 0
                  ? '<tr><td colspan="7" class="text-center text-muted">No strategies mined or created yet.</td></tr>'
                  : this.strategies
                      .slice(0, 8)
                      .map(
                        (s) => `
                    <tr>
                      <td>
                        <strong>${s.name}</strong><br/>
                        <small class="mono text-muted">${s.id}</small>
                      </td>
                      <td><span class="badge category">${s.category}</span></td>
                      <td><span class="badge status-${(s.lifecycle_status || '').toLowerCase()}">${s.lifecycle_status}</span></td>
                      <td><strong>${(s.confidence * 100).toFixed(1)}%</strong></td>
                      <td>${(s.success_rate * 100).toFixed(1)}%</td>
                      <td>${s.is_stale ? '<span class="badge danger">STALE</span>' : '<span class="badge success">FRESH</span>'}</td>
                      <td>
                        <button class="btn btn-sm btn-secondary btn-inspect" data-id="${s.id}">Inspect</button>
                      </td>
                    </tr>
                  `
                      )
                      .join('')
              }
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  // ---------------------------------------------------------------------------
  // Tab 2: Strategy Explorer
  // ---------------------------------------------------------------------------
  renderExplorerTab() {
    return `
      <div class="explorer-container">
        <div class="filter-bar">
          <input type="text" id="strategy-search-input" class="input search" placeholder="Search strategies by name, objective, approach..." />
          <select id="filter-category" class="input select">
            <option value="ALL">All Categories</option>
            <option value="PLANNING">Planning</option>
            <option value="DECISION">Decision</option>
            <option value="RECOVERY">Recovery</option>
            <option value="RESOURCE">Resource</option>
            <option value="RETRIEVAL">Retrieval</option>
            <option value="SECURITY_DEFENSE">Security Defense</option>
          </select>
          <select id="filter-status" class="input select">
            <option value="ALL">All Statuses</option>
            <option value="AVAILABLE">AVAILABLE</option>
            <option value="CANDIDATE">CANDIDATE</option>
            <option value="VALIDATING">VALIDATING</option>
            <option value="SUSPENDED">SUSPENDED</option>
          </select>
        </div>

        <div class="strategy-cards-grid">
          ${
            this.strategies.length === 0
              ? '<div class="empty-state">No strategies matching current filters.</div>'
              : this.strategies
                  .map(
                    (s) => `
                <div class="strategy-card" data-id="${s.id}">
                  <div class="strategy-card-header">
                    <span class="badge category">${s.category}</span>
                    <span class="badge status-${(s.lifecycle_status || '').toLowerCase()}">${s.lifecycle_status}</span>
                  </div>
                  <h3 class="strategy-card-title">${s.name}</h3>
                  <p class="strategy-card-obj">${s.objective || 'No explicit objective documented.'}</p>
                  <div class="strategy-card-meta">
                    <div>Confidence: <strong>${(s.confidence * 100).toFixed(0)}%</strong></div>
                    <div>Usages: <strong>${s.usage_count}</strong></div>
                    <div>Success: <strong>${(s.success_rate * 100).toFixed(0)}%</strong></div>
                  </div>
                  <div class="strategy-card-footer">
                    <button class="btn btn-sm btn-outline btn-inspect" data-id="${s.id}">Inspect Detail &rarr;</button>
                  </div>
                </div>
              `
                  )
                  .join('')
          }
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Tab 3: Strategy Detail
  // ---------------------------------------------------------------------------
  renderDetailTab() {
    const s = this.selectedStrategy || (this.strategies.length > 0 ? this.strategies[0] : null);
    if (!s) {
      return '<div class="empty-state">Select a strategy from the explorer to inspect details.</div>';
    }

    return `
      <div class="strategy-detail-container">
        <header class="detail-header">
          <div>
            <span class="badge category">${s.category}</span>
            <span class="badge status-${(s.lifecycle_status || '').toLowerCase()}">${s.lifecycle_status}</span>
            <h2 class="detail-title">${s.name}</h2>
            <div class="mono text-muted">ID: ${s.id} | Stable: ${s.stable_id} | Domain: ${s.domain_scope}</div>
          </div>
          <div class="detail-actions">
            <button class="btn btn-sm btn-warning btn-revalidate" data-id="${s.id}">Revalidate</button>
            <button class="btn btn-sm btn-primary btn-test-app" data-id="${s.id}">Test Applicability</button>
          </div>
        </header>

        <div class="detail-grid">
          <!-- Left Column: Mechanics -->
          <div class="detail-col">
            <div class="panel">
              <h3>Objective & Approach</h3>
              <p><strong>Objective:</strong> ${s.objective}</p>
              <p><strong>Recommended Approach:</strong></p>
              <pre class="approach-box">${s.recommended_approach}</pre>
            </div>

            <div class="panel">
              <h3>Conditions & Preconditions</h3>
              <div class="condition-list">
                ${
                  (s.conditions || []).length === 0
                    ? '<p class="text-muted">No explicit conditions specified.</p>'
                    : (s.conditions || [])
                        .map(
                          (c) => `
                      <div class="condition-item">
                        <span class="tag">CONDITION</span>
                        <code>${c.field_path} ${c.operator} ${JSON.stringify(c.target_value)}</code>
                      </div>
                    `
                        )
                        .join('')
                }
                ${
                  (s.preconditions || []).map(
                    (p) => `
                    <div class="condition-item precondition">
                      <span class="tag">PRECONDITION</span>
                      <span>${p.requirement_description} (key: <code>${p.verification_key}</code>)</span>
                    </div>
                  `
                  ).join('')
                }
              </div>
            </div>

            <div class="panel contraindication-panel">
              <h3>Contraindications (DO NOT USE WHEN...)</h3>
              <div class="contra-list">
                ${
                  (s.contraindications || []).length === 0
                    ? '<p class="text-muted">No contraindications documented.</p>'
                    : (s.contraindications || [])
                        .map(
                          (c) => `
                      <div class="contra-item severity-${(c.severity || '').toLowerCase()}">
                        <strong>[${c.severity}] ${c.contraindication_type}:</strong>
                        <span>${c.rationale}</span>
                      </div>
                    `
                        )
                        .join('')
                }
              </div>
            </div>
          </div>

          <!-- Right Column: Evidence & Counterexamples -->
          <div class="detail-col">
            <div class="panel">
              <h3>Confidence & Epistemics</h3>
              <div class="stat-row">
                <span>Multi-factor Confidence:</span>
                <strong>${(s.confidence * 100).toFixed(1)}%</strong>
              </div>
              <div class="stat-row">
                <span>Epistemic Uncertainty:</span>
                <strong>${(s.uncertainty * 100).toFixed(1)}%</strong>
              </div>
              <div class="stat-row">
                <span>Empirical Success Rate:</span>
                <strong>${(s.success_rate * 100).toFixed(1)}% (${s.usage_count} usages)</strong>
              </div>
              <div class="stat-row">
                <span>Staleness:</span>
                <strong>${s.is_stale ? 'EXPIRED' : 'FRESH'}</strong>
              </div>
            </div>

            <div class="panel counterexample-panel">
              <h3>Known Counterexamples & Exceptions (${(s.counterexamples || []).length})</h3>
              <div class="counter-list">
                ${
                  (s.counterexamples || []).length === 0
                    ? '<p class="text-muted">No known counterexamples logged yet.</p>'
                    : (s.counterexamples || [])
                        .map(
                          (ce) => `
                      <div class="counter-item">
                        <div class="counter-claim">❌ ${ce.claim}</div>
                        <small class="text-muted">Context: ${JSON.stringify(ce.environmental_context || {})}</small>
                      </div>
                    `
                        )
                        .join('')
                }
              </div>
            </div>

            <div class="panel">
              <h3>Known Failure Modes</h3>
              <div class="failure-list">
                ${
                  (s.failure_modes || []).length === 0
                    ? '<p class="text-muted">No failure modes reported.</p>'
                    : (s.failure_modes || [])
                        .map(
                          (f) => `
                      <div class="failure-item">
                        <strong>${f.failure_class}:</strong> ${f.symptom}
                        <br/><small class="text-muted">Cause: ${f.known_cause}</small>
                      </div>
                    `
                        )
                        .join('')
                }
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Tab 4: Applicability Tester
  // ---------------------------------------------------------------------------
  renderApplicabilityTab() {
    const s = this.selectedStrategy || (this.strategies.length > 0 ? this.strategies[0] : null);

    return `
      <div class="applicability-container">
        <h2>Interactive Applicability Evaluator</h2>
        <p class="text-muted">Simulate operational context against strategy conditions, preconditions, and contraindications.</p>

        <div class="app-tester-grid">
          <div class="tester-input-panel">
            <label>Select Target Strategy:</label>
            <select id="app-test-strategy-select" class="input select">
              ${this.strategies.map((strat) => `<option value="${strat.id}" ${s && strat.id === s.id ? 'selected' : ''}>${strat.name} (${strat.id})</option>`).join('')}
            </select>

            <label style="margin-top: 15px; display: block;">Simulated Context (JSON):</label>
            <textarea id="app-test-context-json" class="input textarea" rows="10">{
  "task_type": "GENERAL",
  "capability": "general_reasoning",
  "environment": "prod",
  "world_state_stale": false,
  "capability_health": "HEALTHY",
  "resource_pressure": "LOW",
  "emergency_stop": false
}</textarea>
            <button id="btn-run-app-test" class="btn btn-primary" style="margin-top: 12px;">Evaluate Applicability</button>
          </div>

          <div class="tester-result-panel" id="app-test-result-box">
            <h3>Evaluation Verdict</h3>
            <div class="text-muted">Click 'Evaluate Applicability' to run live rule matching.</div>
          </div>
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Tab 5: Conflicts
  // ---------------------------------------------------------------------------
  renderConflictsTab() {
    return `
      <div class="conflicts-container">
        <h2>Detected Strategy Conflicts</h2>
        <p class="text-muted">Contending or contradictory approaches exposed transparently to Decision Intelligence.</p>

        <div class="conflicts-list">
          ${
            this.conflicts.length === 0
              ? '<div class="empty-state">No inter-strategy conflicts active in current registry.</div>'
              : this.conflicts
                  .map(
                    (c) => `
                <div class="conflict-card type-${c.conflict_type.toLowerCase()}">
                  <div class="conflict-type-badge">${c.conflict_type} CONFLICT</div>
                  <div class="conflict-body">
                    <p><strong>Description:</strong> ${c.description}</p>
                    <p><strong>Resolution Hint:</strong> ${c.resolution_hint || 'Arbitrate via Decision Intelligence Pareto scoring.'}</p>
                    <small class="text-muted">Between: ${c.strategy_a_id} vs ${c.strategy_b_id}</small>
                  </div>
                </div>
              `
                  )
                  .join('')
          }
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Tab 6: Coverage & Drift
  // ---------------------------------------------------------------------------
  renderCoverageTab() {
    const d = this.dashboardData || {};
    const cov = d.coverage_by_category || {};

    return `
      <div class="coverage-container">
        <h2>Strategy Coverage & Drift Monitoring</h2>
        <p class="text-muted">Empirical distribution across operating categories and drift warnings.</p>

        <div class="coverage-grid">
          ${Object.entries(cov)
            .map(
              ([cat, count]) => `
              <div class="coverage-tile">
                <div class="tile-category">${cat}</div>
                <div class="tile-count">${count}</div>
                <div class="tile-status">${count > 0 ? 'COVERED' : 'UNCOVERED'}</div>
              </div>
            `
            )
            .join('')}
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Tab 7: Proposals & Review
  // ---------------------------------------------------------------------------
  renderProposalsTab() {
    return `
      <div class="proposals-container">
        <h2>Strategy Promotion Proposals</h2>
        <p class="text-muted">Governed promotion workflow moving strategies from CANDIDATE to AVAILABLE.</p>

        <div class="proposals-list">
          ${
            this.proposals.length === 0
              ? '<div class="empty-state">No pending strategy proposals under review.</div>'
              : this.proposals
                  .map(
                    (p) => `
                <div class="proposal-card">
                  <div class="proposal-header">
                    <strong>${p.proposal_title}</strong>
                    <span class="badge status">${p.status}</span>
                  </div>
                  <p>${p.rationale}</p>
                  <div class="proposal-actions">
                    <button class="btn btn-sm btn-success btn-approve-proposal" data-id="${p.id}">Approve Strategy</button>
                    <button class="btn btn-sm btn-danger btn-reject-proposal" data-id="${p.id}">Reject</button>
                  </div>
                </div>
              `
                  )
                  .join('')
          }
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // Event Binding for Interactive Features
  // ---------------------------------------------------------------------------
  _bindTabEvents(viewport) {
    // Inspect buttons
    const inspectBtns = viewport.querySelectorAll('.btn-inspect');
    inspectBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = e.target.dataset.id;
        this.selectedStrategyId = id;
        this.selectedStrategy = this.strategies.find((s) => s.id === id) || null;
        this.activeTab = 'detail';
        const tabBtns = this.container.querySelectorAll('.tab-btn');
        tabBtns.forEach((b) => b.classList.remove('active'));
        const detailTabBtn = this.container.querySelector('[data-tab="detail"]');
        if (detailTabBtn) detailTabBtn.classList.add('active');
        this.renderActiveTab();
      });
    });

    // Revalidate button
    const revalBtns = viewport.querySelectorAll('.btn-revalidate');
    revalBtns.forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.target.dataset.id;
        try {
          if (typeof strategyApi !== 'undefined') {
            await strategyApi.revalidateStrategy(id);
            alert(`Revalidation triggered for strategy ${id}.`);
            await this.loadData();
          }
        } catch (err) {
          alert(`Error revalidating: ${err.message}`);
        }
      });
    });

    // Interactive Applicability Tester
    const runTestBtn = viewport.querySelector('#btn-run-app-test');
    if (runTestBtn) {
      runTestBtn.addEventListener('click', async () => {
        const select = viewport.querySelector('#app-test-strategy-select');
        const jsonArea = viewport.querySelector('#app-test-context-json');
        const resultBox = viewport.querySelector('#app-test-result-box');
        if (!select || !jsonArea || !resultBox) return;

        const stratId = select.value;
        let ctx = {};
        try {
          ctx = JSON.parse(jsonArea.value);
        } catch (err) {
          resultBox.innerHTML = '<div class="alert danger">Invalid JSON in context field.</div>';
          return;
        }

        resultBox.innerHTML = '<div class="loading-spinner">Evaluating rules...</div>';
        try {
          if (typeof strategyApi !== 'undefined') {
            const res = await strategyApi.checkApplicability(stratId, ctx);
            const app = res.data;
            const statusClass = (app.applicability_status || '').toLowerCase();
            resultBox.innerHTML = `
              <div class="result-card status-${statusClass}">
                <div class="result-status-badge">${app.applicability_status}</div>
                <div class="result-score">Applicability Score: <strong>${(app.applicability_score * 100).toFixed(1)}%</strong></div>
                ${app.blocking_reasons && app.blocking_reasons.length > 0 ? `<div class="reasons blocking"><strong>Blocking Reasons:</strong><ul>${app.blocking_reasons.map((r) => `<li>${r}</li>`).join('')}</ul></div>` : ''}
                ${app.uncertainty_reasons && app.uncertainty_reasons.length > 0 ? `<div class="reasons uncertainty"><strong>Uncertainty Reasons:</strong><ul>${app.uncertainty_reasons.map((r) => `<li>${r}</li>`).join('')}</ul></div>` : ''}
              </div>
            `;
          }
        } catch (err) {
          resultBox.innerHTML = `<div class="alert danger">Evaluation failed: ${err.message}</div>`;
        }
      });
    }
  }
}

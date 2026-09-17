/**
 * Adaptation & Governed Evolution Console View (Task 105)
 * Comprehensive UI for closed-loop adaptation, experiment orchestration,
 * multi-objective comparison, safety gates, and governed capability change.
 */

import { adaptationApi, endpoints } from '../../lib/api/endpoints.js';

export class AdaptationView {
  constructor(options = {}) {
    this.container = options.container || (typeof document !== 'undefined' ? document.getElementById('main-content-viewport') : null);
    this.activeTab = 'dashboard';
    this.dashboardData = null;
    this.programs = [];
    this.experiments = [];
    this.hypotheses = [];
    this.comparisons = [];
    this.proposals = [];
    this.changesets = [];
    this.gates = [];
    this.selectedProgramId = null;
    this.selectedRunId = null;
    this.selectedProposalId = null;
    this.loading = false;
    this.error = null;
  }

  async init() {
    this.renderContainer();
    await this.loadData();
  }

  renderContainer() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="adaptation-console" id="adaptation-console-root">
        <!-- Header -->
        <header class="console-header">
          <div class="header-left">
            <div class="header-badge">TASK 105</div>
            <h1 class="console-title">Autonomous Adaptation & Governed Evolution</h1>
            <p class="console-sub">Controlled experimentation, multi-objective validation, and governed capability lifecycle evolution.</p>
          </div>
          <div class="header-right">
            <div id="estop-indicator" class="estop-pill safe">
              <span class="pulse-dot"></span>
              <span id="estop-text">EmergencyStop Disengaged</span>
            </div>
            <button id="btn-refresh-adaptation" class="btn btn-secondary btn-sm">
              <span class="icon">↻</span> Refresh
            </button>
            <button id="btn-new-program" class="btn btn-primary btn-sm">
              <span class="icon">+</span> New Initiative
            </button>
          </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="console-tabs" role="tablist">
          <button class="tab-btn active" data-tab="dashboard">Dashboard</button>
          <button class="tab-btn" data-tab="experiments">Experiment Inbox</button>
          <button class="tab-btn" data-tab="hypotheses">Hypothesis Explorer</button>
          <button class="tab-btn" data-tab="comparisons">Variant Comparison</button>
          <button class="tab-btn" data-tab="gates">Safety & Security Gates</button>
          <button class="tab-btn" data-tab="evidence">Sealed Evidence</button>
          <button class="tab-btn" data-tab="evolution">Governed Evolution</button>
        </nav>

        <!-- Main Viewport for Active Tab -->
        <main class="tab-content" id="adaptation-tab-content">
          <div class="loading-spinner">Loading adaptation data...</div>
        </main>
      </div>
    `;

    this._wireEvents();
  }

  _wireEvents() {
    const root = this.container.querySelector('#adaptation-console-root');
    if (!root) return;

    // Tab buttons
    root.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        root.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeTab = btn.dataset.tab;
        this.renderActiveTab();
      });
    });

    // Refresh
    const refreshBtn = root.querySelector('#btn-refresh-adaptation');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    // New Program Modal Trigger
    const newProgBtn = root.querySelector('#btn-new-program');
    if (newProgBtn) {
      newProgBtn.addEventListener('click', () => this.openNewProgramModal());
    }
  }

  async loadData() {
    this.loading = true;
    try {
      const [dash, progs, exps, hyps, cmps, props, css, gates] = await Promise.all([
        adaptationApi.getDashboard().catch(() => ({})),
        adaptationApi.listPrograms().catch(() => []),
        adaptationApi.listExperiments().catch(() => []),
        adaptationApi.listHypotheses().catch(() => []),
        adaptationApi.listComparisons().catch(() => []),
        adaptationApi.listProposals().catch(() => []),
        adaptationApi.listChangesets().catch(() => []),
        adaptationApi.listGates().catch(() => []),
      ]);

      this.dashboardData = dash;
      this.programs = progs || [];
      this.experiments = exps || [];
      this.hypotheses = hyps || [];
      this.comparisons = cmps || [];
      this.proposals = props || [];
      this.changesets = css || [];
      this.gates = gates || [];

      // Update EmergencyStop pill
      const estopPill = this.container.querySelector('#estop-indicator');
      const estopText = this.container.querySelector('#estop-text');
      if (estopPill && estopText) {
        if (dash.emergency_stop_active) {
          estopPill.className = 'estop-pill danger';
          estopText.textContent = 'EmergencyStop ACTIVE (Blocked)';
        } else {
          estopPill.className = 'estop-pill safe';
          estopText.textContent = 'EmergencyStop Disengaged';
        }
      }

      this.renderActiveTab();
    } catch (err) {
      console.error('Failed to load adaptation data:', err);
      this.error = err.message;
      this.renderError();
    } finally {
      this.loading = false;
    }
  }

  renderActiveTab() {
    const tabContent = this.container.querySelector('#adaptation-tab-content');
    if (!tabContent) return;

    switch (this.activeTab) {
      case 'dashboard':
        tabContent.innerHTML = this.renderDashboardTab();
        break;
      case 'experiments':
        tabContent.innerHTML = this.renderExperimentsTab();
        this._wireExperimentActions(tabContent);
        break;
      case 'hypotheses':
        tabContent.innerHTML = this.renderHypothesesTab();
        break;
      case 'comparisons':
        tabContent.innerHTML = this.renderComparisonsTab();
        break;
      case 'gates':
        tabContent.innerHTML = this.renderGatesTab();
        break;
      case 'evidence':
        tabContent.innerHTML = this.renderEvidenceTab();
        break;
      case 'evolution':
        tabContent.innerHTML = this.renderEvolutionTab();
        this._wireEvolutionActions(tabContent);
        break;
      default:
        tabContent.innerHTML = '<p>Select a tab above.</p>';
    }
  }

  // ============================================================================
  // TAB 1: DASHBOARD
  // ============================================================================
  renderDashboardTab() {
    const d = this.dashboardData || {};
    return `
      <div class="dashboard-grid">
        <!-- KPI Cards Grid -->
        <div class="kpi-row">
          <div class="kpi-card active-card">
            <div class="kpi-title">ACTIVE EXPERIMENTS</div>
            <div class="kpi-value">${d.active_experiments || 0}</div>
            <div class="kpi-sub">Controlled Sandboxes</div>
          </div>
          <div class="kpi-card blocked-card">
            <div class="kpi-title">BLOCKED</div>
            <div class="kpi-value">${d.blocked_count || 0}</div>
            <div class="kpi-sub">Firewall / Gate Stops</div>
          </div>
          <div class="kpi-card failed-card">
            <div class="kpi-title">FAILED</div>
            <div class="kpi-value">${d.failed_count || 0}</div>
            <div class="kpi-sub">Negative Evidence</div>
          </div>
          <div class="kpi-card inconclusive-card">
            <div class="kpi-title">INCONCLUSIVE</div>
            <div class="kpi-value">${d.inconclusive_count || 0}</div>
            <div class="kpi-sub">Low Power / Missing Data</div>
          </div>
          <div class="kpi-card improving-card">
            <div class="kpi-title">IMPROVING</div>
            <div class="kpi-value">${d.improving_count || 0}</div>
            <div class="kpi-sub">Verified Candidates</div>
          </div>
          <div class="kpi-card regressing-card">
            <div class="kpi-title">REGRESSING</div>
            <div class="kpi-value">${d.regressing_count || 0}</div>
            <div class="kpi-sub">Regressions Prevented</div>
          </div>
          <div class="kpi-card review-card">
            <div class="kpi-title">AWAITING REVIEW</div>
            <div class="kpi-value">${d.awaiting_review_count || 0}</div>
            <div class="kpi-sub">Governance Queue</div>
          </div>
          <div class="kpi-card approval-card">
            <div class="kpi-title">AWAITING APPROVAL</div>
            <div class="kpi-value">${d.awaiting_approval_count || 0}</div>
            <div class="kpi-sub">ApprovalRegistry</div>
          </div>
          <div class="kpi-card validating-card">
            <div class="kpi-title">VALIDATING</div>
            <div class="kpi-value">${d.validating_count || 0}</div>
            <div class="kpi-sub">Canary & Pre-Rollout</div>
          </div>
        </div>

        <!-- Two-column Layout: Active Programs & Recent Experiments -->
        <div class="dash-columns">
          <div class="dash-col">
            <div class="section-card">
              <div class="section-header">
                <h3>Active Adaptation Initiatives</h3>
                <span class="badge-count">${this.programs.length}</span>
              </div>
              <div class="item-list">
                ${this.programs.length === 0 ? '<p class="empty-text">No active adaptation programs.</p>' : ''}
                ${this.programs.map((p) => `
                  <div class="list-item">
                    <div class="item-main">
                      <div class="item-title">${p.title}</div>
                      <div class="item-meta">
                        <span class="meta-tag cap-tag">${p.affected_capability}</span>
                        <span class="meta-tag">Baseline: ${p.baseline_id}</span>
                        <span class="meta-tag time-tag">${new Date(p.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                    <div class="item-status status-${p.status.toLowerCase()}">${p.status}</div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>

          <div class="dash-col">
            <div class="section-card">
              <div class="section-header">
                <h3>Recent Experiment Runs</h3>
                <span class="badge-count">${this.experiments.length}</span>
              </div>
              <div class="item-list">
                ${this.experiments.length === 0 ? '<p class="empty-text">No experiment runs recorded.</p>' : ''}
                ${this.experiments.map((r) => `
                  <div class="list-item">
                    <div class="item-main">
                      <div class="item-title">${r.id} (Stage ${r.stage_number})</div>
                      <div class="item-meta">
                        <span class="meta-tag env-tag">${r.environment}</span>
                        <span class="meta-tag">Samples: ${r.current_sample_count}/${r.target_sample_count}</span>
                        ${r.stop_reason ? `<span class="meta-tag reason-tag">${r.stop_reason}</span>` : ''}
                      </div>
                    </div>
                    <div class="item-status status-${r.status.toLowerCase()}">${r.status}</div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // ============================================================================
  // TAB 2: EXPERIMENT INBOX & ACTIONS
  // ============================================================================
  renderExperimentsTab() {
    return `
      <div class="tab-layout">
        <div class="toolbar-row">
          <div class="toolbar-left">
            <h2>Experiment Inbox</h2>
            <p class="section-desc">Inspect, start, stop, pause, and resume staged candidate evaluations.</p>
          </div>
        </div>

        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Program / Plan</th>
                <th>Stage</th>
                <th>Environment</th>
                <th>Status</th>
                <th>Samples</th>
                <th>Gates</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${this.experiments.length === 0 ? '<tr><td colspan="8" class="empty-cell">No experiments registered.</td></tr>' : ''}
              ${this.experiments.map((r) => `
                <tr>
                  <td class="font-mono"><strong>${r.id}</strong></td>
                  <td>${r.program_id}</td>
                  <td>Stage ${r.stage_number}</td>
                  <td><span class="badge env-badge">${r.environment}</span></td>
                  <td><span class="status-badge status-${r.status.toLowerCase()}">${r.status}</span></td>
                  <td>${r.current_sample_count} / ${r.target_sample_count}</td>
                  <td>${r.passed_safety_gates ? '<span class="text-success">✓ Passed</span>' : '<span class="text-danger">✗ Violated</span>'}</td>
                  <td class="actions-cell">
                    ${r.status === 'RUNNING' ? `
                      <button class="btn btn-warning btn-xs btn-pause-exp" data-run-id="${r.id}">Pause</button>
                      <button class="btn btn-danger btn-xs btn-stop-exp" data-run-id="${r.id}">Stop</button>
                    ` : ''}
                    ${r.status === 'PAUSED' ? `
                      <button class="btn btn-primary btn-xs btn-resume-exp" data-run-id="${r.id}">Resume</button>
                      <button class="btn btn-danger btn-xs btn-stop-exp" data-run-id="${r.id}">Stop</button>
                    ` : ''}
                    ${r.status === 'COMPLETED' ? `
                      <button class="btn btn-secondary btn-xs btn-view-results" data-run-id="${r.id}">Results</button>
                    ` : ''}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  _wireExperimentActions(container) {
    container.querySelectorAll('.btn-pause-exp').forEach((b) => {
      b.addEventListener('click', async () => {
        await adaptationApi.stopExperiment(b.dataset.runId, 'Paused from console');
        await this.loadData();
      });
    });

    container.querySelectorAll('.btn-stop-exp').forEach((b) => {
      b.addEventListener('click', async () => {
        await adaptationApi.stopExperiment(b.dataset.runId, 'Stopped from console');
        await this.loadData();
      });
    });

    container.querySelectorAll('.btn-view-results').forEach((b) => {
      b.addEventListener('click', () => {
        this.activeTab = 'comparisons';
        this.renderActiveTab();
      });
    });
  }

  // ============================================================================
  // TAB 3: HYPOTHESIS EXPLORER
  // ============================================================================
  renderHypothesesTab() {
    return `
      <div class="tab-layout">
        <div class="toolbar-row">
          <div>
            <h2>Hypothesis Explorer</h2>
            <p class="section-desc">Explicit IF-THEN-BECAUSE hypotheses with measurable outcome criteria and falsification boundaries.</p>
          </div>
        </div>

        <div class="hypothesis-grid">
          ${this.hypotheses.length === 0 ? '<p class="empty-text">No hypotheses formulated.</p>' : ''}
          ${this.hypotheses.map((h) => `
            <div class="hypothesis-card">
              <div class="hyp-header">
                <span class="font-mono hyp-id">${h.id}</span>
                <span class="confidence-badge">Confidence: ${(h.confidence * 100).toFixed(0)}%</span>
              </div>
              <div class="hyp-body">
                <div class="hyp-clause if-clause">
                  <strong>IF:</strong> <span>${h.condition_change}</span>
                </div>
                <div class="hyp-clause then-clause">
                  <strong>THEN:</strong> <span>${h.expected_outcome}</span>
                </div>
                <div class="hyp-clause because-clause">
                  <strong>BECAUSE:</strong> <span>${h.evidence_reasoning}</span>
                </div>
              </div>
              ${h.falsification_criteria && h.falsification_criteria.length > 0 ? `
                <div class="falsify-box">
                  <strong>Falsification Criteria:</strong>
                  <ul>
                    ${h.falsification_criteria.map((c) => `<li>${c}</li>`).join('')}
                  </ul>
                </div>
              ` : ''}
              ${h.measurable_outcomes ? `
                <div class="metrics-tags">
                  ${Object.entries(h.measurable_outcomes).map(([k, v]) => `
                    <span class="metric-tag">${k}: ${v}</span>
                  `).join('')}
                </div>
              ` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // ============================================================================
  // TAB 4: VARIANT COMPARISONS
  // ============================================================================
  renderComparisonsTab() {
    return `
      <div class="tab-layout">
        <div class="toolbar-row">
          <div>
            <h2>Variant Comparisons</h2>
            <p class="section-desc">Tri-condition comparison: NO_ACTION vs BASELINE vs CANDIDATE across 10 non-collapsible dimensions.</p>
          </div>
        </div>

        <div class="comparisons-list">
          ${this.comparisons.length === 0 ? '<p class="empty-text">No experiment comparisons available yet.</p>' : ''}
          ${this.comparisons.map((c) => `
            <div class="comparison-card">
              <div class="cmp-header">
                <span class="font-mono cmp-id">${c.id} (Run: ${c.run_id})</span>
                <span class="verdict-pill verdict-${c.verdict.toLowerCase()}">${c.verdict}</span>
              </div>
              <p class="cmp-rationale"><strong>Verdict Rationale:</strong> ${c.rationale}</p>
              
              <!-- Metrics Table -->
              <table class="dimension-table">
                <thead>
                  <tr>
                    <th>Dimension</th>
                    <th>Baseline</th>
                    <th>Candidate</th>
                    <th>Delta</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${c.dimension_scores ? Object.entries(c.dimension_scores).map(([dim, val]) => {
                    const delta = val.delta !== undefined ? val.delta : (val.candidate - val.baseline);
                    const isPositive = delta > 0;
                    const deltaCls = isPositive ? 'text-success' : (delta < 0 ? 'text-danger' : '');
                    return `
                      <tr>
                        <td><strong>${dim.toUpperCase()}</strong></td>
                        <td>${val.baseline !== undefined ? val.baseline.toFixed(3) : '-'}</td>
                        <td>${val.candidate !== undefined ? val.candidate.toFixed(3) : '-'}</td>
                        <td class="${deltaCls}">${delta >= 0 ? '+' : ''}${delta.toFixed(3)}</td>
                        <td>${isPositive ? '✓ Improved' : (delta < 0 ? '⚠ Regressed' : 'Parity')}</td>
                      </tr>
                    `;
                  }).join('') : '<tr><td colspan="5">No dimension scores recorded.</td></tr>'}
                </tbody>
              </table>

              <div class="cmp-footer">
                <span class="meta-tag">Sample Size: ${c.sample_size}</span>
                <span class="meta-tag">Causal Attribution: ${c.causal_attribution_verified ? '✓ Verified' : 'Unconfirmed'}</span>
                <span class="meta-tag">World-State: ${c.world_state_verified ? '✓ Reconciled' : '⚠ Drift Detected'}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // ============================================================================
  // TAB 5: GATES
  // ============================================================================
  renderGatesTab() {
    return `
      <div class="tab-layout">
        <div class="toolbar-row">
          <div>
            <h2>Safety & Security Gates</h2>
            <p class="section-desc">Fail-closed evaluation gates and EmergencyStop protections governing experiment runs.</p>
          </div>
        </div>

        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Gate Name</th>
                <th>Run ID</th>
                <th>Status</th>
                <th>Measured Value</th>
                <th>Threshold</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              ${this.gates.length === 0 ? '<tr><td colspan="6" class="empty-cell">No gates evaluated yet.</td></tr>' : ''}
              ${this.gates.map((g) => `
                <tr>
                  <td><strong>${g.gate_name}</strong></td>
                  <td class="font-mono">${g.run_id}</td>
                  <td>${g.passed ? '<span class="status-badge status-successful">PASS</span>' : '<span class="status-badge status-failed">FAIL</span>'}</td>
                  <td>${g.measured_value !== null ? g.measured_value.toFixed(2) : '-'}</td>
                  <td>${g.threshold !== null ? g.threshold.toFixed(2) : '-'}</td>
                  <td>${g.reason}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // ============================================================================
  // TAB 6: SEALED EVIDENCE
  // ============================================================================
  renderEvidenceTab() {
    return `
      <div class="tab-layout">
        <div class="toolbar-row">
          <div>
            <h2>Sealed Evidence Explorer</h2>
            <p class="section-desc">Cryptographically sealed evidence bundles packaging hypotheses, observation traces, and metric deltas.</p>
          </div>
        </div>

        <div class="timeline-container">
          ${this.comparisons.map((c) => `
            <div class="timeline-item">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <div class="timeline-header">
                  <span class="timeline-title">Evidence for Run: ${c.run_id}</span>
                  <span class="badge">${c.verdict}</span>
                </div>
                <p><strong>Rationale:</strong> ${c.rationale}</p>
                <div class="font-mono text-muted text-sm">
                  Causal Attribution: ${c.causal_explanation || 'Verified candidate intervention'}
                </div>
                <div class="font-mono text-muted text-sm">
                  World-State: ${c.world_state_drift_summary || 'Postconditions satisfied without drift.'}
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // ============================================================================
  // TAB 7: GOVERNED EVOLUTION
  // ============================================================================
  renderEvolutionTab() {
    return `
      <div class="tab-layout">
        <div class="toolbar-row">
          <div>
            <h2>Governed Evolution Proposals</h2>
            <p class="section-desc">Evidence-backed capability changes awaiting review, approval, and canary rollout.</p>
          </div>
        </div>

        <div class="proposals-list">
          ${this.proposals.length === 0 ? '<p class="empty-text">No evolution proposals submitted.</p>' : ''}
          ${this.proposals.map((p) => `
            <div class="proposal-card">
              <div class="prop-header">
                <div>
                  <h3 class="prop-title">${p.title}</h3>
                  <div class="prop-sub">
                    Capability: <strong>${p.affected_capability}</strong> (${p.current_version} → ${p.target_version})
                  </div>
                </div>
                <span class="status-badge status-${p.status.toLowerCase()}">${p.status}</span>
              </div>

              <p class="prop-desc">${p.evidence_summary}</p>

              <div class="prop-details-grid">
                <div class="prop-detail">
                  <strong>Rollback Plan:</strong>
                  <span>${p.rollback_plan}</span>
                </div>
                <div class="prop-detail">
                  <strong>Deployment Scope:</strong>
                  <span>${p.deployment_scope}</span>
                </div>
                <div class="prop-detail">
                  <strong>Confidence:</strong>
                  <span>${(p.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>

              <div class="prop-actions">
                ${p.status === 'SUBMITTED' || p.status === 'UNDER_REVIEW' ? `
                  <button class="btn btn-success btn-sm btn-approve-prop" data-prop-id="${p.id}">Approve Proposal</button>
                  <button class="btn btn-danger btn-sm btn-reject-prop" data-prop-id="${p.id}">Reject Proposal</button>
                ` : ''}
                <button class="btn btn-secondary btn-sm btn-validate-prop" data-prop-id="${p.id}">Run Pre-Rollout Validation</button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _wireEvolutionActions(container) {
    container.querySelectorAll('.btn-approve-prop').forEach((b) => {
      b.addEventListener('click', async () => {
        const propId = b.dataset.propId;
        const rationale = prompt('Enter approval rationale for this evolution proposal:');
        if (!rationale) return;
        await adaptationApi.reviewProposal(propId, {
          reviewer: 'Console Operator',
          status: 'APPROVED',
          rationale,
        });
        await this.loadData();
      });
    });

    container.querySelectorAll('.btn-reject-prop').forEach((b) => {
      b.addEventListener('click', async () => {
        const propId = b.dataset.propId;
        const rationale = prompt('Enter rejection rationale for this evolution proposal:');
        if (!rationale) return;
        await adaptationApi.reviewProposal(propId, {
          reviewer: 'Console Operator',
          status: 'REJECTED',
          rationale,
        });
        await this.loadData();
      });
    });

    container.querySelectorAll('.btn-validate-prop').forEach((b) => {
      b.addEventListener('click', async () => {
        const propId = b.dataset.propId;
        const cs = this.changesets.find((c) => c.proposal_id === propId) || { id: 'cs_default' };
        alert(`Initiating multi-suite pre-rollout validation for proposal ${propId}...`);
        await adaptationApi.validateChangeset({
          proposal_id: propId,
          changeset_id: cs.id,
          include_holdout: true,
        });
        await this.loadData();
      });
    });
  }

  // ============================================================================
  // MODAL: NEW ADAPTATION INITIATIVE
  // ============================================================================
  openNewProgramModal() {
    const title = prompt('Enter Initiative Title:');
    if (!title) return;
    const cap = prompt('Enter Affected Capability (e.g. web_search, context_engine):');
    if (!cap) return;

    adaptationApi.createProgram({
      title,
      objective: `Remediate regressions and safely optimize ${cap}`,
      problem_statement: `Continuous evaluation observed optimization opportunities for ${cap}`,
      affected_capability: cap,
    }).then(() => this.loadData());
  }

  renderError() {
    const tabContent = this.container.querySelector('#adaptation-tab-content');
    if (tabContent) {
      tabContent.innerHTML = `
        <div class="error-banner">
          <h3>Failed to load Adaptation data</h3>
          <p>${this.error || 'Unknown error occurred.'}</p>
          <button class="btn btn-secondary btn-sm" onclick="location.reload()">Reload</button>
        </div>
      `;
    }
  }
}

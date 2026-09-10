/**
 * Kairo Continuous Learning, Experience Consolidation & Strategy Engine (Task 43 + Task 52)
 * Displays Governed Strategies, Multi-Factor Ranking, Tool Reliability,
 * Clustered Failure Signatures, Canary Experimentation, Empirical Lessons,
 * Reusable Workflows, Decision Heuristics, Safe Experience Replay, and Invariant Boundaries.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class LearningView {
  constructor(container) {
    this.container = container;
    this.stats = null;
    this.continuousMetrics = null;
    this.strategies = [];
    this.experiences = [];
    this.failurePatterns = [];
    this.experiments = [];
    this.recommendations = [];
    this.lessons = [];
    this.workflows = [];
    this.heuristics = [];
    this.governancePolicy = null;
    this.activeTab = 'strategies';
    this.isLoading = false;
  }

  formatPercent(val) {
    if (val === null || val === undefined) return '0.0%';
    return (val * 100).toFixed(1) + '%';
  }

  formatLatency(ms) {
    if (ms === null || ms === undefined) return '0ms';
    if (ms >= 1000) return (ms / 1000).toFixed(2) + 's';
    return Math.round(ms) + 'ms';
  }

  formatCost(dollars) {
    if (dollars === null || dollars === undefined) return '$0.0000';
    return '$' + Number(dollars).toFixed(4);
  }

  async render() {
    this.container.innerHTML = `
      <div class="learning-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Continuous Learning & Experience Consolidation Engine</h1>
            <p class="page-subtitle">Evidence-grounded self-improvement, lesson extraction, reusable workflows, experience replay, and invariant-governed adaptation</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-learning-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="new-strategy-btn">
              + Propose Strategy
            </button>
          </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <div class="metrics-grid" id="learning-kpis">
          <div class="metric-card">
            <span class="metric-label">Active Strategies</span>
            <span class="metric-value text-primary" id="kpi-active-strategies">0</span>
            <span class="metric-trend">Governed Execution</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Verified Experiences</span>
            <span class="metric-value text-success" id="kpi-verified-exp">0</span>
            <span class="metric-trend">Empirical Grounding</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Extracted Lessons</span>
            <span class="metric-value text-info" id="kpi-extracted-lessons">0</span>
            <span class="metric-trend">Non-Overgeneralized</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Workflows & Heuristics</span>
            <span class="metric-value text-warning" id="kpi-workflows-heuristics">0</span>
            <span class="metric-trend">Policy-Bounded</span>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-nav">
          <button class="tab-btn active" data-tab="strategies">Strategy Performance</button>
          <button class="tab-btn" data-tab="lessons">Extracted Lessons</button>
          <button class="tab-btn" data-tab="workflows">Workflows & Heuristics</button>
          <button class="tab-btn" data-tab="reliability">Tool & Provider Reliability</button>
          <button class="tab-btn" data-tab="failures">Failure Clusters</button>
          <button class="tab-btn" data-tab="experiments">Canary Trials</button>
          <button class="tab-btn" data-tab="governance">Safety Governance</button>
        </div>

        <!-- Tab Content Panes -->
        <div class="tab-content" style="margin-top: 16px;">
          <!-- Strategies Pane -->
          <div class="tab-pane active" id="learning-tab-strategies">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Governed Strategies & Multi-Factor Ranks</h3>
                <span class="badge badge-info" id="strategies-count-badge">0 strategies</span>
              </div>
              <div class="table-responsive" style="padding: 12px;">
                <table class="data-table" id="strategies-table" style="width: 100%;">
                  <thead>
                    <tr>
                      <th>Strategy ID</th>
                      <th>Domain</th>
                      <th>Description</th>
                      <th>Status</th>
                      <th>Verif Rate</th>
                      <th>Success Rate</th>
                      <th>Latency</th>
                      <th>Samples</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody id="strategies-table-body">
                    <tr><td colspan="9" class="text-center text-muted">No strategies registered yet.</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Lessons Pane (Task 52) -->
          <div class="tab-pane" id="learning-tab-lessons" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Empirical Continuous Lessons & Scoped Grounding</h3>
                <span class="badge badge-info" id="lessons-count-badge">0 lessons</span>
              </div>
              <div class="table-responsive" style="padding: 12px;">
                <table class="data-table" id="lessons-table" style="width: 100%;">
                  <thead>
                    <tr>
                      <th>Lesson ID</th>
                      <th>Type</th>
                      <th>Statement</th>
                      <th>Scope</th>
                      <th>Status</th>
                      <th>Confidence</th>
                      <th>Evidence Count</th>
                    </tr>
                  </thead>
                  <tbody id="lessons-table-body">
                    <tr><td colspan="7" class="text-center text-muted">No empirical lessons extracted yet.</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Workflows & Heuristics Pane (Task 52) -->
          <div class="tab-pane" id="learning-tab-workflows" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Reusable Workflow Patterns & Decision Heuristics</h3>
              </div>
              <div style="padding: 16px;">
                <h4 style="margin-bottom: 8px;">Promoted Workflows</h4>
                <div id="workflows-container">
                  <p class="text-muted">No reusable workflow patterns promoted yet.</p>
                </div>
                <hr style="margin: 16px 0; border: none; border-top: 1px solid var(--border-color, #e0e0e0);" />
                <h4 style="margin-bottom: 8px;">Validated Planning Heuristics</h4>
                <div id="heuristics-container">
                  <p class="text-muted">No validated heuristics registered yet.</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Reliability Pane -->
          <div class="tab-pane" id="learning-tab-reliability" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Empirical Tool & Provider Reliability Matrix</h3>
              </div>
              <div id="reliability-container" style="padding: 16px;">
                <p class="text-muted">Tracking successes, timeouts, and unknown outcome rates across tool registry and model providers.</p>
              </div>
            </div>
          </div>

          <!-- Failures Pane -->
          <div class="tab-pane" id="learning-tab-failures" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Recurring Failure Signatures & Pre-Flight Warnings</h3>
              </div>
              <div id="failures-container" style="padding: 16px;">
                <p class="text-muted">No active failure clusters detected.</p>
              </div>
            </div>
          </div>

          <!-- Experiments Pane -->
          <div class="tab-pane" id="learning-tab-experiments" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Controlled A/B Canary Strategy Experiments</h3>
              </div>
              <div id="experiments-container" style="padding: 16px;">
                <p class="text-muted">No canary trials active.</p>
              </div>
            </div>
          </div>

          <!-- Governance Pane (Task 52) -->
          <div class="tab-pane" id="learning-tab-governance" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Policy Boundaries & Invariant Safeguards</h3>
              </div>
              <div id="governance-container" style="padding: 16px;">
                <div class="alert alert-info" style="margin-bottom: 12px;">
                  <strong>Safety Invariant Guarantee:</strong> Continuous learning is strictly bounded. Security policies, authorization, approval gates, audit trails, and foundation model weights can never be automatically modified or learned away.
                </div>
                <div id="governance-policy-details">
                  <p class="text-muted">Loading governance policy...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  }

  bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-learning-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    const tabs = this.container.querySelectorAll('.tab-btn');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        const tabName = tab.getAttribute('data-tab');
        this.activeTab = tabName;

        const panes = this.container.querySelectorAll('.tab-pane');
        panes.forEach((p) => (p.style.display = 'none'));
        const activePane = this.container.querySelector(`#learning-tab-${tabName}`);
        if (activePane) activePane.style.display = 'block';
      });
    });
  }

  async loadData() {
    try {
      this.isLoading = true;
      const [stats, strategies, failures, experiments, metrics, lessons, workflows, heuristics, gov] = await Promise.all([
        Endpoints.getLearningStats().catch(() => null),
        Endpoints.listLearningStrategies().catch(() => []),
        Endpoints.listLearningFailures().catch(() => []),
        Endpoints.listLearningExperiments().catch(() => []),
        Endpoints.getContinuousLearningMetrics().catch(() => null),
        Endpoints.listLearningLessons().catch(() => []),
        Endpoints.listLearningWorkflows().catch(() => []),
        Endpoints.listLearningHeuristics().catch(() => []),
        Endpoints.getLearningGovernancePolicy().catch(() => null),
      ]);

      if (stats) {
        this.stats = stats;
        this.updateKpis(stats, metrics, lessons, workflows, heuristics);
      }
      if (Array.isArray(strategies)) {
        this.strategies = strategies;
        this.renderStrategiesTable(strategies);
      }
      if (Array.isArray(failures)) {
        this.failurePatterns = failures;
      }
      if (Array.isArray(experiments)) {
        this.experiments = experiments;
      }
      if (Array.isArray(lessons)) {
        this.lessons = lessons;
        this.renderLessonsTable(lessons);
      }
      if (Array.isArray(workflows)) {
        this.workflows = workflows;
        this.renderWorkflows(workflows);
      }
      if (Array.isArray(heuristics)) {
        this.heuristics = heuristics;
        this.renderHeuristics(heuristics);
      }
      if (gov) {
        this.governancePolicy = gov;
        this.renderGovernance(gov);
      }
    } catch (err) {
      console.warn('Could not load learning engine data:', err);
    } finally {
      this.isLoading = false;
    }
  }

  updateKpis(stats, metrics, lessons = [], workflows = [], heuristics = []) {
    const stratEl = this.container.querySelector('#kpi-active-strategies');
    const expEl = this.container.querySelector('#kpi-verified-exp');
    const lessonEl = this.container.querySelector('#kpi-extracted-lessons');
    const wfEl = this.container.querySelector('#kpi-workflows-heuristics');

    if (stratEl) stratEl.textContent = stats?.total_strategies || 0;
    if (expEl) expEl.textContent = metrics?.total_experiences || stats?.total_experiences || 0;
    if (lessonEl) lessonEl.textContent = metrics?.total_lessons || lessons.length || 0;
    if (wfEl) wfEl.textContent = (metrics?.total_workflows || workflows.length) + ' / ' + (metrics?.total_heuristics || heuristics.length);
  }

  renderStrategiesTable(strategies) {
    const tbody = this.container.querySelector('#strategies-table-body');
    const badge = this.container.querySelector('#strategies-count-badge');
    if (badge) badge.textContent = `${strategies.length} strategies`;

    if (!tbody) return;
    if (strategies.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No strategies registered yet.</td></tr>';
      return;
    }

    tbody.innerHTML = strategies.map((s) => {
      const statusBadge = this.getStatusBadge(s.status);
      return `
        <tr>
          <td><code>${escapeHtml(s.strategy_id)}</code></td>
          <td><span class="badge badge-outline">${escapeHtml(s.domain)}</span></td>
          <td>${escapeHtml(s.description)}</td>
          <td>${statusBadge}</td>
          <td><strong>${(s.verification_rate * 100).toFixed(0)}%</strong></td>
          <td>${(s.success_rate * 100).toFixed(0)}%</td>
          <td>${s.latency_ms.toFixed(0)}ms</td>
          <td>${s.sample_size} runs</td>
          <td>
            ${s.status === 'CANDIDATE' ? `<button class="btn btn-sm btn-primary" data-action="promote" data-id="${escapeHtml(s.strategy_id)}">Promote</button>` : ''}
            ${s.status === 'ACTIVE' ? `<button class="btn btn-sm btn-outline-danger" data-action="rollback" data-id="${escapeHtml(s.strategy_id)}">Rollback</button>` : ''}
          </td>
        </tr>
      `;
    }).join('');
  }

  renderLessonsTable(lessons) {
    const tbody = this.container.querySelector('#lessons-table-body');
    const badge = this.container.querySelector('#lessons-count-badge');
    if (badge) badge.textContent = `${lessons.length} lessons`;

    if (!tbody) return;
    if (lessons.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No empirical lessons extracted yet.</td></tr>';
      return;
    }

    tbody.innerHTML = lessons.map((l) => {
      return `
        <tr>
          <td><code>${escapeHtml(l.lesson_id)}</code></td>
          <td><span class="badge badge-outline">${escapeHtml(l.lesson_type || 'PATTERN')}</span></td>
          <td>${escapeHtml(l.statement)}</td>
          <td><span class="badge badge-secondary">${escapeHtml(l.scope || 'PROJECT')}</span></td>
          <td>${this.getStatusBadge(l.status)}</td>
          <td><strong>${((l.confidence || 0) * 100).toFixed(0)}%</strong></td>
          <td>${(l.evidence || []).length} items</td>
        </tr>
      `;
    }).join('');
  }

  renderWorkflows(workflows) {
    const el = this.container.querySelector('#workflows-container');
    if (!el) return;
    if (!workflows || workflows.length === 0) {
      el.innerHTML = '<p class="text-muted">No reusable workflow patterns promoted yet.</p>';
      return;
    }
    el.innerHTML = workflows.map((wf) => `
      <div style="padding: 8px 12px; border: 1px solid var(--border-color, #eee); border-radius: 4px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <strong>${escapeHtml(wf.name)}</strong>
          <span class="badge badge-success">${escapeHtml(wf.status || 'ACTIVE')}</span>
        </div>
        <div style="font-size: 0.85em; color: var(--text-muted, #666); margin-top: 4px;">
          ${(wf.steps || []).length} steps | Success Count: ${wf.success_count || 0}
        </div>
      </div>
    `).join('');
  }

  renderHeuristics(heuristics) {
    const el = this.container.querySelector('#heuristics-container');
    if (!el) return;
    if (!heuristics || heuristics.length === 0) {
      el.innerHTML = '<p class="text-muted">No validated heuristics registered yet.</p>';
      return;
    }
    el.innerHTML = heuristics.map((h) => `
      <div style="padding: 8px 12px; border: 1px solid var(--border-color, #eee); border-radius: 4px; margin-bottom: 8px;">
        <div><strong>Condition:</strong> <code>${escapeHtml(h.condition)}</code></div>
        <div style="margin-top: 4px;"><strong>Recommendation:</strong> ${escapeHtml(h.recommendation)}</div>
        <div style="font-size: 0.85em; color: var(--text-muted, #666); margin-top: 4px;">
          Scope: ${escapeHtml(h.scope || 'TASK')} | Confidence: ${((h.confidence || 0) * 100).toFixed(0)}%
        </div>
      </div>
    `).join('');
  }

  renderGovernance(gov) {
    const el = this.container.querySelector('#governance-policy-details');
    if (!el) return;
    el.innerHTML = `
      <ul style="list-style: none; padding: 0;">
        <li style="margin-bottom: 6px;"><strong>Max Auto Scope:</strong> <code>${escapeHtml(gov.scope || 'PROJECT')}</code></li>
        <li style="margin-bottom: 6px;"><strong>Allowed Adaptations:</strong> ${(gov.allowed_adaptations || []).map(a => `<span class="badge badge-outline">${escapeHtml(a)}</span>`).join(' ')}</li>
        <li style="margin-bottom: 6px;"><strong>Approval Required for Model Changes:</strong> ${gov.approval_required_for_models ? '<span class="badge badge-warning">YES</span>' : '<span class="badge badge-secondary">NO</span>'}</li>
        <li style="margin-bottom: 6px;"><strong>Shadow Mode Active:</strong> ${gov.shadow_mode_required ? '<span class="badge badge-info">ENABLED</span>' : '<span class="badge badge-secondary">DISABLED</span>'}</li>
        <li style="margin-bottom: 6px;"><strong>Rollback Degradation Threshold:</strong> <code>${(gov.rollback_degradation_threshold || 0.1) * 100}%</code></li>
      </ul>
    `;
  }

  getStatusBadge(status) {
    switch (status) {
      case 'ACTIVE':
        return '<span class="badge badge-success">ACTIVE</span>';
      case 'EXPERIMENTAL':
        return '<span class="badge badge-info">EXPERIMENTAL</span>';
      case 'CANDIDATE':
        return '<span class="badge badge-warning">CANDIDATE</span>';
      case 'WEAKENED':
        return '<span class="badge badge-warning">WEAKENED</span>';
      case 'SUPERSEDED':
      case 'DEPRECATED':
        return '<span class="badge badge-secondary">' + escapeHtml(status) + '</span>';
      case 'ROLLED_BACK':
      case 'BLOCKED':
      case 'REJECTED':
        return '<span class="badge badge-danger">' + escapeHtml(status) + '</span>';
      default:
        return '<span class="badge badge-secondary">' + escapeHtml(status || 'UNKNOWN') + '</span>';
    }
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

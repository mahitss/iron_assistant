/**
 * Kairo Adaptive Learning & Strategy Optimization View (Task 43)
 * Displays Governed Strategies, Multi-Factor Ranking, Tool Reliability,
 * Clustered Failure Signatures, and Canary Experimentation.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class LearningView {
  constructor(container) {
    this.container = container;
    this.stats = null;
    this.strategies = [];
    this.experiences = [];
    this.failurePatterns = [];
    this.experiments = [];
    this.recommendations = [];
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
            <h1 class="page-title">Adaptive Learning & Strategy Optimization</h1>
            <p class="page-subtitle">Evidence-grounded self-improvement, deterministic strategy ranking, tool reliability, and safe governed promotion</p>
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
            <span class="metric-label">Failure Patterns</span>
            <span class="metric-value text-warning" id="kpi-failure-patterns">0</span>
            <span class="metric-trend">Clustered Signatures</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Canary Experiments</span>
            <span class="metric-value text-info" id="kpi-canary-exp">0</span>
            <span class="metric-trend">A/B Controlled Trials</span>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-nav">
          <button class="tab-btn active" data-tab="strategies">Strategy Performance</button>
          <button class="tab-btn" data-tab="reliability">Tool & Provider Reliability</button>
          <button class="tab-btn" data-tab="failures">Failure Clusters & Warnings</button>
          <button class="tab-btn" data-tab="experiments">Canary Experiments</button>
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
      const [stats, strategies, failures, experiments] = await Promise.all([
        Endpoints.getLearningStats().catch(() => null),
        Endpoints.listLearningStrategies().catch(() => []),
        Endpoints.listLearningFailures().catch(() => []),
        Endpoints.listLearningExperiments().catch(() => []),
      ]);

      if (stats) {
        this.stats = stats;
        this.updateKpis(stats);
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
    } catch (err) {
      console.warn('Could not load learning engine data:', err);
    } finally {
      this.isLoading = false;
    }
  }

  updateKpis(stats) {
    const stratEl = this.container.querySelector('#kpi-active-strategies');
    const expEl = this.container.querySelector('#kpi-verified-exp');
    const failEl = this.container.querySelector('#kpi-failure-patterns');
    const canEl = this.container.querySelector('#kpi-canary-exp');

    if (stratEl) stratEl.textContent = stats.total_strategies || 0;
    if (expEl) expEl.textContent = stats.total_experiences || 0;
    if (failEl) failEl.textContent = stats.total_failure_patterns || 0;
    if (canEl) canEl.textContent = stats.total_experiments || 0;
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

  getStatusBadge(status) {
    switch (status) {
      case 'ACTIVE':
        return '<span class="badge badge-success">ACTIVE</span>';
      case 'EXPERIMENTAL':
        return '<span class="badge badge-info">EXPERIMENTAL</span>';
      case 'CANDIDATE':
        return '<span class="badge badge-warning">CANDIDATE</span>';
      case 'ROLLED_BACK':
      case 'BLOCKED':
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

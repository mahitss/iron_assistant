/**
 * Kairo Cognitive Planning & Adaptive Decision Engine View (Task 41)
 * Displays structured goals, execution DAGs, step verifications, plan diffs, and decision rationales.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class CognitionView {
  constructor(container) {
    this.container = container;
    this.dashboardData = null;
    this.activeTab = 'plans';
    this.selectedPlan = null;
    this.isLoading = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="cognition-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Cognitive Planning & Adaptive Reasoning</h1>
            <p class="page-subtitle">Objective decomposition, dependency DAGs, independent verifications, and adaptive replanning</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-cognition-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="new-goal-btn">
              + New Goal
            </button>
          </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <div class="metrics-grid" id="cognition-kpis">
          <div class="metric-card">
            <span class="metric-label">Active Plans</span>
            <span class="metric-value text-primary" id="kpi-active-plans">0</span>
            <span class="metric-trend">Executing</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Completed Goals</span>
            <span class="metric-value text-success" id="kpi-completed-goals">0</span>
            <span class="metric-trend">Verified</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Waiting Approval</span>
            <span class="metric-value text-warning" id="kpi-waiting-approval">0</span>
            <span class="metric-trend">High Risk Gates</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Verification Coverage</span>
            <span class="metric-value text-info" id="kpi-verification-coverage">100%</span>
            <span class="metric-trend">Anti Self-Attestation</span>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs-nav" role="tablist" style="margin-top: 24px;">
          <button class="tab-btn active" data-tab="plans">Active Plans</button>
          <button class="tab-btn" data-tab="goals">Goals & Objectives</button>
          <button class="tab-btn" data-tab="templates">Approved Templates</button>
          <button class="tab-btn" data-tab="rationale">Decision Rationale</button>
        </div>

        <!-- Tab Content Area -->
        <div class="tab-content" style="margin-top: 16px;">
          <div id="cognition-tab-plans" class="tab-pane active">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Active Execution DAGs</h3>
              </div>
              <div class="table-responsive">
                <table class="data-table" id="plans-table">
                  <thead>
                    <tr>
                      <th>Plan ID</th>
                      <th>Version</th>
                      <th>Reasoning Mode</th>
                      <th>Risk Level</th>
                      <th>Status</th>
                      <th>Steps</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody id="plans-table-body">
                    <tr><td colspan="7" class="text-center text-muted" style="padding: 24px;">No active cognitive plans found. Create a goal to begin.</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div id="cognition-tab-goals" class="tab-pane" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Tracked Objectives</h3>
              </div>
              <div id="goals-list-container">
                <p class="text-muted" style="padding: 16px;">No tracked goals.</p>
              </div>
            </div>
          </div>

          <div id="cognition-tab-templates" class="tab-pane" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Approved Plan Templates</h3>
              </div>
              <div id="templates-list-container">
                <p class="text-muted" style="padding: 16px;">Loading verified templates...</p>
              </div>
            </div>
          </div>

          <div id="cognition-tab-rationale" class="tab-pane" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Explainable Decision Factors</h3>
              </div>
              <div id="rationale-container" style="padding: 16px;">
                <p class="text-muted">Select a step in an active plan to inspect structured rationale without raw chain-of-thought exposure.</p>
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
    const refreshBtn = this.container.querySelector('#refresh-cognition-btn');
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
        const activePane = this.container.querySelector(`#cognition-tab-${tabName}`);
        if (activePane) activePane.style.display = 'block';
      });
    });
  }

  async loadData() {
    try {
      this.isLoading = true;
      const data = await Endpoints.getCognitiveDashboard();
      if (data) {
        this.dashboardData = data;
        this.updateKpis(data);
      }
    } catch (err) {
      console.warn('Could not load cognitive dashboard data:', err);
    } finally {
      this.isLoading = false;
    }
  }

  updateKpis(data) {
    const activeEl = this.container.querySelector('#kpi-active-plans');
    const compEl = this.container.querySelector('#kpi-completed-goals');
    const waitEl = this.container.querySelector('#kpi-waiting-approval');

    if (activeEl) activeEl.textContent = data.active_plans || 0;
    if (compEl) compEl.textContent = data.completed_plans || 0;
    if (waitEl) waitEl.textContent = data.waiting_approval || 0;
  }
}

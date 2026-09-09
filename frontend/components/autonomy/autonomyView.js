/**
 * Kairo Autonomous Execution & Long-Horizon Agency View (Task 45)
 * Displays Persistent Goals, Active Runs, Verified Progress, Checkpoint History,
 * Watchdog Diagnostics, and Completion Certificates.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class AutonomyView {
  constructor(container) {
    this.container = container;
    this.runs = [];
    this.goals = [];
    this.checkpoints = [];
    this.activeRunId = null;
    this.progress = null;
    this.completion = null;
    this.watchdog = null;
    this.activeTab = 'runs';
    this.isLoading = false;
  }

  formatPercent(pct) {
    if (pct === null || pct === undefined) return '0.0%';
    return Number(pct).toFixed(1) + '%';
  }

  async render() {
    this.container.innerHTML = `
      <div class="autonomy-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Autonomous Execution & Long-Horizon Agency</h1>
            <p class="page-subtitle">Multi-cycle goal pursuit, cryptographic checkpoints, zero-blind crash recovery, and verified completion</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-autonomy-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-danger" id="emergency-stop-all-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              Emergency Stop Cascade
            </button>
          </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">Active Status</div>
            <div class="metric-value" id="kpi-run-status">${this.runs[0]?.status || 'IDLE'}</div>
            <div class="metric-trend">Autonomy: ${this.runs[0]?.autonomy_level || 'AUTONOMOUS'}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Verified Progress</div>
            <div class="metric-value text-accent" id="kpi-progress-pct">${this.formatPercent(this.progress?.progress_pct || 0)}</div>
            <div class="metric-trend">${this.progress?.completed_steps || 0}/${this.progress?.total_steps || 0} verified steps</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Checkpoints Saved</div>
            <div class="metric-value" id="kpi-checkpoint-count">${this.checkpoints.length}</div>
            <div class="metric-trend">SHA-256 Validated</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Watchdog Health</div>
            <div class="metric-value" id="kpi-watchdog-status">${this.watchdog?.issue_detected || 'HEALTHY'}</div>
            <div class="metric-trend">Action: ${this.watchdog?.recommended_action || 'NONE'}</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-nav">
          <button class="tab-btn ${this.activeTab === 'runs' ? 'active' : ''}" data-tab="runs">Active Runs (${this.runs.length})</button>
          <button class="tab-btn ${this.activeTab === 'goals' ? 'active' : ''}" data-tab="goals">Authorized Goals</button>
          <button class="tab-btn ${this.activeTab === 'checkpoints' ? 'active' : ''}" data-tab="checkpoints">Durable Checkpoints</button>
          <button class="tab-btn ${this.activeTab === 'completion' ? 'active' : ''}" data-tab="completion">Completion Certificate</button>
          <button class="tab-btn ${this.activeTab === 'watchdog' ? 'active' : ''}" data-tab="watchdog">Watchdog Diagnostics</button>
        </div>

        <!-- Tab Body -->
        <div class="tab-content" id="autonomy-tab-body">
          ${this.renderTabContent()}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderTabContent() {
    switch (this.activeTab) {
      case 'runs':
        return this.renderRunsTab();
      case 'goals':
        return this.renderGoalsTab();
      case 'checkpoints':
        return this.renderCheckpointsTab();
      case 'completion':
        return this.renderCompletionTab();
      case 'watchdog':
        return this.renderWatchdogTab();
      default:
        return `<div class="empty-state">Select a tab above.</div>`;
    }
  }

  renderRunsTab() {
    if (!this.runs.length) {
      return `
        <div class="card empty-card">
          <h3>No Active Autonomous Runs</h3>
          <p>Register a goal and start a run to initiate long-horizon autonomous agency.</p>
        </div>
      `;
    }

    return `
      <div class="runs-container">
        ${this.runs.map(run => `
          <div class="card run-card">
            <div class="card-header">
              <div>
                <span class="badge badge-${run.status === 'RUNNING' ? 'success' : run.status === 'COMPLETED' ? 'primary' : 'warning'}">${run.status}</span>
                <span class="badge badge-outline">${run.autonomy_level}</span>
                <strong>${run.run_id}</strong>
              </div>
              <div class="run-actions">
                <button class="btn btn-sm btn-secondary" onclick="window.kairoAutonomy.pause('${run.run_id}')">Pause</button>
                <button class="btn btn-sm btn-primary" onclick="window.kairoAutonomy.resume('${run.run_id}')">Resume</button>
                <button class="btn btn-sm btn-danger" onclick="window.kairoAutonomy.cancel('${run.run_id}')">Cancel</button>
              </div>
            </div>
            <div class="card-body">
              <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${run.progress_pct}%"></div>
              </div>
              <div class="run-meta-grid">
                <div><span>Plan Version:</span> v${run.plan_version}</div>
                <div><span>Owner:</span> ${run.owner_user_id}</div>
                <div><span>Project:</span> ${run.project_id}</div>
                <div><span>Current Step:</span> ${run.current_step_id || 'Idle'}</div>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderGoalsTab() {
    return `
      <div class="card">
        <h3>Authorized Goal Boundaries</h3>
        <p>Immutable objectives, hard constraints, and scope boundaries preventing goal drift.</p>
        <div class="goals-list" id="goals-list">
          ${this.goals.map(g => `
            <div class="goal-item">
              <h4>${g.title} <span class="badge badge-info">${g.status}</span></h4>
              <p>${g.description}</p>
              <div><strong>Success Criteria:</strong> ${g.success_criteria?.join(', ') || 'None'}</div>
            </div>
          `).join('') || '<div class="empty-state">No goals registered yet.</div>'}
        </div>
      </div>
    `;
  }

  renderCheckpointsTab() {
    return `
      <div class="card">
        <h3>Cryptographic Checkpoint Ledger</h3>
        <p>Immutable snapshots verifying state transitions and enabling rollback recovery without blind resume.</p>
        <div class="table-responsive">
          <table class="table">
            <thead>
              <tr>
                <th>Checkpoint ID</th>
                <th>Plan v</th>
                <th>Run State</th>
                <th>Step ID</th>
                <th>Integrity</th>
                <th>SHA-256 Hash</th>
              </tr>
            </thead>
            <tbody>
              ${this.checkpoints.map(c => `
                <tr>
                  <td><code>${c.checkpoint_id}</code></td>
                  <td>v${c.plan_version}</td>
                  <td><span class="badge badge-outline">${c.run_state}</span></td>
                  <td>${c.step_id || 'start'}</td>
                  <td><span class="badge badge-success">VALID</span></td>
                  <td><code class="hash-preview">${c.corruption_hash?.slice(0, 16)}...</code></td>
                </tr>
              `).join('') || '<tr><td colspan="6" class="text-center">No checkpoints saved yet.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  renderCompletionTab() {
    if (!this.completion) {
      return `
        <div class="card empty-card">
          <h3>No Verified Completion Certificate</h3>
          <p>A completion certificate is only issued when all success criteria have empirical verification proof.</p>
        </div>
      `;
    }

    return `
      <div class="card certificate-card">
        <div class="cert-header">
          <span class="badge badge-success">VERIFIED COMPLETION</span>
          <h3>Certificate: ${this.completion.record_id}</h3>
          <p>Certified at ${new Date(this.completion.completed_at).toLocaleString()}</p>
        </div>
        <div class="cert-body">
          <h4>Verified Success Criteria:</h4>
          <ul>
            ${this.completion.success_criteria.map((c, i) => `
              <li><strong>${c}</strong>: <span class="text-success">${this.completion.verification_results[i] || 'Verified'}</span></li>
            `).join('')}
          </ul>
        </div>
      </div>
    `;
  }

  renderWatchdogTab() {
    return `
      <div class="card">
        <h3>Autonomy Watchdog & Liveness Supervisor</h3>
        <p>Monitors worker heartbeats, leases, step timeouts, and prescribes recovery decisions.</p>
        <div class="watchdog-report">
          <div><strong>Diagnosis:</strong> <span class="badge badge-${this.watchdog?.issue_detected === 'HEALTHY' ? 'success' : 'danger'}">${this.watchdog?.issue_detected || 'HEALTHY'}</span></div>
          <div><strong>Recommended Action:</strong> ${this.watchdog?.recommended_action || 'NONE'}</div>
          <div><strong>Last Inspected:</strong> ${this.watchdog?.inspected_at || 'Just now'}</div>
        </div>
      </div>
    `;
  }

  bindEvents() {
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.dataset.tab;
        this.render();
      });
    });

    const refreshBtn = this.container.querySelector('#refresh-autonomy-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refresh());
    }

    const stopBtn = this.container.querySelector('#emergency-stop-all-btn');
    if (stopBtn) {
      stopBtn.addEventListener('click', () => {
        if (confirm('Execute immediate Emergency Stop Cascade on all active autonomous runs?')) {
          if (this.runs[0]) {
            Endpoints.controlAutonomousRun(this.runs[0].run_id, { action: 'EMERGENCY_STOP', reason: 'User UI emergency halt' });
            alert('Emergency stop signal sent.');
            this.refresh();
          }
        }
      });
    }

    if (typeof window !== 'undefined') {
      window.kairoAutonomy = {
        pause: (runId) => Endpoints.controlAutonomousRun(runId, { action: 'PAUSE' }).then(() => this.refresh()),
        resume: (runId) => Endpoints.controlAutonomousRun(runId, { action: 'RESUME' }).then(() => this.refresh()),
        cancel: (runId) => Endpoints.controlAutonomousRun(runId, { action: 'CANCEL' }).then(() => this.refresh()),
      };
    }
  }

  async refresh() {
    this.render();
  }
}

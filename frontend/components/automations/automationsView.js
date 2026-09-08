/**
 * Kairo Automations View
 * Provides a clean automation dashboard, run triggers, run history, and workflow creation.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class AutomationsView {
  constructor(container) {
    this.container = container;
    this.workflows = [];
    this.selectedWorkflow = null;
    this.runs = [];
    this.isLoading = false;
    this.isCreating = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="automations-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Automations</h1>
            <p class="page-subtitle">Scheduled monitors, background tasks, and autonomous CI watchers</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-automations-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="create-automation-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
              New Automation
            </button>
          </div>
        </header>

        <div class="automations-layout">
          <section class="automations-list-column">
            <div id="automations-list-container">
              <div class="loading-spinner">Loading workflows...</div>
            </div>
          </section>

          <section class="automation-detail-column" id="automation-detail-panel">
            <div class="empty-state">
              <div class="empty-icon">⚙️</div>
              <h3>Select an Automation</h3>
              <p>Choose a workflow from the list to inspect trigger conditions, actions, and recent execution history.</p>
            </div>
          </section>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadWorkflows();
  }

  _bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-automations-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadWorkflows());

    const createBtn = this.container.querySelector('#create-automation-btn');
    if (createBtn) createBtn.addEventListener('click', () => this.openCreateModal());
  }

  async loadWorkflows() {
    const listContainer = this.container.querySelector('#automations-list-container');
    if (!listContainer) return;

    this.isLoading = true;
    listContainer.innerHTML = '<div class="loading-spinner">Loading automations...</div>';

    try {
      const res = await Endpoints.listWorkflows();
      this.workflows = Array.isArray(res) ? res : (res.items || []);
      this.isLoading = false;

      if (this.workflows.length === 0) {
        listContainer.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">⚡</div>
            <h3>No automations configured</h3>
            <p>Automations let Kairo handle recurring work like daily checks, CI monitoring, and alerts.</p>
            <button class="btn btn-primary" id="empty-create-wf-btn">Create Automation</button>
          </div>
        `;
        const btn = listContainer.querySelector('#empty-create-wf-btn');
        if (btn) btn.addEventListener('click', () => this.openCreateModal());
        return;
      }

      this._renderWorkflowList();
      if (this.workflows.length > 0 && !this.selectedWorkflow) {
        this.selectWorkflow(this.workflows[0].id);
      }
    } catch (err) {
      this.isLoading = false;
      listContainer.innerHTML = `
        <div class="error-state">
          <div class="error-icon">⚠️</div>
          <h3>Failed to load automations</h3>
          <p>${err.message || 'Server error'}</p>
          <button class="btn btn-secondary" id="retry-wf-btn">Retry</button>
        </div>
      `;
      const retryBtn = listContainer.querySelector('#retry-wf-btn');
      if (retryBtn) retryBtn.addEventListener('click', () => this.loadWorkflows());
    }
  }

  _renderWorkflowList() {
    const listContainer = this.container.querySelector('#automations-list-container');
    if (!listContainer) return;

    listContainer.innerHTML = `
      <div class="workflow-card-list">
        ${this.workflows.map(wf => {
          const isSelected = this.selectedWorkflow?.id === wf.id;
          const statusClass = wf.enabled ? 'badge-success' : 'badge-neutral';
          const statusText = wf.enabled ? 'ACTIVE' : 'PAUSED';
          return `
            <div class="workflow-item-card ${isSelected ? 'selected' : ''}" data-id="${wf.id}" tabindex="0" role="button">
              <div class="workflow-item-header">
                <span class="workflow-item-name">${escapeHtml(wf.name)}</span>
                <span class="badge ${statusClass}">${statusText}</span>
              </div>
              <p class="workflow-item-desc">${escapeHtml(wf.description || 'No description provided')}</p>
              <div class="workflow-item-meta">
                <span class="meta-field"><strong>Trigger:</strong> ${escapeHtml(wf.trigger_type || 'manual')}</span>
                <span class="meta-field"><strong>Created:</strong> ${new Date(wf.created_at || Date.now()).toLocaleDateString()}</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    listContainer.querySelectorAll('.workflow-item-card').forEach(card => {
      card.addEventListener('click', () => this.selectWorkflow(card.dataset.id));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.selectWorkflow(card.dataset.id);
        }
      });
    });
  }

  async selectWorkflow(workflowId) {
    this.selectedWorkflow = this.workflows.find(w => w.id === workflowId);
    this._renderWorkflowList();

    const detailPanel = this.container.querySelector('#automation-detail-panel');
    if (!detailPanel || !this.selectedWorkflow) return;

    detailPanel.innerHTML = '<div class="loading-spinner">Loading workflow details & run history...</div>';

    try {
      const runs = await Endpoints.getWorkflowRuns(workflowId);
      this.runs = Array.isArray(runs) ? runs : [];
    } catch {
      this.runs = [];
    }

    const wf = this.selectedWorkflow;
    detailPanel.innerHTML = `
      <div class="workflow-detail-card">
        <div class="detail-header">
          <div>
            <div class="title-row">
              <h2 class="detail-title">${escapeHtml(wf.name)}</h2>
              <span class="badge ${wf.enabled ? 'badge-success' : 'badge-neutral'}">
                ${wf.enabled ? 'ACTIVE' : 'PAUSED'}
              </span>
            </div>
            <p class="detail-description">${escapeHtml(wf.description || 'No description.')}</p>
          </div>
          <div class="detail-actions">
            <button class="btn btn-primary" id="run-now-btn" ${store.isEmergencyStopped() ? 'disabled' : ''}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              Run Now
            </button>
            <button class="btn btn-secondary" id="toggle-wf-btn">
              ${wf.enabled ? 'Pause' : 'Enable'}
            </button>
          </div>
        </div>

        <div class="workflow-specs-grid">
          <div class="spec-box">
            <span class="spec-label">Trigger</span>
            <span class="spec-value">${escapeHtml(wf.trigger_type || 'Schedule')}</span>
          </div>
          <div class="spec-box">
            <span class="spec-label">Schedule / Cron</span>
            <span class="spec-value font-mono">${escapeHtml(wf.cron_expression || 'On Demand')}</span>
          </div>
          <div class="spec-box">
            <span class="spec-label">Total Steps</span>
            <span class="spec-value">${Array.isArray(wf.steps) ? wf.steps.length : 0} actions</span>
          </div>
          <div class="spec-box">
            <span class="spec-label">Risk Level</span>
            <span class="spec-value badge badge-info">Standard</span>
          </div>
        </div>

        <div class="detail-section">
          <h3 class="subsection-title">Execution Steps</h3>
          <div class="workflow-steps-list">
            ${(wf.steps || []).map((step, idx) => `
              <div class="step-card">
                <span class="step-index">${idx + 1}</span>
                <div class="step-info">
                  <div class="step-action font-mono">${escapeHtml(step.action || step.type || 'Action')}</div>
                  <div class="step-target">${escapeHtml(step.tool || step.target || 'Tool Executor')}</div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <div class="detail-section">
          <div class="section-title-row">
            <h3 class="subsection-title">Run History</h3>
            <span class="history-count">${this.runs.length} runs</span>
          </div>
          <div class="run-history-list">
            ${this.runs.length === 0 ? `
              <div class="empty-hint">No execution runs recorded yet. Click "Run Now" to trigger.</div>
            ` : this.runs.map(run => {
              const status = (run.status || 'unknown').toLowerCase();
              const badgeClass = status === 'completed' || status === 'success' ? 'badge-success'
                : status === 'failed' ? 'badge-critical'
                : status === 'running' ? 'badge-info' : 'badge-neutral';
              return `
                <div class="run-row">
                  <span class="badge ${badgeClass}">${run.status || 'UNKNOWN'}</span>
                  <span class="run-time font-mono">${new Date(run.started_at || run.created_at || Date.now()).toLocaleTimeString()}</span>
                  <span class="run-duration">${run.duration_seconds ? `${run.duration_seconds}s` : 'Completed'}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>
    `;

    const runNowBtn = detailPanel.querySelector('#run-now-btn');
    if (runNowBtn) {
      runNowBtn.addEventListener('click', async () => {
        runNowBtn.disabled = true;
        runNowBtn.innerText = 'Triggering...';
        try {
          await Endpoints.triggerWorkflow(wf.id);
          store.addNotification({
            id: `run_${Date.now()}`,
            title: `Workflow "${wf.name}" triggered`,
            severity: 'info',
            message: 'Execution started in background.',
            created_at: new Date().toISOString(),
          });
          setTimeout(() => this.selectWorkflow(wf.id), 1500);
        } catch (err) {
          alert(`Failed to run automation: ${err.message}`);
          runNowBtn.disabled = false;
          runNowBtn.innerText = 'Run Now';
        }
      });
    }

    const toggleBtn = detailPanel.querySelector('#toggle-wf-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', async () => {
        try {
          await Endpoints.updateWorkflow(wf.id, { enabled: !wf.enabled });
          await this.loadWorkflows();
        } catch (err) {
          alert(`Failed to update status: ${err.message}`);
        }
      });
    }
  }

  openCreateModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-card" role="dialog" aria-labelledby="create-wf-title">
        <div class="modal-header">
          <h2 id="create-wf-title">Create New Automation</h2>
          <button class="modal-close-btn" aria-label="Close modal">&times;</button>
        </div>
        <form id="create-wf-form">
          <div class="form-group">
            <label for="wf-name">Automation Name</label>
            <input type="text" id="wf-name" required placeholder="e.g. Daily CI Monitor" class="input-field" />
          </div>
          <div class="form-group">
            <label for="wf-desc">Description</label>
            <input type="text" id="wf-desc" placeholder="Inspect repository health and alert on failure" class="input-field" />
          </div>
          <div class="form-group">
            <label for="wf-trigger">Trigger Type</label>
            <select id="wf-trigger" class="input-field">
              <option value="schedule">Schedule / Cron</option>
              <option value="webhook">Webhook / Event</option>
              <option value="manual">Manual Trigger</option>
            </select>
          </div>
          <div class="form-group">
            <label for="wf-cron">Cron Expression (if scheduled)</label>
            <input type="text" id="wf-cron" value="0 * * * *" class="input-field font-mono" />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary modal-cancel-btn">Cancel</button>
            <button type="submit" class="btn btn-primary" id="save-wf-btn">Save Automation</button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(modal);

    const close = () => modal.remove();
    modal.querySelector('.modal-close-btn').addEventListener('click', close);
    modal.querySelector('.modal-cancel-btn').addEventListener('click', close);

    modal.querySelector('#create-wf-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = modal.querySelector('#save-wf-btn');
      saveBtn.disabled = true;
      saveBtn.innerText = 'Creating...';

      const payload = {
        name: modal.querySelector('#wf-name').value.trim(),
        description: modal.querySelector('#wf-desc').value.trim(),
        trigger_type: modal.querySelector('#wf-trigger').value,
        cron_expression: modal.querySelector('#wf-cron').value.trim(),
        enabled: true,
        steps: [
          { action: 'check_status', tool: 'github_tools' }
        ]
      };

      try {
        await Endpoints.createWorkflow(payload);
        close();
        await this.loadWorkflows();
      } catch (err) {
        alert(`Failed to create: ${err.message}`);
        saveBtn.disabled = false;
        saveBtn.innerText = 'Save Automation';
      }
    });
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

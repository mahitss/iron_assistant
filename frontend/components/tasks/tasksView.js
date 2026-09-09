/**
 * Kairo Autonomous Tasks View (Task 31)
 * Provides autonomous task oversight, step DAG progress visualization,
 * interactive human approvals, waiting user responses, and task controls.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class TasksView {
  constructor(container) {
    this.container = container;
    this.tasks = [];
    this.selectedTask = null;
    this.activeTab = 'all'; // all, active, waiting, completed, failed
    this.isLoading = false;
    this.isCreating = false;
    this._pollInterval = null;
  }

  async render() {
    this.container.innerHTML = `
      <div class="tasks-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Autonomous Tasks</h1>
            <p class="page-subtitle">Objective-oriented execution DAGs with bounded autonomous planning, verification, and human oversight</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-tasks-btn" title="Refresh task status">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="new-task-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
              New Task
            </button>
          </div>
        </header>

        <!-- Filter Tabs -->
        <div class="filter-tabs" style="display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid var(--border-color, #2d3748); padding-bottom: 8px;">
          <button class="tab-btn ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all">All Tasks</button>
          <button class="tab-btn ${this.activeTab === 'active' ? 'active' : ''}" data-tab="active">Active</button>
          <button class="tab-btn ${this.activeTab === 'waiting' ? 'active' : ''}" data-tab="waiting">Waiting (Approval / User)</button>
          <button class="tab-btn ${this.activeTab === 'completed' ? 'active' : ''}" data-tab="completed">Completed</button>
          <button class="tab-btn ${this.activeTab === 'failed' ? 'active' : ''}" data-tab="failed">Failed / Cancelled</button>
        </div>

        <div class="tasks-layout" style="display: grid; grid-template-columns: 360px 1fr; gap: 20px; min-height: 600px;">
          <!-- Left Column: Tasks List -->
          <section class="tasks-list-column">
            <div id="tasks-list-container">
              <div class="loading-spinner">Loading autonomous tasks...</div>
            </div>
          </section>

          <!-- Right Column: Task Detail Panel -->
          <section class="task-detail-column" id="task-detail-panel" style="background: var(--bg-surface, #1a202c); border: 1px solid var(--border-color, #2d3748); border-radius: 8px; padding: 20px;">
            <div class="empty-state" style="text-align: center; padding: 60px 20px; color: var(--text-muted, #a0aec0);">
              <div class="empty-icon" style="font-size: 40px; margin-bottom: 12px;">🎯</div>
              <h3>Select a Task</h3>
              <p>Choose an autonomous task from the left column to inspect execution progress, plan steps, and verification results.</p>
            </div>
          </section>
        </div>

        <!-- New Task Modal (hidden by default) -->
        <div id="new-task-modal" class="modal-backdrop" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center;">
          <div class="modal-card" style="background: var(--bg-surface, #1a202c); border: 1px solid var(--border-color, #2d3748); border-radius: 8px; max-width: 600px; width: 90%; padding: 24px;">
            <h2 style="margin-top: 0; margin-bottom: 16px;">Initiate Autonomous Task</h2>
            <div class="form-group" style="margin-bottom: 16px;">
              <label style="display: block; margin-bottom: 6px; font-weight: 600;">High-Level Objective *</label>
              <textarea id="task-objective-input" rows="4" style="width: 100%; box-sizing: border-box; background: var(--bg-input, #2d3748); border: 1px solid var(--border-color, #4a5568); color: inherit; padding: 8px; border-radius: 4px;" placeholder="e.g. Investigate why Kairo CI is failing, identify root cause, research fix, and report changes."></textarea>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
              <div class="form-group">
                <label style="display: block; margin-bottom: 6px; font-weight: 600;">Autonomy Level</label>
                <select id="task-autonomy-input" style="width: 100%; background: var(--bg-input, #2d3748); border: 1px solid var(--border-color, #4a5568); color: inherit; padding: 8px; border-radius: 4px;">
                  <option value="SUPERVISED" selected>SUPERVISED (Reads run, Writes ask)</option>
                  <option value="ASSISTED">ASSISTED (Confirm every major step)</option>
                  <option value="AUTONOMOUS_READ">AUTONOMOUS_READ (Strictly read-only)</option>
                  <option value="AUTONOMOUS_BOUNDED">AUTONOMOUS_BOUNDED (Low-risk writes allowed)</option>
                </select>
              </div>
              <div class="form-group">
                <label style="display: block; margin-bottom: 6px; font-weight: 600;">Priority</label>
                <select id="task-priority-input" style="width: 100%; background: var(--bg-input, #2d3748); border: 1px solid var(--border-color, #4a5568); color: inherit; padding: 8px; border-radius: 4px;">
                  <option value="NORMAL" selected>NORMAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>
            </div>
            <div class="form-group" style="margin-bottom: 20px;">
              <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                <input type="checkbox" id="task-dryrun-input">
                <span><strong>Dry Run:</strong> Plan & validate without applying external mutations</span>
              </label>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 12px;">
              <button class="btn btn-secondary" id="cancel-modal-btn">Cancel</button>
              <button class="btn btn-primary" id="submit-task-btn">Start Autonomous Task</button>
            </div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadTasks();

    // Start 4-second polling for active updates
    if (this._pollInterval) clearInterval(this._pollInterval);
    this._pollInterval = setInterval(() => this._pollActiveTask(), 4000);
  }

  _bindEvents() {
    // Refresh button
    const refreshBtn = this.container.querySelector('#refresh-tasks-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadTasks());

    // New task modal triggers
    const newBtn = this.container.querySelector('#new-task-btn');
    const modal = this.container.querySelector('#new-task-modal');
    const cancelModalBtn = this.container.querySelector('#cancel-modal-btn');
    const submitTaskBtn = this.container.querySelector('#submit-task-btn');

    if (newBtn && modal) {
      newBtn.addEventListener('click', () => { modal.style.display = 'flex'; });
    }
    if (cancelModalBtn && modal) {
      cancelModalBtn.addEventListener('click', () => { modal.style.display = 'none'; });
    }
    if (submitTaskBtn) {
      submitTaskBtn.addEventListener('click', () => this._handleCreateTask());
    }

    // Tabs
    const tabBtns = this.container.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeTab = btn.getAttribute('data-tab');
        this._renderTasksList();
      });
    });
  }

  async loadTasks() {
    this.isLoading = true;
    try {
      this.tasks = await Endpoints.getTasks({ limit: 50 });
      this._renderTasksList();
      if (this.selectedTask) {
        // Refresh selected task
        const updated = this.tasks.find(t => t.id === this.selectedTask.id);
        if (updated) {
          this.selectedTask = updated;
          this._renderTaskDetail(updated);
        }
      }
    } catch (err) {
      console.error('Failed to load tasks:', err);
      const listContainer = this.container.querySelector('#tasks-list-container');
      if (listContainer) {
        listContainer.innerHTML = `<div class="error-message">Failed to load tasks: ${this._escape(err.message)}</div>`;
      }
    } finally {
      this.isLoading = false;
    }
  }

  _renderTasksList() {
    const listContainer = this.container.querySelector('#tasks-list-container');
    if (!listContainer) return;

    let filtered = this.tasks;
    if (this.activeTab === 'active') {
      filtered = this.tasks.filter(t => ['RUNNING', 'PLANNING', 'REPLANNING', 'VERIFYING'].includes(t.status));
    } else if (this.activeTab === 'waiting') {
      filtered = this.tasks.filter(t => ['WAITING_APPROVAL', 'WAITING_USER'].includes(t.status));
    } else if (this.activeTab === 'completed') {
      filtered = this.tasks.filter(t => ['COMPLETED', 'PARTIALLY_COMPLETED'].includes(t.status));
    } else if (this.activeTab === 'failed') {
      filtered = this.tasks.filter(t => ['FAILED', 'CANCELLED', 'TIMED_OUT', 'BLOCKED'].includes(t.status));
    }

    if (filtered.length === 0) {
      listContainer.innerHTML = `
        <div style="text-align: center; padding: 40px 10px; color: var(--text-muted, #a0aec0);">
          <div style="font-size: 28px; margin-bottom: 8px;">📋</div>
          <p>No tasks found in this view.</p>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = filtered.map(t => {
      const isSelected = this.selectedTask && this.selectedTask.id === t.id;
      const statusBadgeClass = this._getStatusBadgeClass(t.status);
      return `
        <div class="task-card ${isSelected ? 'selected' : ''}" data-task-id="${t.id}" style="padding: 14px; border-radius: 6px; background: ${isSelected ? 'var(--bg-highlight, #2d3748)' : 'var(--bg-surface, #1a202c)'}; border: 1px solid ${isSelected ? 'var(--primary-color, #4299e1)' : 'var(--border-color, #2d3748)'}; margin-bottom: 10px; cursor: pointer;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span class="status-badge ${statusBadgeClass}" style="font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600;">${t.status}</span>
            <span style="font-size: 11px; color: var(--text-muted, #a0aec0);">${t.progress_text || ''}</span>
          </div>
          <h4 style="margin: 0 0 6px 0; font-size: 14px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${this._escape(t.objective)}</h4>
          <div style="font-size: 11px; color: var(--text-muted, #a0aec0); display: flex; gap: 10px;">
            <span>Mode: ${t.autonomy_level}</span>
            <span>Priority: ${t.priority}</span>
          </div>
        </div>
      `;
    }).join('');

    // Attach click listeners
    listContainer.querySelectorAll('.task-card').forEach(card => {
      card.addEventListener('click', () => {
        const taskId = card.getAttribute('data-task-id');
        const task = this.tasks.find(t => t.id === taskId);
        if (task) {
          this.selectedTask = task;
          this._renderTasksList();
          this._renderTaskDetail(task);
        }
      });
    });
  }

  _renderTaskDetail(task) {
    const detailPanel = this.container.querySelector('#task-detail-panel');
    if (!detailPanel) return;

    const isRunning = ['RUNNING', 'PLANNING', 'REPLANNING', 'VERIFYING'].includes(task.status);
    const isPaused = task.status === 'PAUSED';
    const isTerminal = ['COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED', 'CANCELLED', 'TIMED_OUT'].includes(task.status);

    // Progress bar calculation
    const pct = task.total_steps > 0 ? Math.round((task.completed_steps / task.total_steps) * 100) : 0;

    detailPanel.innerHTML = `
      <div class="task-detail-header" style="border-bottom: 1px solid var(--border-color, #2d3748); padding-bottom: 16px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
          <div>
            <span class="status-badge ${this._getStatusBadgeClass(task.status)}" style="font-size: 13px; padding: 4px 12px; border-radius: 12px; font-weight: 600;">${task.status}</span>
            <span style="font-size: 12px; color: var(--text-muted, #a0aec0); margin-left: 10px;">ID: ${task.id}</span>
          </div>
          <div class="task-controls" style="display: flex; gap: 8px;">
            ${isRunning ? `<button class="btn btn-secondary btn-sm" id="pause-task-btn">⏸ Pause</button>` : ''}
            ${isPaused ? `<button class="btn btn-primary btn-sm" id="resume-task-btn">▶ Resume</button>` : ''}
            ${!isTerminal ? `<button class="btn btn-danger btn-sm" id="cancel-task-btn">🛑 Cancel</button>` : ''}
            ${isTerminal ? `<button class="btn btn-secondary btn-sm" id="retry-task-btn">🔄 Retry Attempt</button>` : ''}
          </div>
        </div>

        <h2 style="margin: 0 0 10px 0; font-size: 18px; line-height: 1.4;">${this._escape(task.objective)}</h2>

        <!-- Progress Bar (Spec 67, 86) -->
        <div style="margin-top: 12px;">
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
            <span>Progress: <strong>${task.progress_text}</strong></span>
            <span>${pct}%</span>
          </div>
          <div style="width: 100%; height: 8px; background: var(--bg-input, #2d3748); border-radius: 4px; overflow: hidden;">
            <div style="width: ${pct}%; height: 100%; background: var(--primary-color, #4299e1); transition: width 0.3s ease;"></div>
          </div>
        </div>
      </div>

      <!-- Approval Card (Spec 19, 87) -->
      ${task.status === 'WAITING_APPROVAL' && task.pending_approval ? `
        <div class="approval-card" style="background: rgba(237, 137, 54, 0.15); border: 1px solid #ed8936; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
          <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #ed8936; margin-bottom: 8px;">
            <span>⚠️</span>
            <span>ACTION REQUIRES HUMAN APPROVAL</span>
          </div>
          <p style="margin: 0 0 8px 0;"><strong>Step:</strong> ${this._escape(task.pending_approval.action)}</p>
          <p style="margin: 0 0 8px 0;"><strong>Target:</strong> ${this._escape(task.pending_approval.target)}</p>
          <p style="margin: 0 0 12px 0;"><strong>Risk Level:</strong> <span class="risk-badge" style="background: #e53e3e; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${task.pending_approval.risk}</span></p>
          <div style="display: flex; gap: 10px;">
            <button class="btn btn-primary btn-sm" id="btn-approve-action" style="background: #38a169; border-color: #38a169;">✓ Approve Action</button>
            <button class="btn btn-secondary btn-sm" id="btn-reject-action">✗ Reject</button>
          </div>
        </div>
      ` : ''}

      <!-- Waiting User Card (Spec 65, 88) -->
      ${task.status === 'WAITING_USER' ? `
        <div class="waiting-user-card" style="background: rgba(66, 153, 225, 0.15); border: 1px solid #4299e1; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
          <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #4299e1; margin-bottom: 8px;">
            <span>❓</span>
            <span>CLARIFICATION REQUIRED</span>
          </div>
          <p style="margin: 0 0 10px 0;">${this._escape(task.waiting_user_question || 'Please provide additional details to continue execution:')}</p>
          <div style="display: flex; gap: 10px;">
            <input type="text" id="user-clarification-input" placeholder="Enter your response..." style="flex: 1; background: var(--bg-input, #2d3748); border: 1px solid var(--border-color, #4a5568); color: inherit; padding: 6px 10px; border-radius: 4px;" />
            <button class="btn btn-primary btn-sm" id="btn-submit-clarification">Submit Response</button>
          </div>
        </div>
      ` : ''}

      <!-- Result Summary Card (Spec 89, 90, 91) -->
      ${task.result_summary ? `
        <div class="result-summary-card" style="background: var(--bg-surface-alt, #2d3748); border: 1px solid var(--border-color, #4a5568); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
          <h3 style="margin-top: 0; margin-bottom: 8px; font-size: 15px;">Outcome Summary: ${this._escape(task.result_summary.outcome)}</h3>
          <p style="margin: 0 0 10px 0; font-size: 13px; line-height: 1.4;">${this._escape(task.result_summary.summary)}</p>
          ${task.result_summary.evidence && task.result_summary.evidence.length > 0 ? `
            <div style="font-size: 12px; margin-top: 8px;">
              <strong>Evidence Collected:</strong>
              <ul style="margin: 4px 0 0 0; padding-left: 20px;">
                ${task.result_summary.evidence.map(e => `<li>${this._escape(JSON.stringify(e))}</li>`).join('')}
              </ul>
            </div>
          ` : ''}
        </div>
      ` : ''}

      <!-- Plan Step DAG Tree (Spec 86) -->
      <div class="steps-dag-section">
        <h3 style="margin: 0 0 12px 0; font-size: 15px;">Execution Plan (Plan v${task.plan_version})</h3>
        <div class="steps-list">
          ${task.steps && task.steps.length > 0 ? task.steps.map(s => {
            const icon = this._getStepIcon(s.status);
            return `
              <div class="step-item" style="display: flex; gap: 12px; padding: 10px; border-radius: 6px; background: var(--bg-surface-alt, #242c3d); margin-bottom: 8px; border: 1px solid var(--border-color, #2d3748); align-items: flex-start;">
                <span style="font-size: 16px; line-height: 1.2;">${icon}</span>
                <div style="flex: 1;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <strong style="font-size: 13px;">${s.sequence}. ${this._escape(s.title)}</strong>
                    <span class="risk-badge" style="font-size: 10px; padding: 1px 6px; border-radius: 4px; background: ${s.risk_level === 'READ' ? '#2b6cb0' : '#c53030'}; color: white;">${s.risk_level}</span>
                  </div>
                  <div style="font-size: 12px; color: var(--text-muted, #a0aec0); margin-bottom: 4px;">${this._escape(s.objective)}</div>
                  <div style="font-size: 11px; color: var(--text-muted, #718096); display: flex; gap: 12px;">
                    <span>Status: <strong>${s.status}</strong></span>
                    ${s.tool_name ? `<span>Tool: <code>${s.tool_name}</code></span>` : ''}
                    ${s.skill_id ? `<span>Skill: <code>${s.skill_id}</code></span>` : ''}
                  </div>
                  ${s.error ? `<div style="margin-top: 6px; font-size: 11px; color: #fc8181; background: rgba(229, 62, 62, 0.1); padding: 4px 8px; border-radius: 4px;">Error: ${this._escape(s.error)}</div>` : ''}
                </div>
              </div>
            `;
          }).join('') : `<p style="color: var(--text-muted, #a0aec0);">Plan is currently generating...</p>`}
        </div>
      </div>
    `;

    this._bindDetailActions(task);
  }

  _bindDetailActions(task) {
    const panel = this.container.querySelector('#task-detail-panel');
    if (!panel) return;

    // Pause
    const pauseBtn = panel.querySelector('#pause-task-btn');
    if (pauseBtn) {
      pauseBtn.addEventListener('click', async () => {
        try {
          await Endpoints.pauseTask(task.id);
          await this.loadTasks();
        } catch (e) {
          alert('Failed to pause: ' + e.message);
        }
      });
    }

    // Resume
    const resumeBtn = panel.querySelector('#resume-task-btn');
    if (resumeBtn) {
      resumeBtn.addEventListener('click', async () => {
        try {
          await Endpoints.resumeTask(task.id);
          await this.loadTasks();
        } catch (e) {
          alert('Failed to resume: ' + e.message);
        }
      });
    }

    // Cancel
    const cancelBtn = panel.querySelector('#cancel-task-btn');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', async () => {
        if (confirm('Are you sure you want to cancel this autonomous task?')) {
          try {
            await Endpoints.cancelTask(task.id);
            await this.loadTasks();
          } catch (e) {
            alert('Failed to cancel: ' + e.message);
          }
        }
      });
    }

    // Retry
    const retryBtn = panel.querySelector('#retry-task-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', async () => {
        try {
          await Endpoints.retryTask(task.id);
          await this.loadTasks();
        } catch (e) {
          alert('Failed to retry: ' + e.message);
        }
      });
    }

    // Approve step
    const approveBtn = panel.querySelector('#btn-approve-action');
    if (approveBtn) {
      approveBtn.addEventListener('click', async () => {
        try {
          await Endpoints.approveTaskStep(task.id, { approved: true });
          await this.loadTasks();
        } catch (e) {
          alert('Approval error: ' + e.message);
        }
      });
    }

    // Reject step
    const rejectBtn = panel.querySelector('#btn-reject-action');
    if (rejectBtn) {
      rejectBtn.addEventListener('click', async () => {
        const reason = prompt('Rejection reason (optional):') || 'Rejected by user';
        try {
          await Endpoints.approveTaskStep(task.id, { approved: false, reason });
          await this.loadTasks();
        } catch (e) {
          alert('Rejection error: ' + e.message);
        }
      });
    }

    // User clarification submit
    const submitClarificationBtn = panel.querySelector('#btn-submit-clarification');
    const clarInput = panel.querySelector('#user-clarification-input');
    if (submitClarificationBtn && clarInput) {
      submitClarificationBtn.addEventListener('click', async () => {
        const val = clarInput.value.trim();
        if (!val) return;
        try {
          await Endpoints.respondToTask(task.id, val);
          await this.loadTasks();
        } catch (e) {
          alert('Response error: ' + e.message);
        }
      });
    }
  }

  async _handleCreateTask() {
    const objInput = this.container.querySelector('#task-objective-input');
    const autonomyInput = this.container.querySelector('#task-autonomy-input');
    const priorityInput = this.container.querySelector('#task-priority-input');
    const dryRunInput = this.container.querySelector('#task-dryrun-input');
    const modal = this.container.querySelector('#new-task-modal');

    const objective = objInput.value.trim();
    if (!objective) {
      alert('Please enter a task objective.');
      return;
    }

    try {
      const newTask = await Endpoints.createTask({
        objective,
        autonomy_level: autonomyInput.value,
        priority: priorityInput.value,
        dry_run: dryRunInput.checked,
      });
      modal.style.display = 'none';
      objInput.value = '';
      await this.loadTasks();
      this.selectedTask = newTask;
      this._renderTaskDetail(newTask);
    } catch (err) {
      alert('Failed to start task: ' + err.message);
    }
  }

  async _pollActiveTask() {
    // If selected task is currently active, refresh it quietly
    if (this.selectedTask && ['RUNNING', 'PLANNING', 'REPLANNING', 'VERIFYING', 'WAITING_APPROVAL', 'WAITING_USER'].includes(this.selectedTask.status)) {
      try {
        const fresh = await Endpoints.getTask(this.selectedTask.id);
        if (fresh) {
          this.selectedTask = fresh;
          // Update in array
          const idx = this.tasks.findIndex(t => t.id === fresh.id);
          if (idx >= 0) this.tasks[idx] = fresh;
          this._renderTasksList();
          this._renderTaskDetail(fresh);
        }
      } catch (e) {
        // Silent poll error
      }
    }
  }

  _getStatusBadgeClass(status) {
    switch (status) {
      case 'RUNNING':
      case 'PLANNING':
      case 'REPLANNING':
      case 'VERIFYING':
        return 'badge-info';
      case 'COMPLETED':
        return 'badge-success';
      case 'PARTIALLY_COMPLETED':
      case 'WAITING_APPROVAL':
      case 'WAITING_USER':
        return 'badge-warning';
      case 'FAILED':
      case 'CANCELLED':
      case 'TIMED_OUT':
      case 'BLOCKED':
        return 'badge-danger';
      default:
        return 'badge-secondary';
    }
  }

  _getStepIcon(status) {
    switch (status) {
      case 'COMPLETED': return '✓';
      case 'RUNNING': return '●';
      case 'WAITING_APPROVAL': return '⏸';
      case 'FAILED': return '✗';
      case 'CANCELLED': return '⊘';
      default: return '○';
    }
  }

  _escape(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  destroy() {
    if (this._pollInterval) {
      clearInterval(this._pollInterval);
      this._pollInterval = null;
    }
  }
}

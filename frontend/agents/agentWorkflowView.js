/**
 * AgentWorkflowView — Frontend visualization controller for Kairo Multi-Agent Orchestration.
 * Displays role, status, and safe summaries for sub-agent tasks without exposing raw chain-of-thought.
 */

export class AgentWorkflowView {
  constructor(options = {}) {
    this.taskId = options.taskId || null;
    this.objective = options.objective || '';
    this.supervisorStatus = options.supervisorStatus || 'idle'; // idle, planning, running, synthesizing, completed, cancelled, failed
    this.tasks = options.tasks || [];
  }

  initPlan(taskId, objective, tasks = []) {
    this.taskId = taskId;
    this.objective = objective;
    this.supervisorStatus = 'running';
    this.tasks = tasks.map((t) => ({
      id: t.task_id || t.id,
      agent_type: t.agent_type,
      objective: t.objective,
      status: t.status || 'PENDING',
      summary: t.summary || null,
      dependencies: t.dependencies || [],
    }));
  }

  updateTaskStatus(taskId, status, summary = null) {
    const task = this.tasks.find((t) => t.id === taskId);
    if (task) {
      task.status = status;
      if (summary) {
        task.summary = summary;
      }
    }
  }

  setSupervisorStatus(status) {
    this.supervisorStatus = status;
  }

  cancelTask() {
    this.supervisorStatus = 'cancelled';
    for (const t of this.tasks) {
      if (t.status === 'PENDING' || t.status === 'RUNNING') {
        t.status = 'CANCELLED';
      }
    }
    return { taskId: this.taskId, status: 'CANCELLED', cancelled: true };
  }

  getStatusIcon(status) {
    switch (String(status).toUpperCase()) {
      case 'COMPLETED':
        return '<span class="text-success fw-bold">✓</span>';
      case 'RUNNING':
        return '<span class="text-primary fw-bold">●</span>';
      case 'WAITING_APPROVAL':
        return '<span class="text-warning fw-bold">⏸</span>';
      case 'FAILED':
        return '<span class="text-danger fw-bold">✗</span>';
      case 'CANCELLED':
        return '<span class="text-secondary fw-bold">⊘</span>';
      case 'PENDING':
      default:
        return '<span class="text-muted fw-bold">○</span>';
    }
  }

  renderUI() {
    const tasksHtml = this.tasks
      .map((t) => {
        const icon = this.getStatusIcon(t.status);
        const summaryText = t.summary
          ? `<div class="small text-muted ps-3">${t.summary}</div>`
          : `<div class="small text-muted ps-3">${t.objective}</div>`;
        return `
        <div class="agent-task-item py-1" id="agent-task-${t.id}">
          <div>${icon} <strong>${t.agent_type}</strong></div>
          ${summaryText}
        </div>
      `.trim();
      })
      .join('\n');

    const supervisorIcon = this.getStatusIcon(
      this.supervisorStatus === 'completed'
        ? 'COMPLETED'
        : this.supervisorStatus === 'cancelled'
        ? 'CANCELLED'
        : this.supervisorStatus === 'failed'
        ? 'FAILED'
        : 'RUNNING'
    );

    return `
      <div class="card p-3 my-2 border shadow-sm agent-workflow-panel" id="agent-workflow-${this.taskId || 'active'}">
        <div class="d-flex justify-content-between align-items-center mb-2 border-bottom pb-2">
          <h6 class="mb-0 fw-bold">KAIRO ORCHESTRATION</h6>
          <span class="badge bg-secondary">${this.supervisorStatus.toUpperCase()}</span>
        </div>
        <div class="small mb-2"><strong>Task:</strong> ${this.objective || 'Processing request'}</div>
        <div class="agent-tasks-list mb-3">
          ${tasksHtml || '<p class="text-muted small">No sub-agent tasks planned.</p>'}
          <div class="agent-task-item py-1 mt-2 border-top pt-2">
            <div>${supervisorIcon} <strong>SUPERVISOR</strong></div>
            <div class="small text-muted ps-3">
              ${this.supervisorStatus === 'synthesizing' ? 'Synthesizing final findings...' : this.supervisorStatus === 'completed' ? 'Final answer synthesized' : 'Supervising execution'}
            </div>
          </div>
        </div>
        ${this.supervisorStatus === 'running' || this.supervisorStatus === 'synthesizing' ? `<button class="btn btn-sm btn-outline-danger w-100" onclick="agentWorkflowView.cancelTask()">Cancel Execution</button>` : ''}
      </div>
    `.trim();
  }
}

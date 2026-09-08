/**
 * SecurityCenterPanel — Frontend state and controller for Kairo Security Center.
 * Controls capability toggles, pending approvals, emergency stop, and audit activity.
 */

export class SecurityCenterPanel {
  constructor(options = {}) {
    this.userId = options.userId || 'default_user';
    this.capabilities = {
      web_research: true,
      browser: true,
      voice: true,
      vision: true,
      computer_control: false, // Default OFF
      developer_tools: true,
      automation: true,
      ...options.capabilities,
    };
    this.emergencyStop = {
      is_stopped: false,
      status: 'ACTIVE',
      reason: null,
      ...options.emergencyStop,
    };
    this.pendingApprovals = options.pendingApprovals || [];
    this.auditEvents = options.auditEvents || [];
  }

  toggleCapability(capKey) {
    if (Object.prototype.hasOwnProperty.call(this.capabilities, capKey)) {
      this.capabilities[capKey] = !this.capabilities[capKey];
      return this.capabilities[capKey];
    }
    throw new Error(`Unknown capability: ${capKey}`);
  }

  triggerEmergencyStop(reason = 'User initiated stop') {
    this.emergencyStop = {
      is_stopped: true,
      status: 'STOPPED',
      reason,
      timestamp: new Date().toISOString(),
    };
    return this.emergencyStop;
  }

  resetEmergencyStop() {
    this.emergencyStop = {
      is_stopped: false,
      status: 'ACTIVE',
      reason: null,
      timestamp: new Date().toISOString(),
    };
    return this.emergencyStop;
  }

  addApproval(approval) {
    this.pendingApprovals.push({
      status: 'pending',
      created_at: new Date().toISOString(),
      ...approval,
    });
  }

  decideApproval(approvalId, decision, reason = null) {
    const idx = this.pendingApprovals.findIndex((a) => a.id === approvalId);
    if (idx === -1) {
      throw new Error(`Approval '${approvalId}' not found`);
    }

    const app = this.pendingApprovals[idx];
    if (app.status !== 'pending') {
      throw new Error(`Approval '${approvalId}' already in state '${app.status}'`);
    }

    app.status = decision === 'approve' ? 'approved' : 'denied';
    app.decision_reason = reason;
    app.decided_at = new Date().toISOString();

    // Remove from pending view
    this.pendingApprovals.splice(idx, 1);
    return app;
  }

  recordAuditEvent(event) {
    this.auditEvents.unshift({
      timestamp: new Date().toISOString(),
      ...event,
    });
    // Keep max 100 in memory
    if (this.auditEvents.length > 100) {
      this.auditEvents.pop();
    }
  }

  renderPendingApprovalsUI() {
    if (this.pendingApprovals.length === 0) {
      return '<p class="text-muted">No pending approvals required.</p>';
    }

    return this.pendingApprovals
      .map(
        (app) => `
      <div class="approval-card border p-3 mb-2 rounded bg-warning-subtle" id="approval-${app.id}">
        <div class="fw-bold text-danger">ACTION REQUIRES APPROVAL</div>
        <div><strong>Tool:</strong> ${app.tool_name}</div>
        <div><strong>Action:</strong> ${app.action_description || 'Restricted operation'}</div>
        <div><strong>Risk:</strong> <span class="badge bg-danger">${app.risk_level}</span></div>
        <div class="mt-2">
          <button class="btn btn-sm btn-success me-2" onclick="securityPanel.decideApproval('${app.id}', 'approve')">APPROVE</button>
          <button class="btn btn-sm btn-outline-danger" onclick="securityPanel.decideApproval('${app.id}', 'deny')">DENY</button>
        </div>
      </div>
    `
      )
      .join('');
  }
}

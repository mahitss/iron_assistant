/**
 * Automation Panel component for Kairo.
 * Provides workflow listing, schedule controls, execution history,
 * in-app notifications, and human-in-the-loop approval management.
 */

export class AutomationPanel {
  constructor(options = {}) {
    this.workflows = options.workflows || [];
    this.selectedWorkflowId = options.selectedWorkflowId || null;
    this.runs = options.runs || [];
    this.pendingApprovals = options.pendingApprovals || [];
    this.notifications = options.notifications || [];
  }

  setWorkflows(workflowList) {
    this.workflows = Array.isArray(workflowList) ? [...workflowList] : [];
  }

  addWorkflow(workflow) {
    this.workflows.unshift(workflow);
  }

  toggleWorkflowEnabled(workflowId) {
    const wf = this.workflows.find((w) => w.id === workflowId);
    if (!wf) throw new Error(`Workflow '${workflowId}' not found.`);
    wf.enabled = !wf.enabled;
    return wf.enabled;
  }

  deleteWorkflow(workflowId) {
    const prevLen = this.workflows.length;
    this.workflows = this.workflows.filter((w) => w.id !== workflowId);
    return this.workflows.length < prevLen;
  }

  setRuns(runList) {
    this.runs = Array.isArray(runList) ? [...runList] : [];
  }

  setPendingApprovals(approvalList) {
    this.pendingApprovals = Array.isArray(approvalList) ? [...approvalList] : [];
  }

  setNotifications(notificationList) {
    this.notifications = Array.isArray(notificationList) ? [...notificationList] : [];
  }

  approveAction(approvalId) {
    const appr = this.pendingApprovals.find((a) => a.id === approvalId);
    if (!appr) throw new Error(`Approval '${approvalId}' not found.`);
    appr.status = "approved";
    this.pendingApprovals = this.pendingApprovals.filter((a) => a.id !== approvalId);
    return appr;
  }

  denyAction(approvalId, reason = "Denied by user") {
    const appr = this.pendingApprovals.find((a) => a.id === approvalId);
    if (!appr) throw new Error(`Approval '${approvalId}' not found.`);
    appr.status = "denied";
    appr.reason = reason;
    this.pendingApprovals = this.pendingApprovals.filter((a) => a.id !== approvalId);
    return appr;
  }

  render() {
    return {
      type: "AutomationPanel",
      summary: {
        totalWorkflows: this.workflows.length,
        enabledWorkflows: this.workflows.filter((w) => w.enabled).length,
        pendingApprovalsCount: this.pendingApprovals.length,
        totalRuns: this.runs.length,
        unreadNotifications: this.notifications.filter((n) => !n.read).length,
      },
      workflows: this.workflows.map((wf) => ({
        id: wf.id,
        name: wf.name,
        description: wf.description,
        enabled: wf.enabled,
        triggerType: wf.trigger_type,
        triggerDetails: wf.trigger_config,
        lastRunAt: wf.last_run_at || "Never",
        nextRunAt: wf.next_run_at || (wf.enabled ? "Pending calculation" : "Disabled"),
        controls: ["Enable", "Disable", "Run Now", "Cancel", "Delete"],
      })),
      pendingApprovals: this.pendingApprovals.map((appr) => ({
        id: appr.id,
        runId: appr.run_id,
        toolName: appr.tool_name,
        toolArgs: appr.tool_args,
        permissionLevel: appr.permission_level,
        status: appr.status,
        expiresAt: appr.expires_at,
        actions: ["APPROVE", "DENY"],
      })),
      recentRuns: this.runs.slice(0, 10),
      notifications: this.notifications.slice(0, 10),
    };
  }
}

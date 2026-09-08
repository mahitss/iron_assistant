import { test, describe } from 'node:test';
import assert from 'node:assert';
import { AutomationPanel } from '../automation/automationPanel.js';

describe('Frontend Automation Panel Tests', () => {
  test('initializes with default empty state', () => {
    const panel = new AutomationPanel();
    const state = panel.render();

    assert.strictEqual(state.summary.totalWorkflows, 0);
    assert.strictEqual(state.summary.enabledWorkflows, 0);
    assert.strictEqual(state.summary.pendingApprovalsCount, 0);
    assert.strictEqual(state.workflows.length, 0);
  });

  test('manages workflows, enable/disable toggling, and deletion', () => {
    const panel = new AutomationPanel();
    const wf1 = {
      id: 'wf_1',
      name: 'Daily CI Monitor',
      description: 'Checks GitHub CI every morning',
      enabled: true,
      trigger_type: 'schedule',
      trigger_config: { interval: 'daily', time: '08:00' },
      last_run_at: null,
      next_run_at: '2026-09-09T08:00:00Z',
    };
    panel.addWorkflow(wf1);

    let state = panel.render();
    assert.strictEqual(state.summary.totalWorkflows, 1);
    assert.strictEqual(state.summary.enabledWorkflows, 1);
    assert.strictEqual(state.workflows[0].name, 'Daily CI Monitor');

    // Toggle disabled
    const isEnabled = panel.toggleWorkflowEnabled('wf_1');
    assert.strictEqual(isEnabled, false);
    state = panel.render();
    assert.strictEqual(state.summary.enabledWorkflows, 0);

    // Delete workflow
    const deleted = panel.deleteWorkflow('wf_1');
    assert.strictEqual(deleted, true);
    state = panel.render();
    assert.strictEqual(state.summary.totalWorkflows, 0);
  });

  test('manages pending approvals, approval decisions, and denial reason', () => {
    const panel = new AutomationPanel();
    panel.setPendingApprovals([
      {
        id: 'appr_123',
        run_id: 'run_456',
        tool_name: 'test_runner',
        tool_args: { command: 'pytest' },
        permission_level: 'EXECUTE',
        status: 'pending',
        expires_at: '2026-09-08T23:30:00Z',
      },
      {
        id: 'appr_789',
        run_id: 'run_999',
        tool_name: 'git_push',
        tool_args: {},
        permission_level: 'EXTERNAL',
        status: 'pending',
        expires_at: '2026-09-08T23:35:00Z',
      },
    ]);

    let state = panel.render();
    assert.strictEqual(state.summary.pendingApprovalsCount, 2);
    assert.strictEqual(state.pendingApprovals[0].toolName, 'test_runner');

    // Approve first action
    const approved = panel.approveAction('appr_123');
    assert.strictEqual(approved.status, 'approved');

    state = panel.render();
    assert.strictEqual(state.summary.pendingApprovalsCount, 1);

    // Deny second action
    const denied = panel.denyAction('appr_789', 'Untrusted environment');
    assert.strictEqual(denied.status, 'denied');
    assert.strictEqual(denied.reason, 'Untrusted environment');

    state = panel.render();
    assert.strictEqual(state.summary.pendingApprovalsCount, 0);
  });
});

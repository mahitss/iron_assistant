import test from 'node:test';
import assert from 'node:assert/strict';
import { SecurityCenterPanel } from '../security/securityPanel.js';

test('Frontend Security Center Panel Tests', async (t) => {
  await t.test('initializes with default capabilities and computer control OFF', () => {
    const panel = new SecurityCenterPanel();
    assert.strictEqual(panel.capabilities.computer_control, false);
    assert.strictEqual(panel.capabilities.web_research, true);
    assert.strictEqual(panel.capabilities.browser, true);
    assert.strictEqual(panel.capabilities.developer_tools, true);
    assert.strictEqual(panel.emergencyStop.status, 'ACTIVE');
    assert.strictEqual(panel.emergencyStop.is_stopped, false);
  });

  await t.test('toggles capabilities safely', () => {
    const panel = new SecurityCenterPanel();
    assert.strictEqual(panel.capabilities.browser, true);
    panel.toggleCapability('browser');
    assert.strictEqual(panel.capabilities.browser, false);
    panel.toggleCapability('browser');
    assert.strictEqual(panel.capabilities.browser, true);
  });

  await t.test('manages emergency stop trigger and reset lifecycle', () => {
    const panel = new SecurityCenterPanel();
    panel.triggerEmergencyStop('Suspicious behavior detected');
    assert.strictEqual(panel.emergencyStop.is_stopped, true);
    assert.strictEqual(panel.emergencyStop.status, 'STOPPED');
    assert.strictEqual(panel.emergencyStop.reason, 'Suspicious behavior detected');

    panel.resetEmergencyStop();
    assert.strictEqual(panel.emergencyStop.is_stopped, false);
    assert.strictEqual(panel.emergencyStop.status, 'ACTIVE');
  });

  await t.test('manages pending approval decisions and UI rendering', () => {
    const panel = new SecurityCenterPanel();
    panel.addApproval({
      id: 'app_1',
      tool_name: 'git_push',
      action_description: 'Push main branch to GitHub',
      risk_level: 'HIGH',
    });

    assert.strictEqual(panel.pendingApprovals.length, 1);
    const html = panel.renderPendingApprovalsUI();
    assert.match(html, /Push main branch to GitHub/);
    assert.match(html, /APPROVE/);

    const decided = panel.decideApproval('app_1', 'approve');
    assert.strictEqual(decided.status, 'approved');
    assert.strictEqual(panel.pendingApprovals.length, 0);
  });
});

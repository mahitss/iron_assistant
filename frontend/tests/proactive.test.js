import test from 'node:test';
import assert from 'node:assert/strict';
import { ProactivePanel } from '../proactive/proactivePanel.js';

test('Frontend Proactive Intelligence Panel Tests', async (t) => {
  await t.test('initializes with default settings and 0 unread', () => {
    const panel = new ProactivePanel();
    assert.strictEqual(panel.settings.proactive_enabled, true);
    assert.strictEqual(panel.settings.notify_on_workflow_failure, true);
    assert.strictEqual(panel.settings.minimum_priority, 'MEDIUM');
    assert.strictEqual(panel.settings.quiet_hours_enabled, false);
    assert.strictEqual(panel.getUnreadCount(), 0);
  });

  await t.test('toggles preferences and sets minimum priority', () => {
    const panel = new ProactivePanel();
    assert.strictEqual(panel.settings.notify_on_ci_failure, true);
    panel.toggleSetting('notify_on_ci_failure');
    assert.strictEqual(panel.settings.notify_on_ci_failure, false);

    panel.setMinimumPriority('HIGH');
    assert.strictEqual(panel.settings.minimum_priority, 'HIGH');

    assert.throws(() => panel.setMinimumPriority('INVALID'));
  });

  await t.test('tracks notifications, unread count, and renders bell', () => {
    const panel = new ProactivePanel();
    panel.addNotification({
      id: 'n1',
      title: 'CI Failed in Kairo',
      summary: 'Build failed on main branch',
      priority: 'HIGH',
      suggested_action: 'View Run',
    });
    panel.addNotification({
      id: 'n2',
      title: 'Approval Waiting',
      summary: 'Action waiting for your review',
      priority: 'HIGH',
      suggested_action: 'Review',
    });

    assert.strictEqual(panel.getUnreadCount(), 2);
    const bellHtml = panel.renderNotificationBellUI();
    assert.match(bellHtml, /🔔/);
    assert.match(bellHtml, />2</);

    panel.markRead('n1');
    assert.strictEqual(panel.getUnreadCount(), 1);

    const feedHtml = panel.renderFeedUI();
    assert.match(feedHtml, /CI Failed in Kairo/);
    assert.match(feedHtml, /View Run/);
    assert.match(feedHtml, /Dismiss/);

    panel.dismissNotification('n1');
    assert.strictEqual(panel.notifications.length, 1);
  });

  await t.test('manages web monitors collection', () => {
    const panel = new ProactivePanel();
    const mon = panel.addWebMonitor({
      name: 'Python Docs',
      url: 'https://docs.python.org',
    });
    assert.strictEqual(panel.webMonitors.length, 1);
    assert.strictEqual(mon.name, 'Python Docs');

    panel.removeWebMonitor(mon.id);
    assert.strictEqual(panel.webMonitors.length, 0);
  });

  await t.test('renders settings UI cleanly', () => {
    const panel = new ProactivePanel();
    const settingsHtml = panel.renderSettingsUI();
    assert.match(settingsHtml, /PROACTIVE INTELLIGENCE/);
    assert.match(settingsHtml, /Enable Proactive Notifications/);
    assert.match(settingsHtml, /Workflow Failures/);
    assert.match(settingsHtml, /Quiet Hours/);
  });
});

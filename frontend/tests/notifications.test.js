import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints } from '../lib/api/endpoints.js';
import { NotificationsView } from '../components/notifications/notificationsView.js';

test('Kairo Unified Notification Layer Frontend Tests (Task 34)', async (t) => {
  await t.test('Endpoints defines all required Notification, Action, and Preference methods (Spec 118, 119)', () => {
    assert.strictEqual(typeof Endpoints.listNotifications, 'function');
    assert.strictEqual(typeof Endpoints.getNotification, 'function');
    assert.strictEqual(typeof Endpoints.markNotificationRead, 'function');
    assert.strictEqual(typeof Endpoints.dismissNotification, 'function');
    assert.strictEqual(typeof Endpoints.markAllNotificationsRead, 'function');
    assert.strictEqual(typeof Endpoints.executeNotificationAction, 'function');
    assert.strictEqual(typeof Endpoints.getNotificationPreferences, 'function');
    assert.strictEqual(typeof Endpoints.updateNotificationPreferences, 'function');
  });

  await t.test('NotificationsView renders Tabs, Mark All Read, and header controls (Spec 75, 78)', () => {
    let capturedHtml = '';
    const mockContainer = {
      set innerHTML(val) { capturedHtml = val; },
      get innerHTML() { return capturedHtml; },
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new NotificationsView(mockContainer);
    view.render();

    assert.ok(capturedHtml.includes('id="mark-all-read-btn"'), 'Mark All Read button must be rendered');
    assert.ok(capturedHtml.includes('id="notif-tab-all"'), 'All tab must be rendered');
    assert.ok(capturedHtml.includes('id="notif-tab-unread"'), 'Unread tab must be rendered');
    assert.ok(capturedHtml.includes('id="notif-tab-tasks"'), 'Tasks tab must be rendered');
    assert.ok(capturedHtml.includes('id="notif-tab-security"'), 'Security tab must be rendered');
    assert.ok(capturedHtml.includes('id="notif-tab-projects"'), 'Projects tab must be rendered');
  });

  await t.test('NotificationsView renders approval notification with Approve/Reject action buttons (Spec 80)', () => {
    let capturedListHtml = '';
    const mockListContainer = {
      set innerHTML(val) { capturedListHtml = val; },
      get innerHTML() { return capturedListHtml; },
      querySelectorAll: () => [],
    };

    const mockContainer = {
      querySelector: (selector) => {
        if (selector === '#notifications-list') return mockListContainer;
        return null;
      },
      querySelectorAll: () => [],
    };

    const view = new NotificationsView(mockContainer);
    view.notifications = [
      {
        id: 'notif_app_test',
        type: 'APPROVAL',
        priority: 'HIGH',
        title: 'Action Requires Approval',
        body: 'Kairo needs authorization to deploy to prod.',
        status: 'DELIVERED',
        actions: [
          { id: 'act_app_1', type: 'APPROVE', label: 'Approve' },
          { id: 'act_rej_1', type: 'REJECT', label: 'Reject' },
        ],
        metadata: {
          target: 'Production Cluster',
          risk_level: 'HIGH',
        },
      },
    ];

    view._renderList();

    assert.ok(capturedListHtml.includes('APPROVAL REQUIRED'), 'Approval badge must render');
    assert.ok(capturedListHtml.includes('Approve'), 'Approve button must render');
    assert.ok(capturedListHtml.includes('Reject'), 'Reject button must render');
    assert.ok(capturedListHtml.includes('Production Cluster'), 'Target metadata must render');
    assert.ok(capturedListHtml.includes('data-action-id="act_app_1"'), 'Action ID must be bound to button');
  });

  await t.test('NotificationsView renders distinctive visual styling for Security alerts (Spec 79)', () => {
    let capturedListHtml = '';
    const mockListContainer = {
      set innerHTML(val) { capturedListHtml = val; },
      get innerHTML() { return capturedListHtml; },
      querySelectorAll: () => [],
    };

    const mockContainer = {
      querySelector: (selector) => {
        if (selector === '#notifications-list') return mockListContainer;
        return null;
      },
      querySelectorAll: () => [],
    };

    const view = new NotificationsView(mockContainer);
    view.notifications = [
      {
        id: 'notif_sec_test',
        type: 'SECURITY',
        priority: 'URGENT',
        title: 'Device Revoked',
        body: 'Suspicious device revoked.',
        status: 'DELIVERED',
      },
    ];

    view._renderList();

    assert.ok(capturedListHtml.includes('is-security-alert'), 'Security alert CSS class must be applied');
    assert.ok(capturedListHtml.includes('SECURITY'), 'SECURITY badge must render');
    assert.ok(capturedListHtml.includes('badge-critical'), 'Critical badge style must render');
  });
});

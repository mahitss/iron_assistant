import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints } from '../lib/api/endpoints.js';
import { EnvironmentView } from '../components/environment/environmentView.js';
import { AppShell } from '../components/layout/shell.js';

test('Kairo World Model & Live Environment Frontend Tests (Task 32)', async (t) => {
  await t.test('Endpoints defines all required World Model API methods (Spec 120, 121)', () => {
    assert.strictEqual(typeof Endpoints.getWorldOverview, 'function');
    assert.strictEqual(typeof Endpoints.getWorldProject, 'function');
    assert.strictEqual(typeof Endpoints.getWorldEntity, 'function');
    assert.strictEqual(typeof Endpoints.getWorldDependencies, 'function');
    assert.strictEqual(typeof Endpoints.getWorldChanges, 'function');
    assert.strictEqual(typeof Endpoints.refreshWorld, 'function');
    assert.strictEqual(typeof Endpoints.createWorldSnapshot, 'function');
    assert.strictEqual(typeof Endpoints.getWorldHealth, 'function');
  });

  await t.test('EnvironmentView renders header, action buttons, and metric cards (Spec 93, 148)', async () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const mockApi = {
      getWorldOverview: async () => ({
        data: {
          projects_count: 3,
          active_tasks_count: 2,
          connected_devices_count: 2,
          healthy_services_count: 4,
          degraded_services_count: 1,
          synced_repos_count: 5,
          stale_repos_count: 1,
          automations_count: 3,
          stale_total: 0,
          conflicts_count: 0,
        },
      }),
      getWorldChanges: async () => ({ changes: [] }),
    };

    const view = new EnvironmentView({ container: mockContainer, api: mockApi });
    await view.render();

    const html = mockContainer.innerHTML;
    assert.ok(html.includes('Environment &amp; World Model') || html.includes('Environment & World Model'), 'Header title must be present');
    assert.ok(html.includes('id="envRefreshBtn"'), 'Reconcile button must be present');
    assert.ok(html.includes('id="envSnapshotBtn"'), 'Create Snapshot button must be present');
    assert.ok(html.includes('Projects'), 'Projects metric card must be present');
    assert.ok(html.includes('Active Tasks'), 'Active Tasks metric card must be present');
    assert.ok(html.includes('Connected Devices'), 'Connected Devices metric card must be present');
    assert.ok(html.includes('Healthy Services'), 'Healthy Services metric card must be present');
  });

  await t.test('EnvironmentView renders stale warning banner when stale entities exist (Spec 95)', async () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const mockApi = {
      getWorldOverview: async () => ({
        data: {
          projects_count: 1,
          active_tasks_count: 0,
          connected_devices_count: 1,
          healthy_services_count: 2,
          degraded_services_count: 0,
          synced_repos_count: 1,
          stale_repos_count: 1,
          automations_count: 0,
          stale_total: 3,
          conflicts_count: 0,
        },
      }),
      getWorldChanges: async () => ({ changes: [] }),
    };

    const view = new EnvironmentView({ container: mockContainer, api: mockApi });
    await view.render();

    const html = mockContainer.innerHTML;
    assert.ok(html.includes('id="staleAlertBanner"'), 'Stale warning banner must be displayed');
    assert.ok(html.includes('3 entity observation(s) have exceeded freshness policies'), 'Stale count must be shown');
  });

  await t.test('EnvironmentView renders state conflict banner when conflicts exist (Spec 96)', async () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const mockApi = {
      getWorldOverview: async () => ({
        data: {
          projects_count: 1,
          active_tasks_count: 0,
          connected_devices_count: 1,
          healthy_services_count: 1,
          degraded_services_count: 0,
          synced_repos_count: 1,
          stale_repos_count: 0,
          automations_count: 0,
          stale_total: 0,
          conflicts_count: 2,
        },
      }),
      getWorldChanges: async () => ({ changes: [] }),
    };

    const view = new EnvironmentView({ container: mockContainer, api: mockApi });
    await view.render();

    const html = mockContainer.innerHTML;
    assert.ok(html.includes('id="conflictAlertBanner"'), 'Conflict banner must be displayed');
    assert.ok(html.includes('2 state update conflict(s) resolved via authoritative source priority'), 'Conflict count must be shown');
  });

  await t.test('AppShell renders Environment navigation item under COMMAND CENTER', () => {
    const mockStore = {
      getState: () => ({
        emergencyStop: { is_stopped: false },
        activeProject: null,
        projects: [],
        unreadNotificationCount: 0,
        currentView: 'environment',
        pendingApprovals: [],
        activeTasksCount: 0,
      }),
    };

    const shell = new AppShell({ store: mockStore });
    const html = shell.render();

    assert.ok(html.includes("window.kairoApp.navigateTo('environment')"), 'Environment navigation button must exist');
    assert.ok(html.includes('Environment'), 'Environment nav text must exist');
  });
});

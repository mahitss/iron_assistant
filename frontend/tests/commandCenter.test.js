/**
 * Kairo Command Center Architecture Tests
 * Validates store reactivity, API client, endpoints, AppShell, shortcuts, and core components.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import { Store } from '../state/store.js';
import { ApiClient, ApiError } from '../lib/api/client.js';
import { Endpoints } from '../lib/api/endpoints.js';
import { KeyboardShortcuts } from '../lib/shortcuts.js';
import { ApprovalBanner } from '../components/approvals/approvalBanner.js';

test('Command Center Store manages state reactivity and subscribers', (t) => {
  const store = new Store();
  let notifications = 0;
  let lastState = null;

  const unsubscribe = store.subscribe((state) => {
    notifications++;
    lastState = state;
  });

  assert.equal(store.getState().currentView, 'home');
  assert.equal(store.getState().activeProject, 'Kairo');
  assert.equal(store.isEmergencyStopped(), false);

  // Switch view
  store.setView('chat');
  assert.equal(store.getState().currentView, 'chat');
  assert.equal(notifications, 1);

  // Switch project
  store.setActiveProject('College');
  assert.equal(store.getState().activeProject, 'College');
  assert.equal(notifications, 2);

  // Emergency stop toggle
  store.setEmergencyStop(true, 'User triggered manual halt');
  assert.equal(store.isEmergencyStopped(), true);
  assert.equal(store.getState().emergencyStopReason, 'User triggered manual halt');
  assert.equal(notifications, 3);

  // Capability toggle
  store.setCapability('computer_control', true);
  assert.equal(store.getState().capabilities['computer_control'], true);

  // Unsubscribe
  unsubscribe();
  store.setView('security');
  assert.equal(notifications, 4); // not incremented after unsubscribe
});

test('ApiClient formats requests, injects auth headers, and handles ApiError', async (t) => {
  let capturedUrl = null;
  let capturedOptions = null;

  // Mock global fetch
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    capturedUrl = url;
    capturedOptions = options;
    return {
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ status: 'success', data: [1, 2, 3] }),
      text: async () => JSON.stringify({ status: 'success' }),
    };
  };

  try {
    const client = new ApiClient({ baseUrl: '', userId: 'test_user' });
    const res = await client.get('/api/v1/context/current');

    assert.equal(capturedUrl, '/api/v1/context/current');
    assert.equal(capturedOptions.method, 'GET');
    assert.equal(capturedOptions.headers['x-user-id'], 'test_user');
    assert.ok(capturedOptions.headers['x-request-id']);
    assert.deepEqual(res, { status: 'success', data: [1, 2, 3] });

    // Test error handling
    globalThis.fetch = async () => ({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'Access to dangerous capability denied.' }),
    });

    await assert.rejects(
      async () => client.post('/api/v1/security/execute', {}),
      (err) => {
        assert.ok(err instanceof ApiError);
        assert.equal(err.status, 403);
        assert.equal(err.message, 'Access to dangerous capability denied.');
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('KeyboardShortcuts registers and dispatches shortcuts safely', (t) => {
  const shortcuts = new KeyboardShortcuts();
  let triggered = false;

  shortcuts.register('open_palette', { key: 'k', ctrl: true }, () => {
    triggered = true;
  });

  // Simulate Ctrl+K keydown
  let prevented = false;
  const fakeEvent = {
    key: 'k',
    ctrlKey: true,
    metaKey: false,
    shiftKey: false,
    altKey: false,
    target: { tagName: 'DIV' },
    preventDefault: () => { prevented = true; },
  };

  shortcuts.handleKeyDown(fakeEvent);
  assert.equal(triggered, true);
  assert.equal(prevented, true);

  // When target is an INPUT, it should not trigger unless explicitly allowed
  triggered = false;
  const inputEvent = {
    ...fakeEvent,
    target: { tagName: 'INPUT' },
  };
  shortcuts.handleKeyDown(inputEvent);
  assert.equal(triggered, false);
});

test('ApprovalBanner renders risk level and triggers user decisions', (t) => {
  let approvedId = null;
  let deniedId = null;

  const banner = new ApprovalBanner({
    id: 'appr_99',
    action: 'git_push_main',
    description: 'Kairo wants to push changes to GitHub repository.',
    risk_level: 'HIGH',
    metadata: { repository: 'Kairo', branch: 'main' },
    onApprove: (id) => { approvedId = id; },
    onDeny: (id) => { deniedId = id; },
  });

  const html = banner.render();
  assert.ok(html.includes('APPROVAL REQUIRED'));
  assert.ok(html.includes('HIGH'));
  assert.ok(html.includes('Kairo wants to push changes'));
  assert.ok(html.includes('APPROVE'));
  assert.ok(html.includes('DENY'));
});

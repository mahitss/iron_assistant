import test from 'node:test';
import assert from 'node:assert/strict';
import { Endpoints } from '../lib/api/endpoints.js';
import { SettingsView } from '../components/settings/settingsView.js';

test('Kairo Identity, Session Continuity, Device Trust, and Presence Tests (Task 33)', async (t) => {
  await t.test('Endpoints defines all required Identity, Session, Trust, and Handoff methods (Spec 116)', () => {
    assert.strictEqual(typeof Endpoints.getSessions, 'function');
    assert.strictEqual(typeof Endpoints.createSession, 'function');
    assert.strictEqual(typeof Endpoints.revokeSession, 'function');
    assert.strictEqual(typeof Endpoints.revokeAllSessions, 'function');
    assert.strictEqual(typeof Endpoints.getPresence, 'function');
    assert.strictEqual(typeof Endpoints.sendPresenceHeartbeat, 'function');
    assert.strictEqual(typeof Endpoints.getOnlineStatus, 'function');
    assert.strictEqual(typeof Endpoints.createHandoff, 'function');
    assert.strictEqual(typeof Endpoints.completeHandoff, 'function');
    assert.strictEqual(typeof Endpoints.resolveTaskContinuity, 'function');
    assert.strictEqual(typeof Endpoints.resolveDeviceTarget, 'function');
    assert.strictEqual(typeof Endpoints.trustDevice, 'function');
    assert.strictEqual(typeof Endpoints.initiateDevicePairing, 'function');
    assert.strictEqual(typeof Endpoints.consumeDevicePairing, 'function');
  });

  await t.test('SettingsView renders Active Sessions section in Security Tab (Spec 77, 78)', async () => {
    const mockContainer = {
      innerHTML: '',
      querySelector: () => null,
      querySelectorAll: () => [],
    };

    const view = new SettingsView(mockContainer);
    view.activeTab = 'security';
    const html = view._renderSecurityTab();

    assert.ok(html.includes('ACTIVE SESSIONS'), 'Active Sessions title must be present');
    assert.ok(html.includes('id="refresh-sessions-btn"'), 'Refresh sessions button must be present');
    assert.ok(html.includes('id="signout-everywhere-btn"'), 'Sign Out Everywhere button must be present');
    assert.ok(html.includes('id="active-sessions-list"'), 'Active sessions container must be present');
  });

  await t.test('SettingsView renders Session Cards with correct client icons (Spec 77, 124)', () => {
    const view = new SettingsView({});
    const mockSession = {
      session_id: 'sess_1234567890abcdef',
      user_id: 'user_alice',
      client_type: 'WEB',
      device_id: 'dev_mac',
      status: 'ACTIVE',
      created_at: new Date().toISOString(),
      last_activity_at: new Date().toISOString(),
    };

    const cardHtml = view._renderSessionCard(mockSession);
    assert.ok(cardHtml.includes('🌐'), 'Web client icon must render');
    assert.ok(cardHtml.includes('WEB Session'), 'Client type label must render');
    assert.ok(cardHtml.includes('● Active'), 'Active badge must render');
    assert.ok(cardHtml.includes('Sign Out'), 'Sign Out button must render');
    assert.ok(cardHtml.includes('data-id="sess_1234567890abcdef"'), 'Session ID bound to button');
  });

  await t.test('SettingsView renders Device Cards with Trust Status badges and Pair button (Spec 76, 123)', () => {
    const view = new SettingsView({});
    const tabHtml = view._renderDevicesTab();
    assert.ok(tabHtml.includes('id="pair-device-modal-btn"'), 'Pair New Device button must render');

    const mockTrustedDevice = {
      id: 'dev_macbook_01',
      device_name: 'Workstation Mac',
      os_name: 'darwin',
      os_version: '14.5',
      companion_version: '1.1.0',
      status: 'ACTIVE',
      trust_status: 'TRUSTED',
      computer_control_enabled: false,
      voice_enabled: true,
      camera_enabled: false,
      filesystem_enabled: false,
    };

    const cardHtml = view._renderDeviceCard(mockTrustedDevice);
    assert.ok(cardHtml.includes('🛡️ Trusted'), 'Trusted badge must render');
    assert.ok(cardHtml.includes('● Online'), 'Online status badge must render');
    assert.ok(cardHtml.includes('Manage'), 'Manage button must render');
    assert.ok(cardHtml.includes('Revoke'), 'Revoke button must render');
  });

  await t.test('SettingsView shows Trust Device button for untrusted devices (Spec 12)', () => {
    const view = new SettingsView({});
    const mockUntrusted = {
      id: 'dev_new_laptop',
      device_name: 'New Laptop',
      os_name: 'windows',
      status: 'ACTIVE',
      trust_status: 'UNTRUSTED',
    };

    const cardHtml = view._renderDeviceCard(mockUntrusted);
    assert.ok(cardHtml.includes('⚠️ UNTRUSTED') || cardHtml.includes('Untrusted'), 'Untrusted badge must render');
    assert.ok(cardHtml.includes('Trust Device'), 'Trust Device button must be present for untrusted device');
  });
});

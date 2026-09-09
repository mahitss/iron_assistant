import test from 'node:test';
import assert from 'node:assert/strict';
import { SettingsView } from '../components/settings/settingsView.js';
import { SecurityView } from '../components/security/securityView.js';

test('Frontend Companion & Device Management Tests', async (t) => {
  await t.test('SettingsView renders Devices tab structure', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new SettingsView(mockContainer);
    view.activeTab = 'devices';
    const html = view._renderDevicesTab();

    assert.match(html, /DEVICES/);
    assert.match(html, /devices-container/);
    assert.match(html, /companion\.src\.main register/);
  });

  await t.test('SettingsView renders device card with capabilities and status', () => {
    const mockContainer = { innerHTML: '', querySelectorAll: () => [], querySelector: () => null };
    const view = new SettingsView(mockContainer);
    const mockDevice = {
      id: 'dev_12345678',
      device_name: 'Workstation Alpha',
      os_name: 'Windows',
      os_version: '11',
      companion_version: '1.0.0',
      status: 'ACTIVE',
      computer_control_enabled: false,
      microphone_enabled: true,
      camera_enabled: false,
      filesystem_restricted: true,
      allowed_paths: ['C:\\Projects'],
      last_seen_at: '2026-09-09T10:00:00Z',
    };

    const cardHtml = view._renderDeviceCard(mockDevice);
    assert.match(cardHtml, /Workstation Alpha/);
    assert.match(cardHtml, /● Online/);
    assert.match(cardHtml, /Computer Control:/);
    assert.match(cardHtml, /OFF/);
    assert.match(cardHtml, /Voice:/);
    assert.match(cardHtml, /Ready/);
    assert.match(cardHtml, /Manage/);
    assert.match(cardHtml, /Revoke/);
  });

  await t.test('SecurityView renders Device Security section with defense in depth', () => {
    const view = new SecurityView({
      devices: [
        {
          id: 'dev_888',
          device_name: 'Studio Desktop',
          status: 'ACTIVE',
          computer_control_enabled: false,
          microphone_enabled: false,
          camera_enabled: false,
        },
      ],
    });

    const html = view.render();
    assert.match(html, /DEVICE SECURITY/);
    assert.match(html, /Studio Desktop/);
    assert.match(html, /Cloud Authorization/);
    assert.match(html, /Local Policy/);
    assert.match(html, /Emergency Stop/);
    assert.match(html, /READY/);
  });
});

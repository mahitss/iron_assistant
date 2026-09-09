/**
 * Kairo Settings View
 * Centralized configuration for general preferences, appearance, voice, context, notifications, and security.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class SettingsView {
  constructor(container) {
    this.container = container;
    this.activeTab = 'general';
    this.settings = {
      theme: 'dark',
      soundEnabled: true,
      contextExtraction: true,
      maxMemoriesInContext: 5,
      voiceSpeed: 1.0,
      autoListenAfterSpeak: false,
      notifyOnCritical: true,
      notifyOnAutomations: true,
      autoDismissAfterHours: 24,
      requireStrictApprovals: true,
    };
  }

  async render() {
    this.container.innerHTML = `
      <div class="settings-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Settings</h1>
            <p class="page-subtitle">Configure assistant behavior, interfaces, memory limits, and security thresholds</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-primary" id="save-all-settings-btn">Save Changes</button>
          </div>
        </header>

        <div class="settings-layout">
          <nav class="settings-sidebar" aria-label="Settings categories">
            <button class="settings-nav-btn active" data-tab="general">General</button>
            <button class="settings-nav-btn" data-tab="appearance">Appearance</button>
            <button class="settings-nav-btn" data-tab="voice">Voice</button>
            <button class="settings-nav-btn" data-tab="context">Context & Memory</button>
            <button class="settings-nav-btn" data-tab="notifications">Notifications</button>
            <button class="settings-nav-btn" data-tab="security">Security</button>
            <button class="settings-nav-btn" data-tab="devices">Devices</button>
          </nav>

          <section class="settings-content-panel" id="settings-panel-body">
            ${this._renderTabContent()}
          </section>
        </div>
      </div>
    `;

    this._bindEvents();
    if (this.activeTab === 'devices') {
      this._loadDevices();
    }
  }

  _bindEvents() {
    const navBtns = this.container.querySelectorAll('.settings-nav-btn');
    navBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeTab = btn.dataset.tab;
        const panelBody = this.container.querySelector('#settings-panel-body');
        if (panelBody) {
          panelBody.innerHTML = this._renderTabContent();
          if (this.activeTab === 'devices') {
            this._loadDevices();
          }
        }
      });
    });

    const saveBtn = this.container.querySelector('#save-all-settings-btn');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => {
        saveBtn.innerText = 'Saved!';
        setTimeout(() => { saveBtn.innerText = 'Save Changes'; }, 1500);
      });
    }
  }

  _renderTabContent() {
    switch (this.activeTab) {
      case 'general':
        return `
          <div class="settings-section">
            <h2 class="settings-section-title">General Preferences</h2>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Assistant Persona</strong>
                <p>Kairo behaves with a calm, technical, and restrained tone.</p>
              </div>
              <span class="badge badge-info">Fixed: Kairo v1.1</span>
            </div>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>User Identifier</strong>
                <p>Scoped identifier used for multi-tenant isolation and memory routing.</p>
              </div>
              <input type="text" class="input-field font-mono" value="default_user" readonly style="max-width: 220px;" />
            </div>
          </div>
        `;

      case 'appearance':
        return `
          <div class="settings-section">
            <h2 class="settings-section-title">Appearance & Theme</h2>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Color Theme</strong>
                <p>Command Center defaults to a sleek, dark glassmorphism palette.</p>
              </div>
              <select class="input-field" style="max-width: 180px;">
                <option value="dark" selected>Kairo Dark (Default)</option>
                <option value="high-contrast">High Contrast</option>
              </select>
            </div>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Motion & Animations</strong>
                <p>Subtle transitions for streaming chunks and agent progress.</p>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" checked />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        `;

      case 'voice':
        return `
          <div class="settings-section">
            <h2 class="settings-section-title">Voice Interaction</h2>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Explicit Activation</strong>
                <p>Microphone is only activated upon pressing the push-to-talk button.</p>
              </div>
              <span class="badge badge-success">Enforced</span>
            </div>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Text-to-Speech Output</strong>
                <p>Synthesize audible responses for completed actions.</p>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" checked />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        `;

      case 'context':
        return `
          <div class="settings-section">
            <h2 class="settings-section-title">Personal Context & Memory</h2>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Active Context Injection</strong>
                <p>Assemble relevant project files, active branch, and long-term memories into chat context.</p>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" checked />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Max Memories in Context</strong>
                <p>Limits number of ranked long-term memory items passed to supervisor.</p>
              </div>
              <input type="number" class="input-field" value="5" min="1" max="20" style="max-width: 100px;" />
            </div>
          </div>
        `;

      case 'notifications':
        return `
          <div class="settings-section">
            <h2 class="settings-section-title">Proactive Alerts & Notifications</h2>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>CI & Build Failure Alerts</strong>
                <p>Immediately notify when monitored repositories experience failures.</p>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" checked />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Pending Approval Badges</strong>
                <p>Show prominent count badge when actions require your human authorization.</p>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" checked />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        `;

      case 'security':
        return `
          <div class="settings-section">
            <h2 class="settings-section-title">Security Center Policies</h2>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Strict Human-In-The-Loop Approvals</strong>
                <p>Requires explicit click authorization for code execution, file writes, and external API requests.</p>
              </div>
              <span class="badge badge-success">Always Required</span>
            </div>
            <div class="setting-row">
              <div class="setting-meta">
                <strong>Emergency Stop Availability</strong>
                <p>Top-right security indicator provides immediate kill switch for all active actions.</p>
              </div>
              <span class="badge badge-info">Armed</span>
            </div>
          </div>
        `;

      case 'devices':
        return this._renderDevicesTab();

      default:
        return '';
    }
  }

  _renderDevicesTab() {
    return `
      <div class="settings-section">
        <div class="card-header-flex" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
          <div>
            <h2 class="settings-section-title">DEVICES</h2>
            <p class="settings-section-desc" style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
              Manage paired local runtime companions, hardware capabilities, and cryptographic credentials.
            </p>
          </div>
          <button class="btn btn-secondary" id="refresh-devices-btn" style="font-size: 0.8rem;">↻ Refresh</button>
        </div>

        <div id="devices-container" class="devices-grid">
          <div class="loading-spinner" style="padding: 2rem; text-align: center; color: var(--text-muted);">
            Scanning paired devices...
          </div>
        </div>

        <div class="card" style="margin-top: 2rem; background: rgba(0, 0, 0, 0.2); border: 1px dashed var(--border-glass); border-radius: var(--radius-sm); padding: 1.25rem;">
          <h4 style="font-size: 0.9rem; margin-bottom: 0.5rem; color: var(--text-main);">Pair a New Local Device</h4>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem;">
            Install and run the Kairo Companion daemon on your workstation. Devices authenticate using unique cryptographic identities.
          </p>
          <code class="font-mono" style="display: block; background: #0f172a; padding: 0.65rem 1rem; border-radius: 4px; font-size: 0.8rem; color: #38bdf8;">
            python -m companion.src.main register --url http://localhost:8000 --token &lt;USER_SESSION_TOKEN&gt;
          </code>
        </div>
      </div>
    `;
  }

  async _loadDevices() {
    const container = this.container.querySelector('#devices-container');
    if (!container) return;

    const refreshBtn = this.container.querySelector('#refresh-devices-btn');
    if (refreshBtn) {
      refreshBtn.onclick = () => this._loadDevices();
    }

    try {
      const devices = await Endpoints.listDevices(true);
      if (!Array.isArray(devices) || devices.length === 0) {
        container.innerHTML = `
          <div class="empty-state-box" style="grid-column: 1 / -1; padding: 2.5rem; text-align: center; background: rgba(0,0,0,0.2); border-radius: var(--radius-sm);">
            <span style="font-size: 2rem; display: block; margin-bottom: 0.5rem;">🖥️</span>
            <strong>No devices currently paired</strong>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">
              Connect your first desktop or laptop runtime using the registration command below.
            </p>
          </div>
        `;
        return;
      }

      container.innerHTML = devices.map(d => this._renderDeviceCard(d)).join('');
      this._bindDeviceCardEvents(devices);
    } catch (err) {
      container.innerHTML = `
        <div class="empty-state-box" style="grid-column: 1 / -1; padding: 1.5rem; text-align: center; color: #ef4444;">
          Failed to load devices: ${this._escapeHtml(err.message)}
        </div>
      `;
    }
  }

  _renderDeviceCard(device) {
    const isOnline = device.status === 'ACTIVE';
    const isRevoked = device.status === 'REVOKED';
    const badgeClass = isOnline ? 'badge-success' : (isRevoked ? 'badge-danger' : 'badge-warning');
    const badgeText = isOnline ? '● Online' : (isRevoked ? '✕ Revoked' : `○ ${device.status}`);

    return `
      <div class="device-card" id="device-card-${device.id}">
        <div class="device-card-header">
          <div class="device-title-col">
            <div class="device-name">
              <span class="device-icon">🖥️</span>
              <strong>${this._escapeHtml(device.device_name)}</strong>
            </div>
            <div class="device-meta-sub">
              ${this._escapeHtml(device.os_name || 'OS')} ${this._escapeHtml(device.os_version || '')} &bull; Companion ${this._escapeHtml(device.companion_version || '1.0.0')}
            </div>
          </div>
          <span class="badge ${badgeClass}">${badgeText}</span>
        </div>

        <div class="device-capabilities-summary">
          <div class="cap-item">
            <span class="cap-label">Computer Control:</span>
            <span class="cap-status ${device.computer_control_enabled ? 'status-warn' : 'status-muted'}">
              ${device.computer_control_enabled ? 'ARMED' : 'OFF'}
            </span>
          </div>
          <div class="cap-item">
            <span class="cap-label">Voice:</span>
            <span class="cap-status ${device.microphone_enabled ? 'status-active' : 'status-muted'}">
              ${device.microphone_enabled ? 'Ready' : 'OFF'}
            </span>
          </div>
          <div class="cap-item">
            <span class="cap-label">Camera:</span>
            <span class="cap-status ${device.camera_enabled ? 'status-active' : 'status-muted'}">
              ${device.camera_enabled ? 'Ready' : 'OFF'}
            </span>
          </div>
          <div class="cap-item">
            <span class="cap-label">Filesystem:</span>
            <span class="cap-status ${device.filesystem_restricted ? 'status-active' : 'status-muted'}">
              ${device.filesystem_restricted ? 'Restricted' : 'OFF'}
            </span>
          </div>
        </div>

        <div class="device-card-actions">
          <button class="btn btn-secondary btn-sm manage-dev-btn" data-id="${device.id}">Manage</button>
          ${!isRevoked ? `
            <button class="btn btn-danger btn-sm revoke-dev-btn" data-id="${device.id}" data-name="${this._escapeHtml(device.device_name)}">Revoke</button>
          ` : ''}
        </div>
      </div>
    `;
  }

  _bindDeviceCardEvents(devices) {
    this.container.querySelectorAll('.revoke-dev-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const deviceId = e.currentTarget.dataset.id;
        const deviceName = e.currentTarget.dataset.name;
        if (confirm(`Revoke device "${deviceName}"? It will be disconnected immediately and cannot reconnect without fresh pairing.`)) {
          try {
            await Endpoints.revokeDevice(deviceId);
            await this._loadDevices();
          } catch (err) {
            alert(`Failed to revoke device: ${err.message}`);
          }
        }
      });
    });

    this.container.querySelectorAll('.manage-dev-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const deviceId = e.currentTarget.dataset.id;
        const device = devices.find(d => d.id === deviceId);
        if (device) this._showDeviceDetailModal(device);
      });
    });
  }

  _showDeviceDetailModal(device) {
    const existing = document.getElementById('device-detail-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'device-detail-modal';
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-dialog" style="max-width: 520px; background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1.5rem; color: #f3f4f6;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.75rem;">
          <h3 style="font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; margin: 0;">
            <span>🖥️</span> ${this._escapeHtml(device.device_name)}
          </h3>
          <button id="close-device-modal-btn" style="background: none; border: none; color: #9ca3af; font-size: 1.25rem; cursor: pointer;">&times;</button>
        </div>

        <div style="display: flex; flex-direction: column; gap: 0.75rem; font-size: 0.85rem;">
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 0.4rem;">
            <span style="color: #9ca3af;">Device ID:</span>
            <span class="font-mono" style="font-size: 0.75rem;">${this._escapeHtml(device.id)}</span>
          </div>
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 0.4rem;">
            <span style="color: #9ca3af;">OS / Platform:</span>
            <span>${this._escapeHtml(device.os_name)} ${this._escapeHtml(device.os_version)}</span>
          </div>
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 0.4rem;">
            <span style="color: #9ca3af;">Companion Version:</span>
            <span>${this._escapeHtml(device.companion_version || '1.0.0')}</span>
          </div>
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 0.4rem;">
            <span style="color: #9ca3af;">Last Seen:</span>
            <span>${device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : 'Never'}</span>
          </div>
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 0.4rem;">
            <span style="color: #9ca3af;">Security Status:</span>
            <span class="status-active">Enforced (Defense in Depth)</span>
          </div>

          <div style="margin-top: 0.5rem;">
            <strong style="display: block; margin-bottom: 0.5rem;">Remote Capability Toggles:</strong>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="display: flex; justify-content: space-between; align-items: center;">
                <span>Computer Control (Mouse/Keyboard)</span>
                <input type="checkbox" id="modal-cap-computer" ${device.computer_control_enabled ? 'checked' : ''} ${device.status === 'REVOKED' ? 'disabled' : ''}>
              </label>
              <label style="display: flex; justify-content: space-between; align-items: center;">
                <span>Microphone Access</span>
                <input type="checkbox" id="modal-cap-mic" ${device.microphone_enabled ? 'checked' : ''} ${device.status === 'REVOKED' ? 'disabled' : ''}>
              </label>
              <label style="display: flex; justify-content: space-between; align-items: center;">
                <span>Camera Access</span>
                <input type="checkbox" id="modal-cap-cam" ${device.camera_enabled ? 'checked' : ''} ${device.status === 'REVOKED' ? 'disabled' : ''}>
              </label>
            </div>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; margin-top: 1.5rem; pt: 1rem; border-top: 1px solid rgba(255,255,255,0.06);">
          ${device.status !== 'REVOKED' ? `
            <button class="btn btn-danger btn-sm" id="modal-revoke-btn">Revoke Device</button>
          ` : `<span></span>`}
          <button class="btn btn-primary btn-sm" id="modal-save-btn">Save Changes</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('#close-device-modal-btn').onclick = () => modal.remove();
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };

    const revokeBtn = modal.querySelector('#modal-revoke-btn');
    if (revokeBtn) {
      revokeBtn.onclick = async () => {
        if (confirm(`Revoke device "${device.device_name}" immediately?`)) {
          try {
            await Endpoints.revokeDevice(device.id);
            modal.remove();
            await this._loadDevices();
          } catch (err) {
            alert(`Revocation failed: ${err.message}`);
          }
        }
      };
    }

    modal.querySelector('#modal-save-btn').onclick = async () => {
      const computer_control_enabled = modal.querySelector('#modal-cap-computer').checked;
      const microphone_enabled = modal.querySelector('#modal-cap-mic').checked;
      const camera_enabled = modal.querySelector('#modal-cap-cam').checked;

      try {
        await Endpoints.updateDevice(device.id, {
          computer_control_enabled,
          microphone_enabled,
          camera_enabled,
        });
        modal.remove();
        await this._loadDevices();
      } catch (err) {
        alert(`Failed to update device settings: ${err.message}`);
      }
    };
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}


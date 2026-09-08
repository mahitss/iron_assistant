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
          </nav>

          <section class="settings-content-panel" id="settings-panel-body">
            ${this._renderTabContent()}
          </section>
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _bindEvents() {
    const navBtns = this.container.querySelectorAll('.settings-nav-btn');
    navBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeTab = btn.dataset.tab;
        const panelBody = this.container.querySelector('#settings-panel-body');
        if (panelBody) panelBody.innerHTML = this._renderTabContent();
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

      default:
        return '';
    }
  }
}

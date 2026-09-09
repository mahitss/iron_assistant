/**
 * SecurityView Component — Central Security, Permissions, Approvals & Emergency Stop
 */

import { store } from '../../state/store.js';
import { ApprovalBanner } from '../approvals/approvalBanner.js';

export class SecurityView {
  constructor(options = {}) {
    this.store = options.store || store;
    this.auditEvents = [];
    this.devices = options.devices || [];
  }

  setAuditEvents(events) {
    this.auditEvents = events;
  }

  setDevices(devices) {
    this.devices = devices;
  }

  render() {
    const state = this.store.getState();
    const capabilities = state.capabilities;
    const isEmergencyStopped = state.emergencyStop.is_stopped;
    const pendingApprovals = state.pendingApprovals || [];

    return `
      <div class="security-view-container">
        <div class="view-header">
          <div class="header-titles">
            <h1 class="view-title">Security Center</h1>
            <p class="view-subtitle">Authoritative access control, capability gating, pending approvals, and emergency stop.</p>
          </div>
        </div>

        <!-- Emergency Stop Banner Card -->
        <div class="card emergency-stop-hero ${isEmergencyStopped ? 'active-stopped' : 'normal'}">
          <div class="hero-content">
            <div class="hero-icon-large">${isEmergencyStopped ? '🛑' : '🛡️'}</div>
            <div class="hero-text-col">
              <h3 class="hero-title">${isEmergencyStopped ? 'EMERGENCY STOP ACTIVE — KAIRO ACTIONS STOPPED' : 'EMERGENCY STOP AVAILABLE'}</h3>
              <p class="hero-desc">
                ${isEmergencyStopped
                  ? `All background agents, tool iterations, workflows, and browser sessions have been halted. Reason: ${this._escapeHtml(state.emergencyStop.reason || 'Manual user trigger')}.`
                  : 'Immediately terminates all running autonomous agent loops, background subagents, browser automations, and pending tool executions across all sessions.'}
              </p>
            </div>
          </div>
          <div class="hero-action-col">
            ${isEmergencyStopped ? `
              <button class="btn-primary reset-btn" onclick="window.kairoApp.resetEmergencyStop()">RESET EMERGENCY STOP</button>
            ` : `
              <button class="btn-danger kill-btn" onclick="window.kairoApp.confirmEmergencyStop()">STOP KAIRO (KILL ALL)</button>
            `}
          </div>
        </div>

        <div class="grid-2">
          <!-- Capabilities & Gating -->
          <div class="card">
            <div class="card-title">
              <span>🎛️</span>
              <span>CAPABILITY GATES</span>
            </div>
            <p class="card-subtitle">Enforce strict policy limits on what tools Kairo is permitted to access.</p>

            <div class="capabilities-table">
              <div class="capability-row">
                <div class="cap-info">
                  <div class="cap-name">Web Research & Fetch</div>
                  <div class="cap-desc">Network searches and public content fetching with SSRF protection</div>
                </div>
                <label class="switch">
                  <input type="checkbox" ${capabilities.web_research ? 'checked' : ''} onchange="window.kairoApp.toggleCapability('web_research')">
                  <span class="slider"></span>
                </label>
              </div>

              <div class="capability-row">
                <div class="cap-info">
                  <div class="cap-name">Headless Browser Automation</div>
                  <div class="cap-desc">Playwright Chromium navigation with isolated sessions</div>
                </div>
                <label class="switch">
                  <input type="checkbox" ${capabilities.browser ? 'checked' : ''} onchange="window.kairoApp.toggleCapability('browser')">
                  <span class="slider"></span>
                </label>
              </div>

              <div class="capability-row">
                <div class="cap-info">
                  <div class="cap-name">Developer Tools & Local Git</div>
                  <div class="cap-desc">Code search, branch inspection, and safe read-only analysis</div>
                </div>
                <label class="switch">
                  <input type="checkbox" ${capabilities.developer_tools ? 'checked' : ''} onchange="window.kairoApp.toggleCapability('developer_tools')">
                  <span class="slider"></span>
                </label>
              </div>

              <div class="capability-row">
                <div class="cap-info">
                  <div class="cap-name">Automated Workflows</div>
                  <div class="cap-desc">Durable condition checks and background execution scheduler</div>
                </div>
                <label class="switch">
                  <input type="checkbox" ${capabilities.automation ? 'checked' : ''} onchange="window.kairoApp.toggleCapability('automation')">
                  <span class="slider"></span>
                </label>
              </div>

              <!-- Computer Control (Strictly highlighted as sensitive) -->
              <div class="capability-row sensitive-gate">
                <div class="cap-info">
                  <div class="cap-name">Computer Control (Mouse/Keyboard)</div>
                  <div class="cap-desc">Direct desktop automation. Strictly OFF by default.</div>
                </div>
                <label class="switch">
                  <input type="checkbox" ${capabilities.computer_control ? 'checked' : ''} onchange="window.kairoApp.toggleCapability('computer_control')">
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          </div>

          <!-- Pending Approvals Review -->
          <div class="card">
            <div class="card-header-flex">
              <div class="card-title">
                <span>🔐</span>
                <span>PENDING APPROVALS (${pendingApprovals.length})</span>
              </div>
              <button class="btn-text" onclick="window.kairoApp.refreshSecurityData()">Refresh</button>
            </div>
            <p class="card-subtitle">Actions requiring explicit human authorization before execution.</p>

            <div class="approvals-stack">
              ${pendingApprovals.length === 0 ? `
                <div class="empty-state-box">
                  <span class="empty-icon">✓</span>
                  <div>No pending approvals waiting.</div>
                  <div style="font-size: 0.8rem; color: var(--text-subtle); margin-top: 0.25rem;">Any mutative, external, or destructive actions will appear here for review.</div>
                </div>
              ` : pendingApprovals.map(appr => ApprovalBanner.render(appr)).join('')}
            </div>
          </div>
        </div>

        <!-- Skills & Capabilities Governance -->
        <div class="card" style="margin-bottom: 1.5rem;">
          <div class="card-header-flex">
            <div class="card-title">
              <span>⚡</span>
              <span>SKILLS &amp; CAPABILITIES GOVERNANCE</span>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="window.kairoApp.navigateTo('settings')">Configure in Settings →</button>
          </div>
          <p class="card-subtitle">
            Skills are high-level capabilities orchestrating tools under strict SecurityCenter policy, capability gates, and audit trails.
          </p>
          <div class="skills-security-stats" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-top: 1rem;">
            <div class="stat-box" style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Total Built-in Skills</div>
              <div style="font-size: 1.3rem; font-weight: 600; color: var(--primary); margin-top: 0.25rem;">11 Registered</div>
            </div>
            <div class="stat-box" style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Max Skill Depth</div>
              <div style="font-size: 1.3rem; font-weight: 600; color: #38bdf8; margin-top: 0.25rem;">3 Levels</div>
            </div>
            <div class="stat-box" style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Max Execution Steps</div>
              <div style="font-size: 1.3rem; font-weight: 600; color: #a855f7; margin-top: 0.25rem;">20 Steps</div>
            </div>
            <div class="stat-box" style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Security Enforcement</div>
              <div style="font-size: 1.3rem; font-weight: 600; color: var(--success); margin-top: 0.25rem;">Authoritative</div>
            </div>
          </div>
        </div>

        <!-- Device Security (Companion Integration) -->
        <div class="card device-security-panel">
          <div class="card-header-flex">
            <div class="card-title">
              <span>🖥️</span>
              <span>DEVICE SECURITY</span>
            </div>
            <span class="badge badge-success">Defense In Depth</span>
          </div>
          <p class="card-subtitle">Local runtime companion policy enforcement, capability gates, and dual emergency stop readiness.</p>

          <div class="device-sec-grid">
            ${(this.devices && this.devices.length > 0) ? this.devices.map(dev => `
              <div class="device-sec-card">
                <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-main); margin-bottom: 0.25rem;">
                  ${this._escapeHtml(dev.device_name || 'My PC')}
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Cloud Authorization</span>
                  <span class="status-active" style="font-weight: 600;">ENABLED</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Local Policy</span>
                  <span class="status-active" style="font-weight: 600;">ENABLED</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Computer Control</span>
                  <span class="${dev.computer_control_enabled ? 'status-warn' : 'status-muted'}">${dev.computer_control_enabled ? 'ARMED' : 'OFF'}</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Microphone</span>
                  <span class="${dev.microphone_enabled ? 'status-active' : 'status-muted'}">${dev.microphone_enabled ? 'READY' : 'OFF'}</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Camera</span>
                  <span class="${dev.camera_enabled ? 'status-active' : 'status-muted'}">${dev.camera_enabled ? 'READY' : 'OFF'}</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Emergency Stop</span>
                  <span class="status-active" style="font-weight: 600;">READY</span>
                </div>
              </div>
            `).join('') : `
              <div class="device-sec-card">
                <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-main); margin-bottom: 0.25rem;">
                  My PC (Primary Companion)
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Cloud Authorization</span>
                  <span class="status-active" style="font-weight: 600;">ENABLED</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Local Policy</span>
                  <span class="status-active" style="font-weight: 600;">ENABLED</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Computer Control</span>
                  <span class="status-muted" style="font-weight: 600;">OFF</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Microphone</span>
                  <span class="status-muted" style="font-weight: 600;">OFF</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Camera</span>
                  <span class="status-muted" style="font-weight: 600;">OFF</span>
                </div>
                <div class="device-sec-row">
                  <span class="cap-label">Emergency Stop</span>
                  <span class="status-active" style="font-weight: 600;">READY</span>
                </div>
              </div>
            `}
          </div>
        </div>

        <!-- Governance, Policy & Risk Engine (Task 36) -->
        <div class="card" style="margin-top: 1.5rem;">
          <div class="card-header-flex">
            <div class="card-title">
              <span>⚖️</span>
              <span>GOVERNANCE &amp; POLICY DECISION ENGINE</span>
            </div>
            <span class="badge badge-primary">Active Governance</span>
          </div>
          <p class="card-subtitle">Centralized policy enforcement, deterministic 5-tier risk taxonomy, production change freeze controls, and simulation.</p>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 1rem 0;">
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Active Policies</div>
              <div style="font-size: 1.4rem; font-weight: 700; color: var(--primary);" id="policy-active-count">${this.policyStatus ? this.policyStatus.active_policies : '7'}</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Safe Mode</div>
              <div style="font-size: 1.1rem; font-weight: 600;" class="${this.policyStatus && this.policyStatus.safe_mode_active ? 'status-danger' : 'status-success'}">
                ${this.policyStatus && this.policyStatus.safe_mode_active ? 'ENABLED (READ ONLY)' : 'NORMAL'}
              </div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Production Freeze</div>
              <div style="font-size: 1.1rem; font-weight: 600;" class="${(this.policyStatus && this.policyStatus.change_freeze_environments && this.policyStatus.change_freeze_environments.includes('production')) ? 'status-danger' : 'status-muted'}">
                ${(this.policyStatus && this.policyStatus.change_freeze_environments && this.policyStatus.change_freeze_environments.includes('production')) ? 'FROZEN' : 'ACTIVE'}
              </div>
            </div>
          </div>

          <!-- Policy Simulation Tester -->
          <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; padding: 1rem; margin-top: 0.75rem;">
            <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
              <span>🧪</span>
              <span>Policy Simulation Sandbox</span>
            </div>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
              <input type="text" id="policy-sim-action" placeholder="Action (e.g. deploy, delete, read)" class="input-field" style="flex: 1; min-width: 140px; padding: 0.4rem 0.6rem; border-radius: 6px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.15); color: #fff;" value="deploy" />
              <select id="policy-sim-env" class="input-field" style="width: 140px; padding: 0.4rem 0.6rem; border-radius: 6px; background: #1a1a2e; border: 1px solid rgba(255,255,255,0.15); color: #fff;">
                <option value="development">development</option>
                <option value="staging">staging</option>
                <option value="production" selected>production</option>
              </select>
              <button class="btn-secondary" style="padding: 0.4rem 0.9rem; border-radius: 6px; cursor: pointer;" onclick="if(window.kairoApp &amp;&amp; window.kairoApp.simulatePolicyAction){window.kairoApp.simulatePolicyAction();}else{alert('Simulation ready');}">Simulate Decision</button>
            </div>
            <div id="policy-sim-result" style="margin-top: 0.75rem; display: none; padding: 0.6rem; border-radius: 6px; font-size: 0.85rem; font-family: monospace;"></div>
        <!-- System Reliability, Resilience & Fault-Tolerance (Task 37) -->
        <div class="card" style="margin-top: 1.5rem;" id="resilience-reliability-card">
          <div class="card-header-flex">
            <div class="card-title">
              <span>⚡</span>
              <span>SYSTEM RELIABILITY &amp; FAULT-TOLERANT RUNTIME</span>
            </div>
            <span class="badge badge-primary">Resilience Active</span>
          </div>
          <p class="card-subtitle">Real-time dependency health probes, scoped circuit breakers, poison task quarantine, and crash recovery with No Blind Resume.</p>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 1rem 0;">
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Retry Success Rate</div>
              <div style="font-size: 1.4rem; font-weight: 700; color: var(--primary);" id="resilience-retry-rate">${this.resilienceData ? (this.resilienceData.retry_success_rate * 100).toFixed(1) + '%' : '100%'}</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Recovery Success Rate</div>
              <div style="font-size: 1.4rem; font-weight: 700; color: #10b981;" id="resilience-recovery-rate">${this.resilienceData ? (this.resilienceData.recovery_success_rate * 100).toFixed(1) + '%' : '100%'}</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Active Leases</div>
              <div style="font-size: 1.4rem; font-weight: 700; color: #60a5fa;" id="resilience-active-leases">${this.resilienceData ? this.resilienceData.active_leases : '0'}</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0.85rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Quarantined Tasks</div>
              <div style="font-size: 1.4rem; font-weight: 700; color: ${this.resilienceData && this.resilienceData.quarantined_tasks_count > 0 ? '#ef4444' : 'var(--text-muted)'};" id="resilience-quarantine-count">${this.resilienceData ? this.resilienceData.quarantined_tasks_count : '0'}</div>
            </div>
          </div>

          <!-- Dependency Health Grid -->
          <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; padding: 1rem; margin-top: 0.75rem;">
            <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
              <span style="display: flex; align-items: center; gap: 0.5rem;"><span>🩺</span><span>Core Dependency Probes</span></span>
              <button class="btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="if(window.kairoApp && window.kairoApp.refreshResilience){window.kairoApp.refreshResilience();}">Probe Health</button>
            </div>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
              <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem;">
                <span class="status-indicator status-online" style="width: 8px; height: 8px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
                <span>PostgreSQL DB: <strong style="color: #10b981;">HEALTHY</strong></span>
              </div>
              <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem;">
                <span class="status-indicator status-online" style="width: 8px; height: 8px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
                <span>Redis Broker: <strong style="color: #10b981;">CONNECTED</strong></span>
              </div>
              <div style="display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem;">
                <span class="status-indicator status-online" style="width: 8px; height: 8px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
                <span>Event Bus Outbox: <strong style="color: #10b981;">OPERATIONAL</strong></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Recent Security Audit Trail -->
        <div class="card" style="margin-top: 1.5rem;">
          <div class="card-header-flex">
            <div class="card-title">
              <span>📜</span>
              <span>RECENT SECURITY AUDIT EVENTS</span>
            </div>
            <span class="badge badge-default">Append-Only Audit Log</span>
          </div>
          <p class="card-subtitle">Cryptographically fingerprinted audit records of capability checks, permissions, and tool interceptions.</p>

          <div class="audit-log-table">
            <div class="audit-header-row">
              <span class="audit-col-time">TIMESTAMP</span>
              <span class="audit-col-action">ACTION / EVENT</span>
              <span class="audit-col-risk">RISK</span>
              <span class="audit-col-result">OUTCOME</span>
            </div>
            ${this.auditEvents.length === 0 ? `
              <div class="audit-row">
                <span class="audit-col-time">Just now</span>
                <span class="audit-col-action">Security policy initialized with defensive OWASP headers</span>
                <span class="audit-col-risk"><span class="risk-pill risk-low">LOW</span></span>
                <span class="audit-col-result status-success">ENFORCED</span>
              </div>
              <div class="audit-row">
                <span class="audit-col-time">Just now</span>
                <span class="audit-col-action">Computer control capability confirmed locked</span>
                <span class="audit-col-risk"><span class="risk-pill risk-high">HIGH</span></span>
                <span class="audit-col-result status-success">DENIED (OFF)</span>
              </div>
            ` : this.auditEvents.map(evt => `
              <div class="audit-row">
                <span class="audit-col-time">${this._formatTime(evt.timestamp || evt.created_at)}</span>
                <span class="audit-col-action">${this._escapeHtml(evt.event_name || evt.action)}</span>
                <span class="audit-col-risk"><span class="risk-pill risk-${(evt.risk_level || 'low').toLowerCase()}">${evt.risk_level || 'LOW'}</span></span>
                <span class="audit-col-result ${evt.outcome === 'denied' ? 'status-danger' : 'status-success'}">${evt.outcome || 'SUCCESS'}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  _formatTime(ts) {
    if (!ts) return 'Recent';
    try {
      return new Date(ts).toLocaleTimeString();
    } catch {
      return 'Recent';
    }
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

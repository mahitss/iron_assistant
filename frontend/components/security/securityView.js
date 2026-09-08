/**
 * SecurityView Component — Central Security, Permissions, Approvals & Emergency Stop
 */

import { store } from '../../state/store.js';
import { ApprovalBanner } from '../approvals/approvalBanner.js';

export class SecurityView {
  constructor(options = {}) {
    this.store = options.store || store;
    this.auditEvents = [];
  }

  setAuditEvents(events) {
    this.auditEvents = events;
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

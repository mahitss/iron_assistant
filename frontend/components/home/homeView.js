/**
 * HomeView — Kairo Command Center Dashboard
 * Answers "What matters right now?" with active attention items, project summary, quick-action omnibar, and health status.
 */

import { store } from '../../state/store.js';

export class HomeView {
  constructor(options = {}) {
    this.store = options.store || store;
  }

  render() {
    const state = this.store.getState();
    const activeProject = state.activeProject;
    const pendingApprovals = state.pendingApprovals || [];
    const notifications = state.notifications || [];
    const criticalNotifications = notifications.filter(n => n.priority === 'CRITICAL' || n.priority === 'HIGH');
    const health = state.systemHealth || { api: 'healthy', database: 'healthy', ai_provider: 'healthy' };

    // Get time-based greeting
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning.' : hour < 18 ? 'Good afternoon.' : 'Good evening.';

    return `
      <div class="command-center-view">
        <!-- Welcome & Attention Banner -->
        <div class="view-header">
          <div class="header-titles">
            <h1 class="view-title">Command Center</h1>
            <p class="view-subtitle">${greeting} Here is what matters right now across your projects and workflows.</p>
          </div>
        </div>

        <!-- Section 1: What Needs Your Attention -->
        <div class="card attention-card">
          <div class="card-header-flex">
            <div class="card-title">
              <span>⚠️</span>
              <span>WHAT NEEDS YOUR ATTENTION</span>
            </div>
            ${pendingApprovals.length + criticalNotifications.length > 0 ? `
              <span class="badge badge-warning">${pendingApprovals.length + criticalNotifications.length} Action(s) Required</span>
            ` : `
              <span class="badge badge-success">✓ All Nominal</span>
            `}
          </div>

          <div class="attention-items-list">
            ${pendingApprovals.length === 0 && criticalNotifications.length === 0 ? `
              <div class="empty-state-banner">
                <span class="empty-icon">✓</span>
                <div>
                  <div style="font-weight: 500;">No blocking issues or pending approvals.</div>
                  <div style="font-size: 0.85rem; color: var(--text-muted);">All workflows are executing normally within safety parameters.</div>
                </div>
              </div>
            ` : ''}

            <!-- Pending Approvals -->
            ${pendingApprovals.map(appr => `
              <div class="attention-row warning">
                <div class="attention-left">
                  <span class="attention-dot warning"></span>
                  <div>
                    <div class="attention-title">Approval Waiting: ${this._escapeHtml(appr.action_description || appr.tool_name)}</div>
                    <div class="attention-meta">Risk Level: <strong>${appr.risk_level || 'HIGH'}</strong> &bull; Requested by Kairo Core</div>
                  </div>
                </div>
                <div class="attention-actions">
                  <button class="btn-sm btn-primary" onclick="window.kairoApp.navigateTo('security')">Review Approval</button>
                </div>
              </div>
            `).join('')}

            <!-- Critical Notifications -->
            ${criticalNotifications.map(notif => `
              <div class="attention-row danger">
                <div class="attention-left">
                  <span class="attention-dot danger"></span>
                  <div>
                    <div class="attention-title">${this._escapeHtml(notif.title)}</div>
                    <div class="attention-meta">${this._escapeHtml(notif.summary)}</div>
                  </div>
                </div>
                <div class="attention-actions">
                  <button class="btn-sm btn-outline" onclick="window.kairoApp.navigateTo('notifications')">View Alert</button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Section 2: Active Project & Quick Action Grid -->
        <div class="grid-2">
          <!-- Active Project Overview -->
          <div class="card">
            <div class="card-header-flex">
              <div class="card-title">
                <span>📁</span>
                <span>ACTIVE PROJECT</span>
              </div>
              <button class="btn-text" onclick="window.kairoApp.navigateTo('projects')">Switch Project &rarr;</button>
            </div>

            ${activeProject ? `
              <div class="project-summary-box">
                <div class="project-header-row">
                  <h3 class="project-heading">${this._escapeHtml(activeProject.name)}</h3>
                  <span class="status-pill status-${activeProject.status.toLowerCase()}">${activeProject.status}</span>
                </div>
                <p class="project-desc">${this._escapeHtml(activeProject.description || 'Dedicated workspace for repository and autonomous workflow tasks.')}</p>

                <div class="project-details-grid">
                  <div class="detail-item">
                    <span class="detail-label">Repository:</span>
                    <span class="detail-value">${activeProject.repositories && activeProject.repositories.length > 0 ? this._escapeHtml(activeProject.repositories[0]) : 'None linked'}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Workflows:</span>
                    <span class="detail-value">${activeProject.workflows ? activeProject.workflows.length : 0} Active</span>
                  </div>
                </div>

                <div class="recent-bullets">
                  <div class="recent-title">Recent Activity:</div>
                  <div class="bullet-item">&bull; Context Engine resolved active repository anchors</div>
                  <div class="bullet-item">&bull; Safe read permissions enabled for developer tools</div>
                  <div class="bullet-item">&bull; Memory scopes verified for project tenant isolation</div>
                </div>
              </div>
            ` : `
              <div class="empty-state-box">
                <p>No project workspace currently active.</p>
                <button class="btn-primary btn-sm" onclick="window.kairoApp.navigateTo('projects')">+ Create or Select Project</button>
              </div>
            `}
          </div>

          <!-- Quick Action Omnibar -->
          <div class="card">
            <div class="card-title">
              <span>⚡</span>
              <span>QUICK ACTION</span>
            </div>
            <p class="card-subtitle">Directly ask Kairo questions, trigger research, or instruct workflows.</p>

            <form class="quick-action-form" onsubmit="window.kairoApp.handleQuickAction(event)">
              <div class="quick-input-wrapper">
                <input
                  type="text"
                  id="quickActionInput"
                  class="quick-input"
                  placeholder="Ask Kairo anything... (e.g. 'Check why CI failed')"
                  autocomplete="off"
                />
                <button type="submit" class="btn-primary quick-submit-btn">
                  Ask &rarr;
                </button>
              </div>
            </form>

            <div class="suggested-prompts">
              <span class="prompts-label">Suggested:</span>
              <button class="prompt-chip" onclick="window.kairoApp.runSuggestedPrompt('Check why the build is failing')">"Check why the build is failing"</button>
              <button class="prompt-chip" onclick="window.kairoApp.runSuggestedPrompt('What should I work on today?')">"What should I work on today?"</button>
              <button class="prompt-chip" onclick="window.kairoApp.runSuggestedPrompt('Summarize active project context')">"Summarize active project context"</button>
            </div>

            <!-- Compact System Health Card -->
            <div class="system-compact-bar">
              <div class="health-col">
                <span class="health-dot ${health.api === 'healthy' ? 'good' : 'bad'}"></span>
                <span class="health-name">API: ${health.api}</span>
              </div>
              <div class="health-col">
                <span class="health-dot ${health.database === 'healthy' ? 'good' : 'bad'}"></span>
                <span class="health-name">Database: ${health.database}</span>
              </div>
              <div class="health-col">
                <span class="health-dot ${health.ai_provider === 'healthy' ? 'good' : 'bad'}"></span>
                <span class="health-name">AI Provider: ${health.ai_provider}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

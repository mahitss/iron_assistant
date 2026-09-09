/**
 * Kairo Application Shell
 * Renders the primary navigation, top bar with project switcher and emergency stop,
 * and coordinates view switching.
 */

import { store } from '../../state/store.js';

export class AppShell {
  constructor(options = {}) {
    this.store = options.store || store;
    this.container = options.container || null;
  }

  render() {
    const state = this.store.getState();
    const isEmergencyStopped = state.emergencyStop.is_stopped;
    const activeProjectName = state.activeProject ? state.activeProject.name : 'All Projects';
    const unreadCount = state.unreadNotificationCount || 0;

    return `
      <div class="kairo-shell ${isEmergencyStopped ? 'shell-emergency-stopped' : ''}">
        <!-- Top Application Bar -->
        <header class="kairo-topbar" role="banner">
          <div class="topbar-left">
            <button class="mobile-nav-toggle" aria-label="Toggle navigation menu" onclick="window.kairoApp.toggleSidebar()">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
            </button>
            <div class="brand-badge" onclick="window.kairoApp.navigateTo('home')" style="cursor: pointer;">
              <span class="brand-orb">K</span>
              <span class="brand-name">KAIRO</span>
              <span class="brand-version">v1.1</span>
            </div>

            <!-- Active Project Switcher -->
            <div class="project-switcher-dropdown" id="projectSwitcher">
              <button class="project-switcher-btn" onclick="window.kairoApp.toggleProjectDropdown()" aria-haspopup="true" aria-expanded="false" id="projectDropdownBtn">
                <span class="project-icon">📁</span>
                <span class="project-label" id="currentProjectLabel">${this._escapeHtml(activeProjectName)}</span>
                <span class="dropdown-caret">▼</span>
              </button>
              <div class="project-dropdown-menu" id="projectDropdownMenu" style="display: none;" role="menu">
                <div class="dropdown-header">SWITCH PROJECT</div>
                <div id="projectDropdownItems">
                  ${this._renderProjectMenuItems(state.projects, state.activeProject)}
                </div>
                <div class="dropdown-divider"></div>
                <button class="dropdown-action-btn" onclick="window.kairoApp.navigateTo('projects')">+ Manage Projects</button>
              </div>
            </div>
          </div>

          <div class="topbar-center">
            <!-- Command Palette Shortcut Pill -->
            <button class="command-palette-trigger" onclick="window.kairoApp.openCommandPalette()" aria-label="Open command palette (Ctrl+K)">
              <span class="search-icon">🔍</span>
              <span class="trigger-label">Quick Actions...</span>
              <kbd class="shortcut-kbd">Ctrl K</kbd>
            </button>
          </div>

          <div class="topbar-right">
            <!-- System Status Indicator -->
            <div class="system-status-indicator" onclick="window.kairoApp.navigateTo('status')" title="System Health: All operational" style="cursor: pointer;">
              <span class="status-pulse-dot"></span>
              <span class="status-label">Healthy</span>
            </div>

            <!-- Notifications Bell -->
            <button class="notifications-btn" onclick="window.kairoApp.navigateTo('notifications')" aria-label="Notifications (${unreadCount} unread)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
              ${unreadCount > 0 ? `<span class="notification-badge">${unreadCount}</span>` : ''}
            </button>

            <!-- Emergency Stop Control (High Prominence) -->
            <div class="emergency-stop-container">
              ${isEmergencyStopped ? `
                <button class="emergency-stop-btn stopped" onclick="window.kairoApp.resetEmergencyStop()" title="Emergency Stop ACTIVE. Click to reset." aria-live="assertive">
                  <span class="stop-icon">🛑</span>
                  <span class="stop-text">ACTIONS STOPPED</span>
                </button>
              ` : `
                <button class="emergency-stop-btn normal" onclick="window.kairoApp.confirmEmergencyStop()" title="Emergency Stop: Instantly halt all running actions and agents">
                  <span class="stop-icon">🛡️</span>
                  <span class="stop-text">STOP KAIRO</span>
                </button>
              `}
            </div>
          </div>
        </header>

        <!-- Main Layout Body -->
        <div class="kairo-body">
          <!-- Navigation Sidebar -->
          <nav class="kairo-sidebar" id="kairoSidebar" role="navigation" aria-label="Primary Navigation">
            <div class="nav-section">
              <div class="nav-section-title">COMMAND CENTER</div>
              <button class="nav-item ${state.currentView === 'home' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('home')">
                <span class="nav-icon">📊</span>
                <span class="nav-text">Home</span>
              </button>
              <button class="nav-item ${state.currentView === 'chat' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('chat')">
                <span class="nav-icon">💬</span>
                <span class="nav-text">Chat</span>
              </button>
              <button class="nav-item ${state.currentView === 'projects' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('projects')">
                <span class="nav-icon">📁</span>
                <span class="nav-text">Projects</span>
              </button>
              <button class="nav-item ${state.currentView === 'automations' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('automations')">
                <span class="nav-icon">⚡</span>
                <span class="nav-text">Automations</span>
              </button>
              <button class="nav-item ${state.currentView === 'tasks' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('tasks')">
                <span class="nav-icon">🎯</span>
                <span class="nav-text">Tasks</span>
                ${state.activeTasksCount > 0 ? `<span class="pending-pill">${state.activeTasksCount}</span>` : ''}
              </button>
              <button class="nav-item ${state.currentView === 'activity' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('activity')">
                <span class="nav-icon">⏱️</span>
                <span class="nav-text">Activity</span>
              </button>
              <button class="nav-item ${state.currentView === 'security' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('security')">
                <span class="nav-icon">🛡️</span>
                <span class="nav-text">Security Center</span>
                ${state.pendingApprovals.length > 0 ? `<span class="pending-pill">${state.pendingApprovals.length}</span>` : ''}
              </button>
              <button class="nav-item ${state.currentView === 'knowledge' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('knowledge')">
                <span class="nav-icon">🌐</span>
                <span class="nav-text">Knowledge</span>
              </button>
              <button class="nav-item ${state.currentView === 'environment' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('environment')">
                <span class="nav-icon">🌍</span>
                <span class="nav-text">Environment</span>
              </button>
            </div>

            <div class="nav-section">
              <div class="nav-section-title">SYSTEM & UTILITIES</div>
              <button class="nav-item ${state.currentView === 'memory' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('memory')">
                <span class="nav-icon">🧠</span>
                <span class="nav-text">Memory</span>
              </button>
              <button class="nav-item ${state.currentView === 'notifications' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('notifications')">
                <span class="nav-icon">🔔</span>
                <span class="nav-text">Notifications</span>
              </button>
              <button class="nav-item ${state.currentView === 'status' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('status')">
                <span class="nav-icon">📈</span>
                <span class="nav-text">System Status</span>
              </button>
              <button class="nav-item ${state.currentView === 'evaluation' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('evaluation')">
                <span class="nav-icon">🧪</span>
                <span class="nav-text">Evaluation</span>
              </button>
              <button class="nav-item ${state.currentView === 'settings' ? 'active' : ''}" onclick="window.kairoApp.navigateTo('settings')">
                <span class="nav-icon">⚙️</span>
                <span class="nav-text">Settings</span>
              </button>
            </div>

            <div class="sidebar-footer">
              <div class="active-model-pill" title="Model Router Cascade">
                <span class="model-dot"></span>
                <span>OpenRouter / Free</span>
              </div>
            </div>
          </nav>

          <!-- Main View Container -->
          <main class="kairo-content" id="mainContent" role="main" tabindex="-1">
            <!-- Dynamic view injected here -->
          </main>
        </div>
      </div>
    `;
  }

  _renderProjectMenuItems(projects = [], activeProject = null) {
    if (!projects || projects.length === 0) {
      return `<div class="dropdown-empty">No projects yet</div>`;
    }

    return projects.map((p) => {
      const isSelected = activeProject && activeProject.id === p.id;
      return `
        <button class="dropdown-item ${isSelected ? 'selected' : ''}" onclick="window.kairoApp.switchActiveProject('${p.id}')" role="menuitem">
          <span class="item-name">${this._escapeHtml(p.name)}</span>
          ${isSelected ? '<span class="item-check">✓</span>' : ''}
        </button>
      `;
    }).join('');
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

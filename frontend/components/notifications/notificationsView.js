/**
 * Kairo Unified Notification Center (Task 34)
 * Handles unified alerts, CI failures, approval notifications, security alerts, and workflow events.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class NotificationsView {
  constructor(container) {
    this.container = container;
    this.notifications = [];
    this.filter = 'all'; // 'all', 'unread', 'tasks', 'security', 'projects'
    this.isLoading = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="notifications-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Notifications</h1>
            <p class="page-subtitle">Prioritized alerts, execution outcomes, and system communication</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="mark-all-read-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              Mark All Read
            </button>
            <button class="btn btn-secondary" id="refresh-notifs-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
          </div>
        </header>

        <div class="notifications-controls">
          <div class="tabs-nav" role="tablist">
            <button class="tab-btn ${this.filter === 'all' ? 'active' : ''}" data-filter="all" id="notif-tab-all" role="tab">All</button>
            <button class="tab-btn ${this.filter === 'unread' ? 'active' : ''}" data-filter="unread" id="notif-tab-unread" role="tab">Unread</button>
            <button class="tab-btn ${this.filter === 'tasks' ? 'active' : ''}" data-filter="tasks" id="notif-tab-tasks" role="tab">Tasks</button>
            <button class="tab-btn ${this.filter === 'security' ? 'active' : ''}" data-filter="security" id="notif-tab-security" role="tab">Security</button>
            <button class="tab-btn ${this.filter === 'projects' ? 'active' : ''}" data-filter="projects" id="notif-tab-projects" role="tab">Projects</button>
          </div>
        </div>

        <div class="notifications-list-container" id="notifications-list">
          <div class="loading-spinner">Loading notifications...</div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadNotifications();
  }

  _bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-notifs-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadNotifications());

    const markAllBtn = this.container.querySelector('#mark-all-read-btn');
    if (markAllBtn) {
      markAllBtn.addEventListener('click', async () => {
        try {
          await Endpoints.markAllNotificationsRead();
          this.notifications.forEach(n => {
            n.status = 'READ';
            n.is_read = true;
          });
          store.setUnreadNotificationsCount(0);
          this._renderList();
        } catch (err) {
          alert(`Failed to mark all read: ${err.message}`);
        }
      });
    }

    const tabs = this.container.querySelectorAll('.tab-btn[data-filter]');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.filter = tab.dataset.filter;
        this._renderList();
      });
    });
  }

  async loadNotifications() {
    const listContainer = this.container.querySelector('#notifications-list');
    if (!listContainer) return;

    this.isLoading = true;
    listContainer.innerHTML = '<div class="loading-spinner">Loading notifications...</div>';

    try {
      const res = await Endpoints.listNotifications(false);
      const items = res?.items || (Array.isArray(res) ? res : []);
      this.notifications = items;
      this.isLoading = false;

      // Update store count
      const unreadCount = items.filter(n => n.status !== 'READ' && n.status !== 'read' && n.status !== 'DISMISSED' && n.status !== 'dismissed').length;
      store.setUnreadNotificationsCount(unreadCount);

      this._renderList();
    } catch (err) {
      this.isLoading = false;
      listContainer.innerHTML = `
        <div class="error-state">
          <div class="error-icon">⚠️</div>
          <h3>Could not load notifications</h3>
          <p>${err.message || 'Check connection to Kairo server.'}</p>
          <button class="btn btn-secondary" id="retry-notifs-btn">Retry</button>
        </div>
      `;
      const retryBtn = listContainer.querySelector('#retry-notifs-btn');
      if (retryBtn) retryBtn.addEventListener('click', () => this.loadNotifications());
    }
  }

  _renderList() {
    const listContainer = this.container.querySelector('#notifications-list');
    if (!listContainer) return;

    let items = this.notifications;
    if (this.filter === 'unread') {
      items = items.filter(n => n.status !== 'READ' && n.status !== 'read' && n.status !== 'DISMISSED' && n.status !== 'dismissed');
    } else if (this.filter === 'tasks') {
      items = items.filter(n => (n.type || '').toUpperCase() === 'TASK');
    } else if (this.filter === 'security') {
      items = items.filter(n => (n.type || '').toUpperCase() === 'SECURITY');
    } else if (this.filter === 'projects') {
      items = items.filter(n => (n.type || '').toUpperCase() === 'PROJECT');
    }

    if (items.length === 0) {
      listContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔔</div>
          <h3>You're all caught up</h3>
          <p>No notifications ${this.filter === 'unread' ? 'waiting for review' : 'matching filter'}.</p>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = `
      <div class="notif-cards-grid">
        ${items.map(notif => {
          const priority = (notif.priority || notif.severity || 'NORMAL').toUpperCase();
          const badgeClass = priority === 'URGENT' ? 'badge-critical'
            : priority === 'HIGH' ? 'badge-warning'
            : priority === 'LOW' ? 'badge-neutral' : 'badge-info';
          const icon = priority === 'URGENT' ? '🔴' : priority === 'HIGH' ? '🟠' : priority === 'LOW' ? 'ℹ️' : '🟢';
          const isUnread = notif.status !== 'READ' && notif.status !== 'read' && notif.status !== 'DISMISSED';
          const isSecurity = (notif.type || '').toUpperCase() === 'SECURITY';
          const isApproval = (notif.type || '').toUpperCase() === 'APPROVAL';
          const actions = notif.actions || [];

          return `
            <div class="notif-card ${isUnread ? 'is-unread' : ''} ${isSecurity ? 'is-security-alert' : ''}" data-id="${notif.id}">
              <div class="notif-header">
                <div class="notif-title-group">
                  <span class="notif-icon">${icon}</span>
                  <strong class="notif-title">${escapeHtml(notif.title)}</strong>
                  <span class="badge ${badgeClass}">${priority}</span>
                  ${isSecurity ? '<span class="badge badge-critical">SECURITY</span>' : ''}
                  ${isApproval ? '<span class="badge badge-warning">APPROVAL REQUIRED</span>' : ''}
                </div>
                <time class="notif-time font-mono">${new Date(notif.created_at || Date.now()).toLocaleTimeString()}</time>
              </div>
              <div class="notif-body">
                <p>${escapeHtml(notif.body || notif.message || notif.content || '')}</p>
                ${isApproval && notif.metadata ? `
                  <div class="approval-context-box font-mono" style="margin-top: 8px; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 4px; font-size: 11px;">
                    <div>Target: ${escapeHtml(notif.metadata.target || notif.metadata.tool_name || 'System')}</div>
                    <div>Risk: ${escapeHtml(notif.metadata.risk_level || 'HIGH')}</div>
                  </div>
                ` : ''}
              </div>
              <div class="notif-actions">
                ${actions.map(act => {
                  const actType = (act.type || '').toUpperCase();
                  const btnClass = actType === 'APPROVE' ? 'btn-primary'
                    : actType === 'REJECT' || actType === 'CANCEL' ? 'btn-danger'
                    : 'btn-secondary';
                  return `
                    <button class="btn ${btnClass} btn-sm action-btn" data-notif-id="${notif.id}" data-action-id="${act.id}">
                      ${escapeHtml(act.label || actType)}
                    </button>
                  `;
                }).join('')}
                ${isUnread ? `
                  <button class="btn btn-secondary btn-sm mark-read-btn" data-id="${notif.id}">
                    Mark Read
                  </button>
                ` : ''}
                <button class="btn btn-secondary btn-sm dismiss-notif-btn" data-id="${notif.id}">
                  Dismiss
                </button>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    // Bind mark read buttons
    listContainer.querySelectorAll('.mark-read-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        try {
          await Endpoints.markNotificationRead(id);
          const found = this.notifications.find(n => n.id === id);
          if (found) {
            found.status = 'READ';
            found.is_read = true;
          }
          this._renderList();
        } catch (err) {
          alert(`Failed to mark read: ${err.message}`);
        }
      });
    });

    // Bind dismiss buttons
    listContainer.querySelectorAll('.dismiss-notif-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        try {
          await Endpoints.dismissNotification(id);
          this.notifications = this.notifications.filter(n => n.id !== id);
          this._renderList();
        } catch (err) {
          alert(`Failed to dismiss: ${err.message}`);
        }
      });
    });

    // Bind interactive action buttons
    listContainer.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const notifId = btn.dataset.notifId;
        const actId = btn.dataset.actionId;
        btn.disabled = true;
        btn.textContent = 'Executing...';
        try {
          const res = await Endpoints.executeNotificationAction(notifId, actId);
          alert(`Action executed: ${res.status}`);
          await this.loadNotifications();
        } catch (err) {
          alert(`Action failed: ${err.message}`);
          btn.disabled = false;
        }
      });
    });
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Kairo Notifications Center
 * Handles proactive alerts, CI failures, approval notifications, and workflow events.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class NotificationsView {
  constructor(container) {
    this.container = container;
    this.notifications = [];
    this.filter = 'all'; // 'all' or 'unread'
    this.isLoading = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="notifications-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Notifications</h1>
            <p class="page-subtitle">Proactive alerts, execution outcomes, and system events</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-notifs-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
          </div>
        </header>

        <div class="notifications-controls">
          <div class="tabs-nav" role="tablist">
            <button class="tab-btn ${this.filter === 'all' ? 'active' : ''}" id="notif-tab-all" role="tab">All Notifications</button>
            <button class="tab-btn ${this.filter === 'unread' ? 'active' : ''}" id="notif-tab-unread" role="tab">Unread Only</button>
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

    const tabAll = this.container.querySelector('#notif-tab-all');
    const tabUnread = this.container.querySelector('#notif-tab-unread');

    if (tabAll) {
      tabAll.addEventListener('click', () => {
        tabAll.classList.add('active');
        tabUnread?.classList.remove('active');
        this.filter = 'all';
        this._renderList();
      });
    }

    if (tabUnread) {
      tabUnread.addEventListener('click', () => {
        tabUnread.classList.add('active');
        tabAll?.classList.remove('active');
        this.filter = 'unread';
        this._renderList();
      });
    }
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
      const unreadCount = items.filter(n => n.status !== 'read' && n.status !== 'dismissed').length;
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
      items = items.filter(n => n.status === 'unread' || n.read === false);
    }

    if (items.length === 0) {
      listContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔔</div>
          <h3>You're all caught up</h3>
          <p>No notifications ${this.filter === 'unread' ? 'waiting for review' : 'to show'}.</p>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = `
      <div class="notif-cards-grid">
        ${items.map(notif => {
          const priority = (notif.severity || notif.priority || 'medium').toLowerCase();
          const badgeClass = priority === 'critical' ? 'badge-critical'
            : priority === 'high' ? 'badge-warning'
            : priority === 'low' ? 'badge-neutral' : 'badge-info';
          const icon = priority === 'critical' ? '🔴' : priority === 'high' ? '🟡' : 'ℹ️';
          const isUnread = notif.status === 'unread' || notif.read === false;

          return `
            <div class="notif-card ${isUnread ? 'is-unread' : ''}" data-id="${notif.id}">
              <div class="notif-header">
                <div class="notif-title-group">
                  <span class="notif-icon">${icon}</span>
                  <strong class="notif-title">${escapeHtml(notif.title)}</strong>
                  <span class="badge ${badgeClass}">${priority.toUpperCase()}</span>
                </div>
                <time class="notif-time font-mono">${new Date(notif.created_at || Date.now()).toLocaleTimeString()}</time>
              </div>
              <div class="notif-body">
                <p>${escapeHtml(notif.message || notif.content || '')}</p>
              </div>
              <div class="notif-actions">
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

    listContainer.querySelectorAll('.mark-read-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        try {
          await Endpoints.markNotificationRead(id);
          const found = this.notifications.find(n => n.id === id);
          if (found) {
            found.status = 'read';
            found.read = true;
          }
          this._renderList();
        } catch (err) {
          alert(`Failed to mark read: ${err.message}`);
        }
      });
    });

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

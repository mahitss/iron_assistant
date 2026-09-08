/**
 * ProactivePanel — Frontend state and controller for Kairo Proactive Intelligence.
 * Manages notification bell, proactive feed, preferences, and web monitors.
 */

export class ProactivePanel {
  constructor(options = {}) {
    this.userId = options.userId || 'default_user';
    this.settings = {
      proactive_enabled: true,
      notify_on_workflow_failure: true,
      notify_on_ci_failure: true,
      notify_on_approval: true,
      notify_on_web_change: true,
      minimum_priority: 'MEDIUM',
      quiet_hours_enabled: false,
      quiet_hours_start: '22:00',
      quiet_hours_end: '08:00',
      timezone: 'UTC',
      ...options.settings,
    };
    this.notifications = options.notifications || [];
    this.webMonitors = options.webMonitors || [];
  }

  getUnreadCount() {
    return this.notifications.filter(
      (n) => n.status === 'new' || n.status === 'delivered'
    ).length;
  }

  toggleSetting(key) {
    if (Object.prototype.hasOwnProperty.call(this.settings, key)) {
      if (typeof this.settings[key] === 'boolean') {
        this.settings[key] = !this.settings[key];
        return this.settings[key];
      }
    }
    throw new Error(`Unknown or non-boolean proactive setting: ${key}`);
  }

  setMinimumPriority(priority) {
    const valid = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
    const p = String(priority).toUpperCase();
    if (!valid.includes(p)) {
      throw new Error(`Invalid priority: ${priority}`);
    }
    this.settings.minimum_priority = p;
    return this.settings.minimum_priority;
  }

  setQuietHours(enabled, start = '22:00', end = '08:00') {
    this.settings.quiet_hours_enabled = Boolean(enabled);
    this.settings.quiet_hours_start = start;
    this.settings.quiet_hours_end = end;
    return this.settings;
  }

  addNotification(item) {
    this.notifications.unshift({
      id: item.id || `notif_${Date.now()}`,
      status: item.status || 'delivered',
      priority: item.priority || 'MEDIUM',
      actionability: item.actionability || 'INFORMATIONAL',
      created_at: item.created_at || new Date().toISOString(),
      ...item,
    });
  }

  markRead(notificationId) {
    const notif = this.notifications.find((n) => n.id === notificationId);
    if (!notif) {
      throw new Error(`Notification '${notificationId}' not found`);
    }
    notif.status = 'read';
    return notif;
  }

  dismissNotification(notificationId) {
    const idx = this.notifications.findIndex((n) => n.id === notificationId);
    if (idx === -1) {
      throw new Error(`Notification '${notificationId}' not found`);
    }
    const removed = this.notifications.splice(idx, 1)[0];
    removed.status = 'dismissed';
    return removed;
  }

  addWebMonitor(monitor) {
    const item = {
      id: monitor.id || `mon_${Date.now()}`,
      enabled: monitor.enabled !== false,
      check_interval_seconds: monitor.check_interval_seconds || 3600,
      content_fingerprint: monitor.content_fingerprint || null,
      ...monitor,
    };
    this.webMonitors.push(item);
    return item;
  }

  removeWebMonitor(monitorId) {
    const idx = this.webMonitors.findIndex((m) => m.id === monitorId);
    if (idx === -1) {
      throw new Error(`Web monitor '${monitorId}' not found`);
    }
    return this.webMonitors.splice(idx, 1)[0];
  }

  renderNotificationBellUI() {
    const unread = this.getUnreadCount();
    const badgeClass = unread > 0 ? 'badge bg-danger' : 'badge bg-secondary';
    return `
      <div class="notification-bell d-inline-flex align-items-center gap-1" id="kairo-notification-bell">
        <span class="bell-icon">🔔</span>
        <span class="${badgeClass}" id="notification-count">${unread}</span>
      </div>
    `.trim();
  }

  renderFeedUI() {
    const active = this.notifications.filter((n) => n.status !== 'dismissed');
    if (active.length === 0) {
      return '<p class="text-muted p-3">No active notifications or insights.</p>';
    }

    return active
      .map((item) => {
        const priorityColors = {
          CRITICAL: 'border-danger bg-danger-subtle text-danger',
          HIGH: 'border-warning bg-warning-subtle text-dark',
          MEDIUM: 'border-primary bg-light text-dark',
          LOW: 'border-secondary bg-light text-muted',
        };
        const colorClass = priorityColors[item.priority] || 'border-secondary';
        const actionBtn = item.suggested_action
          ? `<button class="btn btn-sm btn-primary me-2 action-btn" data-action="${item.suggested_action}">${item.suggested_action}</button>`
          : '';

        return `
        <div class="insight-card border rounded p-3 mb-2 ${colorClass}" id="insight-${item.id}">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="badge bg-dark">${item.priority}</span>
            <small class="text-muted">${item.status.toUpperCase()}</small>
          </div>
          <div class="fw-bold">${item.title}</div>
          <div class="small mb-2">${item.summary}</div>
          <div class="d-flex gap-2">
            ${actionBtn}
            <button class="btn btn-sm btn-outline-secondary dismiss-btn" onclick="proactivePanel.dismissNotification('${item.id}')">Dismiss</button>
          </div>
        </div>
      `.trim();
      })
      .join('\n');
  }

  renderSettingsUI() {
    return `
      <div class="proactive-settings card p-3" id="proactive-settings-panel">
        <h5 class="card-title mb-3">PROACTIVE INTELLIGENCE</h5>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" id="toggle-proactive" ${this.settings.proactive_enabled ? 'checked' : ''}>
          <label class="form-check-label" for="toggle-proactive">Enable Proactive Notifications</label>
        </div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" id="toggle-wf" ${this.settings.notify_on_workflow_failure ? 'checked' : ''}>
          <label class="form-check-label" for="toggle-wf">Workflow Failures</label>
        </div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" id="toggle-ci" ${this.settings.notify_on_ci_failure ? 'checked' : ''}>
          <label class="form-check-label" for="toggle-ci">CI Failures</label>
        </div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" id="toggle-approval" ${this.settings.notify_on_approval ? 'checked' : ''}>
          <label class="form-check-label" for="toggle-approval">Approval Reminders</label>
        </div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" id="toggle-web" ${this.settings.notify_on_web_change ? 'checked' : ''}>
          <label class="form-check-label" for="toggle-web">Web Changes</label>
        </div>
        <div class="mb-3">
          <label class="form-label" for="select-priority">Minimum Priority</label>
          <select class="form-select form-select-sm" id="select-priority">
            <option value="LOW" ${this.settings.minimum_priority === 'LOW' ? 'selected' : ''}>LOW</option>
            <option value="MEDIUM" ${this.settings.minimum_priority === 'MEDIUM' ? 'selected' : ''}>MEDIUM</option>
            <option value="HIGH" ${this.settings.minimum_priority === 'HIGH' ? 'selected' : ''}>HIGH</option>
          </select>
        </div>
        <div class="form-check form-switch mb-2">
          <input class="form-check-input" type="checkbox" id="toggle-quiet-hours" ${this.settings.quiet_hours_enabled ? 'checked' : ''}>
          <label class="form-check-label" for="toggle-quiet-hours">Quiet Hours</label>
        </div>
      </div>
    `.trim();
  }
}

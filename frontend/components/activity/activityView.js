/**
 * Kairo Unified Activity Center
 * Consolidates actions, security audits, agent executions, and automation logs into a single timeline.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class ActivityView {
  constructor(container) {
    this.container = container;
    this.events = [];
    this.activeFilter = 'all';
    this.isLoading = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="activity-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Activity Timeline</h1>
            <p class="page-subtitle">Unified chronological record of assistant actions, agent investigations, and security audits</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-activity-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
          </div>
        </header>

        <div class="activity-controls">
          <div class="tabs-nav" role="tablist">
            <button class="tab-btn active" data-filter="all" role="tab" aria-selected="true">All Sources</button>
            <button class="tab-btn" data-filter="security" role="tab" aria-selected="false">Security</button>
            <button class="tab-btn" data-filter="agent" role="tab" aria-selected="false">Agents</button>
            <button class="tab-btn" data-filter="automation" role="tab" aria-selected="false">Automations</button>
            <button class="tab-btn" data-filter="tool" role="tab" aria-selected="false">Tools</button>
          </div>
        </div>

        <div class="activity-timeline-container" id="activity-timeline">
          <div class="loading-spinner">Loading activity timeline...</div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadActivity();
  }

  _bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-activity-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadActivity());

    const tabs = this.container.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');
        this.activeFilter = tab.dataset.filter;
        this._renderTimeline();
      });
    });
  }

  async loadActivity() {
    const timeline = this.container.querySelector('#activity-timeline');
    if (!timeline) return;

    this.isLoading = true;
    timeline.innerHTML = '<div class="loading-spinner">Fetching security events & assistant logs...</div>';

    try {
      const auditRes = await Endpoints.listAuditEvents(50);
      const auditEvents = Array.isArray(auditRes) ? auditRes : (auditRes.events || []);

      // Normalize audit events into unified timeline item schema
      const normalizedAudit = auditEvents.map(e => ({
        id: e.id || `audit_${Math.random()}`,
        source: 'security',
        type: e.event_type || 'SECURITY_EVENT',
        title: e.action || e.event_type || 'Security Action',
        description: e.details ? (typeof e.details === 'string' ? e.details : JSON.stringify(e.details)) : 'Action recorded by SecurityCenter',
        timestamp: new Date(e.created_at || e.timestamp || Date.now()),
        severity: e.severity || 'low',
        metadata: e.metadata || {},
      }));

      // Merge with in-memory assistant notifications & actions from store
      const notifs = (store.getState().notifications || []).map(n => ({
        id: n.id,
        source: n.category === 'automation' ? 'automation' : 'agent',
        type: 'NOTIFICATION',
        title: n.title,
        description: n.message || '',
        timestamp: new Date(n.created_at || Date.now()),
        severity: n.severity || 'info',
        metadata: {},
      }));

      // Combine and sort descending
      const combined = [...normalizedAudit, ...notifs];
      combined.sort((a, b) => b.timestamp - a.timestamp);
      this.events = combined;
      this.isLoading = false;

      this._renderTimeline();
    } catch (err) {
      this.isLoading = false;
      timeline.innerHTML = `
        <div class="error-state">
          <div class="error-icon">⚠️</div>
          <h3>Failed to load activity</h3>
          <p>${err.message || 'Audit logs could not be retrieved.'}</p>
          <button class="btn btn-secondary" id="retry-activity-btn">Retry</button>
        </div>
      `;
      const retryBtn = timeline.querySelector('#retry-activity-btn');
      if (retryBtn) retryBtn.addEventListener('click', () => this.loadActivity());
    }
  }

  _renderTimeline() {
    const timeline = this.container.querySelector('#activity-timeline');
    if (!timeline) return;

    let filtered = this.events;
    if (this.activeFilter !== 'all') {
      filtered = this.events.filter(e => e.source === this.activeFilter);
    }

    if (filtered.length === 0) {
      timeline.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📜</div>
          <h3>No events found</h3>
          <p>There are no activity logs matching "${this.activeFilter}".</p>
        </div>
      `;
      return;
    }

    timeline.innerHTML = `
      <div class="timeline-list">
        ${filtered.map(evt => {
          const timeStr = evt.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const dateStr = evt.timestamp.toLocaleDateString([], { month: 'short', day: 'numeric' });
          const sourceBadgeClass = getSourceBadgeClass(evt.source);
          const icon = getSourceIcon(evt.source);

          return `
            <div class="timeline-item">
              <div class="timeline-marker">
                <span class="timeline-icon">${icon}</span>
                <span class="timeline-line"></span>
              </div>
              <div class="timeline-card">
                <div class="timeline-card-header">
                  <div class="timeline-source-group">
                    <span class="badge ${sourceBadgeClass}">${evt.source.toUpperCase()}</span>
                    <span class="timeline-title">${escapeHtml(evt.title)}</span>
                  </div>
                  <time class="timeline-time font-mono" datetime="${evt.timestamp.toISOString()}">${dateStr} ${timeStr}</time>
                </div>
                <div class="timeline-body">
                  <p>${escapeHtml(evt.description)}</p>
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }
}

function getSourceIcon(source) {
  switch (source) {
    case 'security': return '🛡️';
    case 'agent': return '🤖';
    case 'automation': return '⚡';
    case 'tool': return '🔧';
    default: return '📌';
  }
}

function getSourceBadgeClass(source) {
  switch (source) {
    case 'security': return 'badge-critical';
    case 'agent': return 'badge-info';
    case 'automation': return 'badge-success';
    case 'tool': return 'badge-neutral';
    default: return 'badge-neutral';
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

/**
 * Environment Command Center Dashboard Component (Task 32, Spec 93-96, 148).
 * Renders live environment state, entity graph, freshness indicators, and conflict alerts.
 */

export class EnvironmentView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api;
    this.state = {
      overview: {
        projects_count: 0,
        active_tasks_count: 0,
        connected_devices_count: 0,
        healthy_services_count: 0,
        degraded_services_count: 0,
        synced_repos_count: 0,
        stale_repos_count: 0,
        automations_count: 0,
        stale_total: 0,
        conflicts_count: 0,
      },
      selectedTab: 'all',
      recentChanges: [],
      selectedEntity: null,
      dependencyGraph: null,
      isLoading: false,
      isRefreshing: false,
    };
  }

  async render() {
    if (!this.container) return;
    this.container.innerHTML = this._template();
    this._attachEventListeners();
    await this.fetchData();
  }

  async fetchData() {
    this.state.isLoading = true;
    try {
      if (this.api && this.api.getWorldOverview) {
        const res = await this.api.getWorldOverview();
        if (res && res.data) {
          this.state.overview = res.data;
        }
      }
      if (this.api && this.api.getWorldChanges) {
        const changesRes = await this.api.getWorldChanges({ sinceSeconds: 3600 });
        if (changesRes && changesRes.changes) {
          this.state.recentChanges = changesRes.changes;
        }
      }
    } catch (err) {
      console.warn('Failed to fetch world environment overview:', err);
    } finally {
      this.state.isLoading = false;
      this._updateView();
    }
  }

  async refreshEnvironment() {
    this.state.isRefreshing = true;
    this._updateView();
    try {
      if (this.api && this.api.refreshWorld) {
        const res = await this.api.refreshWorld();
        if (res && res.data) {
          this.state.overview = res.data;
        }
      }
      await this.fetchData();
    } catch (err) {
      console.error('Error refreshing environment:', err);
    } finally {
      this.state.isRefreshing = false;
      this._updateView();
    }
  }

  _template() {
    const o = this.state.overview;

    return `
      <div class="environment-view-container">
        <!-- Header -->
        <header class="view-header">
          <div class="view-header-title">
            <span class="header-icon">🌍</span>
            <div>
              <h2>Environment & World Model</h2>
              <p class="view-subtitle">Live situation awareness, connected devices, repositories, and services</p>
            </div>
          </div>
          <div class="view-header-actions">
            <button class="btn btn-secondary" id="envRefreshBtn" ${this.state.isRefreshing ? 'disabled' : ''}>
              ${this.state.isRefreshing ? '⟳ Refreshing...' : '⟳ Reconcile Sources'}
            </button>
            <button class="btn btn-primary" id="envSnapshotBtn">
              📸 Create Snapshot
            </button>
          </div>
        </header>

        <!-- Stale Warning Banner (Spec 95) -->
        ${o.stale_total > 0 ? `
          <div class="environment-alert-banner warning" id="staleAlertBanner">
            <div class="alert-content">
              <span class="alert-icon">⚠️</span>
              <div>
                <strong>Stale Environment State Detected:</strong>
                <span>${o.stale_total} entity observation(s) have exceeded freshness policies.</span>
              </div>
            </div>
            <button class="btn btn-sm btn-outline-warning" onclick="window.kairoEnvironmentView.refreshEnvironment()">
              Refresh Authoritative Sources
            </button>
          </div>
        ` : ''}

        <!-- State Conflict Banner (Spec 96) -->
        ${o.conflicts_count > 0 ? `
          <div class="environment-alert-banner conflict" id="conflictAlertBanner">
            <div class="alert-content">
              <span class="alert-icon">⚡</span>
              <div>
                <strong>State Conflict Detected:</strong>
                <span>${o.conflicts_count} state update conflict(s) resolved via authoritative source priority.</span>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- Metric Summary Cards (Spec 93) -->
        <section class="environment-metrics-grid" id="envMetricsGrid">
          <div class="env-metric-card">
            <div class="metric-icon">📁</div>
            <div class="metric-data">
              <span class="metric-value">${o.projects_count}</span>
              <span class="metric-label">Projects</span>
            </div>
          </div>

          <div class="env-metric-card highlight">
            <div class="metric-icon">🎯</div>
            <div class="metric-data">
              <span class="metric-value">${o.active_tasks_count}</span>
              <span class="metric-label">Active Tasks</span>
            </div>
          </div>

          <div class="env-metric-card">
            <div class="metric-icon">💻</div>
            <div class="metric-data">
              <span class="metric-value">${o.connected_devices_count}</span>
              <span class="metric-label">Connected Devices</span>
            </div>
          </div>

          <div class="env-metric-card">
            <div class="metric-icon">⚙️</div>
            <div class="metric-data">
              <span class="metric-value">${o.healthy_services_count}</span>
              <span class="metric-label">Healthy Services</span>
              ${o.degraded_services_count > 0 ? `<span class="metric-badge danger">${o.degraded_services_count} degraded</span>` : ''}
            </div>
          </div>

          <div class="env-metric-card">
            <div class="metric-icon">📦</div>
            <div class="metric-data">
              <span class="metric-value">${o.synced_repos_count}</span>
              <span class="metric-label">Synced Repos</span>
              ${o.stale_repos_count > 0 ? `<span class="metric-badge warning">${o.stale_repos_count} stale</span>` : ''}
            </div>
          </div>

          <div class="env-metric-card">
            <div class="metric-icon">⚡</div>
            <div class="metric-data">
              <span class="metric-value">${o.automations_count}</span>
              <span class="metric-label">Active Automations</span>
            </div>
          </div>
        </section>

        <!-- Main Environment Split View -->
        <div class="environment-body-layout">
          <!-- Left Column: Navigation / Category Filters -->
          <div class="environment-tabs-panel">
            <div class="env-tab-group">
              <button class="env-tab-btn ${this.state.selectedTab === 'all' ? 'active' : ''}" data-tab="all">
                🌐 All Entities
              </button>
              <button class="env-tab-btn ${this.state.selectedTab === 'devices' ? 'active' : ''}" data-tab="devices">
                💻 Devices (${o.connected_devices_count})
              </button>
              <button class="env-tab-btn ${this.state.selectedTab === 'repositories' ? 'active' : ''}" data-tab="repositories">
                📦 Repositories (${o.synced_repos_count})
              </button>
              <button class="env-tab-btn ${this.state.selectedTab === 'services' ? 'active' : ''}" data-tab="services">
                ⚙️ Services (${o.healthy_services_count + o.degraded_services_count})
              </button>
              <button class="env-tab-btn ${this.state.selectedTab === 'tasks' ? 'active' : ''}" data-tab="tasks">
                🎯 Tasks (${o.active_tasks_count})
              </button>
            </div>

            <!-- Recent Changes Feed (Spec 98, 99) -->
            <div class="recent-changes-card">
              <div class="card-header">
                <h4>Recent State Changes</h4>
                <span class="time-badge">Past 1h</span>
              </div>
              <div class="changes-list" id="recentChangesList">
                ${this.state.recentChanges.length === 0 ? `
                  <div class="empty-state-hint">No recent state changes recorded.</div>
                ` : this.state.recentChanges.map(c => `
                  <div class="change-item">
                    <span class="change-dot"></span>
                    <div class="change-info">
                      <span class="change-summary">${this._escapeHtml(c.summary)}</span>
                      <span class="change-time">${new Date(c.observed_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>

          <!-- Right Column: Operational Situational Awareness Panel -->
          <div class="environment-detail-panel">
            <div class="situation-awareness-card">
              <div class="card-header">
                <h3>Live Situation Awareness</h3>
                <span class="badge badge-success">Online</span>
              </div>
              <div class="card-body">
                <p class="awareness-summary">
                  Kairo is monitoring <strong>${o.projects_count} project(s)</strong>, 
                  <strong>${o.connected_devices_count} active device(s)</strong>, and 
                  <strong>${o.healthy_services_count} healthy service(s)</strong> across authorized boundaries.
                </p>

                <div class="source-authority-summary">
                  <h4>Authoritative Sources:</h4>
                  <ul class="authority-list">
                    <li><span class="auth-tag">GitHub</span> Repository commit heads & CI verification</li>
                    <li><span class="auth-tag">Local Companion</span> Authorized connected device execution</li>
                    <li><span class="auth-tag">Autonomous Task Engine</span> Operational task lifecycle and DAG status</li>
                    <li><span class="auth-tag">Observability</span> System & microservice health endpoints</li>
                    <li><span class="auth-tag">SecurityCenter</span> Definitive action & permission decisions</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    const refreshBtn = this.container.querySelector('#envRefreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refreshEnvironment());
    }

    const snapshotBtn = this.container.querySelector('#envSnapshotBtn');
    if (snapshotBtn) {
      snapshotBtn.addEventListener('click', async () => {
        if (this.api && this.api.createWorldSnapshot) {
          try {
            await this.api.createWorldSnapshot();
            alert('Environment snapshot created successfully!');
          } catch (e) {
            console.error(e);
          }
        }
      });
    }

    const tabs = this.container.querySelectorAll('.env-tab-btn');
    tabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        this.state.selectedTab = e.currentTarget.dataset.tab;
        this._updateView();
      });
    });

    if (typeof window !== 'undefined') {
      window.kairoEnvironmentView = this;
    }
  }

  _updateView() {
    if (!this.container) return;
    this.container.innerHTML = this._template();
    this._attachEventListeners();
  }

  _escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

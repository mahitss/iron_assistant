/**
 * Kairo Perception, Environmental Awareness, and Live Situational Awareness View (Task 46)
 * Displays Multi-Source Observations, Source Liveness, Live Situation Synthesis,
 * Environmental Changes, Anomalies, and Versioned Snapshots.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class PerceptionView {
  constructor(container) {
    this.container = container;
    this.sources = [];
    this.observations = [];
    this.changes = [];
    this.situation = null;
    this.snapshot = null;
    this.health = null;
    this.activeTab = 'observations';
    this.selectedEnvironment = 'DEVELOPMENT';
    this.isLoading = false;
  }

  formatDate(isoStr) {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  formatConfidence(conf) {
    if (conf === null || conf === undefined) return '100%';
    return (Number(conf) * 100).toFixed(0) + '%';
  }

  async render() {
    this.container.innerHTML = `
      <div class="perception-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Perception & Environmental Awareness Engine</h1>
            <p class="page-subtitle">Bounded, privacy-aware multi-source observation, change detection, and live World Model synchronization</p>
          </div>
          <div class="header-actions">
            <select class="form-select" id="env-selector" style="width: auto; display: inline-block;">
              <option value="DEVELOPMENT" ${this.selectedEnvironment === 'DEVELOPMENT' ? 'selected' : ''}>DEVELOPMENT</option>
              <option value="STAGING" ${this.selectedEnvironment === 'STAGING' ? 'selected' : ''}>STAGING</option>
              <option value="PRODUCTION" ${this.selectedEnvironment === 'PRODUCTION' ? 'selected' : ''}>PRODUCTION</option>
            </select>
            <button class="btn btn-secondary" id="refresh-perception-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="capture-snapshot-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M14.31 8l5.74 9.94M9.69 8h11.48M7.38 12l5.74-9.94M9.69 16L3.95 6.06M14.31 16H2.83M16.62 12l-5.74 9.94"/></svg>
              Capture Snapshot
            </button>
          </div>
        </header>

        <!-- Metrics Ribbon -->
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">Active Sources</div>
            <div class="metric-value" id="kpi-active-sources">${this.sources.filter(s => s.status === 'HEALTHY').length}/${this.sources.length}</div>
            <div class="metric-trend">Authoritative sources</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Recent Observations</div>
            <div class="metric-value text-accent" id="kpi-observations-count">${this.observations.length}</div>
            <div class="metric-trend">${this.health?.events_processed || 0} processed</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Changes Detected</div>
            <div class="metric-value text-warning" id="kpi-changes-count">${this.changes.length}</div>
            <div class="metric-trend">${this.health?.changes_detected || 0} total mutations</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Avg Ingestion Delay</div>
            <div class="metric-value text-success" id="kpi-avg-latency">${(this.health?.avg_latency_ms || 1.2).toFixed(1)}ms</div>
            <div class="metric-trend">Near real-time sync</div>
          </div>
        </div>

        <!-- Live Situation Synthesis (Spec 100-106) -->
        <div class="card" style="margin-bottom: 24px; border-left: 4px solid var(--accent, #6366f1);">
          <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge badge-accent">SITUATION V${this.situation?.version || 1}</span>
              <h3 style="margin: 0;">Live Environmental Situational Awareness</h3>
            </div>
            <span class="text-muted" style="font-size: 12px;">Synced: ${this.formatDate(this.situation?.timestamp)}</span>
          </div>
          <div class="card-body">
            <p style="font-size: 15px; font-weight: 500; margin-bottom: 16px;">
              ${this.situation?.summary || 'Environment nominal. Multi-source observations synchronized with World Model.'}
            </p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;">
              <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 6px;">
                <h4 style="font-size: 12px; text-transform: uppercase; color: var(--accent, #6366f1); margin-bottom: 8px;">Verified Telemetry Facts</h4>
                <ul style="margin: 0; padding-left: 16px; font-size: 12px; color: var(--text-secondary, #94a3b8);">
                  ${(this.situation?.observed_facts || ['All registered sensors emitting expected telemetry']).map(f => `<li>${f}</li>`).join('')}
                </ul>
              </div>
              <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 6px;">
                <h4 style="font-size: 12px; text-transform: uppercase; color: #38bdf8; margin-bottom: 8px;">Inferences & Causation</h4>
                <ul style="margin: 0; padding-left: 16px; font-size: 12px; color: var(--text-secondary, #94a3b8);">
                  ${(this.situation?.inferences?.length ? this.situation.inferences : ['No unexpected deviations identified']).map(i => `<li>${i}</li>`).join('')}
                </ul>
              </div>
              <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 6px;">
                <h4 style="font-size: 12px; text-transform: uppercase; color: #f59e0b; margin-bottom: 8px;">Environmental Uncertainties</h4>
                <ul style="margin: 0; padding-left: 16px; font-size: 12px; color: var(--text-secondary, #94a3b8);">
                  ${(this.situation?.uncertainties?.length ? this.situation.uncertainties : ['Zero unobserved missing sources']).map(u => `<li>${u}</li>`).join('')}
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs-bar">
          <button class="tab-btn ${this.activeTab === 'observations' ? 'active' : ''}" data-tab="observations">Live Observations</button>
          <button class="tab-btn ${this.activeTab === 'sources' ? 'active' : ''}" data-tab="sources">Perception Sources (${this.sources.length})</button>
          <button class="tab-btn ${this.activeTab === 'changes' ? 'active' : ''}" data-tab="changes">Environmental Changes (${this.changes.length})</button>
          <button class="tab-btn ${this.activeTab === 'snapshots' ? 'active' : ''}" data-tab="snapshots">World Snapshots</button>
        </div>

        <!-- Tab Content Panes -->
        <div class="tab-content" style="margin-top: 16px;">
          ${this.renderActiveTab()}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderActiveTab() {
    switch (this.activeTab) {
      case 'sources':
        return this.renderSourcesTab();
      case 'changes':
        return this.renderChangesTab();
      case 'snapshots':
        return this.renderSnapshotsTab();
      case 'observations':
      default:
        return this.renderObservationsTab();
    }
  }

  renderObservationsTab() {
    return `
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Source Type</th>
              <th>Event</th>
              <th>Age</th>
              <th>Delay</th>
              <th>Confidence</th>
              <th>Correlation</th>
            </tr>
          </thead>
          <tbody>
            ${this.observations.length === 0 ? `
              <tr><td colspan="7" class="text-center text-muted">No observations recorded yet. Ingest telemetry or refresh.</td></tr>
            ` : this.observations.map(o => `
              <tr>
                <td><strong>${o.subject}</strong></td>
                <td><span class="badge badge-info">${o.source_type}</span></td>
                <td><span class="badge badge-secondary">${o.event_type}</span></td>
                <td>${o.age_seconds ? o.age_seconds.toFixed(1) + 's' : '<1s'}</td>
                <td>${(o.latency_ms || 0).toFixed(1)}ms</td>
                <td><span class="badge badge-success">${this.formatConfidence(o.confidence)}</span></td>
                <td class="text-muted font-mono" style="font-size: 11px;">${o.correlation_id || 'none'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  renderSourcesTab() {
    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
        ${this.sources.map(s => `
          <div class="card">
            <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
              <strong>${s.name}</strong>
              <span class="badge ${s.status === 'HEALTHY' ? 'badge-success' : s.status === 'DISABLED' ? 'badge-danger' : 'badge-warning'}">${s.status}</span>
            </div>
            <div class="card-body" style="font-size: 13px;">
              <p><strong>Type:</strong> ${s.type}</p>
              <p><strong>Trust Weight:</strong> ${(s.reliability * 100).toFixed(0)}%</p>
              <p><strong>Privacy:</strong> ${s.privacy_level}</p>
              <p><strong>Last Seen:</strong> ${this.formatDate(s.last_seen)}</p>
              <div style="margin-top: 12px; display: flex; justify-content: flex-end; gap: 8px;">
                ${s.status !== 'DISABLED' ? `
                  <button class="btn btn-sm btn-danger disable-src-btn" data-id="${s.source_id}">Disable</button>
                ` : `
                  <span class="text-muted" style="font-size: 11px;">Source disabled</span>
                `}
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderChangesTab() {
    return `
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Mutation Type</th>
              <th>Significance</th>
              <th>Environment</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            ${this.changes.length === 0 ? `
              <tr><td colspan="5" class="text-center text-muted">No environmental mutations detected. Environment is stable.</td></tr>
            ` : this.changes.map(c => `
              <tr>
                <td><strong>${c.subject}</strong></td>
                <td><span class="badge badge-info">${c.change_type}</span></td>
                <td>
                  <span class="badge ${
                    c.significance === 'CRITICAL' ? 'badge-danger' :
                    c.significance === 'HIGH' ? 'badge-warning' :
                    c.significance === 'MEDIUM' ? 'badge-accent' : 'badge-secondary'
                  }">${c.significance}</span>
                </td>
                <td>${c.environment}</td>
                <td>${this.formatDate(c.timestamp)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  renderSnapshotsTab() {
    return `
      <div class="card">
        <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0;">Latest Environment Snapshot</h3>
          <span class="badge badge-accent">Version ${this.snapshot?.version || 1}</span>
        </div>
        <div class="card-body">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 16px;">
            <div><strong>Environment:</strong> ${this.snapshot?.environment || this.selectedEnvironment}</div>
            <div><strong>Atomic:</strong> ${this.snapshot?.is_atomic ? 'Yes (Consistent)' : 'Best-Effort'}</div>
            <div><strong>Timestamp:</strong> ${this.formatDate(this.snapshot?.timestamp)}</div>
            <div><strong>Missing Sources:</strong> ${this.snapshot?.missing_sources?.length || 0}</div>
          </div>
          <pre class="font-mono" style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 6px; font-size: 11px; max-height: 250px; overflow-y: auto;">
${JSON.stringify(this.snapshot || { message: "No snapshot captured yet." }, null, 2)}
          </pre>
        </div>
      </div>
    `;
  }

  bindEvents() {
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.activeTab = e.currentTarget.dataset.tab;
        this.render();
      });
    });

    const envSelector = this.container.querySelector('#env-selector');
    if (envSelector) {
      envSelector.addEventListener('change', (e) => {
        this.selectedEnvironment = e.target.value;
        this.refresh();
      });
    }

    const refreshBtn = this.container.querySelector('#refresh-perception-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refresh());
    }

    const snapBtn = this.container.querySelector('#capture-snapshot-btn');
    if (snapBtn) {
      snapBtn.addEventListener('click', async () => {
        try {
          await Endpoints.captureEnvironmentSnapshot({
            environment: this.selectedEnvironment,
            is_atomic: true,
          });
          await this.refresh();
        } catch (err) {
          console.error('Failed to capture snapshot:', err);
        }
      });
    }

    this.container.querySelectorAll('.disable-src-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const srcId = e.currentTarget.dataset.id;
        try {
          await Endpoints.disablePerceptionSource(srcId);
          await this.refresh();
        } catch (err) {
          console.error('Failed to disable source:', err);
        }
      });
    });

    if (typeof window !== 'undefined') {
      window.kairoPerception = {
        refresh: () => this.refresh(),
        captureSnapshot: (env) => Endpoints.captureEnvironmentSnapshot({ environment: env || this.selectedEnvironment }),
      };
    }
  }

  async refresh() {
    this.isLoading = true;
    try {
      const [sourcesRes, obsRes, changesRes, sitRes, snapRes, healthRes] = await Promise.allSettled([
        Endpoints.listPerceptionSources(),
        Endpoints.getRecentObservations({ environment: this.selectedEnvironment }),
        Endpoints.getRecentChanges(),
        Endpoints.getLiveSituation({ environment: this.selectedEnvironment }),
        Endpoints.getLatestSnapshot({ environment: this.selectedEnvironment }),
        Endpoints.getPerceptionHealth(),
      ]);

      if (sourcesRes.status === 'fulfilled') this.sources = sourcesRes.value || [];
      if (obsRes.status === 'fulfilled') this.observations = obsRes.value || [];
      if (changesRes.status === 'fulfilled') this.changes = changesRes.value || [];
      if (sitRes.status === 'fulfilled') this.situation = sitRes.value || null;
      if (snapRes.status === 'fulfilled') this.snapshot = snapRes.value || null;
      if (healthRes.status === 'fulfilled') this.health = healthRes.value || null;

      this.render();
    } catch (err) {
      console.error('Failed refreshing perception engine:', err);
    } finally {
      this.isLoading = false;
    }
  }
}

/**
 * Kairo Unified Observability & System Intelligence View
 * Displays distributed traces, dynamic service topology, operational incidents, and evidence-backed RCA.
 */

import { Endpoints, nativeRuntimeApi } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class ObservabilityView {
  constructor(container) {
    this.container = container;
    this.dashboardData = null;
    this.activeTab = 'traces';
    this.selectedTrace = null;
    this.isLoading = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="observability-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">System Intelligence & Observability</h1>
            <p class="page-subtitle">Distributed execution traces, real topology maps, operational incidents, and root-cause diagnostics</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-observability-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
          </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <div class="metrics-grid" id="observability-kpis">
          <div class="metric-card">
            <span class="metric-label">Health Score</span>
            <span class="metric-value text-success" id="kpi-health-score">--</span>
            <span class="metric-trend" id="kpi-health-status">Deterministic</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Availability</span>
            <span class="metric-value" id="kpi-availability">--%</span>
            <span class="metric-trend text-muted">Rolling SLI</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">p95 Latency</span>
            <span class="metric-value" id="kpi-latency">-- ms</span>
            <span class="metric-trend text-muted">Execution</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Active Incidents</span>
            <span class="metric-value text-warning" id="kpi-incidents">0</span>
            <span class="metric-trend">Requiring Action</span>
          </div>
          <div class="metric-card" id="kpi-native-card">
            <span class="metric-label">Native Substrate</span>
            <span class="metric-value text-info" id="kpi-native-status">--</span>
            <span class="metric-trend" id="kpi-native-mode">Rust Runtime</span>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs-nav" role="tablist" style="margin-top: 24px;">
          <button class="tab-btn active" data-tab="traces">Distributed Traces</button>
          <button class="tab-btn" data-tab="topology">Service Topology</button>
          <button class="tab-btn" data-tab="incidents">Incidents & RCA</button>
          <button class="tab-btn" data-tab="diagnostics">Diagnostics</button>
        </div>

        <div class="tab-content" id="observability-tab-content" style="margin-top: 16px;">
          <div class="loading-spinner">Loading telemetry data...</div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadData();
  }

  _bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-observability-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadData());

    const tabs = this.container.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.activeTab = tab.dataset.tab;
        this.renderTabContent();
      });
    });
  }

  async loadData() {
    this.isLoading = true;
    try {
      this.dashboardData = await Endpoints.getObservabilityDashboard();
      this.updateKPIs();
      this.renderTabContent();
    } catch (err) {
      console.error('Failed to load observability dashboard:', err);
      const content = this.container.querySelector('#observability-tab-content');
      if (content) {
        content.innerHTML = `<div class="error-banner">Failed to load telemetry: ${err.message}</div>`;
      }
    } finally {
      this.isLoading = false;
    }
  }

  updateKPIs() {
    if (!this.dashboardData) return;
    const health = this.dashboardData.health || {};
    const kpiScore = this.container.querySelector('#kpi-health-score');
    const kpiAvail = this.container.querySelector('#kpi-availability');
    const kpiLat = this.container.querySelector('#kpi-latency');
    const kpiInc = this.container.querySelector('#kpi-incidents');
    const kpiStatus = this.container.querySelector('#kpi-health-status');

    if (kpiScore) kpiScore.textContent = `${health.score || 100}/100`;
    if (kpiAvail) kpiAvail.textContent = `${health.availability_percent || 100}%`;
    if (kpiLat) kpiLat.textContent = `${health.latency_p95_ms || 25} ms`;
    if (kpiInc) kpiInc.textContent = this.dashboardData.active_incident_count || 0;
    if (kpiStatus) kpiStatus.textContent = health.overall_status || 'HEALTHY';

    const kpiNative = this.container.querySelector('#kpi-native-status');
    const kpiNativeMode = this.container.querySelector('#kpi-native-mode');
    if (kpiNative) {
      nativeRuntimeApi.getHealth().then(res => {
        const st = res?.status || 'UNAVAILABLE';
        kpiNative.textContent = st;
        kpiNative.className = `metric-value ${st === 'READY' ? 'text-success' : (st === 'DISABLED' ? 'text-muted' : 'text-warning')}`;
        if (kpiNativeMode) {
          kpiNativeMode.textContent = res?.mode ? `Mode: ${res.mode}` : 'Rust Runtime';
        }
      }).catch(() => {
        kpiNative.textContent = 'OFFLINE';
        kpiNative.className = 'metric-value text-muted';
      });
    }
  }

  renderTabContent() {
    const content = this.container.querySelector('#observability-tab-content');
    if (!content) return;

    if (this.activeTab === 'traces') {
      this.renderTracesTab(content);
    } else if (this.activeTab === 'topology') {
      this.renderTopologyTab(content);
    } else if (this.activeTab === 'incidents') {
      this.renderIncidentsTab(content);
    } else if (this.activeTab === 'diagnostics') {
      this.renderDiagnosticsTab(content);
    }
  }

  renderTracesTab(content) {
    const traces = this.dashboardData?.recent_traces || [];
    if (traces.length === 0) {
      content.innerHTML = '<div class="empty-state"><p>No traces recorded yet. Operations will appear here automatically.</p></div>';
      return;
    }

    content.innerHTML = `
      <div class="traces-layout" style="display: grid; grid-template-columns: 1fr; gap: 16px;">
        <div class="panel">
          <div class="panel-header">
            <h3>Recent Distributed Traces</h3>
          </div>
          <table class="data-table">
            <thead>
              <tr>
                <th>Trace ID</th>
                <th>Root Operation</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Spans</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              ${traces.map(t => `
                <tr class="trace-row" data-id="${t.trace_id}">
                  <td><code>${t.trace_id}</code></td>
                  <td><strong>${t.root_operation}</strong></td>
                  <td><span class="badge badge-${t.status === 'SUCCESS' ? 'success' : (t.status === 'ERROR' ? 'danger' : 'warning')}">${t.status}</span></td>
                  <td>${t.duration_ms ? `${Math.round(t.duration_ms)} ms` : '--'}</td>
                  <td>${t.spans ? t.spans.length : 0} spans</td>
                  <td>${new Date(t.started_at).toLocaleTimeString()}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  renderTopologyTab(content) {
    const serviceMap = this.dashboardData?.service_map || { nodes: [], edges: [] };
    content.innerHTML = `
      <div class="panel">
        <div class="panel-header">
          <h3>Logical Service Topology</h3>
          <span class="badge badge-info">${serviceMap.nodes.length} Components Discovered</span>
        </div>
        <div class="topology-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-top: 16px;">
          ${serviceMap.nodes.map(n => `
            <div class="card" style="border-left: 4px solid ${n.health === 'HEALTHY' ? 'var(--color-success)' : 'var(--color-warning)'};">
              <h4>${n.name}</h4>
              <p class="text-muted" style="font-size: 12px; margin: 4px 0;">Type: ${n.type}</p>
              <div style="font-size: 13px; margin-top: 8px;">
                <div>Health: <strong class="${n.health === 'HEALTHY' ? 'text-success' : 'text-warning'}">${n.health}</strong></div>
                <div>p95: ${n.latency_p95_ms} ms</div>
                <div>Errors: ${(n.error_rate * 100).toFixed(1)}%</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderIncidentsTab(content) {
    const incidents = this.dashboardData?.incidents || [];
    content.innerHTML = `
      <div class="panel">
        <div class="panel-header">
          <h3>Correlated Operational Incidents</h3>
        </div>
        ${incidents.length === 0 ? '<div class="empty-state"><p>Zero active operational incidents. System is operating normally.</p></div>' : `
          <div class="incident-list" style="display: flex; flex-direction: column; gap: 12px;">
            ${incidents.map(inc => `
              <div class="card incident-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h4>${inc.title}</h4>
                  <span class="badge badge-${inc.status === 'RESOLVED' ? 'success' : (inc.status === 'OPEN' ? 'danger' : 'warning')}">${inc.status}</span>
                </div>
                <p class="text-muted" style="margin: 6px 0; font-size: 13px;">Affected: ${inc.affected_components.join(', ')}</p>
                <div style="font-size: 12px; margin-top: 8px;">Evidence events: ${inc.evidence ? inc.evidence.length : 0}</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderDiagnosticsTab(content) {
    content.innerHTML = `
      <div class="panel">
        <div class="panel-header">
          <h3>User-Safe Diagnostics ("What Happened?")</h3>
        </div>
        <div style="display: flex; gap: 8px; margin: 16px 0;">
          <input type="text" id="diagnostic-target-input" class="form-control" placeholder="Enter Trace ID or Task ID (e.g. trc_...)" style="flex: 1;">
          <button class="btn btn-primary" id="run-diagnostic-btn">Analyze Issue</button>
        </div>
        <div id="diagnostic-result-container"></div>
      </div>
    `;

    const btn = content.querySelector('#run-diagnostic-btn');
    if (btn) {
      btn.addEventListener('click', async () => {
        const input = content.querySelector('#diagnostic-target-input');
        const targetRef = input ? input.value.trim() : '';
        if (!targetRef) return;
        const resContainer = content.querySelector('#diagnostic-result-container');
        resContainer.innerHTML = '<div class="loading-spinner">Performing safe diagnosis...</div>';
        try {
          const report = await Endpoints.runDiagnostics(targetRef);
          resContainer.innerHTML = `
            <div class="card" style="margin-top: 16px;">
              <h4 class="text-primary">${report.summary}</h4>
              <p style="margin: 12px 0;">${report.what_happened}</p>
              <div class="alert alert-info"><strong>Recommended Action:</strong> ${report.next_steps}</div>
            </div>
          `;
        } catch (err) {
          resContainer.innerHTML = `<div class="error-banner">Diagnosis failed: ${err.message}</div>`;
        }
      });
    }
  }
}

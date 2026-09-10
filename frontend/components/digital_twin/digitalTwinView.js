/**
 * Kairo Environmental Intelligence & Digital Twin View (Task 54)
 * Provides comprehensive visual operational control center for:
 * - System Topology & Dependency Graph
 * - Expected vs Actual State Drift Inspector
 * - Evidence-backed Health & Incident Blast Radius Visualizer
 * - What-If Hypothetical Failure Simulator
 * - Governed Remediation Plans & Auto-Healing Console
 */

import { Endpoints } from '../../lib/api/endpoints.js';

export class DigitalTwinView {
  constructor(container) {
    this.container = container;
    this.activeTab = 'overview';
    this.activeScope = 'SYSTEM';
    this.twin = null;
    this.summary = null;
    this.unhealthyResources = [];
    this.productionResources = [];
    this.simulationResult = null;
    this.remediationPlans = [];
    this.selectedNodeId = null;
    this.nodeDependents = [];
    this.nodeDependencies = [];
    this.isLoading = false;
  }

  async init() {
    this.renderSkeleton();
    await this.loadAll();
  }

  formatDate(isoStr) {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  async loadAll() {
    this.isLoading = true;
    try {
      const [twinRes, sumRes, unhRes, prodRes] = await Promise.allSettled([
        Endpoints.getDigitalTwin(this.activeScope),
        Endpoints.getEnvironmentSummary(this.activeScope),
        Endpoints.getEnvironmentUnhealthy(this.activeScope),
        Endpoints.getEnvironmentProduction(),
      ]);

      if (twinRes.status === 'fulfilled' && twinRes.value) this.twin = twinRes.value;
      if (sumRes.status === 'fulfilled' && sumRes.value) this.summary = sumRes.value;
      if (unhRes.status === 'fulfilled' && unhRes.value) {
        this.unhealthyResources = unhRes.value.unhealthy_resources || [];
      }
      if (prodRes.status === 'fulfilled' && prodRes.value) {
        this.productionResources = prodRes.value.production_resources || [];
      }
    } catch (err) {
      console.error('Failed to load digital twin state:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  renderSkeleton() {
    this.container.innerHTML = `
      <div class="digital-twin-view" style="padding: 24px; color: var(--text-primary, #e2e8f0); font-family: system-ui, -apple-system, sans-serif;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
          <div>
            <h2 style="margin: 0; font-size: 1.6rem; font-weight: 700; background: linear-gradient(135deg, #10b981, #06b6d4, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Environmental Intelligence & Digital Twin
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 0.88rem; color: var(--text-muted, #94a3b8);">
              Continuously reconcilable topology, expected vs actual drift detection, and governed operational awareness.
            </p>
          </div>
          <div style="display: flex; gap: 8px;">
            <select id="dt-scope-selector" style="background: rgba(30, 41, 59, 0.8); color: #e2e8f0; border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 6px 12px; font-size: 0.85rem;">
              <option value="SYSTEM" selected>Scope: SYSTEM</option>
              <option value="DEVICE">Scope: DEVICE</option>
              <option value="HOST">Scope: HOST</option>
              <option value="APPLICATION">Scope: APPLICATION</option>
              <option value="ENVIRONMENT">Scope: ENVIRONMENT</option>
              <option value="CLOUD">Scope: CLOUD</option>
              <option value="NETWORK">Scope: NETWORK</option>
            </select>
            <button id="dt-btn-refresh" style="background: linear-gradient(135deg, #059669, #0d9488); border: none; color: white; padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer;">
              Refresh Twin
            </button>
          </div>
        </div>

        <div style="display: flex; gap: 8px; border-bottom: 1px solid rgba(148, 163, 184, 0.15); margin-bottom: 20px;">
          ${['overview', 'topology', 'drift', 'health_incidents', 'simulation'].map(tab => `
            <button class="dt-tab-btn" data-tab="${tab}" style="background: transparent; border: none; padding: 8px 16px; color: ${this.activeTab === tab ? '#10b981' : '#94a3b8'}; border-bottom: 2px solid ${this.activeTab === tab ? '#10b981' : 'transparent'}; font-weight: 600; cursor: pointer; text-transform: capitalize;">
              ${tab.replace('_', ' ')}
            </button>
          `).join('')}
        </div>

        <div id="dt-tab-content">
          <div style="text-align: center; padding: 40px; color: #94a3b8;">Loading environment digital twin telemetry...</div>
        </div>
      </div>
    `;
    this.bindSkeletonEvents();
  }

  bindSkeletonEvents() {
    const selector = this.container.querySelector('#dt-scope-selector');
    if (selector) {
      selector.value = this.activeScope;
      selector.addEventListener('change', (e) => {
        this.activeScope = e.target.value;
        this.loadAll();
      });
    }

    const refreshBtn = this.container.querySelector('#dt-btn-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadAll());
    }

    this.container.querySelectorAll('.dt-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.dataset.tab;
        this.render();
      });
    });
  }

  render() {
    this.renderSkeleton();
    const content = this.container.querySelector('#dt-tab-content');
    if (!content) return;

    if (this.activeTab === 'overview') {
      content.innerHTML = this.renderOverviewTab();
    } else if (this.activeTab === 'topology') {
      content.innerHTML = this.renderTopologyTab();
      this.bindTopologyEvents();
    } else if (this.activeTab === 'drift') {
      content.innerHTML = this.renderDriftTab();
    } else if (this.activeTab === 'health_incidents') {
      content.innerHTML = this.renderHealthIncidentsTab();
    } else if (this.activeTab === 'simulation') {
      content.innerHTML = this.renderSimulationTab();
      this.bindSimulationEvents();
    }
  }

  renderOverviewTab() {
    const s = this.summary || {};
    const m = s.metrics || {};
    const t = this.twin || {};

    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
        <div style="background: rgba(30, 41, 59, 0.6); padding: 16px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
          <div style="font-size: 0.8rem; color: #94a3b8;">ACTIVE SCOPE</div>
          <div style="font-size: 1.3rem; font-weight: 700; color: #10b981; margin-top: 4px;">${this.activeScope}</div>
          <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">Twin ID: ${t.twin_id || 'N/A'}</div>
        </div>
        <div style="background: rgba(30, 41, 59, 0.6); padding: 16px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
          <div style="font-size: 0.8rem; color: #94a3b8;">FRESHNESS & CONFIDENCE</div>
          <div style="font-size: 1.3rem; font-weight: 700; color: ${s.freshness === 'FRESH' ? '#10b981' : '#f59e0b'}; margin-top: 4px;">
            ${s.freshness || 'UNKNOWN'} (${((s.confidence || 1.0) * 100).toFixed(0)}%)
          </div>
          <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">Version ${s.version || 1}</div>
        </div>
        <div style="background: rgba(30, 41, 59, 0.6); padding: 16px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
          <div style="font-size: 0.8rem; color: #94a3b8;">TOPOLOGY SIZE</div>
          <div style="font-size: 1.3rem; font-weight: 700; color: #38bdf8; margin-top: 4px;">
            ${m.total_nodes || 0} Nodes / ${m.total_edges || 0} Edges
          </div>
          <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">${m.unverified_edges || 0} unverified edges</div>
        </div>
        <div style="background: rgba(30, 41, 59, 0.6); padding: 16px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
          <div style="font-size: 0.8rem; color: #94a3b8;">ACTIVE DRIFT & INCIDENTS</div>
          <div style="font-size: 1.3rem; font-weight: 700; color: ${(s.active_drifts_count || 0) > 0 ? '#f43f5e' : '#10b981'}; margin-top: 4px;">
            ${s.active_drifts_count || 0} Drifts / ${s.open_incidents_count || 0} Incidents
          </div>
          <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">${this.unhealthyResources.length} unhealthy nodes</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div style="background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.1);">
          <h3 style="margin: 0 0 12px 0; font-size: 1.05rem; font-weight: 600; color: #e2e8f0;">Recent Environmental Changes</h3>
          ${(s.recent_changes && s.recent_changes.length > 0) ? `
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${s.recent_changes.slice(0, 5).map(c => `
                <div style="padding: 10px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border-left: 3px solid #38bdf8; font-size: 0.85rem;">
                  <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: 600; color: #e2e8f0;">${c.resource}</span>
                    <span style="color: #94a3b8; font-size: 0.78rem;">${c.change_type}</span>
                  </div>
                  <div style="color: #64748b; font-size: 0.78rem; margin-top: 4px;">Source: ${c.source} | ${this.formatDate(c.timestamp)}</div>
                </div>
              `).join('')}
            </div>
          ` : '<div style="color: #94a3b8; font-size: 0.85rem;">No recent mutations recorded.</div>'}
        </div>

        <div style="background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.1);">
          <h3 style="margin: 0 0 12px 0; font-size: 1.05rem; font-weight: 600; color: #e2e8f0;">Production Environment Resources</h3>
          ${(this.productionResources && this.productionResources.length > 0) ? `
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${this.productionResources.slice(0, 5).map(p => `
                <div style="padding: 10px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border-left: 3px solid #f43f5e; font-size: 0.85rem;">
                  <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: 600; color: #fecdd3;">${p.display_name}</span>
                    <span style="color: #94a3b8; font-size: 0.78rem;">${p.node_type}</span>
                  </div>
                  <div style="color: #64748b; font-size: 0.78rem; margin-top: 4px;">Status: ${p.status} | Canonical: ${p.canonical_id}</div>
                </div>
              `).join('')}
            </div>
          ` : '<div style="color: #94a3b8; font-size: 0.85rem;">No production nodes registered.</div>'}
        </div>
      </div>
    `;
  }

  renderTopologyTab() {
    return `
      <div style="display: grid; grid-template-columns: 320px 1fr; gap: 20px;">
        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
          <h3 style="margin: 0 0 12px 0; font-size: 1.05rem; font-weight: 600; color: #e2e8f0;">Inspect Node Dependencies</h3>
          <div style="display: flex; gap: 8px; margin-bottom: 16px;">
            <input id="dt-node-query-input" type="text" placeholder="e.g. svc_order_service" style="flex: 1; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 6px 12px; color: #e2e8f0; font-size: 0.85rem;">
            <button id="dt-btn-inspect-node" style="background: #38bdf8; border: none; color: #0f172a; padding: 6px 12px; border-radius: 8px; font-weight: 600; cursor: pointer;">Lookup</button>
          </div>

          ${this.selectedNodeId ? `
            <div style="margin-top: 16px;">
              <div style="font-size: 0.85rem; font-weight: 600; color: #38bdf8; margin-bottom: 8px;">Target: ${this.selectedNodeId}</div>
              
              <div style="font-size: 0.8rem; color: #94a3b8; font-weight: 600; margin-top: 12px;">What depends on this? (Downstream)</div>
              ${this.nodeDependents.length > 0 ? `
                <ul style="padding-left: 18px; margin: 4px 0; font-size: 0.82rem; color: #e2e8f0;">
                  ${this.nodeDependents.map(d => `<li>${d}</li>`).join('')}
                </ul>
              ` : '<div style="font-size: 0.78rem; color: #64748b;">No downstream dependents found.</div>'}

              <div style="font-size: 0.8rem; color: #94a3b8; font-weight: 600; margin-top: 12px;">What does this depend on? (Upstream)</div>
              ${this.nodeDependencies.length > 0 ? `
                <ul style="padding-left: 18px; margin: 4px 0; font-size: 0.82rem; color: #e2e8f0;">
                  ${this.nodeDependencies.map(d => `<li>${d}</li>`).join('')}
                </ul>
              ` : '<div style="font-size: 0.78rem; color: #64748b;">No upstream dependencies mapped.</div>'}
            </div>
          ` : '<div style="color: #64748b; font-size: 0.82rem;">Enter a resource or service node ID above to trace upstream dependencies and downstream callers.</div>'}
        </div>

        <div style="background: rgba(30, 41, 59, 0.3); padding: 20px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.1);">
          <h3 style="margin: 0 0 12px 0; font-size: 1.05rem; font-weight: 600; color: #e2e8f0;">Anti-False Topology Invariants</h3>
          <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">
            Kairo strictly enforces Prompt #10: Co-location within the same environment does <strong>NOT</strong> constitute a dependency.
            Edges are only validated if corroborated by concrete network connection traces, API contracts, or verified telemetry.
          </p>
          <div style="margin-top: 20px; padding: 16px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border-left: 4px solid #10b981;">
            <div style="font-size: 0.85rem; font-weight: 600; color: #e2e8f0;">Safe Directed Graph Traversal</div>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">
              Graph queries are bounded by depth and count limits to prevent memory and LLM prompt context explosion.
            </div>
          </div>
        </div>
      </div>
    `;
  }

  bindTopologyEvents() {
    const input = this.container.querySelector('#dt-node-query-input');
    const btn = this.container.querySelector('#dt-btn-inspect-node');
    if (btn && input) {
      btn.addEventListener('click', async () => {
        const val = input.value.trim();
        if (!val) return;
        this.selectedNodeId = val;
        try {
          const [depRes, subRes] = await Promise.allSettled([
            Endpoints.getEnvironmentDependents(val, this.activeScope),
            Endpoints.getEnvironmentDependencies(val, this.activeScope),
          ]);
          this.nodeDependents = (depRes.status === 'fulfilled' && depRes.value) ? (depRes.value.dependents || []) : [];
          this.nodeDependencies = (subRes.status === 'fulfilled' && subRes.value) ? (subRes.value.dependencies || []) : [];
        } catch (err) {
          console.error('Topology lookup failed:', err);
        }
        this.render();
      });
    }
  }

  renderDriftTab() {
    const drifts = (this.summary && this.summary.active_drifts) || [];
    return `
      <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
        <h3 style="margin: 0 0 16px 0; font-size: 1.05rem; font-weight: 600; color: #e2e8f0;">Expected vs Actual State Drift</h3>
        ${drifts.length > 0 ? `
          <div style="display: flex; flex-direction: column; gap: 12px;">
            ${drifts.map(d => `
              <div style="padding: 14px; background: rgba(15, 23, 42, 0.7); border-radius: 8px; border-left: 4px solid ${d.severity === 'CRITICAL' ? '#f43f5e' : '#f59e0b'}; font-size: 0.85rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: 600; color: #e2e8f0;">Resource: ${d.resource}</span>
                  <span style="padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; background: ${d.severity === 'CRITICAL' ? 'rgba(244, 63, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)'}; color: ${d.severity === 'CRITICAL' ? '#f43f5e' : '#f59e0b'};">
                    ${d.drift_type} (${d.severity})
                  </span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px; font-size: 0.8rem;">
                  <div style="background: rgba(30, 41, 59, 0.5); padding: 8px; border-radius: 6px;">
                    <span style="color: #94a3b8; font-weight: 600;">Expected:</span>
                    <pre style="margin: 4px 0 0 0; color: #a5f3fc; font-family: monospace;">${JSON.stringify(d.expected, null, 2)}</pre>
                  </div>
                  <div style="background: rgba(30, 41, 59, 0.5); padding: 8px; border-radius: 6px;">
                    <span style="color: #94a3b8; font-weight: 600;">Actual:</span>
                    <pre style="margin: 4px 0 0 0; color: #fecdd3; font-family: monospace;">${JSON.stringify(d.actual, null, 2)}</pre>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        ` : '<div style="color: #94a3b8; font-size: 0.85rem;">Zero drift detected. All observed operational states align with declared configurations.</div>'}
      </div>
    `;
  }

  renderHealthIncidentsTab() {
    const incs = (this.summary && this.summary.open_incidents) || [];
    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
          <h3 style="margin: 0 0 16px 0; font-size: 1.05rem; font-weight: 600; color: #e2e8f0;">Unhealthy or Degraded Services</h3>
          ${this.unhealthyResources.length > 0 ? `
            <div style="display: flex; flex-direction: column; gap: 10px;">
              ${this.unhealthyResources.map(u => `
                <div style="padding: 12px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border-left: 3px solid ${u.status === 'UNHEALTHY' ? '#f43f5e' : '#f59e0b'}; font-size: 0.85rem;">
                  <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: 600; color: #e2e8f0;">${u.display_name}</span>
                    <span style="font-weight: 600; color: ${u.status === 'UNHEALTHY' ? '#f43f5e' : '#f59e0b'};">${u.status}</span>
                  </div>
                  <div style="color: #94a3b8; font-size: 0.78rem; margin-top: 4px;">Reason: ${u.reason || 'Telemetry threshold breach'}</div>
                </div>
              `).join('')}
            </div>
          ` : '<div style="color: #94a3b8; font-size: 0.85rem;">All monitored services are operating with verified healthy telemetry.</div>'}
        </div>

        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
          <h3 style="margin: 0 0 16px 0; font-size: 1.05rem; font-weight: 600; color: #e2e8f0;">Open Incidents & Symptoms</h3>
          ${incs.length > 0 ? `
            <div style="display: flex; flex-direction: column; gap: 10px;">
              ${incs.map(inc => `
                <div style="padding: 12px; background: rgba(15, 23, 42, 0.6); border-radius: 8px; border-left: 3px solid #f43f5e; font-size: 0.85rem;">
                  <div style="display: flex; justify-content: space-between;">
                    <span style="font-weight: 600; color: #fecdd3;">${inc.incident_id} (${inc.severity})</span>
                    <span style="color: #94a3b8; font-size: 0.78rem;">${this.formatDate(inc.detected_at)}</span>
                  </div>
                  <div style="color: #e2e8f0; font-size: 0.8rem; margin-top: 4px;">
                    Symptoms: ${(inc.symptoms || []).join(', ')}
                  </div>
                  <div style="color: #64748b; font-size: 0.75rem; margin-top: 4px;">
                    Suspected: ${inc.suspected_cause || 'Under investigation'}
                  </div>
                </div>
              `).join('')}
            </div>
          ` : '<div style="color: #94a3b8; font-size: 0.85rem;">Zero active incidents. Operational awareness nominal.</div>'}
        </div>
      </div>
    `;
  }

  renderSimulationTab() {
    return `
      <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15);">
        <h3 style="margin: 0 0 8px 0; font-size: 1.05rem; font-weight: 600; color: #e2e8f0;">What-If Hypothetical Failure Simulator</h3>
        <p style="font-size: 0.85rem; color: #94a3b8; margin: 0 0 16px 0;">
          Simulate node degradation or outages non-destructively over digital twin topology to estimate blast radius.
        </p>

        <div style="display: flex; gap: 10px; margin-bottom: 20px;">
          <input id="dt-sim-target-input" type="text" placeholder="Target Node ID (e.g. svc_db_main)" style="flex: 1; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 8px 12px; color: #e2e8f0; font-size: 0.85rem;">
          <select id="dt-sim-event-select" style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 8px 12px; color: #e2e8f0; font-size: 0.85rem;">
            <option value="service_outage">Event: Service Outage</option>
            <option value="latency_spike">Event: Latency Spike</option>
            <option value="pod_crash">Event: Pod Crash</option>
          </select>
          <button id="dt-btn-run-sim" style="background: linear-gradient(135deg, #6366f1, #818cf8); border: none; color: white; padding: 8px 18px; border-radius: 8px; font-weight: 600; cursor: pointer;">
            Run Simulation
          </button>
        </div>

        ${this.simulationResult ? `
          <div style="padding: 16px; background: rgba(15, 23, 42, 0.8); border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.3);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; color: #818cf8;">Hypothetical Simulation: ${this.simulationResult.hypothetical_event}</span>
              <span style="padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; background: rgba(99, 102, 241, 0.2); color: #818cf8;">
                ${this.simulationResult.is_hypothetical ? 'HYPOTHETICAL ONLY' : 'ACTUAL'}
              </span>
            </div>
            <div style="font-size: 0.85rem; color: #e2e8f0; margin-top: 8px;">
              Potential Impact: <strong>${this.simulationResult.potential_impact}</strong> | Blast Radius Score: ${(this.simulationResult.blast_radius_score * 100).toFixed(0)}%
            </div>
            <div style="font-size: 0.82rem; color: #94a3b8; margin-top: 8px;">
              Potentially Affected Nodes:
              ${(this.simulationResult.affected_nodes && this.simulationResult.affected_nodes.length > 0) ? `
                <ul style="padding-left: 18px; margin: 4px 0;">
                  ${this.simulationResult.affected_nodes.map(n => `<li>${n}</li>`).join('')}
                </ul>
              ` : '<span style="color: #64748b;"> None (isolated node)</span>'}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  bindSimulationEvents() {
    const input = this.container.querySelector('#dt-sim-target-input');
    const select = this.container.querySelector('#dt-sim-event-select');
    const btn = this.container.querySelector('#dt-btn-run-sim');

    if (btn && input && select) {
      btn.addEventListener('click', async () => {
        const target = input.value.trim();
        if (!target) return;
        try {
          const res = await Endpoints.simulateEnvironmentWhatIf({
            target_node_id: target,
            event: select.value,
            scope: this.activeScope,
          });
          if (res && res.simulation) {
            this.simulationResult = res.simulation;
          }
        } catch (err) {
          console.error('Simulation failed:', err);
        }
        this.render();
      });
    }
  }
}

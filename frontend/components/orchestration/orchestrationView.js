/**
 * Kairo Resource & Capability Orchestration Engine View (Task 59)
 * High-assurance glassmorphic control center for capabilities, resources, assignments, topology, and failovers.
 */

import { orchestrationApi } from '../../lib/api/endpoints.js';

export class OrchestrationView {
  constructor(containerId = 'orchestration-container') {
    this.containerId = containerId;
    this.activeTab = 'plans'; // 'plans' | 'capabilities' | 'resources' | 'assignments' | 'topology' | 'failover' | 'audit'
    this.plans = [];
    this.selectedPlan = null;
    this.capabilities = [];
    this.resources = [];
    this.auditEvents = [];
    this.isLoading = false;
  }

  async init() {
    this.render();
    await this.loadData();
  }

  async loadData() {
    this.isLoading = true;
    this.renderLoading(true);
    try {
      const [plansRes, capsRes, resRes] = await Promise.all([
        orchestrationApi.list(null, 25).catch(() => []),
        orchestrationApi.listCapabilities().catch(() => []),
        orchestrationApi.listResources().catch(() => []),
      ]);
      this.plans = Array.isArray(plansRes) ? plansRes : [];
      this.capabilities = Array.isArray(capsRes) ? capsRes : [];
      this.resources = Array.isArray(resRes) ? resRes : [];
      if (this.plans.length > 0 && !this.selectedPlan) {
        this.selectedPlan = this.plans[0];
      }
    } catch (err) {
      console.error('Failed to load orchestration data:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  selectPlan(plan) {
    this.selectedPlan = plan;
    this.render();
  }

  render() {
    if (typeof document === 'undefined') return;
    const container = document.getElementById(this.containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="orchestration-dashboard" style="display: flex; flex-direction: column; gap: 20px; font-family: 'Inter', system-ui, sans-serif; color: #e2e8f0; padding: 24px;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px;">
          <div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Resource & Capability Orchestration Engine
            </h1>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">
              High-assurance mapping, multi-agent coordination, capacity accounting, and dynamic failovers
            </p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="btn-refresh-orchestration" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Metric Badges -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Active Plans</div>
            <div style="font-size: 24px; font-weight: 700; color: #38bdf8; margin-top: 4px;">${this.plans.length}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Registered Capabilities</div>
            <div style="font-size: 24px; font-weight: 700; color: #818cf8; margin-top: 4px;">${this.capabilities.length}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Managed Resources</div>
            <div style="font-size: 24px; font-weight: 700; color: #34d399; margin-top: 4px;">${this.resources.length}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Active Boundary</div>
            <div style="font-size: 15px; font-weight: 600; color: #f59e0b; margin-top: 8px;">Execution Firewall ACTIVE</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 8px;">
          ${this.renderTabBtn('plans', 'Orchestration Plans')}
          ${this.renderTabBtn('capabilities', 'Capabilities Catalog')}
          ${this.renderTabBtn('resources', 'Resource Inventory')}
          ${this.renderTabBtn('assignments', 'Task Assignments')}
          ${this.renderTabBtn('topology', 'Execution Topology')}
          ${this.renderTabBtn('failover', 'Failover & Recovery')}
          ${this.renderTabBtn('audit', 'Audit Trail')}
        </div>

        <!-- Tab Content -->
        <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
          ${this.renderActiveTabContent()}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  renderTabBtn(tabKey, label) {
    const isActive = this.activeTab === tabKey;
    const bg = isActive ? 'rgba(56, 189, 248, 0.2)' : 'transparent';
    const border = isActive ? '#38bdf8' : 'transparent';
    const color = isActive ? '#38bdf8' : '#94a3b8';
    return `
      <button class="orch-tab-btn" data-tab="${tabKey}" style="background: ${bg}; border: 1px solid ${border}; color: ${color}; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s ease;">
        ${label}
      </button>
    `;
  }

  renderActiveTabContent() {
    switch (this.activeTab) {
      case 'plans':
        return this.renderPlansTab();
      case 'capabilities':
        return this.renderCapabilitiesTab();
      case 'resources':
        return this.renderResourcesTab();
      case 'assignments':
        return this.renderAssignmentsTab();
      case 'topology':
        return this.renderTopologyTab();
      case 'failover':
        return this.renderFailoverTab();
      case 'audit':
        return this.renderAuditTab();
      default:
        return `<div>Select a tab</div>`;
    }
  }

  renderPlansTab() {
    if (this.plans.length === 0) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;">No orchestration plans recorded yet. Create one via API or Strategic Plan pipeline.</div>`;
    }
    return `
      <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 20px;">
        <!-- Left: Plan List -->
        <div style="display: flex; flex-direction: column; gap: 10px; max-height: 500px; overflow-y: auto;">
          ${this.plans.map(p => `
            <div class="orch-plan-card" data-plan-id="${p.orchestration_id}" style="background: ${this.selectedPlan?.orchestration_id === p.orchestration_id ? 'rgba(56, 189, 248, 0.15)' : 'rgba(30, 41, 59, 0.5)'}; border: 1px solid ${this.selectedPlan?.orchestration_id === p.orchestration_id ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}; border-radius: 8px; padding: 14px; cursor: pointer; transition: all 0.2s ease;">
              <div style="font-weight: 600; font-size: 14px; color: #f8fafc;">${p.name}</div>
              <div style="display: flex; gap: 8px; margin-top: 6px; font-size: 11px;">
                <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 2px 6px; border-radius: 4px;">${p.status}</span>
                <span style="background: rgba(52, 211, 153, 0.2); color: #34d399; padding: 2px 6px; border-radius: 4px;">v${p.version}</span>
                <span style="color: #94a3b8;">${p.assignments?.length || 0} tasks</span>
              </div>
            </div>
          `).join('')}
        </div>

        <!-- Right: Selected Plan Detail -->
        <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 20px;">
          ${this.selectedPlan ? `
            <h3 style="margin-top: 0; color: #f8fafc;">${this.selectedPlan.name}</h3>
            <p style="font-size: 12px; color: #94a3b8;">Orchestration ID: <code>${this.selectedPlan.orchestration_id}</code></p>
            <div style="margin-top: 16px;">
              <div style="font-weight: 600; font-size: 13px; color: #cbd5e1; margin-bottom: 8px;">Execution Waves (${this.selectedPlan.execution_waves?.length || 0})</div>
              <div style="display: flex; flex-direction: column; gap: 8px;">
                ${(this.selectedPlan.execution_waves || []).map(w => `
                  <div style="background: rgba(15, 23, 42, 0.6); padding: 10px; border-radius: 6px; font-size: 12px;">
                    <span style="font-weight: 600; color: #38bdf8;">Wave ${w.wave_number}:</span>
                    <span style="color: #94a3b8; margin-left: 8px;">${w.tasks?.map(t => t.task_id).join(', ')}</span>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : `<div>Select a plan to inspect details</div>`}
        </div>
      </div>
    `;
  }

  renderCapabilitiesTab() {
    return `
      <div>
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">Catalog of Registered Capabilities (${this.capabilities.length})</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;">
          ${this.capabilities.map(c => `
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
              <div style="font-weight: 600; color: #38bdf8; font-size: 13px;">${c.name}</div>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Provider: <code>${c.provider}</code></div>
              <div style="font-size: 11px; color: #cbd5e1; margin-top: 8px;">${c.description || 'Verified system capability'}</div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px; font-size: 11px;">
                <span style="color: #34d399;">Rel: ${(c.reliability * 100).toFixed(0)}%</span>
                <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px;">${c.status}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderResourcesTab() {
    return `
      <div>
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">Managed Resources & Quotas (${this.resources.length})</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;">
          ${this.resources.map(r => `
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
              <div style="font-weight: 600; color: #34d399; font-size: 13px;">${r.name}</div>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Type: ${r.resource_type} (${r.environment})</div>
              <div style="margin-top: 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #cbd5e1; margin-bottom: 4px;">
                  <span>Available: ${r.available_capacity} ${r.unit}</span>
                  <span>Total: ${r.total_capacity} ${r.unit}</span>
                </div>
                <div style="background: rgba(15, 23, 42, 0.8); height: 6px; border-radius: 3px; overflow: hidden;">
                  <div style="background: #38bdf8; height: 100%; width: ${(r.available_capacity / r.total_capacity) * 100}%;"></div>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderAssignmentsTab() {
    const assignments = this.selectedPlan?.assignments || [];
    if (assignments.length === 0) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;">No assignments in selected plan.</div>`;
    }
    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        ${assignments.map(a => `
          <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; color: #f8fafc; font-size: 14px;">${a.task_id}</div>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Assigned: <strong style="color: #38bdf8;">${a.provider_name}</strong> (${a.provider_type})</div>
              <div style="font-size: 11px; color: #cbd5e1; margin-top: 4px;">Rationale: ${a.rationale || 'Optimal composite score'}</div>
            </div>
            <div style="text-align: right;">
              <span style="background: rgba(52, 211, 153, 0.2); color: #34d399; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">${a.status}</span>
              ${a.fallback_provider ? `<div style="font-size: 11px; color: #f59e0b; margin-top: 6px;">Fallback: ${a.fallback_provider}</div>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderTopologyTab() {
    return `
      <div>
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">Execution Graph & Waves</div>
        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 20px; font-family: monospace; font-size: 12px; color: #38bdf8; white-space: pre-wrap;">
${JSON.stringify({
  task_graph: this.selectedPlan?.task_graph || {},
  execution_waves: this.selectedPlan?.execution_waves || [],
  synchronization_points: this.selectedPlan?.synchronization_points || [],
}, null, 2)}
        </div>
      </div>
    `;
  }

  renderFailoverTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc;">Dynamic Failover & Resilience Controls</div>
        <p style="font-size: 13px; color: #94a3b8;">
          Trigger authorized failover for any failed task to its pre-calculated fallback provider. Irreversible operations require manual reconciliation.
        </p>
        <div style="display: flex; gap: 10px;">
          <input id="input-failover-task" type="text" placeholder="Task ID (e.g. task_001)" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 8px 12px; border-radius: 6px; font-size: 13px; width: 220px;" />
          <input id="input-failover-err" type="text" placeholder="Error reason (e.g. timeout)" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 8px 12px; border-radius: 6px; font-size: 13px; flex: 1;" />
          <button id="btn-trigger-failover" style="background: #ef4444; border: none; color: white; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;">
            Trigger Failover
          </button>
        </div>
        <div id="failover-result-box" style="margin-top: 10px; font-size: 12px;"></div>
      </div>
    `;
  }

  renderAuditTab() {
    return `
      <div>
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">Cryptographic Audit Trail (SHA-256 Hash Chain)</div>
        <button id="btn-load-audit" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; margin-bottom: 12px;">
          Fetch Audit Trail
        </button>
        <div id="audit-trail-container" style="display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto;">
          <div style="color: #94a3b8; font-size: 12px;">Click 'Fetch Audit Trail' to load verified logs.</div>
        </div>
      </div>
    `;
  }

  renderLoading(show) {
    const el = document.getElementById(this.containerId);
    if (el && show) {
      el.style.opacity = '0.6';
    } else if (el) {
      el.style.opacity = '1.0';
    }
  }

  attachEventListeners() {
    // Tabs
    document.querySelectorAll('.orch-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.target.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    // Refresh
    const refreshBtn = document.getElementById('btn-refresh-orchestration');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    // Plan selection
    document.querySelectorAll('.orch-plan-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const pid = card.getAttribute('data-plan-id');
        const plan = this.plans.find(p => p.orchestration_id === pid);
        if (plan) this.selectPlan(plan);
      });
    });

    // Failover
    const failoverBtn = document.getElementById('btn-trigger-failover');
    if (failoverBtn) {
      failoverBtn.addEventListener('click', async () => {
        const taskId = document.getElementById('input-failover-task')?.value?.trim();
        const errMsg = document.getElementById('input-failover-err')?.value?.trim() || 'Provider error';
        const resBox = document.getElementById('failover-result-box');
        if (!taskId || !this.selectedPlan) {
          if (resBox) resBox.innerHTML = `<span style="color: #ef4444;">Please provide a Task ID and ensure a plan is selected.</span>`;
          return;
        }
        try {
          const res = await orchestrationApi.failover(this.selectedPlan.orchestration_id, {
            task_id: taskId,
            error_message: errMsg,
          });
          if (resBox) resBox.innerHTML = `<span style="color: #34d399;">Failover Action: ${res.action} (${res.reason})</span>`;
          await this.loadData();
        } catch (err) {
          if (resBox) resBox.innerHTML = `<span style="color: #ef4444;">Failover Error: ${err.message}</span>`;
        }
      });
    }

    // Audit
    const loadAuditBtn = document.getElementById('btn-load-audit');
    if (loadAuditBtn) {
      loadAuditBtn.addEventListener('click', async () => {
        const container = document.getElementById('audit-trail-container');
        if (!container) return;
        try {
          const events = await orchestrationApi.getAudit(this.selectedPlan?.orchestration_id || null, 50);
          if (events.length === 0) {
            container.innerHTML = `<div style="color: #94a3b8; font-size: 12px;">No audit events recorded.</div>`;
            return;
          }
          container.innerHTML = events.map(ev => `
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 8px 12px; font-size: 11px;">
              <div style="display: flex; justify-content: space-between; color: #38bdf8; font-weight: 600;">
                <span>${ev.event_type}</span>
                <span style="color: #94a3b8;">${ev.timestamp}</span>
              </div>
              <div style="color: #cbd5e1; margin-top: 4px;">Hash: <code>${ev.hash?.substring(0, 16)}...</code></div>
            </div>
          `).join('');
        } catch (err) {
          container.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Failed to load audit trail: ${err.message}</div>`;
        }
      });
    }
  }
}

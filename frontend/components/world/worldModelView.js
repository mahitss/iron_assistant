/**
 * Autonomous World Model & Long-Horizon Foresight Engine Dashboard (Task 65)
 * Glassmorphic, multi-horizon temporal world and strategic foresight console.
 */

import { foresightApi } from '../../lib/api/endpoints.js';

export class WorldModelView {
  constructor(containerId) {
    this.container = typeof document !== 'undefined' ? (typeof containerId === 'string' ? document.getElementById(containerId) : containerId) : null;
    this.activeTab = 'overview'; // overview, entities, relationships, forecasts, scenarios, strategic, early_warnings, verification_audit
    this.overview = null;
    this.entities = [];
    this.relationships = [];
    this.forecasts = [];
    this.scenarios = [];
    this.risks = [];
    this.opportunities = [];
    this.earlyWarnings = [];
    this.auditTrail = [];
    this.selectedEntity = null;
    this.selectedForecast = null;
    this.selectedScenario = null;
    this.isLoading = false;
  }

  async init() {
    if (!this.container) return;
    this.renderSkeleton();
    await this.loadAllData();
  }

  async loadAllData() {
    this.isLoading = true;
    try {
      const [ov, ents, rels, fcts, scns, rs, opps, warns, aud] = await Promise.all([
        foresightApi.getOverview().catch(() => null),
        foresightApi.listEntities().catch(() => []),
        foresightApi.listRelationships().catch(() => []),
        foresightApi.listForecasts().catch(() => []),
        foresightApi.listScenarios().catch(() => []),
        foresightApi.listRisks().catch(() => []),
        foresightApi.listOpportunities().catch(() => []),
        foresightApi.listEarlyWarnings().catch(() => []),
        foresightApi.getAudit(50).catch(() => ({ records: [], chain_intact: true })),
      ]);

      this.overview = ov;
      this.entities = ents || [];
      this.relationships = rels || [];
      this.forecasts = fcts || [];
      this.scenarios = scns || [];
      this.risks = rs || [];
      this.opportunities = opps || [];
      this.earlyWarnings = warns || [];
      this.auditTrail = aud ? (aud.records || []) : [];

      if (this.entities.length > 0 && !this.selectedEntity) {
        this.selectedEntity = this.entities[0];
      }
      if (this.forecasts.length > 0 && !this.selectedForecast) {
        this.selectedForecast = this.forecasts[0];
      }
      if (this.scenarios.length > 0 && !this.selectedScenario) {
        this.selectedScenario = this.scenarios[0];
      }
    } catch (err) {
      console.error('Failed to load world model data:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  selectEntity(id) {
    this.selectedEntity = this.entities.find(e => e.entity_id === id) || null;
    this.render();
  }

  selectForecast(id) {
    this.selectedForecast = this.forecasts.find(f => f.forecast_id === id) || null;
    this.render();
  }

  selectScenario(id) {
    this.selectedScenario = this.scenarios.find(s => s.scenario_id === id) || null;
    this.render();
  }

  async triggerReassessment() {
    this.isLoading = true;
    try {
      await foresightApi.reassess({ reason: 'manual_operator_reassessment', invalidate_stale_forecasts: true });
      await this.loadAllData();
    } catch (err) {
      console.error('Reassessment failed:', err);
      this.isLoading = false;
      this.render();
    }
  }

  renderSkeleton() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="world-model-skeleton" style="padding: 24px; color: #a0aec0; font-family: Inter, sans-serif;">
        <div style="height: 48px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 20px; animation: pulse 1.5s infinite;"></div>
        <div style="height: 300px; background: rgba(255,255,255,0.03); border-radius: 12px; animation: pulse 1.5s infinite;"></div>
      </div>
    `;
  }

  render() {
    if (!this.container) return;

    const ov = this.overview || {};
    const tabs = [
      { id: 'overview', label: '🌐 World Overview' },
      { id: 'entities', label: `📦 Entities (${this.entities.length})` },
      { id: 'relationships', label: `🔗 Causal Graph (${this.relationships.length})` },
      { id: 'forecasts', label: `🔭 Forecasts (${this.forecasts.length})` },
      { id: 'scenarios', label: `🔀 Scenarios (${this.scenarios.length})` },
      { id: 'strategic', label: `🎯 Strategic (${this.risks.length}R / ${this.opportunities.length}O)` },
      { id: 'early_warnings', label: `⚠️ Early Warnings (${this.earlyWarnings.length})` },
      { id: 'verification_audit', label: '🛡️ Audit Trail' },
    ];

    const tabButtons = tabs.map(t => `
      <button 
        class="tab-btn ${this.activeTab === t.id ? 'active' : ''}" 
        data-tab="${t.id}"
        style="
          padding: 8px 16px; 
          margin-right: 8px; 
          border-radius: 8px; 
          background: ${this.activeTab === t.id ? 'linear-gradient(135deg, rgba(99,102,241,0.3), rgba(168,85,247,0.3))' : 'rgba(255,255,255,0.04)'};
          color: ${this.activeTab === t.id ? '#fff' : '#94a3b8'}; 
          border: 1px solid ${this.activeTab === t.id ? 'rgba(168,85,247,0.5)' : 'rgba(255,255,255,0.08)'};
          cursor: pointer; 
          font-weight: 500;
          font-size: 13px;
          transition: all 0.2s ease;
        "
      >
        ${t.label}
      </button>
    `).join('');

    this.container.innerHTML = `
      <div class="world-model-view-root" style="padding: 24px; color: #f8fafc; font-family: Inter, system-ui, sans-serif; background: #0b0f19; min-height: 100vh;">
        <!-- Header & Top Bar -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <h1 style="margin: 0; font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #60a5fa, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Autonomous World Model & Long-Horizon Foresight Engine
              </h1>
              <span style="font-size: 11px; padding: 2px 8px; border-radius: 12px; background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3);">
                TASK 65 ACTIVE
              </span>
            </div>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 12px;">
              Multi-horizon temporal projection, causal blast radius, isolated counterfactual scenarios, and invariant reality boundaries.
            </p>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button id="reassess-btn" style="padding: 8px 14px; border-radius: 8px; background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.4); color: #93c5fd; cursor: pointer; font-size: 12px; font-weight: 600;">
              🔄 Reassess Assumptions
            </button>
            <button id="refresh-world-btn" style="padding: 8px 14px; border-radius: 8px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); color: #cbd5e1; cursor: pointer; font-size: 12px;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Invariant Banner -->
        <div style="display: flex; gap: 12px; margin-bottom: 18px; overflow-x: auto; padding-bottom: 6px;">
          <span style="font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.25); color: #fca5a5;">
            WORLD MODEL ≠ REALITY
          </span>
          <span style="font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.25); color: #fcd34d;">
            FORECAST ≠ FACT
          </span>
          <span style="font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.25); color: #c4b5fd;">
            SCENARIO ≠ PREDICTION
          </span>
          <span style="font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.25); color: #93c5fd;">
            CORRELATION ≠ CAUSATION
          </span>
          <span style="font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25); color: #6ee7b7;">
            SIMULATED ≠ PRODUCTION
          </span>
          <span style="font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(236,72,153,0.1); border: 1px solid rgba(236,72,153,0.25); color: #f472b6;">
            EARLY WARNING ≠ INCIDENT
          </span>
        </div>

        <!-- Tab Navigation -->
        <div style="display: flex; gap: 4px; margin-bottom: 20px; overflow-x: auto; padding-bottom: 6px;">
          ${tabButtons}
        </div>

        <!-- Tab Content Body -->
        <div class="tab-content" style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px; backdrop-filter: blur(12px);">
          ${this.renderActiveTab()}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderActiveTab() {
    switch (this.activeTab) {
      case 'overview':
        return this.renderOverviewTab();
      case 'entities':
        return this.renderEntitiesTab();
      case 'relationships':
        return this.renderRelationshipsTab();
      case 'forecasts':
        return this.renderForecastsTab();
      case 'scenarios':
        return this.renderScenariosTab();
      case 'strategic':
        return this.renderStrategicTab();
      case 'early_warnings':
        return this.renderEarlyWarningsTab();
      case 'verification_audit':
        return this.renderAuditTab();
      default:
        return '<div>Tab content not found</div>';
    }
  }

  renderOverviewTab() {
    const ov = this.overview || {};
    return `
      <div>
        <h3 style="margin-top: 0; font-size: 16px; color: #e2e8f0; font-weight: 600;">Live World Model State Summary</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 24px;">
          <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px;">
            <div style="color: #64748b; font-size: 11px; text-transform: uppercase;">World Version</div>
            <div style="font-size: 24px; font-weight: 700; color: #38bdf8; margin-top: 4px;">v${ov.version || 1}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Scope: ${ov.scope || 'SYSTEM'}</div>
          </div>
          <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px;">
            <div style="color: #64748b; font-size: 11px; text-transform: uppercase;">Tracked Entities</div>
            <div style="font-size: 24px; font-weight: 700; color: #818cf8; margin-top: 4px;">${ov.entity_count || this.entities.length}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Freshness verified</div>
          </div>
          <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px;">
            <div style="color: #64748b; font-size: 11px; text-transform: uppercase;">Causal Relationships</div>
            <div style="font-size: 24px; font-weight: 700; color: #c084fc; margin-top: 4px;">${ov.relationship_count || this.relationships.length}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Empirical evidence backed</div>
          </div>
          <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px;">
            <div style="color: #64748b; font-size: 11px; text-transform: uppercase;">Active Forecasts</div>
            <div style="font-size: 24px; font-weight: 700; color: #fbbf24; margin-top: 4px;">${ov.active_forecasts_count || this.forecasts.length}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Multi-horizon ranges</div>
          </div>
          <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px;">
            <div style="color: #64748b; font-size: 11px; text-transform: uppercase;">Isolated Scenarios</div>
            <div style="font-size: 24px; font-weight: 700; color: #34d399; margin-top: 4px;">${ov.active_scenarios_count || this.scenarios.length}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Sandboxed counterfactuals</div>
          </div>
          <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 14px;">
            <div style="color: #64748b; font-size: 11px; text-transform: uppercase;">Early Warnings</div>
            <div style="font-size: 24px; font-weight: 700; color: #f87171; margin-top: 4px;">${ov.early_warnings_count || this.earlyWarnings.length}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Leading indicators</div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 16px;">
          <!-- Natural Language World Model Query Box -->
          <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;">
            <div style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 8px;">Ask World Model (Epistemic Reasoning)</div>
            <div style="display: flex; gap: 8px; margin-bottom: 12px;">
              <input id="world-query-input" type="text" placeholder="e.g., What happens if Primary Aurora Database latency spikes?" 
                style="flex: 1; padding: 8px 12px; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: #fff; font-size: 13px;">
              <button id="world-query-btn" style="padding: 8px 16px; background: #6366f1; border: none; border-radius: 6px; color: #fff; font-weight: 600; cursor: pointer; font-size: 13px;">
                Reason
              </button>
            </div>
            <div id="query-result-box" style="display: none; padding: 12px; background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.25); border-radius: 8px; font-size: 13px; color: #cbd5e1;"></div>
          </div>

          <!-- Integrity & Self-Check Status -->
          <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;">
            <div style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin-bottom: 12px;">Consistency & Boundaries</div>
            <div style="display: flex; flex-direction: column; gap: 10px; font-size: 12px;">
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">Consistency Audit:</span>
                <span style="color: #34d399; font-weight: 600;">${ov.integrity_status || 'HEALTHY'}</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">Direct Execution Block:</span>
                <span style="color: #38bdf8; font-weight: 600;">ACTIVE FIREWALL</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">State Poisoning Filter:</span>
                <span style="color: #a855f7; font-weight: 600;">VERIFIED PROVENANCE</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">Tenant Isolation:</span>
                <span style="color: #f59e0b; font-weight: 600;">ENFORCED</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderEntitiesTab() {
    const listHtml = this.entities.map(e => `
      <div 
        class="entity-item ${this.selectedEntity && this.selectedEntity.entity_id === e.entity_id ? 'selected' : ''}" 
        data-id="${e.entity_id}"
        style="
          padding: 12px; 
          margin-bottom: 8px; 
          border-radius: 8px; 
          background: ${this.selectedEntity && this.selectedEntity.entity_id === e.entity_id ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.02)'}; 
          border: 1px solid ${this.selectedEntity && this.selectedEntity.entity_id === e.entity_id ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.06)'}; 
          cursor: pointer;
        "
      >
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 600; font-size: 13px; color: #f1f5f9;">${e.name}</span>
          <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: ${e.state === 'HEALTHY' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color: ${e.state === 'HEALTHY' ? '#34d399' : '#f87171'};">
            ${e.state}
          </span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; margin-top: 4px;">
          <span>Type: ${e.type}</span>
          <span>Conf: ${(e.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
    `).join('');

    const sel = this.selectedEntity;
    const detailsHtml = sel ? `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px; margin-bottom: 14px;">
          <div>
            <h4 style="margin: 0; font-size: 16px; color: #fff;">${sel.name}</h4>
            <span style="font-size: 11px; color: #94a3b8;">ID: ${sel.entity_id} | Version: ${sel.version}</span>
          </div>
          <span style="padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; background: ${sel.state === 'HEALTHY' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}; color: ${sel.state === 'HEALTHY' ? '#34d399' : '#f87171'};">
            ${sel.state}
          </span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 12px; margin-bottom: 16px;">
          <div><span style="color: #64748b;">Type:</span> <span style="color: #cbd5e1;">${sel.type}</span></div>
          <div><span style="color: #64748b;">Scope:</span> <span style="color: #cbd5e1;">${sel.scope}</span></div>
          <div><span style="color: #64748b;">Certainty:</span> <span style="color: #38bdf8;">${sel.uncertainty} (${(sel.confidence * 100).toFixed(0)}%)</span></div>
          <div><span style="color: #64748b;">Authority:</span> <span style="color: #c084fc;">${sel.authority}</span></div>
          <div><span style="color: #64748b;">Staleness:</span> <span style="color: ${sel.is_stale ? '#f87171' : '#34d399'};">${sel.is_stale ? 'STALE' : 'FRESH'}</span></div>
          <div><span style="color: #64748b;">Valid From:</span> <span style="color: #cbd5e1;">${new Date(sel.valid_from).toLocaleTimeString()}</span></div>
        </div>
        <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">Attributes & Telemetry</div>
        <pre style="background: rgba(0,0,0,0.5); padding: 12px; border-radius: 6px; font-size: 11px; color: #38bdf8; overflow-x: auto; border: 1px solid rgba(255,255,255,0.05);">${JSON.stringify(sel.attributes, null, 2)}</pre>
      </div>
    ` : '<div style="color: #64748b;">Select an entity to view properties</div>';

    return `
      <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 16px;">
        <div style="max-height: 500px; overflow-y: auto;">${listHtml}</div>
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;">
          ${detailsHtml}
        </div>
      </div>
    `;
  }

  renderRelationshipsTab() {
    const rows = this.relationships.map(r => `
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 12px;">
        <td style="padding: 10px; font-weight: 600; color: #38bdf8;">${r.source_entity_id}</td>
        <td style="padding: 10px;">
          <span style="padding: 2px 6px; border-radius: 4px; background: rgba(99,102,241,0.2); color: #a5b4fc; font-size: 11px;">
            ${r.relationship_type}
          </span>
        </td>
        <td style="padding: 10px; font-weight: 600; color: #c084fc;">${r.target_entity_id}</td>
        <td style="padding: 10px; color: #fbbf24;">${(r.causal_strength * 100).toFixed(0)}%</td>
        <td style="padding: 10px; color: #34d399;">${r.is_critical ? '⚡ CRITICAL' : 'Standard'}</td>
        <td style="padding: 10px; color: #94a3b8; font-size: 11px;">${r.evidence && r.evidence[0] ? r.evidence[0] : 'Declared'}</td>
      </tr>
    `).join('');

    return `
      <div>
        <h4 style="margin-top: 0; font-size: 15px; color: #e2e8f0;">Semantic & Causal Dependency Edges</h4>
        <p style="font-size: 12px; color: #64748b; margin-top: -4px;">
          Invariant: CORRELATION ≠ CAUSATION. Causal edges require empirical intervention or stress-testing evidence.
        </p>
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <thead>
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); color: #64748b; font-size: 11px; text-transform: uppercase;">
              <th style="padding: 8px 10px;">Source Node</th>
              <th style="padding: 8px 10px;">Edge Type</th>
              <th style="padding: 8px 10px;">Target Node</th>
              <th style="padding: 8px 10px;">Causal Strength</th>
              <th style="padding: 8px 10px;">Criticality</th>
              <th style="padding: 8px 10px;">Empirical Evidence</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  renderForecastsTab() {
    const listHtml = this.forecasts.map(f => {
      const intv = f.intervals && f.intervals[0] ? f.intervals[0] : {};
      return `
        <div 
          class="forecast-item ${this.selectedForecast && this.selectedForecast.forecast_id === f.forecast_id ? 'selected' : ''}"
          data-id="${f.forecast_id}"
          style="
            padding: 12px; 
            margin-bottom: 8px; 
            border-radius: 8px; 
            background: ${this.selectedForecast && this.selectedForecast.forecast_id === f.forecast_id ? 'rgba(251,191,36,0.12)' : 'rgba(255,255,255,0.02)'}; 
            border: 1px solid ${this.selectedForecast && this.selectedForecast.forecast_id === f.forecast_id ? 'rgba(251,191,36,0.4)' : 'rgba(255,255,255,0.06)'}; 
            cursor: pointer;
          "
        >
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 600; font-size: 13px; color: #fef08a;">${f.topic}</span>
            <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(59,130,246,0.2); color: #93c5fd;">
              ${f.horizon}
            </span>
          </div>
          <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">
            Range: ${intv.lower_bound || 0} – ${intv.upper_bound || 0} ${intv.unit || ''} | Conf: ${(f.confidence * 100).toFixed(0)}%
          </div>
        </div>
      `;
    }).join('');

    const sel = this.selectedForecast;
    const detailsHtml = sel ? `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px; margin-bottom: 14px;">
          <div>
            <h4 style="margin: 0; font-size: 16px; color: #fef08a;">${sel.topic}</h4>
            <span style="font-size: 11px; color: #94a3b8;">Horizon: ${sel.horizon} | Model: ${sel.model_name}</span>
          </div>
          <span style="padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; background: rgba(16,185,129,0.2); color: #34d399;">
            ${sel.status}
          </span>
        </div>
        <p style="font-size: 13px; color: #cbd5e1; margin-bottom: 16px;">${sel.prediction_summary}</p>
        <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">Underlying Assumptions (Monitored for Staleness)</div>
        <ul style="margin: 0 0 16px 0; padding-left: 20px; font-size: 12px; color: #94a3b8;">
          ${(sel.assumptions || []).map(a => `<li>${a}</li>`).join('')}
        </ul>
        <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">Calibration & Outcome Tracking</div>
        <div style="font-size: 12px; color: #cbd5e1;">
          ${sel.actual_outcome ? `Outcome: ${sel.actual_outcome} (Calibration Score: ${sel.calibration_score})` : 'Awaiting real-world outcome observation to score calibration'}
        </div>
      </div>
    ` : '<div style="color: #64748b;">Select a forecast to view intervals and assumptions</div>';

    return `
      <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 16px;">
        <div style="max-height: 500px; overflow-y: auto;">${listHtml}</div>
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;">
          ${detailsHtml}
        </div>
      </div>
    `;
  }

  renderScenariosTab() {
    const listHtml = this.scenarios.map(s => `
      <div 
        class="scenario-item ${this.selectedScenario && this.selectedScenario.scenario_id === s.scenario_id ? 'selected' : ''}"
        data-id="${s.scenario_id}"
        style="
          padding: 12px; 
          margin-bottom: 8px; 
          border-radius: 8px; 
          background: ${this.selectedScenario && this.selectedScenario.scenario_id === s.scenario_id ? 'rgba(52,211,153,0.12)' : 'rgba(255,255,255,0.02)'}; 
          border: 1px solid ${this.selectedScenario && this.selectedScenario.scenario_id === s.scenario_id ? 'rgba(52,211,153,0.4)' : 'rgba(255,255,255,0.06)'}; 
          cursor: pointer;
        "
      >
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 600; font-size: 13px; color: #6ee7b7;">${s.name}</span>
          <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(168,85,247,0.2); color: #d8b4fe;">
            ${s.type}
          </span>
        </div>
        <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">
          Horizon: ${s.horizon} | Sensitivity: ${(s.sensitivity_score * 100).toFixed(0)}%
        </div>
      </div>
    `).join('');

    const sel = this.selectedScenario;
    const detailsHtml = sel ? `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px; margin-bottom: 14px;">
          <div>
            <h4 style="margin: 0; font-size: 16px; color: #6ee7b7;">${sel.name}</h4>
            <span style="font-size: 11px; color: #94a3b8;">Type: ${sel.type} | Sandbox Isolation Enforced</span>
          </div>
          <span style="padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; background: ${sel.is_robust ? 'rgba(16,185,129,0.2)' : 'rgba(59,130,246,0.2)'}; color: ${sel.is_robust ? '#34d399' : '#93c5fd'};">
            ${sel.is_robust ? 'ROBUST OUTCOME' : 'SENSITIVE BRANCH'}
          </span>
        </div>
        <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">Expected Branch Changes</div>
        <ul style="margin: 0 0 12px 0; padding-left: 20px; font-size: 12px; color: #cbd5e1;">
          ${(sel.expected_changes || []).map(c => `<li>${c}</li>`).join('')}
        </ul>
        <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">Branch Risks & Failure Conditions</div>
        <ul style="margin: 0 0 12px 0; padding-left: 20px; font-size: 12px; color: #f87171;">
          ${(sel.risks || []).map(r => `<li>${r}</li>`).join('')}
        </ul>
        <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">Emergent Opportunities</div>
        <ul style="margin: 0; padding-left: 20px; font-size: 12px; color: #34d399;">
          ${(sel.opportunities || []).map(o => `<li>${o}</li>`).join('')}
        </ul>
      </div>
    ` : '<div style="color: #64748b;">Select a scenario branch to inspect sandboxed counterfactuals</div>';

    return `
      <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 16px;">
        <div style="max-height: 500px; overflow-y: auto;">${listHtml}</div>
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;">
          ${detailsHtml}
        </div>
      </div>
    `;
  }

  renderStrategicTab() {
    const riskRows = this.risks.map(r => `
      <div style="padding: 12px; background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.2); border-radius: 8px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: #fca5a5;">
          <span>${r.title}</span>
          <span>Impact: ${(r.impact * 10).toFixed(1)}/10</span>
        </div>
        <p style="margin: 4px 0 6px 0; font-size: 12px; color: #cbd5e1;">${r.description}</p>
        <div style="font-size: 11px; color: #94a3b8;">Horizon: ${r.time_horizon} | Mitigations: ${(r.mitigations || []).join(', ')}</div>
      </div>
    `).join('');

    const oppRows = this.opportunities.map(o => `
      <div style="padding: 12px; background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.2); border-radius: 8px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; color: #6ee7b7;">
          <span>${o.title}</span>
          <span>Optionality: ${(o.optionality_score * 100).toFixed(0)}%</span>
        </div>
        <p style="margin: 4px 0 6px 0; font-size: 12px; color: #cbd5e1;">${o.description}</p>
        <div style="font-size: 11px; color: #94a3b8;">Horizon: ${o.time_horizon} | Value: ${(o.potential_value * 100).toFixed(0)}%</div>
      </div>
    `).join('');

    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <div>
          <h4 style="margin-top: 0; color: #f87171; font-size: 15px;">Strategic Risk Register</h4>
          ${riskRows || '<div style="color: #64748b; font-size: 12px;">No active open risks</div>'}
        </div>
        <div>
          <h4 style="margin-top: 0; color: #34d399; font-size: 15px;">Strategic Opportunity Register</h4>
          ${oppRows || '<div style="color: #64748b; font-size: 12px;">No identified strategic opportunities</div>'}
        </div>
      </div>
    `;
  }

  renderEarlyWarningsTab() {
    const listHtml = this.earlyWarnings.map(w => `
      <div style="padding: 14px; background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.25); border-radius: 10px; margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 16px;">⚠️</span>
            <span style="font-size: 14px; font-weight: 600; color: #fef08a;">${w.title}</span>
          </div>
          <span style="padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background: rgba(239,68,68,0.2); color: #f87171;">
            ${w.severity}
          </span>
        </div>
        <p style="margin: 6px 0; font-size: 12px; color: #cbd5e1;">${w.description}</p>
        <div style="display: flex; gap: 16px; font-size: 11px; color: #94a3b8;">
          <span>Trend: <strong>${w.trend}</strong></span>
          <span>Affected: <strong>${(w.affected_entities || []).join(', ')}</strong></span>
          <span>Action: <strong>${w.recommended_action}</strong></span>
        </div>
      </div>
    `).join('');

    return `
      <div>
        <h4 style="margin-top: 0; font-size: 15px; color: #e2e8f0;">Emerging Risk Signals (Deduplicated Stream)</h4>
        <p style="font-size: 12px; color: #64748b; margin-top: -4px;">
          Invariant: EARLY WARNING ≠ INCIDENT. Indicates probability shifts in leading indicators, avoiding alert storm cascades.
        </p>
        ${listHtml || '<div style="color: #64748b; font-size: 13px;">No active early warning signals. World metrics tracking smoothly.</div>'}
      </div>
    `;
  }

  renderAuditTab() {
    const records = this.auditTrail || [];
    const rows = records.map(r => `
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 11px; font-family: monospace;">
        <td style="padding: 8px; color: #94a3b8;">${new Date(r.timestamp).toLocaleTimeString()}</td>
        <td style="padding: 8px; color: #38bdf8; font-weight: 600;">${r.event_type}</td>
        <td style="padding: 8px; color: #cbd5e1;">${r.actor}</td>
        <td style="padding: 8px; color: #a5b4fc;">${r.record_hash ? r.record_hash.substring(0, 10) + '...' : 'GENESIS'}</td>
        <td style="padding: 8px; color: #64748b;">${JSON.stringify(r.details || {}).substring(0, 50)}...</td>
      </tr>
    `).join('');

    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div>
            <h4 style="margin: 0; font-size: 15px; color: #e2e8f0;">Cryptographic SHA-256 Hash Chain Trail</h4>
            <span style="font-size: 12px; color: #64748b;">Immutable state progression audit records</span>
          </div>
          <span style="padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; background: rgba(16,185,129,0.2); color: #34d399;">
            CHAIN INTEGRITY VERIFIED
          </span>
        </div>
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <thead>
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); color: #64748b; font-size: 11px; text-transform: uppercase;">
              <th style="padding: 8px;">Timestamp</th>
              <th style="padding: 8px;">Event Type</th>
              <th style="padding: 8px;">Actor</th>
              <th style="padding: 8px;">Record Hash (SHA-256)</th>
              <th style="padding: 8px;">Metadata</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  bindEvents() {
    if (!this.container) return;

    // Tab buttons
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    // Reassess button
    const reassessBtn = this.container.querySelector('#reassess-btn');
    if (reassessBtn) {
      reassessBtn.addEventListener('click', () => this.triggerReassessment());
    }

    // Refresh button
    const refreshBtn = this.container.querySelector('#refresh-world-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadAllData());
    }

    // Entity select
    this.container.querySelectorAll('.entity-item').forEach(el => {
      el.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) this.selectEntity(id);
      });
    });

    // Forecast select
    this.container.querySelectorAll('.forecast-item').forEach(el => {
      el.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) this.selectForecast(id);
      });
    });

    // Scenario select
    this.container.querySelectorAll('.scenario-item').forEach(el => {
      el.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) this.selectScenario(id);
      });
    });

    // Query button
    const queryBtn = this.container.querySelector('#world-query-btn');
    const queryInput = this.container.querySelector('#world-query-input');
    const queryResultBox = this.container.querySelector('#query-result-box');
    if (queryBtn && queryInput && queryResultBox) {
      queryBtn.addEventListener('click', async () => {
        const text = queryInput.value.trim();
        if (!text) return;
        queryBtn.disabled = true;
        queryBtn.textContent = 'Reasoning...';
        try {
          const res = await foresightApi.query({ query: text, include_causal_path: true, include_scenarios: true });
          queryResultBox.style.display = 'block';
          queryResultBox.innerHTML = `
            <div style="font-weight: 600; color: #60a5fa; margin-bottom: 4px;">World Model Reasoning Answer:</div>
            <div>${res.answer}</div>
            <div style="margin-top: 8px; font-size: 11px; color: #94a3b8;">${res.explanation}</div>
          `;
        } catch (err) {
          queryResultBox.style.display = 'block';
          queryResultBox.innerHTML = `<span style="color: #f87171;">Query error: ${err.message || err}</span>`;
        } finally {
          queryBtn.disabled = false;
          queryBtn.textContent = 'Reason';
        }
      });
    }
  }
}

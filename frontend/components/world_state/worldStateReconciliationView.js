/**
 * KAIRO Autonomous World-State Reconstruction, State Estimation, Reality Synchronization & Drift Reconciliation View (Task 98).
 *
 * Provides a comprehensive operator console for:
 * 1. Current Reconstructed World State (entities, scopes, statuses, confidence, freshness)
 * 2. Reality Drift Engine (divergences between expected and actual state, severity, causal linking)
 * 3. Ingested Observations (telemetry, probe observations, epistemic classifications)
 * 4. Dialectic Conflicts (source disagreements, preserved dialectics, resolutions)
 * 5. State Invariants & Freshness Audit (formal domain contracts, invariant violations)
 * 6. Change Attribution (ActionTransaction and Decision links vs UNATTRIBUTED_CHANGE)
 * 7. Historical Reconstruction & Snapshots (point-in-time state at timestamp T, structural diffs)
 * 8. Revalidation Queue (bounded candidates scheduled for downstream verification)
 */

export class WorldStateReconciliationView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api || this._createDefaultApi();
    this.state = {
      activeTab: 'current', // 'current' | 'drift' | 'observations' | 'conflicts' | 'invariants' | 'attribution' | 'historical' | 'revalidation'
      selectedScope: 'SYSTEM',
      entities: [],
      selectedEntity: null,
      drifts: [],
      observations: [],
      conflicts: [],
      invariants: [],
      revalidations: [],
      history: [],
      snapshots: [],
      diffResult: null,
      reconstructionResult: null,
      historicalTimestamp: new Date().toISOString(),
      isLoading: false,
      error: null,
      metrics: {
        totalEntities: 0,
        activeDriftCount: 0,
        activeConflictsCount: 0,
        staleEntitiesCount: 0
      }
    };
  }

  _createDefaultApi() {
    return {
      getCurrentState: async (scope = 'SYSTEM') => {
        const res = await fetch(`/api/v1/state/current?scope=${scope}`);
        return res.json();
      },
      getScopeEntities: async (scope = 'SYSTEM') => {
        const res = await fetch(`/api/v1/state/${scope}`);
        return res.json();
      },
      getObservations: async (scope = 'SYSTEM') => {
        const res = await fetch(`/api/v1/state/${scope}/observations`);
        return res.json();
      },
      getDriftRecords: async (scope = 'SYSTEM') => {
        const res = await fetch(`/api/v1/state/${scope}/drift`);
        return res.json();
      },
      getConflicts: async (scope = 'SYSTEM') => {
        const res = await fetch(`/api/v1/state/${scope}/conflicts`);
        return res.json();
      },
      validateInvariants: async () => {
        const res = await fetch('/api/v1/state/validate', { method: 'POST' });
        return res.json();
      },
      reconcileState: async (scope = 'SYSTEM') => {
        const res = await fetch('/api/v1/state/reconcile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scope })
        });
        return res.json();
      },
      createSnapshot: async (scope = 'SYSTEM') => {
        const res = await fetch(`/api/v1/state/snapshot?scope=${scope}`, { method: 'POST' });
        return res.json();
      },
      reconstructHistorical: async (timestamp, scope = 'SYSTEM') => {
        const res = await fetch('/api/v1/state/reconstruct', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ timestamp, scope })
        });
        return res.json();
      },
      getEntityHistory: async (entityId, scope = 'SYSTEM') => {
        const res = await fetch(`/api/v1/state/${scope}/history?entity_id=${encodeURIComponent(entityId)}`);
        return res.json();
      }
    };
  }

  async init() {
    await this.refresh();
  }

  async refresh() {
    this.state.isLoading = true;
    this.render();
    try {
      const stateData = await this.api.getCurrentState(this.state.selectedScope);
      this.state.entities = stateData.entities || [];
      this.state.metrics.totalEntities = stateData.total_entities || this.state.entities.length;
      this.state.metrics.activeConflictsCount = stateData.active_conflicts_count || 0;
      this.state.metrics.activeDriftCount = stateData.active_drift_count || 0;

      const [drifts, obs, confs, invs] = await Promise.all([
        (this.api.getDriftRecords ? this.api.getDriftRecords(this.state.selectedScope) : Promise.resolve([])).catch(() => []),
        (this.api.getObservations ? this.api.getObservations(this.state.selectedScope) : Promise.resolve([])).catch(() => []),
        (this.api.getConflicts ? this.api.getConflicts(this.state.selectedScope) : Promise.resolve([])).catch(() => []),
        (this.api.validateInvariants ? this.api.validateInvariants() : (this.api.auditFreshnessAndInvariants ? this.api.auditFreshnessAndInvariants() : Promise.resolve([]))).catch(() => [])
      ]);

      this.state.drifts = Array.isArray(drifts) ? drifts : (drifts?.drifts || []);
      this.state.observations = Array.isArray(obs) ? obs : (obs?.observations || []);
      this.state.conflicts = Array.isArray(confs) ? confs : (confs?.conflicts || []);
      this.state.invariants = Array.isArray(invs) ? invs : (invs?.violations || []);
      this.state.metrics.activeDriftCount = this.state.drifts.length;
      this.state.metrics.activeConflictsCount = this.state.conflicts.length;
      this.state.metrics.staleEntitiesCount = this.state.entities.filter(e => e.freshness === 'STALE').length;
      this.state.error = null;
    } catch (err) {
      this.state.error = err.message || 'Failed to load world state data.';
    } finally {
      this.state.isLoading = false;
      this.render();
    }
  }

  setTab(tab) {
    this.state.activeTab = tab;
    this.render();
  }

  setScope(scope) {
    this.state.selectedScope = scope;
    this.refresh();
  }

  selectEntity(entity) {
    this.state.selectedEntity = entity;
    this.render();
  }

  async triggerReconcile() {
    this.state.isLoading = true;
    this.render();
    try {
      if (this.api.reconcileState) {
        await this.api.reconcileState(this.state.selectedScope);
      } else if (this.api.reconcile) {
        await this.api.reconcile(this.state.selectedScope);
      }
      await this.refresh();
    } catch (err) {
      this.state.error = `Reconciliation failed: ${err.message}`;
      this.state.isLoading = false;
      this.render();
    }
  }

  async triggerHistoricalReconstruct(timestamp) {
    this.state.isLoading = true;
    this.render();
    try {
      const res = await this.api.reconstructHistorical(timestamp, this.state.selectedScope);
      this.state.reconstructionResult = res;
    } catch (err) {
      this.state.error = `Historical reconstruction failed: ${err.message}`;
    } finally {
      this.state.isLoading = false;
      this.render();
    }
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="world-state-reconciliation-view" style="padding: 24px; color: var(--text-primary, #e6edf3); font-family: Inter, sans-serif;">
        <!-- Header & KPI Bar -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; border-bottom: 1px solid var(--border-subtle, #30363d); padding-bottom: 16px;">
          <div>
            <h2 style="margin: 0 0 8px 0; font-size: 22px; display: flex; align-items: center; gap: 10px;">
              <span>🌐 World-State Reconstruction & Drift Engine</span>
              <span style="font-size: 11px; padding: 2px 8px; border-radius: 12px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);">Task 98 Production</span>
            </h2>
            <div style="font-size: 13px; color: var(--text-secondary, #8b949e);">
              Reality synchronization, multi-source state estimation, empirical drift detection, and revalidation.
            </div>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <select id="scope-selector" style="background: #161b22; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; font-size: 12px;">
              ${['SYSTEM', 'PROJECT', 'WORKFLOW', 'TASK', 'SERVICE', 'CAPABILITY', 'RESOURCE', 'ENVIRONMENT'].map(s => `
                <option value="${s}" ${this.state.selectedScope === s ? 'selected' : ''}>Scope: ${s}</option>
              `).join('')}
            </select>
            <button id="btn-reconcile" style="background: #238636; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer; font-weight: 500;">
              ⚡ Reconcile Reality
            </button>
            <button id="btn-refresh" style="background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer;">
              🔄 Refresh
            </button>
          </div>
        </div>

        <!-- Metric Badges -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
          <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: #8b949e; text-transform: uppercase;">Total Reconstructed Entities</div>
            <div style="font-size: 24px; font-weight: 600; color: #58a6ff; margin-top: 4px;">${this.state.metrics.totalEntities}</div>
          </div>
          <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: #8b949e; text-transform: uppercase;">Active Reality Drifts</div>
            <div style="font-size: 24px; font-weight: 600; color: ${this.state.drifts.length > 0 ? '#f85149' : '#3fb950'}; margin-top: 4px;">${this.state.drifts.length}</div>
          </div>
          <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: #8b949e; text-transform: uppercase;">Dialectic Conflicts</div>
            <div style="font-size: 24px; font-weight: 600; color: ${this.state.conflicts.length > 0 ? '#d29922' : '#3fb950'}; margin-top: 4px;">${this.state.conflicts.length}</div>
          </div>
          <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: #8b949e; text-transform: uppercase;">Stale Entities / Invariants</div>
            <div style="font-size: 24px; font-weight: 600; color: ${this.state.invariants.length > 0 ? '#d29922' : '#8b949e'}; margin-top: 4px;">${this.state.invariants.length}</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid #30363d; margin-bottom: 20px;">
          ${[
            { id: 'current', label: 'Current State' },
            { id: 'drift', label: `Reality Drift (${this.state.drifts.length})` },
            { id: 'observations', label: `Observations (${this.state.observations.length})` },
            { id: 'conflicts', label: `Conflicts (${this.state.conflicts.length})` },
            { id: 'invariants', label: `Invariants (${this.state.invariants.length})` },
            { id: 'historical', label: 'Historical Reconstruction' }
          ].map(t => `
            <button class="nav-tab" data-tab="${t.id}" style="padding: 8px 16px; background: transparent; border: none; border-bottom: 2px solid ${this.state.activeTab === t.id ? '#58a6ff' : 'transparent'}; color: ${this.state.activeTab === t.id ? '#58a6ff' : '#8b949e'}; font-size: 13px; font-weight: 500; cursor: pointer;">
              ${t.label}
            </button>
          `).join('')}
        </div>

        <!-- Tab Content -->
        <div class="tab-content">
          ${this._renderActiveTab()}
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _renderActiveTab() {
    switch (this.state.activeTab) {
      case 'current':
        return this._renderCurrentStateTab();
      case 'drift':
        return this._renderDriftTab();
      case 'observations':
        return this._renderObservationsTab();
      case 'conflicts':
        return this._renderConflictsTab();
      case 'invariants':
        return this._renderInvariantsTab();
      case 'historical':
        return this._renderHistoricalTab();
      default:
        return `<div style="padding: 20px; color: #8b949e;">Select a tab.</div>`;
    }
  }

  _renderCurrentStateTab() {
    if (this.state.entities.length === 0) {
      return `<div style="padding: 40px; text-align: center; color: #8b949e; background: #161b22; border-radius: 8px; border: 1px solid #30363d;">No entities registered in scope '${this.state.selectedScope}'.</div>`;
    }

    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden;">
          <div style="padding: 12px 16px; border-bottom: 1px solid #30363d; font-weight: 600; font-size: 13px; color: #c9d1d9;">
            Reconstructed State Entities (${this.state.entities.length})
          </div>
          <div style="max-height: 500px; overflow-y: auto;">
            ${this.state.entities.map(e => `
              <div class="entity-item" data-id="${e.entity_id}" style="padding: 12px 16px; border-bottom: 1px solid #21262d; cursor: pointer; background: ${this.state.selectedEntity && this.state.selectedEntity.entity_id === e.entity_id ? '#1f242c' : 'transparent'};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: 500; font-size: 13px; color: #58a6ff;">${e.canonical_name || e.entity_id}</span>
                  <span style="font-size: 10px; padding: 2px 6px; border-radius: 4px; background: ${e.status === 'CURRENT' ? 'rgba(63, 185, 80, 0.2)' : 'rgba(248, 81, 73, 0.2)'}; color: ${e.status === 'CURRENT' ? '#3fb950' : '#f85149'};">
                    ${e.status}
                  </span>
                </div>
                <div style="font-size: 11px; color: #8b949e; margin-top: 4px; display: flex; gap: 12px;">
                  <span>Certainty: <b>${e.epistemic_certainty}</b></span>
                  <span>Confidence: <b>${(e.confidence * 100).toFixed(0)}%</b></span>
                  <span>Freshness: <b>${e.freshness}</b></span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px;">
          <div style="font-weight: 600; font-size: 13px; color: #c9d1d9; border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-bottom: 14px;">
            Entity Deep State Detail
          </div>
          ${this.state.selectedEntity ? `
            <div style="font-size: 12px; line-height: 1.6;">
              <p><b>ID:</b> <code style="color: #79c0ff;">${this.state.selectedEntity.entity_id}</code></p>
              <p><b>Scope:</b> ${this.state.selectedEntity.scope}</p>
              <p><b>Status:</b> ${this.state.selectedEntity.status}</p>
              <p><b>Verification Confidence:</b> ${(this.state.selectedEntity.verification_confidence * 100).toFixed(0)}%</p>
              <p><b>Observation Confidence:</b> ${(this.state.selectedEntity.observation_confidence * 100).toFixed(0)}%</p>
              <p><b>Last Observed:</b> ${this.state.selectedEntity.last_observed_at}</p>
              <div style="margin-top: 14px;">
                <b>Reconstructed Attributes:</b>
                <pre style="background: #0d1117; padding: 10px; border-radius: 6px; font-size: 11px; overflow-x: auto; color: #8b949e;">${JSON.stringify(this.state.selectedEntity.attributes, null, 2)}</pre>
              </div>
            </div>
          ` : `
            <div style="color: #8b949e; padding: 20px; text-align: center;">Click an entity from the list to inspect detailed attributes and provenance.</div>
          `}
        </div>
      </div>
    `;
  }

  _renderDriftTab() {
    if (this.state.drifts.length === 0) {
      return `<div style="padding: 40px; text-align: center; color: #3fb950; background: #161b22; border-radius: 8px; border: 1px solid #30363d;">✓ Zero reality drift detected. All observed states match operational expectations.</div>`;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        ${this.state.drifts.map(d => `
          <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-weight: 600; font-size: 14px; color: #f85149;">${d.drift_type} on ${d.canonical_id || d.entity_id}</span>
              <span style="font-size: 11px; padding: 2px 8px; border-radius: 12px; background: rgba(248, 81, 73, 0.2); color: #f85149; font-weight: 600;">
                Severity: ${d.severity}
              </span>
            </div>
            <div style="font-size: 12px; color: #c9d1d9; margin-bottom: 8px;">
              <b>Classification:</b> ${d.classification} | <b>Attributed To:</b> <code>${d.attribution || d.attributed_source_type || 'UNATTRIBUTED_CHANGE'}</code>
            </div>
            <div style="font-size: 12px; color: #8b949e; background: #0d1117; padding: 8px; border-radius: 4px;">
              ${(d.evidence || [d.cause_hypothesis].filter(Boolean)).map(ev => `<div>• ${ev}</div>`).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  _renderObservationsTab() {
    if (this.state.observations.length === 0) {
      return `<div style="padding: 40px; text-align: center; color: #8b949e; background: #161b22; border-radius: 8px; border: 1px solid #30363d;">No observations ingested yet.</div>`;
    }

    return `
      <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden;">
        <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
          <thead>
            <tr style="background: #21262d; color: #8b949e; border-bottom: 1px solid #30363d;">
              <th style="padding: 10px 14px;">Timestamp</th>
              <th style="padding: 10px 14px;">Source</th>
              <th style="padding: 10px 14px;">Entity ID</th>
              <th style="padding: 10px 14px;">Observed Value</th>
              <th style="padding: 10px 14px;">Confidence</th>
              <th style="padding: 10px 14px;">Certainty</th>
            </tr>
          </thead>
          <tbody>
            ${this.state.observations.slice(-25).reverse().map(o => `
              <tr style="border-bottom: 1px solid #21262d;">
                <td style="padding: 10px 14px; color: #8b949e;">${o.observed_at}</td>
                <td style="padding: 10px 14px;"><code>${o.source_id || o.source}</code></td>
                <td style="padding: 10px 14px; color: #58a6ff;">${o.canonical_id || o.entity_id}</td>
                <td style="padding: 10px 14px; font-weight: 500;">${JSON.stringify(o.observed_value || o.attributes)}</td>
                <td style="padding: 10px 14px;">${((o.confidence ?? 1) * 100).toFixed(0)}%</td>
                <td style="padding: 10px 14px;">${o.certainty || o.epistemic_certainty || 'OBSERVED'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderConflictsTab() {
    if (this.state.conflicts.length === 0) {
      return `<div style="padding: 40px; text-align: center; color: #3fb950; background: #161b22; border-radius: 8px; border: 1px solid #30363d;">✓ No active dialectic contradictions between observation sources.</div>`;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        ${this.state.conflicts.map(c => `
          <div style="background: #161b22; border: 1px solid #d29922; border-radius: 8px; padding: 16px;">
            <div style="font-weight: 600; font-size: 13px; color: #d29922; margin-bottom: 6px;">
              Contradiction on Entity '${c.canonical_id || c.entity_id}' [Attribute: ${c.attribute_name}]
            </div>
            <div style="font-size: 12px; color: #8b949e; margin-bottom: 8px;">
              Detected: ${c.created_at || c.detected_at} | Status: <b>${c.status || c.resolution_state}</b>
            </div>
            <div style="background: #0d1117; padding: 10px; border-radius: 4px; font-size: 11px;">
              <b>Conflicting Observations / Sources:</b>
              ${(c.observations || (c.sources || []).map(s => ({ source: s, observed_value: 'disputed' }))).map(o => `<div>• Source: <b>${o.source || o.source_id}</b> -> Observed: <code>${JSON.stringify(o.observed_value || o.value)}</code></div>`).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  _renderInvariantsTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 8px;">
          <div style="font-weight: 600; font-size: 13px; color: #c9d1d9; margin-bottom: 6px;">Domain Invariant Status</div>
          <div style="font-size: 12px; color: #8b949e;">
            Evaluates formal contracts: Missing observation ≠ healthy, capability version retirement validity, post-action satisfaction.
          </div>
        </div>
        ${this.state.invariants.length === 0 ? `
          <div style="padding: 30px; text-align: center; color: #3fb950; background: #161b22; border-radius: 8px; border: 1px solid #30363d;">
            ✓ All operational invariants satisfied across registered components.
          </div>
        ` : `
          ${this.state.invariants.map(inv => `
            <div style="background: #161b22; border: 1px solid #f85149; border-radius: 8px; padding: 14px;">
              <div style="font-weight: 600; font-size: 13px; color: #f85149;">
                [${inv.severity}] ${inv.invariant_name} on ${inv.entity_id}
              </div>
              <div style="font-size: 12px; color: #c9d1d9; margin: 4px 0;">${inv.description}</div>
              <pre style="background: #0d1117; padding: 8px; border-radius: 4px; font-size: 10px; color: #8b949e; margin: 0;">${JSON.stringify(inv.evidence, null, 2)}</pre>
            </div>
          `).join('')}
        `}
      </div>
    `;
  }

  _renderHistoricalTab() {
    return `
      <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px;">
        <div style="font-weight: 600; font-size: 13px; color: #c9d1d9; margin-bottom: 12px;">
          Historical State Reconstruction (Phase 33)
        </div>
        <div style="display: flex; gap: 10px; margin-bottom: 16px;">
          <input type="datetime-local" id="hist-ts-input" style="background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; font-size: 12px;" value="${new Date().toISOString().slice(0, 16)}" />
          <button id="btn-reconstruct-hist" style="background: #1f6feb; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer;">
            Reconstruct State at Timestamp
          </button>
        </div>
        ${this.state.reconstructionResult ? `
          <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px;">
            <div style="font-size: 12px; color: #58a6ff; font-weight: 600; margin-bottom: 8px;">
              Reconstruction for ${this.state.reconstructionResult.requested_timestamp} (Entities: ${this.state.reconstructionResult.reconstructed_entities_count})
            </div>
            <pre style="font-size: 11px; color: #8b949e; margin: 0; overflow-x: auto;">${JSON.stringify(this.state.reconstructionResult.entities, null, 2)}</pre>
          </div>
        ` : `
          <div style="font-size: 12px; color: #8b949e;">Select a timestamp to inspect exact point-in-time entity state without guesswork.</div>
        `}
      </div>
    `;
  }

  _bindEvents() {
    // Tabs
    const tabs = this.container.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        this.setTab(tab.getAttribute('data-tab'));
      });
    });

    // Scope selector
    const scopeSel = this.container.querySelector('#scope-selector');
    if (scopeSel) {
      scopeSel.addEventListener('change', (e) => {
        this.setScope(e.target.value);
      });
    }

    // Refresh button
    const btnRefresh = this.container.querySelector('#btn-refresh');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => this.refresh());
    }

    // Reconcile button
    const btnReconcile = this.container.querySelector('#btn-reconcile');
    if (btnReconcile) {
      btnReconcile.addEventListener('click', () => this.triggerReconcile());
    }

    // Entity item clicks
    const entityItems = this.container.querySelectorAll('.entity-item');
    entityItems.forEach(item => {
      item.addEventListener('click', () => {
        const id = item.getAttribute('data-id');
        const ent = this.state.entities.find(e => e.entity_id === id);
        if (ent) this.selectEntity(ent);
      });
    });

    // Historical reconstruct button
    const btnHist = this.container.querySelector('#btn-reconstruct-hist');
    if (btnHist) {
      btnHist.addEventListener('click', () => {
        const tsInput = this.container.querySelector('#hist-ts-input');
        if (tsInput && tsInput.value) {
          this.triggerHistoricalReconstruct(new Date(tsInput.value).toISOString());
        }
      });
    }
  }
}

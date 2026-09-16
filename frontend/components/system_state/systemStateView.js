/**
 * Kairo Autonomous System State Graph, Self-Modeling & Operational Digital Twin Component (Task 93).
 *
 * Provides a unified operational view of Kairo's internal reality:
 * 1. Overview & Health Metrics
 * 2. Interactive Operational State Graph
 * 3. Active Goals
 * 4. Active Tasks & Workflows
 * 5. Native Runtime Substrate
 * 6. Capabilities Lifecycle
 * 7. Resource Pressure
 * 8. Dependencies
 * 9. Incidents & Blast Radius
 * 10. Security & EmergencyStop
 * 11. Governance Constraints
 * 12. Providers & Models
 * 13. State Deltas & Changes
 * 14. Snapshots History
 * 15. Structured Self-Diagnostics & Canonical Self-Model Introspection
 */

export class SystemStateView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api || this._createDefaultApi();
    this.state = {
      activeTab: 'overview',
      summary: null,
      health: null,
      graphData: { nodes: [], links: [] },
      diagnostics: null,
      selfModel: null,
      resources: null,
      dependencies: null,
      incidents: null,
      changes: [],
      snapshots: [],
      selectedComponent: null,
      impactResult: null,
      isLoading: false,
      error: null,
    };
  }

  _createDefaultApi() {
    return {
      getSummary: async () => (await fetch('/api/v1/system-state/summary')).json(),
      getHealth: async () => (await fetch('/api/v1/system-state/health')).json(),
      getGraph: async () => (await fetch('/api/v1/system-state/graph')).json(),
      getDiagnostics: async () => (await fetch('/api/v1/system-state/diagnostics')).json(),
      getSelfModel: async () => (await fetch('/api/v1/system-state/self-model')).json(),
      getResources: async () => (await fetch('/api/v1/system-state/resources')).json(),
      getDependencies: async () => (await fetch('/api/v1/system-state/dependencies')).json(),
      getIncidents: async () => (await fetch('/api/v1/system-state/incidents')).json(),
      getChanges: async () => (await fetch('/api/v1/system-state/changes')).json(),
      getSnapshots: async () => (await fetch('/api/v1/system-state/snapshots')).json(),
      createSnapshot: async (data) =>
        (
          await fetch('/api/v1/system-state/snapshot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data || {}),
          })
        ).json(),
      reconcile: async () =>
        (
          await fetch('/api/v1/system-state/reconcile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
          })
        ).json(),
      getImpact: async (id) => (await fetch(`/api/v1/system-state/impact/${encodeURIComponent(id)}`)).json(),
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
    this._updateLoadingState();

    try {
      const [summary, health, graph, diagnostics, selfModel, resources, deps, incs, changes, snaps] =
        await Promise.all([
          this.api.getSummary().catch(() => null),
          this.api.getHealth().catch(() => null),
          this.api.getGraph().catch(() => ({ nodes: [], links: [] })),
          this.api.getDiagnostics().catch(() => null),
          this.api.getSelfModel().catch(() => null),
          this.api.getResources().catch(() => null),
          this.api.getDependencies().catch(() => null),
          this.api.getIncidents().catch(() => null),
          this.api.getChanges().catch(() => []),
          this.api.getSnapshots().catch(() => []),
        ]);

      this.state.summary = summary;
      this.state.health = health;
      this.state.graphData = graph || { nodes: [], links: [] };
      this.state.diagnostics = diagnostics;
      this.state.selfModel = selfModel;
      this.state.resources = resources;
      this.state.dependencies = deps;
      this.state.incidents = incs;
      this.state.changes = changes || [];
      this.state.snapshots = snaps || [];
      this.state.error = null;
    } catch (err) {
      this.state.error = err.message || 'Failed to load system state data.';
    } finally {
      this.state.isLoading = false;
      this._renderActiveTab();
    }
  }

  _template() {
    return `
      <div class="system-state-view">
        <header class="ss-header">
          <div class="ss-title-block">
            <h2>KAIRO Autonomous System State Graph</h2>
            <span class="ss-subtitle">Operational Digital Twin & Self-Modeling Substrate (Task 93)</span>
          </div>
          <div class="ss-header-actions">
            <button id="ss-btn-reconcile" class="btn btn-secondary" title="Reconcile live state against authoritative subsystems">
              <span class="icon">🔄</span> Reconcile State
            </button>
            <button id="ss-btn-snapshot" class="btn btn-primary" title="Capture immutable operational snapshot">
              <span class="icon">📸</span> Capture Snapshot
            </button>
            <button id="ss-btn-refresh" class="btn btn-icon" title="Refresh">↻</button>
          </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="ss-nav-tabs">
          <button class="ss-tab active" data-tab="overview">Overview</button>
          <button class="ss-tab" data-tab="graph">Live State Graph</button>
          <button class="ss-tab" data-tab="goals">Active Goals</button>
          <button class="ss-tab" data-tab="tasks">Active Tasks</button>
          <button class="ss-tab" data-tab="runtime">Runtime Substrate</button>
          <button class="ss-tab" data-tab="capabilities">Capabilities</button>
          <button class="ss-tab" data-tab="resources">Resources</button>
          <button class="ss-tab" data-tab="dependencies">Dependencies</button>
          <button class="ss-tab" data-tab="incidents">Incidents</button>
          <button class="ss-tab" data-tab="security">Security & Stop</button>
          <button class="ss-tab" data-tab="diagnostics">Diagnostics</button>
          <button class="ss-tab" data-tab="self_model">Self-Model Introspection</button>
          <button class="ss-tab" data-tab="changes">Changes & Deltas</button>
          <button class="ss-tab" data-tab="snapshots">Snapshots</button>
        </nav>

        <div id="ss-content-pane" class="ss-content-pane">
          <div class="ss-spinner">Loading system state...</div>
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    const tabs = this.container.querySelectorAll('.ss-tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', (e) => {
        tabs.forEach((t) => t.classList.remove('active'));
        e.target.classList.add('active');
        this.state.activeTab = e.target.getAttribute('data-tab');
        this._renderActiveTab();
      });
    });

    const refreshBtn = this.container.querySelector('#ss-btn-refresh');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.fetchData());

    const snapBtn = this.container.querySelector('#ss-btn-snapshot');
    if (snapBtn) {
      snapBtn.addEventListener('click', async () => {
        try {
          snapBtn.disabled = true;
          snapBtn.innerText = 'Capturing...';
          await this.api.createSnapshot({ metadata: { source: 'ui_console' } });
          await this.fetchData();
        } catch (err) {
          alert('Failed to capture snapshot: ' + err.message);
        } finally {
          snapBtn.disabled = false;
          snapBtn.innerHTML = '<span class="icon">📸</span> Capture Snapshot';
        }
      });
    }

    const recBtn = this.container.querySelector('#ss-btn-reconcile');
    if (recBtn) {
      recBtn.addEventListener('click', async () => {
        try {
          recBtn.disabled = true;
          recBtn.innerText = 'Reconciling...';
          const res = await this.api.reconcile();
          alert(`Reconciliation Complete: Repaired ${res.repaired_entities}, Stale ${res.stale_entities}`);
          await this.fetchData();
        } catch (err) {
          alert('Failed to reconcile state: ' + err.message);
        } finally {
          recBtn.disabled = false;
          recBtn.innerHTML = '<span class="icon">🔄</span> Reconcile State';
        }
      });
    }
  }

  _updateLoadingState() {
    const pane = this.container.querySelector('#ss-content-pane');
    if (pane && this.state.isLoading) {
      pane.innerHTML = '<div class="ss-spinner">Loading operational system state...</div>';
    }
  }

  _renderActiveTab() {
    const pane = this.container.querySelector('#ss-content-pane');
    if (!pane) return;

    if (this.state.error) {
      pane.innerHTML = `<div class="ss-error-banner">Error: ${this.state.error}</div>`;
      return;
    }

    switch (this.state.activeTab) {
      case 'overview':
        pane.innerHTML = this._renderOverview();
        break;
      case 'graph':
        pane.innerHTML = this._renderGraphView();
        this._bindGraphInteractions();
        break;
      case 'goals':
        pane.innerHTML = this._renderGoalsView();
        break;
      case 'tasks':
        pane.innerHTML = this._renderTasksView();
        break;
      case 'runtime':
        pane.innerHTML = this._renderRuntimeView();
        break;
      case 'capabilities':
        pane.innerHTML = this._renderCapabilitiesView();
        break;
      case 'resources':
        pane.innerHTML = this._renderResourcesView();
        break;
      case 'dependencies':
        pane.innerHTML = this._renderDependenciesView();
        break;
      case 'incidents':
        pane.innerHTML = this._renderIncidentsView();
        break;
      case 'security':
        pane.innerHTML = this._renderSecurityView();
        break;
      case 'diagnostics':
        pane.innerHTML = this._renderDiagnosticsView();
        break;
      case 'self_model':
        pane.innerHTML = this._renderSelfModelView();
        break;
      case 'changes':
        pane.innerHTML = this._renderChangesView();
        break;
      case 'snapshots':
        pane.innerHTML = this._renderSnapshotsView();
        break;
      default:
        pane.innerHTML = this._renderOverview();
    }
  }

  _renderOverview() {
    const s = this.state.summary || {};
    const d = this.state.diagnostics || {};
    const stateBadgeClass = (s.overall_state || 'UNKNOWN').toLowerCase();

    return `
      <div class="ss-overview-grid">
        <div class="ss-card ss-metric-card">
          <div class="ss-metric-title">Operational Health</div>
          <div class="ss-metric-value health-${stateBadgeClass}">${Math.round((s.health_score || 1.0) * 100)}%</div>
          <div class="ss-badge badge-${stateBadgeClass}">${s.overall_state || 'HEALTHY'}</div>
        </div>

        <div class="ss-card ss-metric-card">
          <div class="ss-metric-title">Graph Topology</div>
          <div class="ss-metric-value">${s.total_entities || 0} Entities</div>
          <div class="ss-metric-sub">${s.total_edges || 0} Directed Edges</div>
        </div>

        <div class="ss-card ss-metric-card">
          <div class="ss-metric-title">Active Work</div>
          <div class="ss-metric-value">${s.active_work_count || 0} Tasks / Workflows</div>
          <div class="ss-metric-sub">${s.active_objectives_count || 0} Active Goals</div>
        </div>

        <div class="ss-card ss-metric-card">
          <div class="ss-metric-title">Emergency Stop</div>
          <div class="ss-metric-value ${s.security_emergency_stop ? 'status-stopped' : 'status-healthy'}">
            ${s.security_emergency_stop ? 'STOPPED' : 'NORMAL'}
          </div>
          <div class="ss-metric-sub">Sole Authority: SecurityCenter</div>
        </div>
      </div>

      <div class="ss-two-column">
        <div class="ss-card">
          <h3>Epistemological Classification Breakdown</h3>
          <p class="ss-hint">Rigidly distinguishes observed physical facts from derived, inferred, and predicted states.</p>
          <div class="ss-epistemic-list">
            ${Object.entries(s.epistemic_breakdown || {})
              .map(
                ([k, v]) => `
              <div class="ss-epistemic-item">
                <span class="badge-epistemic badge-${k.toLowerCase()}">${k}</span>
                <span class="count">${v}</span>
              </div>
            `
              )
              .join('')}
          </div>
        </div>

        <div class="ss-card">
          <h3>System State Fingerprint & Provenance</h3>
          <div class="ss-meta-table">
            <div><strong>System Version:</strong> ${s.system_version || '0.93.0'}</div>
            <div><strong>Latest Snapshot:</strong> <code>${s.latest_snapshot_id || 'None'}</code></div>
            <div><strong>State Hash:</strong> <code>${s.latest_state_hash || 'None'}</code></div>
            <div><strong>Active Incidents:</strong> ${s.active_incidents_count || 0}</div>
          </div>
        </div>
      </div>
    `;
  }

  _renderGraphView() {
    const nodes = this.state.graphData.nodes || [];
    const links = this.state.graphData.links || [];

    return `
      <div class="ss-graph-container">
        <div class="ss-graph-controls">
          <span><strong>${nodes.length}</strong> Nodes | <strong>${links.length}</strong> Directed Relations</span>
          <input type="text" id="ss-node-filter" placeholder="Filter component or node..." class="input-filter" />
        </div>
        <div class="ss-graph-nodes-grid" id="ss-nodes-grid">
          ${nodes
            .map(
              (n) => `
            <div class="ss-node-card status-${n.status.toLowerCase()}" data-id="${n.id}">
              <div class="ss-node-header">
                <span class="ss-node-type">${n.type}</span>
                <span class="badge-epistemic badge-${n.epistemic.toLowerCase()}">${n.epistemic}</span>
              </div>
              <div class="ss-node-id">${n.label || n.id}</div>
              <div class="ss-node-meta">
                Status: <strong>${n.status}</strong> | Health: ${Math.round(n.health * 100)}%
              </div>
              <button class="btn btn-xs btn-impact" data-target="${n.id}">Impact Analysis</button>
            </div>
          `
            )
            .join('')}
        </div>
        <div id="ss-impact-modal" class="ss-impact-modal" style="display:none;"></div>
      </div>
    `;
  }

  _bindGraphInteractions() {
    const filterInput = this.container.querySelector('#ss-node-filter');
    if (filterInput) {
      filterInput.addEventListener('input', (e) => {
        const val = e.target.value.toLowerCase();
        const cards = this.container.querySelectorAll('.ss-node-card');
        cards.forEach((c) => {
          const id = c.getAttribute('data-id').toLowerCase();
          c.style.display = id.includes(val) ? 'block' : 'none';
        });
      });
    }

    const impactBtns = this.container.querySelectorAll('.btn-impact');
    impactBtns.forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const id = e.target.getAttribute('data-target');
        try {
          const res = await this.api.getImpact(id);
          this._showImpactModal(res);
        } catch (err) {
          alert('Failed to run impact analysis: ' + err.message);
        }
      });
    });
  }

  _showImpactModal(impact) {
    const modal = this.container.querySelector('#ss-impact-modal');
    if (!modal) return;

    modal.style.display = 'block';
    modal.innerHTML = `
      <div class="ss-modal-content">
        <header class="ss-modal-header">
          <h4>Blast Radius & Downstream Impact: <code>${impact.target_component}</code></h4>
          <button class="btn-close" id="btn-close-modal">✕</button>
        </header>
        <div class="ss-modal-body">
          <p>If this component degrades, <strong>${impact.total_impacted_entities}</strong> downstream entities are affected.</p>
          <div><strong>Impacted Goals:</strong> ${impact.affected_goals.length > 0 ? impact.affected_goals.join(', ') : 'None'}</div>
          <div><strong>Impacted Tasks:</strong> ${impact.affected_tasks.length > 0 ? impact.affected_tasks.join(', ') : 'None'}</div>
          <div><strong>Impacted Capabilities:</strong> ${impact.affected_capabilities.length > 0 ? impact.affected_capabilities.join(', ') : 'None'}</div>
        </div>
      </div>
    `;

    const closeBtn = modal.querySelector('#btn-close-modal');
    if (closeBtn) closeBtn.addEventListener('click', () => (modal.style.display = 'none'));
  }

  _renderGoalsView() {
    const goals = (this.state.graphData.nodes || []).filter((n) => n.type === 'GOAL');
    return `
      <div class="ss-card">
        <h3>Active Strategic Goals</h3>
        ${
          goals.length === 0
            ? '<p class="ss-empty">No active goals registered in state graph.</p>'
            : `<table class="ss-table">
            <thead><tr><th>Goal ID</th><th>Status</th><th>Health</th><th>Epistemic</th></tr></thead>
            <tbody>
              ${goals
                .map(
                  (g) => `
                <tr>
                  <td><code>${g.id}</code></td>
                  <td><span class="badge-${g.status.toLowerCase()}">${g.status}</span></td>
                  <td>${Math.round(g.health * 100)}%</td>
                  <td><span class="badge-epistemic badge-${g.epistemic.toLowerCase()}">${g.epistemic}</span></td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _renderTasksView() {
    const tasks = (this.state.graphData.nodes || []).filter((n) => n.type === 'TASK' || n.type === 'WORKFLOW');
    return `
      <div class="ss-card">
        <h3>Active Tasks & Running Workflows</h3>
        ${
          tasks.length === 0
            ? '<p class="ss-empty">No running tasks or active workflows.</p>'
            : `<table class="ss-table">
            <thead><tr><th>Type</th><th>ID</th><th>Status</th><th>Health</th></tr></thead>
            <tbody>
              ${tasks
                .map(
                  (t) => `
                <tr>
                  <td>${t.type}</td>
                  <td><code>${t.id}</code></td>
                  <td><span class="badge-${t.status.toLowerCase()}">${t.status}</span></td>
                  <td>${Math.round(t.health * 100)}%</td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _renderRuntimeView() {
    const runtimes = (this.state.graphData.nodes || []).filter((n) => n.type === 'RUNTIME');
    return `
      <div class="ss-card">
        <h3>Native Rust Substrate & Runtime Components</h3>
        <p class="ss-hint">Heartbeat-tracked processes. Missing heartbeat transitions to UNKNOWN, never blindly assumes FAILED.</p>
        ${
          runtimes.length === 0
            ? '<p class="ss-empty">No runtime processes registered.</p>'
            : `<table class="ss-table">
            <thead><tr><th>Runtime ID</th><th>Status</th><th>Epistemic</th><th>Source</th></tr></thead>
            <tbody>
              ${runtimes
                .map(
                  (r) => `
                <tr>
                  <td><code>${r.id}</code></td>
                  <td><span class="badge-${r.status.toLowerCase()}">${r.status}</span></td>
                  <td><span class="badge-epistemic badge-${r.epistemic.toLowerCase()}">${r.epistemic}</span></td>
                  <td>${r.source}</td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _renderCapabilitiesView() {
    const caps = (this.state.graphData.nodes || []).filter((n) => n.type === 'CAPABILITY');
    return `
      <div class="ss-card">
        <h3>Capabilities Lifecycle Integration (Task 91)</h3>
        ${
          caps.length === 0
            ? '<p class="ss-empty">No capability entities registered in state graph.</p>'
            : `<table class="ss-table">
            <thead><tr><th>Capability</th><th>Status</th><th>Confidence</th></tr></thead>
            <tbody>
              ${caps
                .map(
                  (c) => `
                <tr>
                  <td><code>${c.id}</code></td>
                  <td><span class="badge-${c.status.toLowerCase()}">${c.status}</span></td>
                  <td>${Math.round(c.confidence * 100)}%</td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _renderResourcesView() {
    const pools = this.state.resources?.pools || [];
    return `
      <div class="ss-card">
        <h3>Resource Economy & Constraints</h3>
        ${
          pools.length === 0
            ? '<p class="ss-empty">No resource pools recorded.</p>'
            : `<table class="ss-table">
            <thead><tr><th>Pool ID</th><th>Status</th><th>Health</th></tr></thead>
            <tbody>
              ${pools
                .map(
                  (p) => `
                <tr>
                  <td><code>${p.id}</code></td>
                  <td><span class="badge-${p.status.toLowerCase()}">${p.status}</span></td>
                  <td>${Math.round(p.health * 100)}%</td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _renderDependenciesView() {
    const deps = this.state.dependencies || {};
    return `
      <div class="ss-card">
        <h3>Operational Dependencies</h3>
        <h4>Internal Dependencies:</h4>
        <div class="ss-tag-list">
          ${(deps.internal_dependencies || []).map((d) => `<span class="ss-tag">${d.id} (${d.status})</span>`).join('') || 'None'}
        </div>
        <h4 style="margin-top:1rem;">External Dependencies:</h4>
        <div class="ss-tag-list">
          ${(deps.external_dependencies || []).map((d) => `<span class="ss-tag">${d.id} (${d.status})</span>`).join('') || 'None'}
        </div>
      </div>
    `;
  }

  _renderIncidentsView() {
    const incs = this.state.incidents?.active_incidents || [];
    return `
      <div class="ss-card">
        <h3>Active Incidents & Cascade Protection</h3>
        ${
          incs.length === 0
            ? '<p class="ss-empty">Zero active incidents. System operational.</p>'
            : `<table class="ss-table">
            <thead><tr><th>Incident ID</th><th>Status</th><th>Affected Entities</th></tr></thead>
            <tbody>
              ${incs
                .map(
                  (inc) => `
                <tr>
                  <td><code>${inc.incident_id}</code></td>
                  <td><span class="badge-failed">${inc.status}</span></td>
                  <td>${inc.affected_entities?.length || 0} impacted</td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _renderSecurityView() {
    const isStopped = this.state.summary?.security_emergency_stop;
    return `
      <div class="ss-card">
        <h3>SecurityCenter & EmergencyStop Boundary</h3>
        <div class="ss-alert ${isStopped ? 'alert-danger' : 'alert-success'}">
          <strong>Kill-Switch Status:</strong> ${isStopped ? 'EMERGENCY STOP IS ACTIVE — All mutations halted' : 'NORMAL OPERATION'}
        </div>
        <p class="ss-hint">
          <strong>Invariant:</strong> The System State Graph is strictly an observational layer.
          It never authorizes actions, allocates resources, or bypasses Governance policies.
        </p>
      </div>
    `;
  }

  _renderDiagnosticsView() {
    const diag = this.state.diagnostics;
    if (!diag) return '<div class="ss-card"><p>No diagnostics report available.</p></div>';

    return `
      <div class="ss-card">
        <h3>Structured System Self-Diagnostics</h3>
        <div class="ss-diag-header">
          <div>Composite Health: <strong>${Math.round(diag.health_score * 100)}%</strong></div>
          <div>Diagnosed At: <strong>${new Date(diag.diagnosed_at).toLocaleString()}</strong></div>
        </div>
        <pre class="ss-code-block">${JSON.stringify(diag, null, 2)}</pre>
      </div>
    `;
  }

  _renderSelfModelView() {
    const sm = this.state.selfModel;
    if (!sm) return '<div class="ss-card"><p>Self-model answers unavailable.</p></div>';

    return `
      <div class="ss-card">
        <h3>KAIRO Introspective Self-Model (13 Canonical Inquiries)</h3>
        <div class="ss-qa-list">
          <div class="ss-qa-item">
            <h4>1. What am I doing?</h4>
            <pre>${JSON.stringify(sm.what_am_i_doing, null, 2)}</pre>
          </div>
          <div class="ss-qa-item">
            <h4>2. Why am I doing it? (Serving Goals)</h4>
            <pre>${JSON.stringify(sm.why_am_i_doing_it, null, 2)}</pre>
          </div>
          <div class="ss-qa-item">
            <h4>3. What am I waiting for?</h4>
            <pre>${JSON.stringify(sm.what_am_i_waiting_for, null, 2)}</pre>
          </div>
          <div class="ss-qa-item">
            <h4>4. What is currently broken?</h4>
            <pre>${JSON.stringify(sm.what_is_broken, null, 2)}</pre>
          </div>
          <div class="ss-qa-item">
            <h4>5. What goals are blocked?</h4>
            <pre>${JSON.stringify(sm.what_goals_are_blocked, null, 2)}</pre>
          </div>
          <div class="ss-qa-item">
            <h4>6. What do I not know about my own state?</h4>
            <pre>${JSON.stringify(sm.what_do_i_not_know, null, 2)}</pre>
          </div>
          <div class="ss-qa-item">
            <h4>7. Which assumptions are inferred rather than observed?</h4>
            <pre>${JSON.stringify(sm.which_assumptions_are_inferred, null, 2)}</pre>
          </div>
        </div>
      </div>
    `;
  }

  _renderChangesView() {
    const changes = this.state.changes || [];
    return `
      <div class="ss-card">
        <h3>Recent Operational State Deltas</h3>
        ${
          changes.length === 0
            ? '<p class="ss-empty">No recent state deltas detected.</p>'
            : `<table class="ss-table">
            <thead><tr><th>Delta Type</th><th>Entity</th><th>Transition</th><th>Detected</th></tr></thead>
            <tbody>
              ${changes
                .map(
                  (c) => `
                <tr>
                  <td><span class="badge-delta badge-${c.delta_type?.toLowerCase()}">${c.delta_type}</span></td>
                  <td><code>${c.entity_id}</code></td>
                  <td>${c.from_status || 'None'} → <strong>${c.to_status || 'None'}</strong></td>
                  <td>${new Date(c.detected_at).toLocaleTimeString()}</td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }

  _renderSnapshotsView() {
    const snaps = this.state.snapshots || [];
    return `
      <div class="ss-card">
        <h3>Immutable Point-in-Time State Snapshots</h3>
        ${
          snaps.length === 0
            ? '<p class="ss-empty">No snapshots captured yet.</p>'
            : `<table class="ss-table">
            <thead><tr><th>Snapshot ID</th><th>State Hash</th><th>Entities</th><th>Edges</th><th>Created At</th></tr></thead>
            <tbody>
              ${snaps
                .map(
                  (s) => `
                <tr>
                  <td><code>${s.snapshot_id}</code></td>
                  <td><code>${s.state_hash?.substring(0, 16)}...</code></td>
                  <td>${s.entity_count}</td>
                  <td>${s.edge_count}</td>
                  <td>${new Date(s.created_at).toLocaleString()}</td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>`
        }
      </div>
    `;
  }
}

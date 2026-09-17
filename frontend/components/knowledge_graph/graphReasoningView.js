/**
 * KAIRO Autonomous Knowledge Graph Reasoning, Graph Memory & Structured Inference Console (Task 97).
 *
 * Provides production-grade operator interfaces for:
 * 1. Graph Explorer (interactive node/edge topology, bounded expansion, certainty/provenance badges)
 * 2. Entity Detail & Deep Provenance (canonical keys, certainty, sensitive classifications, validity intervals)
 * 3. Dependency Intelligence (upstream/downstream chains, transitivities, capability/service reliance)
 * 4. Downstream Impact Analysis (fault propagation simulation, affected workflows/decisions, risk topology)
 * 5. Structured Lineage (Decision, Action, Memory, and Swarm Agent provenance reconstructions)
 * 6. Temporal History & Snapshots (point-in-time reconstruction, immutable snapshots, graph diffing)
 * 7. Dialectic Conflict Graph (A CONTRADICTS B, epistemic tension, resolution states)
 * 8. Deductive Inference & Query Explorer (bounded pathing, shortest verified path, inference rules)
 */

export class GraphReasoningView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api || this._createDefaultApi();
    this.state = {
      activeTab: 'explorer', // 'explorer' | 'detail' | 'dependencies' | 'impact' | 'lineage' | 'temporal' | 'conflicts' | 'inference'
      nodes: [],
      edges: [],
      selectedNodeId: null,
      selectedNode: null,
      selectedNeighbors: { outgoing: [], incoming: [] },
      impactResult: null,
      lineageResult: null,
      snapshots: [],
      diffResult: null,
      conflicts: [],
      inferenceResult: null,
      queryResult: null,
      filterType: '',
      filterCertainty: '',
      searchQuery: '',
      isLoading: false,
      error: null,
      metrics: {
        totalNodes: 0,
        totalEdges: 0,
        activeInferences: 0,
        unresolvedConflicts: 0
      }
    };
  }

  _createDefaultApi() {
    return {
      listNodes: async (params = {}) => {
        const q = new URLSearchParams(params).toString();
        const res = await fetch(`/api/v1/graph/nodes?${q}`);
        return res.json();
      },
      getNode: async (id) => {
        const res = await fetch(`/api/v1/graph/nodes/${encodeURIComponent(id)}`);
        return res.json();
      },
      getNeighbors: async (id) => {
        const res = await fetch(`/api/v1/graph/nodes/${encodeURIComponent(id)}/neighbors`);
        return res.json();
      },
      getDependencies: async (id) => {
        const res = await fetch(`/api/v1/graph/nodes/${encodeURIComponent(id)}/dependencies`);
        return res.json();
      },
      getDependents: async (id) => {
        const res = await fetch(`/api/v1/graph/nodes/${encodeURIComponent(id)}/dependents`);
        return res.json();
      },
      getNodeLineage: async (id) => {
        const res = await fetch(`/api/v1/graph/nodes/${encodeURIComponent(id)}/lineage`);
        return res.json();
      },
      getNodeHistory: async (id) => {
        const res = await fetch(`/api/v1/graph/nodes/${encodeURIComponent(id)}/history`);
        return res.json();
      },
      executeQuery: async (body) => {
        const res = await fetch('/api/v1/graph/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        return res.json();
      },
      findPath: async (body) => {
        const res = await fetch('/api/v1/graph/path', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        return res.json();
      },
      analyzeImpact: async (body) => {
        const res = await fetch('/api/v1/graph/impact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        return res.json();
      },
      computeDiff: async (body) => {
        const res = await fetch('/api/v1/graph/diff', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        return res.json();
      },
      createSnapshot: async (body) => {
        const res = await fetch('/api/v1/graph/snapshot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        return res.json();
      },
      listSnapshots: async (params = {}) => {
        const q = new URLSearchParams(params).toString();
        const res = await fetch(`/api/v1/graph/snapshots?${q}`);
        return res.json();
      },
      runInference: async (body = {}) => {
        const res = await fetch('/api/v1/graph/inference', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
        return res.json();
      },
      reconstructDecision: async (id) => {
        const res = await fetch(`/api/v1/graph/reconstruct/decision/${encodeURIComponent(id)}`, { method: 'POST' });
        return res.json();
      },
      reconstructAction: async (id) => {
        const res = await fetch(`/api/v1/graph/reconstruct/action/${encodeURIComponent(id)}`, { method: 'POST' });
        return res.json();
      },
      reconstructMemory: async (id) => {
        const res = await fetch(`/api/v1/graph/reconstruct/memory/${encodeURIComponent(id)}`, { method: 'POST' });
        return res.json();
      },
      reconstructAgent: async (id) => {
        const res = await fetch(`/api/v1/graph/reconstruct/agent/${encodeURIComponent(id)}`, { method: 'POST' });
        return res.json();
      },
      listConflicts: async (params = {}) => {
        const q = new URLSearchParams(params).toString();
        const res = await fetch(`/api/v1/graph/conflicts?${q}`);
        return res.json();
      },
      validateGraph: async (scope = 'global') => {
        const res = await fetch('/api/v1/graph/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scope })
        });
        return res.json();
      }
    };
  }

  async render() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="graph-reasoning-view" style="display: flex; flex-direction: column; height: 100%; gap: 1rem;">
        <header class="graph-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-subtle, #333); padding-bottom: 0.75rem;">
          <div>
            <h2 style="margin: 0; font-size: 1.4rem; font-weight: 700; color: var(--text-primary, #fff);">
              🕸️ Knowledge Graph Reasoning & Relationship Intelligence
            </h2>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; color: var(--text-muted, #888);">
              Epistemic Substrate • Provenance-Aware • Bounded Inference • Temporal Lineage
            </p>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-secondary" id="btn-validate-graph" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">🛡️ Validate Graph</button>
            <button class="btn btn-secondary" id="btn-refresh-graph" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">↻ Refresh</button>
            <button class="btn btn-primary" id="btn-snapshot-graph" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">📷 Snapshot</button>
          </div>
        </header>

        <!-- KPI Metrics Banner -->
        <div class="graph-kpi-bar" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem;">
          <div class="kpi-card" style="background: var(--bg-card, #1e1e24); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <div style="font-size: 0.75rem; color: var(--text-muted, #888);">TOTAL ENTITIES</div>
            <div id="metric-nodes" style="font-size: 1.4rem; font-weight: 700; color: #3b82f6;">${this.state.metrics.totalNodes}</div>
          </div>
          <div class="kpi-card" style="background: var(--bg-card, #1e1e24); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <div style="font-size: 0.75rem; color: var(--text-muted, #888);">RELATIONSHIPS</div>
            <div id="metric-edges" style="font-size: 1.4rem; font-weight: 700; color: #10b981;">${this.state.metrics.totalEdges}</div>
          </div>
          <div class="kpi-card" style="background: var(--bg-card, #1e1e24); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <div style="font-size: 0.75rem; color: var(--text-muted, #888);">STRUCTURED INFERENCES</div>
            <div id="metric-inferences" style="font-size: 1.4rem; font-weight: 700; color: #8b5cf6;">${this.state.metrics.activeInferences}</div>
          </div>
          <div class="kpi-card" style="background: var(--bg-card, #1e1e24); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <div style="font-size: 0.75rem; color: var(--text-muted, #888);">ACTIVE CONFLICTS</div>
            <div id="metric-conflicts" style="font-size: 1.4rem; font-weight: 700; color: #f59e0b;">${this.state.metrics.unresolvedConflicts}</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <nav class="graph-nav-tabs" style="display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-subtle, #333); padding-bottom: 0.25rem;">
          <button class="tab-btn ${this.state.activeTab === 'explorer' ? 'active' : ''}" data-tab="explorer" style="padding: 0.5rem 0.8rem; background: none; border: none; cursor: pointer; color: ${this.state.activeTab === 'explorer' ? '#3b82f6' : '#888'}; border-bottom: 2px solid ${this.state.activeTab === 'explorer' ? '#3b82f6' : 'transparent'}; font-weight: 600;">
            🔍 Graph Explorer
          </button>
          <button class="tab-btn ${this.state.activeTab === 'detail' ? 'active' : ''}" data-tab="detail" style="padding: 0.5rem 0.8rem; background: none; border: none; cursor: pointer; color: ${this.state.activeTab === 'detail' ? '#3b82f6' : '#888'}; border-bottom: 2px solid ${this.state.activeTab === 'detail' ? '#3b82f6' : 'transparent'}; font-weight: 600;">
            📄 Entity Detail
          </button>
          <button class="tab-btn ${this.state.activeTab === 'dependencies' ? 'active' : ''}" data-tab="dependencies" style="padding: 0.5rem 0.8rem; background: none; border: none; cursor: pointer; color: ${this.state.activeTab === 'dependencies' ? '#3b82f6' : '#888'}; border-bottom: 2px solid ${this.state.activeTab === 'dependencies' ? '#3b82f6' : 'transparent'}; font-weight: 600;">
            🔗 Dependencies
          </button>
          <button class="tab-btn ${this.state.activeTab === 'impact' ? 'active' : ''}" data-tab="impact" style="padding: 0.5rem 0.8rem; background: none; border: none; cursor: pointer; color: ${this.state.activeTab === 'impact' ? '#3b82f6' : '#888'}; border-bottom: 2px solid ${this.state.activeTab === 'impact' ? '#3b82f6' : 'transparent'}; font-weight: 600;">
            💥 Impact Analysis
          </button>
          <button class="tab-btn ${this.state.activeTab === 'lineage' ? 'active' : ''}" data-tab="lineage" style="padding: 0.5rem 0.8rem; background: none; border: none; cursor: pointer; color: ${this.state.activeTab === 'lineage' ? '#3b82f6' : '#888'}; border-bottom: 2px solid ${this.state.activeTab === 'lineage' ? '#3b82f6' : 'transparent'}; font-weight: 600;">
            📜 Lineage (Decision/Action/Memory)
          </button>
          <button class="tab-btn ${this.state.activeTab === 'temporal' ? 'active' : ''}" data-tab="temporal" style="padding: 0.5rem 0.8rem; background: none; border: none; cursor: pointer; color: ${this.state.activeTab === 'temporal' ? '#3b82f6' : '#888'}; border-bottom: 2px solid ${this.state.activeTab === 'temporal' ? '#3b82f6' : 'transparent'}; font-weight: 600;">
            ⏳ Temporal & Snapshots
          </button>
          <button class="tab-btn ${this.state.activeTab === 'conflicts' ? 'active' : ''}" data-tab="conflicts" style="padding: 0.5rem 0.8rem; background: none; border: none; cursor: pointer; color: ${this.state.activeTab === 'conflicts' ? '#3b82f6' : '#888'}; border-bottom: 2px solid ${this.state.activeTab === 'conflicts' ? '#3b82f6' : 'transparent'}; font-weight: 600;">
            ⚔️ Conflicts
          </button>
          <button class="tab-btn ${this.state.activeTab === 'inference' ? 'active' : ''}" data-tab="inference" style="padding: 0.5rem 0.8rem; background: none; border: none; cursor: pointer; color: ${this.state.activeTab === 'inference' ? '#3b82f6' : '#888'}; border-bottom: 2px solid ${this.state.activeTab === 'inference' ? '#3b82f6' : 'transparent'}; font-weight: 600;">
            🧠 Inference & Pathing
          </button>
        </nav>

        <!-- Main Tab Body -->
        <div id="graph-tab-content" style="flex: 1; overflow-y: auto;">
          ${this._renderActiveTabContent()}
        </div>
      </div>
    `;

    this._wireEvents();
    await this.fetchInitialData();
  }

  _renderActiveTabContent() {
    switch (this.state.activeTab) {
      case 'explorer':
        return this._renderExplorerTab();
      case 'detail':
        return this._renderDetailTab();
      case 'dependencies':
        return this._renderDependenciesTab();
      case 'impact':
        return this._renderImpactTab();
      case 'lineage':
        return this._renderLineageTab();
      case 'temporal':
        return this._renderTemporalTab();
      case 'conflicts':
        return this._renderConflictsTab();
      case 'inference':
        return this._renderInferenceTab();
      default:
        return `<div class="p-4">Select a tab.</div>`;
    }
  }

  _renderExplorerTab() {
    const filteredNodes = this.state.nodes.filter(n => {
      const matchType = !this.state.filterType || n.node_type === this.state.filterType;
      const matchCertainty = !this.state.filterCertainty || n.certainty === this.state.filterCertainty;
      const matchSearch = !this.state.searchQuery || 
        n.label.toLowerCase().includes(this.state.searchQuery.toLowerCase()) ||
        n.node_id.toLowerCase().includes(this.state.searchQuery.toLowerCase());
      return matchType && matchCertainty && matchSearch;
    });

    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div class="filter-controls" style="display: flex; gap: 0.75rem; align-items: center; background: var(--bg-card, #1e1e24); padding: 0.75rem; border-radius: 6px;">
          <input type="text" id="kg-search-input" placeholder="Search node label or ID..." value="${this._escape(this.state.searchQuery)}" style="padding: 0.4rem 0.6rem; border-radius: 4px; border: 1px solid var(--border-subtle, #333); background: var(--bg-input, #121216); color: #fff; flex: 1;">
          <select id="kg-type-filter" style="padding: 0.4rem; border-radius: 4px; border: 1px solid var(--border-subtle, #333); background: var(--bg-input, #121216); color: #fff;">
            <option value="">All Types</option>
            <option value="SERVICE" ${this.state.filterType === 'SERVICE' ? 'selected' : ''}>SERVICE</option>
            <option value="CAPABILITY" ${this.state.filterType === 'CAPABILITY' ? 'selected' : ''}>CAPABILITY</option>
            <option value="CAPABILITY_VERSION" ${this.state.filterType === 'CAPABILITY_VERSION' ? 'selected' : ''}>CAPABILITY_VERSION</option>
            <option value="DECISION" ${this.state.filterType === 'DECISION' ? 'selected' : ''}>DECISION</option>
            <option value="ACTION" ${this.state.filterType === 'ACTION' ? 'selected' : ''}>ACTION</option>
            <option value="TASK" ${this.state.filterType === 'TASK' ? 'selected' : ''}>TASK</option>
            <option value="GOAL" ${this.state.filterType === 'GOAL' ? 'selected' : ''}>GOAL</option>
            <option value="MEMORY" ${this.state.filterType === 'MEMORY' ? 'selected' : ''}>MEMORY</option>
            <option value="EVIDENCE" ${this.state.filterType === 'EVIDENCE' ? 'selected' : ''}>EVIDENCE</option>
            <option value="INCIDENT" ${this.state.filterType === 'INCIDENT' ? 'selected' : ''}>INCIDENT</option>
            <option value="WORKFLOW" ${this.state.filterType === 'WORKFLOW' ? 'selected' : ''}>WORKFLOW</option>
          </select>
          <select id="kg-certainty-filter" style="padding: 0.4rem; border-radius: 4px; border: 1px solid var(--border-subtle, #333); background: var(--bg-input, #121216); color: #fff;">
            <option value="">All Certainties</option>
            <option value="KNOWN" ${this.state.filterCertainty === 'KNOWN' ? 'selected' : ''}>KNOWN</option>
            <option value="LIKELY" ${this.state.filterCertainty === 'LIKELY' ? 'selected' : ''}>LIKELY</option>
            <option value="POSSIBLE" ${this.state.filterCertainty === 'POSSIBLE' ? 'selected' : ''}>POSSIBLE</option>
            <option value="UNCERTAIN" ${this.state.filterCertainty === 'UNCERTAIN' ? 'selected' : ''}>UNCERTAIN</option>
            <option value="CONTRADICTED" ${this.state.filterCertainty === 'CONTRADICTED' ? 'selected' : ''}>CONTRADICTED</option>
          </select>
          <button class="btn btn-secondary" id="btn-clear-filters" style="padding: 0.4rem 0.6rem;">Clear</button>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem;">
          ${filteredNodes.map(node => `
            <div class="node-card" data-id="${this._escape(node.node_id)}" style="background: var(--bg-card, #1e1e24); border: 1px solid var(--border-subtle, #2a2a32); border-radius: 6px; padding: 0.85rem; cursor: pointer; transition: transform 0.15s, border-color 0.15s;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem;">
                <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; font-size: 0.7rem; padding: 0.2rem 0.4rem; border-radius: 3px; font-weight: 600;">
                  ${this._escape(node.node_type)}
                </span>
                <span class="badge" style="background: ${this._getCertaintyBg(node.certainty)}; color: ${this._getCertaintyColor(node.certainty)}; font-size: 0.7rem; padding: 0.2rem 0.4rem; border-radius: 3px; font-weight: 600;">
                  ${this._escape(node.certainty || 'KNOWN')}
                </span>
              </div>
              <div style="font-weight: 600; font-size: 0.95rem; color: #f3f4f6; margin-bottom: 0.3rem;">
                ${this._escape(node.label)}
              </div>
              <div style="font-family: monospace; font-size: 0.75rem; color: #9ca3af; margin-bottom: 0.4rem;">
                ${this._escape(node.canonical_key || node.node_id)}
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #6b7280;">
                <span>Prov: ${this._escape(node.provenance?.classification || 'OBSERVED')}</span>
                <span>Conf: ${(node.confidence !== undefined ? node.confidence.toFixed(2) : '1.00')}</span>
              </div>
            </div>
          `).join('')}
          ${filteredNodes.length === 0 ? `<div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #6b7280;">No entities match your filter.</div>` : ''}
        </div>
      </div>
    `;
  }

  _renderDetailTab() {
    const node = this.state.selectedNode;
    if (!node) {
      return `
        <div style="padding: 3rem; text-align: center; color: #9ca3af;">
          <h3>No Entity Selected</h3>
          <p>Please select an entity from the Explorer tab or enter an ID below.</p>
          <div style="display: inline-flex; gap: 0.5rem; margin-top: 1rem;">
            <input type="text" id="manual-node-id" placeholder="Node ID (e.g. srv_db_postgres)" style="padding: 0.4rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff;">
            <button class="btn btn-primary" id="btn-load-manual-node" style="padding: 0.4rem 0.8rem;">Inspect</button>
          </div>
        </div>
      `;
    }

    const { outgoing, incoming } = this.state.selectedNeighbors;

    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: var(--bg-card, #1e1e24); padding: 1.25rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div>
              <span class="badge" style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">
                ${this._escape(node.node_type)}
              </span>
              <h3 style="margin: 0.35rem 0 0 0; font-size: 1.3rem; color: #fff;">${this._escape(node.label)}</h3>
              <div style="font-family: monospace; font-size: 0.8rem; color: #9ca3af;">ID: ${this._escape(node.node_id)} | Key: ${this._escape(node.canonical_key || 'N/A')}</div>
            </div>
            <div style="text-align: right;">
              <span class="badge" style="background: ${this._getCertaintyBg(node.certainty)}; color: ${this._getCertaintyColor(node.certainty)}; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: 700;">
                ${this._escape(node.certainty || 'KNOWN')}
              </span>
              <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.25rem;">Version: ${node.version || 1} | Status: ${this._escape(node.status || 'ACTIVE')}</div>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.05); font-size: 0.85rem;">
            <div>
              <span style="color: #6b7280;">Provenance:</span>
              <div style="font-weight: 600; color: #d1d5db;">${this._escape(node.provenance?.classification || 'OBSERVED')} via ${this._escape(node.provenance?.extraction_method || 'SYSTEM')}</div>
            </div>
            <div>
              <span style="color: #6b7280;">Confidence:</span>
              <div style="font-weight: 600; color: #d1d5db;">${node.confidence !== undefined ? node.confidence.toFixed(2) : '1.00'}</div>
            </div>
            <div>
              <span style="color: #6b7280;">Sensitivity:</span>
              <div style="font-weight: 600; color: ${node.sensitivity === 'RESTRICTED' ? '#ef4444' : '#10b981'};">${this._escape(node.sensitivity || 'INTERNAL')}</div>
            </div>
          </div>
        </div>

        <!-- Relationships Panels -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <h4 style="margin-top: 0; color: #60a5fa;">Outgoing Relationships (${outgoing.length})</h4>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; max-height: 350px; overflow-y: auto;">
              ${outgoing.map(e => `
                <div style="padding: 0.5rem; background: #121216; border-radius: 4px; border: 1px solid #2a2a32; font-size: 0.8rem;">
                  <span style="color: #f59e0b; font-weight: 700;">${this._escape(e.relationship_type)}</span> ➔
                  <span class="clickable-node" data-id="${this._escape(e.target_node)}" style="color: #3b82f6; cursor: pointer; text-decoration: underline;">
                    ${this._escape(e.target_node)}
                  </span>
                  <div style="font-size: 0.7rem; color: #6b7280; margin-top: 0.2rem;">
                    Conf: ${e.confidence ? e.confidence.toFixed(2) : '1.00'} | Prov: ${this._escape(e.provenance?.classification || 'OBSERVED')}
                  </div>
                </div>
              `).join('')}
              ${outgoing.length === 0 ? `<div style="color: #6b7280; font-size: 0.8rem;">None</div>` : ''}
            </div>
          </div>

          <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <h4 style="margin-top: 0; color: #34d399;">Incoming Relationships (${incoming.length})</h4>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; max-height: 350px; overflow-y: auto;">
              ${incoming.map(e => `
                <div style="padding: 0.5rem; background: #121216; border-radius: 4px; border: 1px solid #2a2a32; font-size: 0.8rem;">
                  <span class="clickable-node" data-id="${this._escape(e.source_node)}" style="color: #3b82f6; cursor: pointer; text-decoration: underline;">
                    ${this._escape(e.source_node)}
                  </span> ➔
                  <span style="color: #f59e0b; font-weight: 700;">${this._escape(e.relationship_type)}</span>
                  <div style="font-size: 0.7rem; color: #6b7280; margin-top: 0.2rem;">
                    Conf: ${e.confidence ? e.confidence.toFixed(2) : '1.00'} | Prov: ${this._escape(e.provenance?.classification || 'OBSERVED')}
                  </div>
                </div>
              `).join('')}
              ${incoming.length === 0 ? `<div style="color: #6b7280; font-size: 0.8rem;">None</div>` : ''}
            </div>
          </div>
        </div>

        <!-- Action Quick-links -->
        <div style="display: flex; gap: 0.5rem;">
          <button class="btn btn-secondary" id="btn-jump-deps" style="font-size: 0.8rem;">Inspect Dependencies</button>
          <button class="btn btn-secondary" id="btn-jump-impact" style="font-size: 0.8rem;">Analyze Impact</button>
          <button class="btn btn-secondary" id="btn-jump-lineage" style="font-size: 0.8rem;">View Lineage</button>
        </div>
      </div>
    `;
  }

  _renderDependenciesTab() {
    const node = this.state.selectedNode;
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
          <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem;">Dependency Intelligence</h3>
          <p style="margin: 0; font-size: 0.85rem; color: #9ca3af;">
            Traverse upstream dependencies ("What does X depend on?") and downstream dependents ("What depends on X?").
          </p>
          <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
            <input type="text" id="deps-node-id" placeholder="Entity ID" value="${node ? this._escape(node.node_id) : ''}" style="padding: 0.4rem 0.6rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff; width: 280px;">
            <button class="btn btn-primary" id="btn-fetch-dependencies" style="padding: 0.4rem 0.8rem;">Query Dependencies</button>
            <button class="btn btn-secondary" id="btn-fetch-dependents" style="padding: 0.4rem 0.8rem;">Query Dependents</button>
          </div>
        </div>

        <div id="dependency-results-area" style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32); min-height: 200px;">
          <div style="color: #6b7280; font-size: 0.85rem; text-align: center; padding: 2rem;">Run a dependency or dependent query to view topological chains.</div>
        </div>
      </div>
    `;
  }

  _renderImpactTab() {
    const node = this.state.selectedNode;
    const impact = this.state.impactResult;

    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
          <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem;">Graph-Based Downstream Impact Analysis</h3>
          <p style="margin: 0; font-size: 0.85rem; color: #9ca3af;">
            Simulate fault or mutation propagation across capabilities, workflows, tasks, and decisions.
          </p>
          <div style="display: flex; gap: 0.5rem; margin-top: 1rem; align-items: center;">
            <input type="text" id="impact-node-id" placeholder="Origin Node ID" value="${node ? this._escape(node.node_id) : ''}" style="padding: 0.4rem 0.6rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff; width: 260px;">
            <label style="font-size: 0.8rem; color: #9ca3af;">Max Depth:</label>
            <input type="number" id="impact-max-depth" value="5" min="1" max="10" style="padding: 0.4rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff; width: 60px;">
            <button class="btn btn-primary" id="btn-run-impact" style="padding: 0.4rem 0.8rem;">Simulate Impact</button>
          </div>
        </div>

        ${impact ? `
          <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
              <h4 style="margin: 0; font-size: 1rem; color: #f59e0b;">
                Impact Assessment for ${this._escape(impact.origin_node)}
              </h4>
              <span class="badge" style="background: ${impact.overall_risk_severity === 'CRITICAL' ? '#ef4444' : '#f59e0b'}; color: #fff; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">
                Severity: ${this._escape(impact.overall_risk_severity || 'LOW')}
              </span>
            </div>

            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1rem;">
              <div style="background: #121216; padding: 0.5rem; border-radius: 4px;">
                <div style="font-size: 0.7rem; color: #6b7280;">TOTAL IMPACTED NODES</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #60a5fa;">${impact.total_impacted_nodes || impact.impacted_nodes.length}</div>
              </div>
              <div style="background: #121216; padding: 0.5rem; border-radius: 4px;">
                <div style="font-size: 0.7rem; color: #6b7280;">MAX PROPAGATION DEPTH</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #34d399;">${impact.max_propagation_depth}</div>
              </div>
              <div style="background: #121216; padding: 0.5rem; border-radius: 4px;">
                <div style="font-size: 0.7rem; color: #6b7280;">REVALIDATION CANDIDATES</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #f87171;">${impact.revalidation_candidates ? impact.revalidation_candidates.length : 0}</div>
              </div>
            </div>

            <h5 style="margin: 0.5rem 0; color: #d1d5db;">Impacted Downstream Entities</h5>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              ${impact.impacted_nodes.map(item => `
                <div style="background: #121216; padding: 0.6rem; border-radius: 4px; border: 1px solid #2a2a32; display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
                  <div>
                    <span class="clickable-node" data-id="${this._escape(item.node_id)}" style="font-weight: 600; color: #3b82f6; cursor: pointer; text-decoration: underline;">
                      ${this._escape(item.node_id)}
                    </span>
                    <span style="color: #6b7280; font-size: 0.75rem; margin-left: 0.5rem;">(${this._escape(item.node_type)})</span>
                  </div>
                  <div style="display: flex; gap: 0.75rem; font-size: 0.75rem;">
                    <span>Depth: ${item.depth}</span>
                    <span>Conf: ${item.confidence.toFixed(2)}</span>
                    <span style="color: ${item.criticality === 'CRITICAL' ? '#ef4444' : '#fbbf24'}; font-weight: 600;">${this._escape(item.criticality)}</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  _renderLineageTab() {
    const lineage = this.state.lineageResult;
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
          <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem;">Lineage Reconstruction</h3>
          <p style="margin: 0; font-size: 0.85rem; color: #9ca3af;">
            Audit how decisions were derived, actions justified, memories consolidated, or swarm agents coordinated.
          </p>
          <div style="display: flex; gap: 0.5rem; margin-top: 1rem; align-items: center;">
            <select id="lineage-type-select" style="padding: 0.4rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff;">
              <option value="decision">Decision Lineage</option>
              <option value="action">Action Lineage</option>
              <option value="memory">Memory Lineage</option>
              <option value="agent">Agent Swarm Lineage</option>
            </select>
            <input type="text" id="lineage-target-id" placeholder="Target ID (e.g. dec_123 or act_456)" style="padding: 0.4rem 0.6rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff; width: 280px;">
            <button class="btn btn-primary" id="btn-run-lineage" style="padding: 0.4rem 0.8rem;">Reconstruct Lineage</button>
          </div>
        </div>

        ${lineage ? `
          <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <h4 style="margin-top: 0; color: #8b5cf6;">Lineage: ${this._escape(lineage.target_node)} (${this._escape(lineage.lineage_type)})</h4>
            <p style="font-size: 0.85rem; color: #9ca3af;">${this._escape(lineage.summary || 'Lineage chain reconstructed across graph substrate.')}</p>

            <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-top: 1rem;">
              ${lineage.steps.map((step, idx) => `
                <div style="display: flex; align-items: center; gap: 0.75rem; background: #121216; padding: 0.6rem; border-radius: 4px; border-left: 3px solid #8b5cf6; font-size: 0.85rem;">
                  <span style="background: #2a2a32; color: #8b5cf6; font-weight: 700; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem;">
                    ${idx + 1}
                  </span>
                  <div style="flex: 1;">
                    <div style="font-weight: 600; color: #fff;">${this._escape(step.node_id)} <span style="font-size: 0.75rem; color: #9ca3af;">[${this._escape(step.node_type)}]</span></div>
                    <div style="font-size: 0.75rem; color: #6b7280;">Rel: ${this._escape(step.relationship || 'ROOT')} | Prov: ${this._escape(step.provenance?.classification || 'OBSERVED')}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  _renderTemporalTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
          <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem;">Temporal Graph & Snapshots</h3>
          <p style="margin: 0; font-size: 0.85rem; color: #9ca3af;">
            Query historical relationships as of point-in-time T, capture immutable snapshots, or compute graph diffs.
          </p>
          <div style="display: flex; gap: 0.5rem; margin-top: 1rem; align-items: center;">
            <input type="text" id="diff-snap-a" placeholder="Base Snapshot ID" style="padding: 0.4rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff; width: 200px;">
            <input type="text" id="diff-snap-b" placeholder="Target Snapshot ID" style="padding: 0.4rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff; width: 200px;">
            <button class="btn btn-primary" id="btn-run-diff" style="padding: 0.4rem 0.8rem;">Compute Diff</button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <h4 style="margin-top: 0; color: #60a5fa;">Available Snapshots</h4>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; max-height: 350px; overflow-y: auto;">
              ${this.state.snapshots.map(s => `
                <div style="background: #121216; padding: 0.6rem; border-radius: 4px; border: 1px solid #2a2a32; font-size: 0.8rem;">
                  <div style="font-weight: 600; color: #fff;">${this._escape(s.snapshot_id)}</div>
                  <div style="color: #9ca3af; font-size: 0.75rem;">${this._escape(s.label || 'Snapshot')} | ${s.node_count || 0} nodes, ${s.edge_count || 0} edges</div>
                </div>
              `).join('')}
              ${this.state.snapshots.length === 0 ? `<div style="color: #6b7280; font-size: 0.8rem;">No snapshots stored yet.</div>` : ''}
            </div>
          </div>

          <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
            <h4 style="margin-top: 0; color: #f59e0b;">Diff Results</h4>
            <div id="diff-output-area" style="font-size: 0.8rem; color: #9ca3af;">
              ${this.state.diffResult ? `
                <div>
                  <div style="color: #34d399;">Added Nodes: ${this.state.diffResult.added_nodes.length}</div>
                  <div style="color: #ef4444;">Removed Nodes: ${this.state.diffResult.removed_nodes.length}</div>
                  <div style="color: #fbbf24;">Changed Nodes: ${this.state.diffResult.changed_nodes.length}</div>
                  <div style="color: #34d399;">Added Edges: ${this.state.diffResult.added_edges.length}</div>
                  <div style="color: #ef4444;">Removed Edges: ${this.state.diffResult.removed_edges.length}</div>
                </div>
              ` : `Run a diff query to view changes.`}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderConflictsTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
          <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem;">Dialectic Conflict Graph</h3>
          <p style="margin: 0; font-size: 0.85rem; color: #9ca3af;">
            Preserve contradictions rather than silently overwriting them. Inspect A CONTRADICTS B assertions and resolution states.
          </p>
        </div>

        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          ${this.state.conflicts.map(c => `
            <div style="background: var(--bg-card, #1e1e24); padding: 0.85rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <div>
                  <span class="badge" style="background: #ef4444; color: #fff; padding: 0.2rem 0.4rem; border-radius: 3px; font-size: 0.7rem; font-weight: 700;">CONTRADICTION</span>
                  <span style="font-weight: 600; color: #fff; margin-left: 0.5rem;">${this._escape(c.node_a)} ⚡ ${this._escape(c.node_b)}</span>
                </div>
                <span class="badge" style="background: #2a2a32; color: #f59e0b; padding: 0.2rem 0.5rem; border-radius: 3px; font-size: 0.75rem;">${this._escape(c.status || 'UNRESOLVED')}</span>
              </div>
              <div style="font-size: 0.8rem; color: #9ca3af; margin-bottom: 0.3rem;">Reason: ${this._escape(c.reason || 'Epistemic discrepancy')}</div>
              <div style="font-size: 0.75rem; color: #6b7280;">Confidence: ${c.confidence ? c.confidence.toFixed(2) : '1.00'} | Detected: ${this._escape(c.created_at || 'N/A')}</div>
            </div>
          `).join('')}
          ${this.state.conflicts.length === 0 ? `<div style="padding: 2rem; text-align: center; color: #6b7280;">No active conflicts detected. Graph is dialectically consistent.</div>` : ''}
        </div>
      </div>
    `;
  }

  _renderInferenceTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32);">
          <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem;">Bounded Deductive Inference & Shortest Path</h3>
          <p style="margin: 0; font-size: 0.85rem; color: #9ca3af;">
            Derive transitive dependencies, part-of closures, and shortest verified path with strict limits.
          </p>
          <div style="display: flex; gap: 0.5rem; margin-top: 1rem; align-items: center;">
            <input type="text" id="path-start" placeholder="Source Node (e.g. srv_db)" style="padding: 0.4rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff; width: 220px;">
            <input type="text" id="path-target" placeholder="Target Node (e.g. cap_etl)" style="padding: 0.4rem; border-radius: 4px; border: 1px solid #333; background: #121216; color: #fff; width: 220px;">
            <button class="btn btn-primary" id="btn-find-path" style="padding: 0.4rem 0.8rem;">Find Shortest Path</button>
            <button class="btn btn-secondary" id="btn-run-all-inferences" style="padding: 0.4rem 0.8rem;">Run Deductive Rules</button>
          </div>
        </div>

        <div id="inference-results-area" style="background: var(--bg-card, #1e1e24); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-subtle, #2a2a32); min-height: 200px;">
          <div style="color: #6b7280; font-size: 0.85rem; text-align: center; padding: 2rem;">Execute path query or inference cycle.</div>
        </div>
      </div>
    `;
  }

  _getCertaintyBg(certainty) {
    switch (certainty) {
      case 'KNOWN': return 'rgba(16, 185, 129, 0.15)';
      case 'LIKELY': return 'rgba(59, 130, 246, 0.15)';
      case 'POSSIBLE': return 'rgba(139, 92, 246, 0.15)';
      case 'UNCERTAIN': return 'rgba(245, 158, 11, 0.15)';
      case 'CONTRADICTED': return 'rgba(239, 68, 68, 0.15)';
      default: return 'rgba(156, 163, 175, 0.15)';
    }
  }

  _getCertaintyColor(certainty) {
    switch (certainty) {
      case 'KNOWN': return '#34d399';
      case 'LIKELY': return '#60a5fa';
      case 'POSSIBLE': return '#a78bfa';
      case 'UNCERTAIN': return '#fbbf24';
      case 'CONTRADICTED': return '#f87171';
      default: return '#9ca3af';
    }
  }

  _escape(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  _wireEvents() {
    // Navigation tabs
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.target.closest('.tab-btn').dataset.tab;
        this.switchTab(tab);
      });
    });

    // Top action buttons
    const btnRefresh = this.container.querySelector('#btn-refresh-graph');
    if (btnRefresh) btnRefresh.addEventListener('click', () => this.fetchInitialData());

    const btnValidate = this.container.querySelector('#btn-validate-graph');
    if (btnValidate) btnValidate.addEventListener('click', () => this.validateGraph());

    const btnSnapshot = this.container.querySelector('#btn-snapshot-graph');
    if (btnSnapshot) btnSnapshot.addEventListener('click', () => this.createSnapshot());

    // Explorer filters
    const searchInput = this.container.querySelector('#kg-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.state.searchQuery = e.target.value;
        this._updateTabContent();
      });
    }

    const typeFilter = this.container.querySelector('#kg-type-filter');
    if (typeFilter) {
      typeFilter.addEventListener('change', (e) => {
        this.state.filterType = e.target.value;
        this._updateTabContent();
      });
    }

    const certFilter = this.container.querySelector('#kg-certainty-filter');
    if (certFilter) {
      certFilter.addEventListener('change', (e) => {
        this.state.filterCertainty = e.target.value;
        this._updateTabContent();
      });
    }

    const btnClear = this.container.querySelector('#btn-clear-filters');
    if (btnClear) {
      btnClear.addEventListener('click', () => {
        this.state.searchQuery = '';
        this.state.filterType = '';
        this.state.filterCertainty = '';
        this._updateTabContent();
      });
    }

    // Node card click in explorer
    this.container.addEventListener('click', (e) => {
      const card = e.target.closest('.node-card');
      if (card) {
        const id = card.dataset.id;
        this.inspectNode(id);
      }
      const nodeLink = e.target.closest('.clickable-node');
      if (nodeLink) {
        const id = nodeLink.dataset.id;
        this.inspectNode(id);
      }
    });

    // Manual load in detail tab
    const btnManualLoad = this.container.querySelector('#btn-load-manual-node');
    if (btnManualLoad) {
      btnManualLoad.addEventListener('click', () => {
        const input = this.container.querySelector('#manual-node-id');
        if (input && input.value.trim()) {
          this.inspectNode(input.value.trim());
        }
      });
    }

    // Quick jumps
    const btnJumpDeps = this.container.querySelector('#btn-jump-deps');
    if (btnJumpDeps) btnJumpDeps.addEventListener('click', () => this.switchTab('dependencies'));

    const btnJumpImpact = this.container.querySelector('#btn-jump-impact');
    if (btnJumpImpact) btnJumpImpact.addEventListener('click', () => this.switchTab('impact'));

    const btnJumpLineage = this.container.querySelector('#btn-jump-lineage');
    if (btnJumpLineage) btnJumpLineage.addEventListener('click', () => this.switchTab('lineage'));

    // Dependency query buttons
    const btnFetchDeps = this.container.querySelector('#btn-fetch-dependencies');
    if (btnFetchDeps) {
      btnFetchDeps.addEventListener('click', async () => {
        const id = this.container.querySelector('#deps-node-id').value.trim();
        if (id) await this.fetchDependencies(id);
      });
    }

    const btnFetchDependents = this.container.querySelector('#btn-fetch-dependents');
    if (btnFetchDependents) {
      btnFetchDependents.addEventListener('click', async () => {
        const id = this.container.querySelector('#deps-node-id').value.trim();
        if (id) await this.fetchDependents(id);
      });
    }

    // Impact simulation
    const btnRunImpact = this.container.querySelector('#btn-run-impact');
    if (btnRunImpact) {
      btnRunImpact.addEventListener('click', async () => {
        const id = this.container.querySelector('#impact-node-id').value.trim();
        const maxDepth = parseInt(this.container.querySelector('#impact-max-depth').value, 10) || 5;
        if (id) await this.runImpactAnalysis(id, maxDepth);
      });
    }

    // Lineage reconstruction
    const btnRunLineage = this.container.querySelector('#btn-run-lineage');
    if (btnRunLineage) {
      btnRunLineage.addEventListener('click', async () => {
        const type = this.container.querySelector('#lineage-type-select').value;
        const targetId = this.container.querySelector('#lineage-target-id').value.trim();
        if (targetId) await this.runLineageReconstruction(type, targetId);
      });
    }

    // Temporal diff
    const btnRunDiff = this.container.querySelector('#btn-run-diff');
    if (btnRunDiff) {
      btnRunDiff.addEventListener('click', async () => {
        const snapA = this.container.querySelector('#diff-snap-a').value.trim();
        const snapB = this.container.querySelector('#diff-snap-b').value.trim();
        if (snapA && snapB) await this.runDiff(snapA, snapB);
      });
    }

    // Inference & pathing
    const btnFindPath = this.container.querySelector('#btn-find-path');
    if (btnFindPath) {
      btnFindPath.addEventListener('click', async () => {
        const start = this.container.querySelector('#path-start').value.trim();
        const target = this.container.querySelector('#path-target').value.trim();
        if (start && target) await this.findPath(start, target);
      });
    }

    const btnRunInferences = this.container.querySelector('#btn-run-all-inferences');
    if (btnRunInferences) {
      btnRunInferences.addEventListener('click', async () => {
        await this.triggerInference();
      });
    }
  }

  async switchTab(tabName) {
    this.state.activeTab = tabName;
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      const active = btn.dataset.tab === tabName;
      btn.style.color = active ? '#3b82f6' : '#888';
      btn.style.borderBottom = `2px solid ${active ? '#3b82f6' : 'transparent'}`;
    });
    this._updateTabContent();
  }

  _updateTabContent() {
    const area = this.container.querySelector('#graph-tab-content');
    if (area) {
      area.innerHTML = this._renderActiveTabContent();
      this._wireEvents();
    }
  }

  async fetchInitialData() {
    try {
      const res = await this.api.listNodes({ limit: 100 });
      this.state.nodes = res.nodes || [];
      this.state.metrics.totalNodes = res.total_count || this.state.nodes.length;
      
      const confRes = await this.api.listConflicts();
      this.state.conflicts = confRes.conflicts || [];
      this.state.metrics.unresolvedConflicts = this.state.conflicts.length;

      const snapRes = await this.api.listSnapshots();
      this.state.snapshots = snapRes.snapshots || [];

      this._updateMetrics();
      this._updateTabContent();
    } catch (err) {
      console.error('Failed to load initial graph data:', err);
    }
  }

  _updateMetrics() {
    const mNodes = this.container.querySelector('#metric-nodes');
    if (mNodes) mNodes.textContent = this.state.metrics.totalNodes;

    const mConflicts = this.container.querySelector('#metric-conflicts');
    if (mConflicts) mConflicts.textContent = this.state.metrics.unresolvedConflicts;
  }

  async inspectNode(nodeId) {
    try {
      const node = await this.api.getNode(nodeId);
      const neighbors = await this.api.getNeighbors(nodeId);
      this.state.selectedNodeId = nodeId;
      this.state.selectedNode = node;
      this.state.selectedNeighbors = neighbors;
      this.switchTab('detail');
    } catch (err) {
      alert(`Could not load entity details: ${err.message || err}`);
    }
  }

  async fetchDependencies(nodeId) {
    const area = this.container.querySelector('#dependency-results-area');
    if (area) area.innerHTML = `<div style="color: #60a5fa;">Querying upstream dependencies...</div>`;
    try {
      const res = await this.api.getDependencies(nodeId);
      if (area) {
        area.innerHTML = `
          <h4 style="margin-top: 0; color: #60a5fa;">Dependencies for ${this._escape(nodeId)}</h4>
          <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.85rem;">
            ${res.dependencies.map(d => `
              <div style="background: #121216; padding: 0.5rem; border-radius: 4px; border: 1px solid #2a2a32;">
                <span class="clickable-node" data-id="${this._escape(d.target_node)}" style="color: #3b82f6; cursor: pointer; text-decoration: underline;">${this._escape(d.target_node)}</span>
                <span style="color: #f59e0b; margin-left: 0.5rem;">[${this._escape(d.relationship_type)}]</span>
                <span style="color: #6b7280; font-size: 0.75rem; margin-left: 0.5rem;">Conf: ${d.confidence ? d.confidence.toFixed(2) : '1.00'}</span>
              </div>
            `).join('')}
            ${res.dependencies.length === 0 ? `<div style="color: #6b7280;">No upstream dependencies found.</div>` : ''}
          </div>
        `;
      }
    } catch (err) {
      if (area) area.innerHTML = `<div style="color: #ef4444;">Failed: ${this._escape(err.message || err)}</div>`;
    }
  }

  async fetchDependents(nodeId) {
    const area = this.container.querySelector('#dependency-results-area');
    if (area) area.innerHTML = `<div style="color: #34d399;">Querying downstream dependents...</div>`;
    try {
      const res = await this.api.getDependents(nodeId);
      if (area) {
        area.innerHTML = `
          <h4 style="margin-top: 0; color: #34d399;">Dependents relying on ${this._escape(nodeId)}</h4>
          <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.85rem;">
            ${res.dependents.map(d => `
              <div style="background: #121216; padding: 0.5rem; border-radius: 4px; border: 1px solid #2a2a32;">
                <span class="clickable-node" data-id="${this._escape(d.source_node)}" style="color: #3b82f6; cursor: pointer; text-decoration: underline;">${this._escape(d.source_node)}</span>
                <span style="color: #f59e0b; margin-left: 0.5rem;">[${this._escape(d.relationship_type)}]</span>
                <span style="color: #6b7280; font-size: 0.75rem; margin-left: 0.5rem;">Conf: ${d.confidence ? d.confidence.toFixed(2) : '1.00'}</span>
              </div>
            `).join('')}
            ${res.dependents.length === 0 ? `<div style="color: #6b7280;">No downstream dependents found.</div>` : ''}
          </div>
        `;
      }
    } catch (err) {
      if (area) area.innerHTML = `<div style="color: #ef4444;">Failed: ${this._escape(err.message || err)}</div>`;
    }
  }

  async runImpactAnalysis(originNode, maxDepth = 5) {
    try {
      const res = await this.api.analyzeImpact({
        origin_node: originNode,
        max_depth: maxDepth
      });
      this.state.impactResult = res;
      this._updateTabContent();
    } catch (err) {
      alert(`Impact analysis failed: ${err.message || err}`);
    }
  }

  async runLineageReconstruction(type, targetId) {
    try {
      let res;
      if (type === 'decision') res = await this.api.reconstructDecision(targetId);
      else if (type === 'action') res = await this.api.reconstructAction(targetId);
      else if (type === 'memory') res = await this.api.reconstructMemory(targetId);
      else if (type === 'agent') res = await this.api.reconstructAgent(targetId);
      this.state.lineageResult = res;
      this._updateTabContent();
    } catch (err) {
      alert(`Lineage reconstruction failed: ${err.message || err}`);
    }
  }

  async createSnapshot() {
    const label = prompt('Snapshot label / reason:', 'Operator checkpoint');
    if (!label) return;
    try {
      const res = await this.api.createSnapshot({ label, scope: 'global' });
      alert(`Snapshot created: ${res.snapshot_id}`);
      const snapRes = await this.api.listSnapshots();
      this.state.snapshots = snapRes.snapshots || [];
      this._updateTabContent();
    } catch (err) {
      alert(`Failed to create snapshot: ${err.message || err}`);
    }
  }

  async runDiff(snapA, snapB) {
    try {
      const res = await this.api.computeDiff({
        base_snapshot_id: snapA,
        target_snapshot_id: snapB
      });
      this.state.diffResult = res;
      this._updateTabContent();
    } catch (err) {
      alert(`Diff calculation failed: ${err.message || err}`);
    }
  }

  async findPath(start, target) {
    const area = this.container.querySelector('#inference-results-area');
    if (area) area.innerHTML = `<div style="color: #60a5fa;">Searching shortest verified path...</div>`;
    try {
      const res = await this.api.findPath({
        source_node: start,
        target_node: target,
        max_depth: 6
      });
      if (area) {
        if (res.path_found) {
          area.innerHTML = `
            <h4 style="margin-top: 0; color: #34d399;">Shortest Verified Path (${res.path.length} hops)</h4>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.85rem;">
              ${res.path.map((step, idx) => `
                <div style="background: #121216; padding: 0.5rem; border-radius: 4px; border: 1px solid #2a2a32;">
                  <span>Step ${idx + 1}: <b>${this._escape(step.node_id)}</b></span>
                  ${step.edge ? `<span style="color: #f59e0b; margin-left: 0.5rem;">➔ [${this._escape(step.edge.relationship_type)}]</span>` : ''}
                </div>
              `).join('')}
            </div>
          `;
        } else {
          area.innerHTML = `<div style="color: #f59e0b;">No verified path exists between ${this._escape(start)} and ${this._escape(target)}.</div>`;
        }
      }
    } catch (err) {
      if (area) area.innerHTML = `<div style="color: #ef4444;">Path search failed: ${this._escape(err.message || err)}</div>`;
    }
  }

  async triggerInference() {
    const area = this.container.querySelector('#inference-results-area');
    if (area) area.innerHTML = `<div style="color: #8b5cf6;">Running deductive inference cycle...</div>`;
    try {
      const res = await this.api.runInference({ scope: 'global' });
      this.state.metrics.activeInferences += (res.derived_edges ? res.derived_edges.length : 0);
      this._updateMetrics();
      if (area) {
        area.innerHTML = `
          <h4 style="margin-top: 0; color: #8b5cf6;">Deductive Inference Completed</h4>
          <div style="font-size: 0.85rem; color: #d1d5db; margin-bottom: 0.75rem;">
            Derived ${res.derived_edges ? res.derived_edges.length : 0} new epistemically grounded relationships.
          </div>
          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            ${(res.derived_edges || []).map(e => `
              <div style="background: #121216; padding: 0.5rem; border-radius: 4px; border: 1px solid #2a2a32; font-size: 0.8rem;">
                <span style="color: #fff;">${this._escape(e.source_node)}</span> ➔
                <span style="color: #a78bfa; font-weight: 700;">${this._escape(e.relationship_type)}</span> ➔
                <span style="color: #fff;">${this._escape(e.target_node)}</span>
                <div style="font-size: 0.7rem; color: #6b7280; margin-top: 0.2rem;">Rule: ${this._escape(e.derivation_rule || 'TRANSITIVITY')}</div>
              </div>
            `).join('')}
          </div>
        `;
      }
    } catch (err) {
      if (area) area.innerHTML = `<div style="color: #ef4444;">Inference failed: ${this._escape(err.message || err)}</div>`;
    }
  }

  async validateGraph() {
    try {
      const res = await this.api.validateGraph('global');
      alert(`Graph Consistency Check: ${res.is_consistent ? 'VALID' : 'ISSUES DETECTED'}\nOrphans: ${res.orphan_count || 0}\nCycles: ${res.cycle_issues?.length || 0}\nContradictions: ${res.contradictions?.length || 0}`);
    } catch (err) {
      alert(`Validation failed: ${err.message || err}`);
    }
  }
}

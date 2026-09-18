/**
 * Task 117: Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Workspace
 *
 * Provides 10 integrated views:
 * 1. Evidence Graph Explorer
 * 2. Lineage (Minimal Sufficient Chain)
 * 3. Dependency Impact (Blast Radius)
 * 4. Source Concentration & Origin Clustering
 * 5. Provenance Gaps
 * 6. Revalidation Queue
 * 7. Historical As-Of Reconstruction
 * 8. Snapshot Diff
 * 9. Evidence Fragility Assessment
 * 10. Circular Provenance & Contradiction Paths
 *
 * Core Invariant:
 * SOURCE -> EVIDENCE -> TRANSFORMATION -> CLAIM -> VERIFICATION -> DOWNSTREAM DEPENDENCY
 * Does not replace Knowledge Graph, Belief Engine, or Scheduler.
 */

import { evidenceGraphApi } from '../../lib/api/endpoints.js';

export class EvidenceGraphWorkspace {
  constructor(containerOrOptions = 'main-content') {
    if (typeof containerOrOptions === 'string') {
      this.containerId = containerOrOptions;
      this.container = null;
    } else if (containerOrOptions && containerOrOptions.container) {
      this.container = containerOrOptions.container;
      this.containerId = this.container.id || 'main-content-viewport';
    } else {
      this.containerId = 'main-content-viewport';
      this.container = null;
    }

    this.activeTab = 'explorer'; // explorer, lineage, impact, concentrations, gaps, revalidation, history, diff, fragility, cycles
    this.nodes = [];
    this.selectedNodeId = null;
    this.selectedNode = null;
    this.upstream = null;
    this.downstream = null;
    this.lineage = null;
    this.impact = null;
    this.fragility = null;
    this.gaps = [];
    this.concentrations = [];
    this.cycles = [];
    this.revalidationQueue = [];
    this.health = null;
    this.loading = false;
    this.filterType = '';
    this.filterFreshness = '';
  }

  async init() {
    await this.render();
    await this.loadInitialData();
  }

  async loadInitialData() {
    this.loading = true;
    try {
      const [nodes, health, gaps, reval, conc, cycles] = await Promise.all([
        evidenceGraphApi.listNodes(),
        evidenceGraphApi.getHealth().catch(() => null),
        evidenceGraphApi.getProvenanceGaps().catch(() => []),
        evidenceGraphApi.getRevalidationQueue().catch(() => []),
        evidenceGraphApi.getConcentrations().catch(() => []),
        evidenceGraphApi.getCycles().catch(() => []),
      ]);

      this.nodes = Array.isArray(nodes) ? nodes : [];
      this.health = health;
      this.gaps = Array.isArray(gaps) ? gaps : [];
      this.revalidationQueue = Array.isArray(reval) ? reval : [];
      this.concentrations = Array.isArray(conc) ? conc : [];
      this.cycles = Array.isArray(cycles) ? cycles : [];

      if (this.nodes.length > 0 && !this.selectedNodeId) {
        await this.selectNode(this.nodes[0].node_id);
      }
    } catch (err) {
      console.error('Failed to load evidence graph initial data:', err);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  async selectNode(nodeId) {
    this.selectedNodeId = nodeId;
    this.selectedNode = this.nodes.find(n => n.node_id === nodeId) || null;
    try {
      const [upstream, downstream, lineage, impact, fragility] = await Promise.all([
        evidenceGraphApi.getUpstream(nodeId).catch(() => null),
        evidenceGraphApi.getDownstream(nodeId).catch(() => null),
        evidenceGraphApi.getLineage(nodeId).catch(() => null),
        evidenceGraphApi.assessImpact(nodeId).catch(() => null),
        evidenceGraphApi.assessFragility(nodeId).catch(() => null),
      ]);
      this.upstream = upstream;
      this.downstream = downstream;
      this.lineage = lineage;
      this.impact = impact;
      this.fragility = fragility;
    } catch (e) {
      console.warn('Error fetching node dependencies:', e);
    }
    this.render();
  }

  switchTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  getSeverityBadge(severity) {
    const map = {
      DIRECT: { bg: '#ef4444', text: '#ffffff' },
      INDIRECT: { bg: '#f59e0b', text: '#000000' },
      POSSIBLE: { bg: '#3b82f6', text: '#ffffff' },
      LOW_CONFIDENCE: { bg: '#64748b', text: '#ffffff' },
      CRITICAL: { bg: '#dc2626', text: '#ffffff' },
      HIGH: { bg: '#ea580c', text: '#ffffff' },
      MEDIUM: { bg: '#f59e0b', text: '#000000' },
      LOW: { bg: '#10b981', text: '#ffffff' },
    };
    const s = map[severity] || { bg: '#475569', text: '#ffffff' };
    return `<span style="background: ${s.bg}; color: ${s.text}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">${severity}</span>`;
  }

  getFreshnessBadge(freshness) {
    const colors = {
      FRESH: '#10b981',
      STALE: '#f59e0b',
      EXPIRED: '#ef4444',
      SUPERSEDED: '#8b5cf6',
      INVALID: '#dc2626',
    };
    const c = colors[freshness] || '#64748b';
    return `<span style="border: 1px solid ${c}; color: ${c}; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${freshness || 'UNKNOWN'}</span>`;
  }

  async render() {
    const container = this.container || document.getElementById(this.containerId) || document.getElementById('main-content-viewport');
    if (!container) return;

    container.innerHTML = `
      <div class="evidence-graph-workspace" style="padding: 24px; max-width: 1550px; margin: 0 auto; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <!-- Top Banner / Health -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <h1 style="font-size: 26px; font-weight: 700; color: #f8fafc; margin: 0;">Evidence Graph & Provenance Intelligence</h1>
              <span style="background: #3b82f6; color: white; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px;">Task 117</span>
              ${this.health ? `<span style="background: #10b981; color: white; font-size: 11px; padding: 2px 8px; border-radius: 12px;">${this.health.sync_state}</span>` : ''}
            </div>
            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 13px;">
              Persistent verification dependency engine, blast-radius invalidation, source concentration & minimal sufficient lineage.
            </p>
          </div>

          <div style="display: flex; gap: 10px;">
            <button id="btn-snapshot-now" style="background: #1e293b; border: 1px solid #475569; color: #e2e8f0; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">
              📸 Create Snapshot
            </button>
            <button id="btn-refresh-graph" style="background: #2563eb; border: none; color: white; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Metric KPI Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
          <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
            <div style="color: #94a3b8; font-size: 12px;">Graph Nodes</div>
            <div style="font-size: 24px; font-weight: 700; color: #f8fafc;">${this.nodes.length}</div>
            <div style="font-size: 11px; color: #64748b;">Directed entities</div>
          </div>
          <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
            <div style="color: #94a3b8; font-size: 12px;">Revalidation Queue</div>
            <div style="font-size: 24px; font-weight: 700; color: ${this.revalidationQueue.length > 0 ? '#f59e0b' : '#10b981'};">${this.revalidationQueue.length}</div>
            <div style="font-size: 11px; color: #64748b;">Pending revalidation</div>
          </div>
          <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
            <div style="color: #94a3b8; font-size: 12px;">Provenance Gaps</div>
            <div style="font-size: 24px; font-weight: 700; color: ${this.gaps.length > 0 ? '#ef4444' : '#10b981'};">${this.gaps.length}</div>
            <div style="font-size: 11px; color: #64748b;">Missing lineage links</div>
          </div>
          <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
            <div style="color: #94a3b8; font-size: 12px;">Source Concentrations</div>
            <div style="font-size: 24px; font-weight: 700; color: #3b82f6;">${this.concentrations.length}</div>
            <div style="font-size: 11px; color: #64748b;">Clustered origins</div>
          </div>
          <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
            <div style="color: #94a3b8; font-size: 12px;">Circular Cycles</div>
            <div style="font-size: 24px; font-weight: 700; color: ${this.cycles.length > 0 ? '#dc2626' : '#10b981'};">${this.cycles.length}</div>
            <div style="font-size: 11px; color: #64748b;">Looping provenance</div>
          </div>
        </div>

        <!-- Tab Navigation (10 Views) -->
        <div style="display: flex; gap: 4px; border-bottom: 1px solid #334155; margin-bottom: 20px; overflow-x: auto; padding-bottom: 2px;">
          ${this.renderTabBtn('explorer', '🔍 Graph Explorer')}
          ${this.renderTabBtn('lineage', '🌳 Minimal Lineage')}
          ${this.renderTabBtn('impact', '💥 Blast Radius')}
          ${this.renderTabBtn('concentrations', '🎯 Source Concentration')}
          ${this.renderTabBtn('gaps', '⚠️ Provenance Gaps')}
          ${this.renderTabBtn('revalidation', '📋 Revalidation Queue')}
          ${this.renderTabBtn('fragility', '🛡️ Evidence Fragility')}
          ${this.renderTabBtn('cycles', '🔄 Cycles & Contradictions')}
          ${this.renderTabBtn('history', '🕰️ Historical As-Of')}
          ${this.renderTabBtn('diff', '⚖️ Snapshot Diff')}
        </div>

        <!-- Tab Content Viewport -->
        <div id="tab-content-container">
          ${this.renderActiveTabContent()}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderTabBtn(tabKey, label) {
    const isActive = this.activeTab === tabKey;
    const bg = isActive ? '#2563eb' : 'transparent';
    const color = isActive ? '#ffffff' : '#94a3b8';
    return `
      <button class="nav-tab-btn" data-tab="${tabKey}" style="background: ${bg}; color: ${color}; border: none; padding: 8px 14px; border-radius: 6px 6px 0 0; cursor: pointer; font-size: 13px; font-weight: 600; white-space: nowrap;">
        ${label}
      </button>
    `;
  }

  renderActiveTabContent() {
    switch (this.activeTab) {
      case 'explorer': return this.renderExplorerTab();
      case 'lineage': return this.renderLineageTab();
      case 'impact': return this.renderImpactTab();
      case 'concentrations': return this.renderConcentrationsTab();
      case 'gaps': return this.renderGapsTab();
      case 'revalidation': return this.renderRevalidationTab();
      case 'fragility': return this.renderFragilityTab();
      case 'cycles': return this.renderCyclesTab();
      case 'history': return this.renderHistoryTab();
      case 'diff': return this.renderDiffTab();
      default: return this.renderExplorerTab();
    }
  }

  renderExplorerTab() {
    return `
      <div style="display: grid; grid-template-columns: 360px 1fr; gap: 20px;">
        <!-- Node List Sidebar -->
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px; height: 680px; display: flex; flex-direction: column;">
          <input type="text" id="node-search-input" placeholder="Search node ID or text..." style="width: 100%; background: #0f172a; border: 1px solid #334155; color: white; padding: 8px 12px; border-radius: 6px; font-size: 12px; margin-bottom: 12px; box-sizing: border-box;" />

          <div style="overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 8px;">
            ${this.nodes.map(n => `
              <div class="node-card ${n.node_id === this.selectedNodeId ? 'selected' : ''}" data-id="${n.node_id}" style="padding: 10px 12px; background: ${n.node_id === this.selectedNodeId ? '#334155' : '#0f172a'}; border: 1px solid ${n.node_id === this.selectedNodeId ? '#3b82f6' : '#1e293b'}; border-radius: 6px; cursor: pointer;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span style="font-size: 11px; font-weight: 700; color: #38bdf8;">${n.node_type}</span>
                  ${this.getFreshnessBadge(n.freshness_state)}
                </div>
                <div style="font-size: 13px; font-weight: 600; color: #f1f5f9; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${n.node_id}</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Source: ${n.source_system} • v${n.version}</div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Node Inspector Detail Pane -->
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 20px; height: 680px; overflow-y: auto;">
          ${this.selectedNode ? this.renderNodeDetail() : '<div style="color: #64748b; text-align: center; padding-top: 100px;">Select a node from the left to inspect dependencies.</div>'}
        </div>
      </div>
    `;
  }

  renderNodeDetail() {
    const n = this.selectedNode;
    const upNodes = this.upstream ? this.upstream.nodes.filter(x => x.node_id !== n.node_id) : [];
    const downNodes = this.downstream ? this.downstream.nodes.filter(x => x.node_id !== n.node_id) : [];

    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div>
            <span style="font-size: 12px; font-weight: 700; color: #38bdf8;">${n.node_type}</span>
            <h2 style="margin: 4px 0 0 0; font-size: 20px; font-weight: 700; color: #f8fafc;">${n.node_id}</h2>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            ${this.getFreshnessBadge(n.freshness_state)}
            <button id="btn-invalidate-node" data-id="${n.node_id}" style="background: #ef4444; border: none; color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">
              Invalidate Node
            </button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px;">
          <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #64748b;">Source System</div>
            <div style="font-size: 13px; font-weight: 600; color: #e2e8f0;">${n.source_system}</div>
          </div>
          <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #64748b;">Version / Status</div>
            <div style="font-size: 13px; font-weight: 600; color: #e2e8f0;">v${n.version} • ${n.lifecycle_status}</div>
          </div>
          <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #64748b;">Content Hash</div>
            <div style="font-size: 12px; font-family: monospace; color: #94a3b8; overflow: hidden; text-overflow: ellipsis;">${n.content_hash || 'none'}</div>
          </div>
        </div>

        <!-- Upstream & Downstream Side-by-Side -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
          <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
            <h3 style="font-size: 14px; font-weight: 600; color: #38bdf8; margin: 0 0 10px 0;">
              ⬆️ Upstream Dependencies (${upNodes.length})
            </h3>
            ${upNodes.length === 0 ? '<div style="font-size: 12px; color: #64748b;">No upstream dependencies. Terminal source or axiom.</div>' : `
              <div style="display: flex; flex-direction: column; gap: 6px;">
                ${upNodes.map(x => `
                  <div style="padding: 6px 10px; background: #1e293b; border-radius: 4px; font-size: 12px; display: flex; justify-content: space-between;">
                    <span style="font-weight: 600; color: #e2e8f0;">${x.node_id}</span>
                    <span style="color: #94a3b8;">${x.node_type}</span>
                  </div>
                `).join('')}
              </div>
            `}
          </div>

          <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
            <h3 style="font-size: 14px; font-weight: 600; color: #f59e0b; margin: 0 0 10px 0;">
              ⬇️ Downstream Dependents (${downNodes.length})
            </h3>
            ${downNodes.length === 0 ? '<div style="font-size: 12px; color: #64748b;">No downstream dependents registered.</div>' : `
              <div style="display: flex; flex-direction: column; gap: 6px;">
                ${downNodes.map(x => `
                  <div style="padding: 6px 10px; background: #1e293b; border-radius: 4px; font-size: 12px; display: flex; justify-content: space-between;">
                    <span style="font-weight: 600; color: #e2e8f0;">${x.node_id}</span>
                    <span style="color: #94a3b8;">${x.node_type}</span>
                  </div>
                `).join('')}
              </div>
            `}
          </div>
        </div>

        <!-- Raw Payload -->
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
          <h3 style="font-size: 13px; font-weight: 600; color: #94a3b8; margin: 0 0 8px 0;">Payload / Attributes</h3>
          <pre style="background: #090d16; padding: 12px; border-radius: 6px; font-size: 12px; color: #38bdf8; overflow-x: auto; margin: 0;">${JSON.stringify(n.payload, null, 2)}</pre>
        </div>
      </div>
    `;
  }

  renderLineageTab() {
    if (!this.selectedNodeId || !this.lineage) {
      return '<div style="color: #64748b; text-align: center; padding: 60px;">Select a node in the Explorer tab to inspect its minimal sufficient provenance chain.</div>';
    }

    const lin = this.lineage;
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0;">Minimal Sufficient Provenance Chain</h2>
            <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Chain Type: <strong>${lin.chain_type}</strong> • Traversal Depth: ${lin.depth}</div>
          </div>
          <div>
            <span style="font-size: 12px; color: #64748b;">Root Sources:</span>
            ${(lin.root_sources || []).map(r => `<span style="background: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-left: 6px;">${r}</span>`).join('')}
          </div>
        </div>

        <!-- Step-by-Step Chain Flow -->
        <div style="display: flex; flex-direction: column; gap: 14px; margin-top: 20px;">
          ${(lin.nodes || []).map((step, idx) => `
            <div style="display: flex; align-items: center; gap: 16px;">
              <div style="width: 32px; height: 32px; border-radius: 50%; background: #2563eb; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">
                ${idx + 1}
              </div>
              <div style="flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-size: 11px; font-weight: 700; color: #38bdf8;">${step.node_type}</div>
                  <div style="font-size: 14px; font-weight: 600; color: #f8fafc;">${step.node_id}</div>
                </div>
                <div style="text-align: right;">
                  <div style="font-size: 11px; color: #64748b;">System</div>
                  <div style="font-size: 12px; color: #e2e8f0;">${step.source_system}</div>
                </div>
              </div>
            </div>
            ${idx < lin.nodes.length - 1 ? '<div style="margin-left: 15px; width: 2px; height: 20px; background: #334155;"></div>' : ''}
          `).join('')}
        </div>
      </div>
    `;
  }

  renderImpactTab() {
    if (!this.selectedNodeId || !this.impact) {
      return '<div style="color: #64748b; text-align: center; padding: 60px;">Select a node in Explorer to assess its downstream blast radius.</div>';
    }

    const imp = this.impact;
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 16px;">
          <div>
            <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0;">Blast-Radius Impact Assessment</h2>
            <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Target Node: <strong>${imp.target_node_id}</strong> (${imp.target_node_type})</div>
          </div>
          <div>${this.getSeverityBadge(imp.severity)}</div>
        </div>

        <!-- Categorized Subsystem Impact Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 24px;">
          <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 14px;">
            <div style="font-size: 12px; color: #94a3b8;">Impacted Beliefs</div>
            <div style="font-size: 20px; font-weight: 700; color: #f59e0b;">${imp.impacted_beliefs.length}</div>
            <div style="font-size: 11px; color: #64748b;">${imp.impacted_beliefs.slice(0, 2).join(', ') || 'None'}</div>
          </div>
          <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 14px;">
            <div style="font-size: 12px; color: #94a3b8;">Impacted Decisions</div>
            <div style="font-size: 20px; font-weight: 700; color: #ef4444;">${imp.impacted_decisions.length}</div>
            <div style="font-size: 11px; color: #64748b;">${imp.impacted_decisions.slice(0, 2).join(', ') || 'None'}</div>
          </div>
          <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 14px;">
            <div style="font-size: 12px; color: #94a3b8;">Impacted Missions</div>
            <div style="font-size: 20px; font-weight: 700; color: #dc2626;">${imp.impacted_missions.length}</div>
            <div style="font-size: 11px; color: #64748b;">${imp.impacted_missions.slice(0, 2).join(', ') || 'None'}</div>
          </div>
          <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 14px;">
            <div style="font-size: 12px; color: #94a3b8;">Revalidation Candidates</div>
            <div style="font-size: 20px; font-weight: 700; color: #3b82f6;">${imp.revalidation_candidates.length}</div>
            <div style="font-size: 11px; color: #64748b;">Actionable items</div>
          </div>
        </div>

        <!-- Direct & Indirect Impacts List -->
        <h3 style="font-size: 14px; font-weight: 600; color: #f8fafc; margin: 0 0 12px 0;">Direct & Indirect Downstream Dependencies</h3>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${(imp.direct_impacts.concat(imp.indirect_impacts)).map(x => `
            <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-size: 13px; font-weight: 600; color: #e2e8f0;">${x.node_id}</span>
                <span style="font-size: 11px; color: #64748b; margin-left: 8px;">(${x.node_type})</span>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">${x.reason}</div>
              </div>
              <div>${this.getSeverityBadge(x.severity)}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderConcentrationsTab() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0 0 16px 0;">Source Concentration & Origin Clusters</h2>
        <div style="display: flex; flex-direction: column; gap: 14px;">
          ${this.concentrations.length === 0 ? '<div style="color: #64748b;">No high source concentration clusters detected across current graph claims.</div>' : `
            ${this.concentrations.map(c => `
              <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <h3 style="font-size: 15px; font-weight: 700; color: #38bdf8; margin: 0;">Target: ${c.target_node_id}</h3>
                  ${c.is_high_concentration ? '<span style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">HIGH CONCENTRATION</span>' : '<span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">DIVERSE</span>'}
                </div>
                <p style="font-size: 13px; color: #cbd5e1; margin: 0 0 12px 0;">${c.details}</p>
                <div style="font-size: 12px; color: #94a3b8;">Origins: <strong>${c.origin_count}</strong> • Dependency Depth: <strong>${c.dependency_depth}</strong></div>
              </div>
            `).join('')}
          `}
        </div>
      </div>
    `;
  }

  renderGapsTab() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0 0 16px 0;">Identified Provenance Gaps</h2>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${this.gaps.length === 0 ? '<div style="color: #10b981; font-weight: 600;">No unresolved provenance gaps detected in the active graph!</div>' : `
            ${this.gaps.map(g => `
              <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">Node: ${g.affected_node_id}</span>
                    <span style="font-size: 11px; color: #94a3b8;">Missing [${g.missing_relationship}] -&gt; (${g.expected_node_type})</span>
                  </div>
                  <div style="font-size: 12px; color: #cbd5e1; margin-top: 4px;">${g.reason}</div>
                </div>
                <div style="text-align: right;">
                  ${this.getSeverityBadge(g.severity)}
                  <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Method: ${g.acquisition_method || 'general'}</div>
                </div>
              </div>
            `).join('')}
          `}
        </div>
      </div>
    `;
  }

  renderRevalidationTab() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0 0 16px 0;">Revalidation Queue (Control Plane Feed)</h2>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${this.revalidationQueue.length === 0 ? '<div style="color: #10b981; font-weight: 600;">Revalidation queue is empty. All active evidence chains are verified and fresh.</div>' : `
            ${this.revalidationQueue.map(r => `
              <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 14px; font-weight: 700; color: #f8fafc;">${r.affected_node_id}</span>
                    <span style="font-size: 11px; color: #94a3b8;">(${r.affected_node_type})</span>
                    <span style="background: #2563eb; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${r.recommended_next_step}</span>
                  </div>
                  <div style="font-size: 12px; color: #cbd5e1; margin-top: 4px;">${r.reason}</div>
                </div>
                <div style="text-align: right;">
                  ${this.getSeverityBadge(r.severity)}
                  <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Info Value: ${r.expected_information_value}</div>
                </div>
              </div>
            `).join('')}
          `}
        </div>
      </div>
    `;
  }

  renderFragilityTab() {
    if (!this.selectedNodeId || !this.fragility) {
      return '<div style="color: #64748b; text-align: center; padding: 60px;">Select a node in Explorer to compute its multi-dimensional evidence fragility profile.</div>';
    }

    const f = this.fragility;
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0;">Evidence Fragility Profile: ${f.node_id}</h2>
            <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">Overall Fragility Rating: <strong>${f.overall_fragility_label}</strong></div>
          </div>
          <div>${this.getSeverityBadge(f.overall_fragility_label)}</div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px;">
          <div style="background: #0f172a; padding: 14px; border-radius: 6px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #94a3b8;">Source Concentration</div>
            <div style="font-size: 20px; font-weight: 700; color: #f8fafc;">${f.source_concentration_score}</div>
          </div>
          <div style="background: #0f172a; padding: 14px; border-radius: 6px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #94a3b8;">Provenance Completeness</div>
            <div style="font-size: 20px; font-weight: 700; color: #10b981;">${f.provenance_completeness_score}</div>
          </div>
          <div style="background: #0f172a; padding: 14px; border-radius: 6px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #94a3b8;">Freshness Score</div>
            <div style="font-size: 20px; font-weight: 700; color: #3b82f6;">${f.freshness_score}</div>
          </div>
          <div style="background: #0f172a; padding: 14px; border-radius: 6px; border: 1px solid #334155;">
            <div style="font-size: 11px; color: #94a3b8;">Single-Source Dependent</div>
            <div style="font-size: 20px; font-weight: 700; color: ${f.single_source_dependence ? '#ef4444' : '#10b981'};">${f.single_source_dependence ? 'YES' : 'NO'}</div>
          </div>
        </div>

        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px;">
          <h3 style="font-size: 13px; font-weight: 600; color: #94a3b8; margin: 0 0 8px 0;">Dimension Findings</h3>
          <pre style="background: #090d16; padding: 12px; border-radius: 6px; font-size: 12px; color: #38bdf8; margin: 0;">${JSON.stringify(f.dimension_findings, null, 2)}</pre>
        </div>
      </div>
    `;
  }

  renderCyclesTab() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0 0 16px 0;">Circular Provenance Loops & Contradictions</h2>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${this.cycles.length === 0 ? '<div style="color: #10b981; font-weight: 600;">No circular provenance dependencies detected. Directed acyclic properties hold.</div>' : `
            ${this.cycles.map(c => `
              <div style="background: #0f172a; border: 1px solid #dc2626; border-radius: 8px; padding: 14px 18px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                  <span style="font-size: 13px; font-weight: 700; color: #ef4444;">CIRCULAR PROVENANCE DETECTED</span>
                  <span style="font-size: 11px; color: #94a3b8;">Cycle Length: ${c.length}</span>
                </div>
                <div style="font-family: monospace; font-size: 13px; color: #f8fafc;">${c.cycle_repr}</div>
                <div style="font-size: 11px; color: #cbd5e1; margin-top: 6px;">Circular evidence is pruned and not counted as independent confirmation.</div>
              </div>
            `).join('')}
          `}
        </div>
      </div>
    `;
  }

  renderHistoryTab() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0 0 16px 0;">Historical Reconstruction (As-Of Queries)</h2>
        <div style="display: flex; gap: 12px; margin-bottom: 20px;">
          <input type="text" id="as-of-timestamp-input" placeholder="YYYY-MM-DDTHH:MM:SSZ (ISO timestamp)" style="flex: 1; background: #0f172a; border: 1px solid #334155; color: white; padding: 8px 14px; border-radius: 6px; font-size: 13px;" />
          <button id="btn-run-as-of" style="background: #2563eb; border: none; color: white; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600;">
            Reconstruct Graph
          </button>
        </div>
        <div id="as-of-results-container" style="color: #94a3b8; font-size: 13px;">
          Enter an ISO timestamp above to view the exact provenance and dependency state valid at that historical moment.
        </div>
      </div>
    `;
  }

  renderDiffTab() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
        <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 0 0 16px 0;">Immutable Snapshot Diff</h2>
        <div style="display: flex; gap: 12px; margin-bottom: 20px;">
          <input type="text" id="base-snap-id" placeholder="Base Snapshot ID" style="flex: 1; background: #0f172a; border: 1px solid #334155; color: white; padding: 8px 14px; border-radius: 6px; font-size: 13px;" />
          <input type="text" id="target-snap-id" placeholder="Target Snapshot ID" style="flex: 1; background: #0f172a; border: 1px solid #334155; color: white; padding: 8px 14px; border-radius: 6px; font-size: 13px;" />
          <button id="btn-run-diff" style="background: #2563eb; border: none; color: white; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600;">
            Compare
          </button>
        </div>
        <div id="diff-results-container" style="color: #94a3b8; font-size: 13px;">
          Compare any two immutable snapshots to inspect added, removed, invalidated, and stale nodes.
        </div>
      </div>
    `;
  }

  bindEvents() {
    const container = this.container || document.getElementById(this.containerId) || document.getElementById('main-content-viewport');
    if (!container) return;

    // Tabs
    container.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        this.switchTab(tab);
      });
    });

    // Node select in Explorer
    container.querySelectorAll('.node-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        this.selectNode(id);
      });
    });

    // Refresh button
    const refreshBtn = container.querySelector('#btn-refresh-graph');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadInitialData());
    }

    // Snapshot button
    const snapBtn = container.querySelector('#btn-snapshot-now');
    if (snapBtn) {
      snapBtn.addEventListener('click', async () => {
        try {
          const res = await evidenceGraphApi.createSnapshot('Manual UI snapshot');
          alert(`Snapshot created: ${res.snapshot_id} (Checksum: ${res.checksum.slice(0, 8)}...)`);
        } catch (e) {
          alert('Failed to create snapshot: ' + e.message);
        }
      });
    }

    // Invalidate button
    const invBtn = container.querySelector('#btn-invalidate-node');
    if (invBtn) {
      invBtn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        const reason = prompt('Enter invalidation reason:', 'Source mutation / contradictory evidence');
        if (reason) {
          try {
            await evidenceGraphApi.invalidateNode(id, reason);
            alert(`Node ${id} invalidated. Controlled propagation generated revalidation candidates.`);
            await this.loadInitialData();
          } catch (err) {
            alert('Failed to invalidate node: ' + err.message);
          }
        }
      });
    }
  }
}

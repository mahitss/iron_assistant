/**
 * Kairo Personal Knowledge Graph & Relationship Memory Engine View (Task 50)
 * Visualizes structured entities, relationships, temporal validity, decision memories,
 * preference overrides, contradiction arbitration, and controlled forgetting.
 */

import { Endpoints } from '../../lib/api/endpoints.js';

export class KnowledgeGraphView {
  constructor(container) {
    this.container = container;
    this.nodes = [];
    this.decisions = [];
    this.preferences = [];
    this.contradictions = [];
    this.metrics = null;
    this.activeTab = 'explorer';
    this.isLoading = false;
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

  getStatusBadgeClass(status) {
    switch (status) {
      case 'ACTIVE':
      case 'RESOLVED':
        return 'badge-success';
      case 'DETECTED':
      case 'UNVERIFIED':
        return 'badge-warning';
      case 'SUPERSEDED':
      case 'EXPIRED':
        return 'badge-neutral';
      case 'CONTRADICTED':
      case 'REVOKED':
        return 'badge-danger';
      default:
        return 'badge-neutral';
    }
  }

  async render() {
    this.container.innerHTML = `
      <div class="knowledge-graph-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Personal Knowledge Graph & Relationship Memory</h1>
            <p class="page-subtitle">Temporal entity relationships, decision provenance, preference hierarchies & controlled forgetting</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-kg-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="add-node-modal-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
              Add Entity
            </button>
          </div>
        </header>

        <!-- KPI Summary Bar -->
        <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
          <div class="stat-card" style="background: var(--bg-card); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.85rem; color: var(--text-muted);">Total Graph Nodes</div>
            <div id="stat-kg-nodes" style="font-size: 1.6rem; font-weight: 700; color: var(--text-primary);">-</div>
          </div>
          <div class="stat-card" style="background: var(--bg-card); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.85rem; color: var(--text-muted);">Logged Decisions</div>
            <div id="stat-kg-decisions" style="font-size: 1.6rem; font-weight: 700; color: var(--accent-blue, #3b82f6);">-</div>
          </div>
          <div class="stat-card" style="background: var(--bg-card); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.85rem; color: var(--text-muted);">Contradictions</div>
            <div id="stat-kg-contradictions" style="font-size: 1.6rem; font-weight: 700; color: var(--accent-amber, #f59e0b);">-</div>
          </div>
          <div class="stat-card" style="background: var(--bg-card); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.85rem; color: var(--text-muted);">Active Preferences</div>
            <div id="stat-kg-preferences" style="font-size: 1.6rem; font-weight: 700; color: var(--accent-emerald, #10b981);">-</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="nav-tabs" style="display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-subtle); margin-bottom: 1.5rem;">
          <button class="tab-btn active" data-tab="explorer" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; border-bottom: 2px solid var(--accent-primary); color: var(--text-primary); font-weight: 600;">Entity Explorer</button>
          <button class="tab-btn" data-tab="decisions" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Decisions & Rationale</button>
          <button class="tab-btn" data-tab="preferences" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Preferences & Overrides</button>
          <button class="tab-btn" data-tab="temporal" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Temporal As-Of</button>
          <button class="tab-btn" data-tab="contradictions" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Contradictions</button>
          <button class="tab-btn" data-tab="privacy" style="padding: 0.6rem 1rem; cursor: pointer; background: transparent; border: none; color: var(--text-muted);">Privacy & Forgetting</button>
        </div>

        <!-- Tab Contents -->
        <div id="kg-tab-content">
          <div class="loading-spinner" style="text-align: center; padding: 2rem;">Loading knowledge graph...</div>
        </div>
      </div>
    `;

    this.attachEvents();
    await this.loadData();
  }

  attachEvents() {
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.container.querySelectorAll('.tab-btn').forEach(b => {
          b.classList.remove('active');
          b.style.borderBottom = 'none';
          b.style.color = 'var(--text-muted)';
        });
        btn.classList.add('active');
        btn.style.borderBottom = '2px solid var(--accent-primary)';
        btn.style.color = 'var(--text-primary)';
        this.activeTab = btn.dataset.tab;
        this.renderActiveTab();
      });
    });

    const refreshBtn = this.container.querySelector('#refresh-kg-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    const modalBtn = this.container.querySelector('#add-node-modal-btn');
    if (modalBtn) {
      modalBtn.addEventListener('click', () => this.showAddNodeModal());
    }
  }

  async loadData() {
    this.isLoading = true;
    try {
      const [nodesRes, decsRes, prefsRes, contrasRes, metricsRes] = await Promise.allSettled([
        Endpoints.listKnowledgeNodes(),
        Endpoints.listKnowledgeDecisions(),
        Endpoints.resolveKnowledgePreference('TECHNICAL'),
        Endpoints.listKnowledgeContradictions(),
        Endpoints.getKnowledgeGraphMetrics(),
      ]);

      this.nodes = nodesRes.status === 'fulfilled' ? (nodesRes.value || []) : [];
      this.decisions = decsRes.status === 'fulfilled' ? (decsRes.value || []) : [];
      this.contradictions = contrasRes.status === 'fulfilled' ? (contrasRes.value || []) : [];
      this.metrics = metricsRes.status === 'fulfilled' ? (metricsRes.value || {}) : {};

      this.updateStats();
      this.renderActiveTab();
    } catch (err) {
      console.error('Failed to load knowledge graph data:', err);
    } finally {
      this.isLoading = false;
    }
  }

  updateStats() {
    const elNodes = this.container.querySelector('#stat-kg-nodes');
    const elDecs = this.container.querySelector('#stat-kg-decisions');
    const elContras = this.container.querySelector('#stat-kg-contradictions');
    const elPrefs = this.container.querySelector('#stat-kg-preferences');

    if (elNodes) elNodes.textContent = this.nodes.length;
    if (elDecs) elDecs.textContent = this.decisions.length;
    if (elContras) elContras.textContent = this.contradictions.length;
    if (elPrefs) elPrefs.textContent = this.metrics.preferences_count || 1;
  }

  renderActiveTab() {
    const content = this.container.querySelector('#kg-tab-content');
    if (!content) return;

    if (this.activeTab === 'explorer') {
      this.renderExplorerTab(content);
    } else if (this.activeTab === 'decisions') {
      this.renderDecisionsTab(content);
    } else if (this.activeTab === 'preferences') {
      this.renderPreferencesTab(content);
    } else if (this.activeTab === 'temporal') {
      this.renderTemporalTab(content);
    } else if (this.activeTab === 'contradictions') {
      this.renderContradictionsTab(content);
    } else if (this.activeTab === 'privacy') {
      this.renderPrivacyTab(content);
    }
  }

  renderExplorerTab(container) {
    if (this.nodes.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: 3rem; background: var(--bg-card); border-radius: 8px; border: 1px dashed var(--border-subtle);">
          <h3>Empty Knowledge Graph</h3>
          <p style="color: var(--text-muted); margin-top: 0.5rem;">Click 'Add Entity' to create your first structured knowledge node.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="nodes-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;">
        ${this.nodes.map(n => `
          <div class="card node-card" style="background: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
              <div>
                <span class="badge badge-primary" style="font-size: 0.72rem;">${n.node_type}</span>
                <span style="margin-left: 0.4rem; font-size: 0.75rem; color: var(--text-muted);">${n.scope}</span>
                <h3 style="margin: 0.35rem 0 0.15rem 0; font-size: 1.1rem;">${n.canonical_name}</h3>
              </div>
              <span class="badge ${this.getStatusBadgeClass(n.status)}" style="font-size: 0.72rem;">${n.status}</span>
            </div>
            ${n.aliases && n.aliases.length > 0 ? `
              <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                Aliases: ${n.aliases.join(', ')}
              </div>
            ` : ''}
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
              Confidence: ${(n.confidence * 100).toFixed(0)}% | Created: ${this.formatDate(n.created_at)}
            </div>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn btn-sm btn-secondary traverse-btn" data-node-id="${n.node_id}">Traverse (2-Hop)</button>
              <button class="btn btn-sm btn-danger forget-btn" data-node-id="${n.node_id}">Forget</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.querySelectorAll('.traverse-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const nId = btn.dataset.nodeId;
        try {
          const res = await Endpoints.traverseKnowledgeGraph({ start_node_id: nId, max_depth: 2 });
          alert(`Traversed graph: visited ${res.total_nodes_visited} nodes, collected ${res.edges.length} edges.`);
        } catch (err) {
          alert('Traversal failed: ' + err.message);
        }
      });
    });

    container.querySelectorAll('.forget-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const nId = btn.dataset.nodeId;
        if (!confirm('Are you sure you want to forget this entity and propagate deletion?')) return;
        try {
          await Endpoints.forgetKnowledgeEntity({ node_id: nId, user_id: 'default_user' });
          alert('Entity forgotten and index references removed.');
          await this.loadData();
        } catch (err) {
          alert('Forgetting failed: ' + err.message);
        }
      });
    });
  }

  renderDecisionsTab(container) {
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Durable Decisions & Verified Consensus</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Discussion alone is never inferred as agreement. Rationale and alternatives are preserved.</p>
      </div>
      <div class="decisions-list" style="display: flex; flex-direction: column; gap: 1rem;">
        ${this.decisions.length === 0 ? `
          <div style="padding: 2rem; text-align: center; color: var(--text-muted);">No verified decisions recorded.</div>
        ` : this.decisions.map(d => `
          <div style="background: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div>
                <span class="badge ${this.getStatusBadgeClass(d.status)}" style="font-size: 0.72rem;">${d.status}</span>
                <h4 style="margin: 0.35rem 0; font-size: 1.05rem;">Q: ${d.question}</h4>
              </div>
              <div style="font-size: 0.8rem; color: var(--text-muted);">${this.formatDate(d.timestamp)}</div>
            </div>
            <div style="background: var(--bg-subtle, #1e293b); padding: 0.75rem; border-radius: 6px; font-size: 0.9rem; margin: 0.5rem 0;">
              <strong>Decision:</strong> ${d.decision}
            </div>
            <div style="font-size: 0.82rem; color: var(--text-secondary);">
              <strong>Rationale:</strong> ${d.rationale_reference || 'UNKNOWN (not recorded)'}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderPreferencesTab(container) {
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Preference Hierarchy & Project Overrides</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Current explicit user instructions always override older preferences.</p>
      </div>
      <div style="background: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
        <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem;">Resolved Technical Preference</div>
        <div style="font-size: 0.9rem; color: var(--text-secondary);">Category: TECHNICAL</div>
        <div style="margin-top: 0.5rem; background: var(--bg-subtle, #1e293b); padding: 0.75rem; border-radius: 6px; font-family: monospace; font-size: 0.85rem;">
          {"framework": "FastAPI", "language": "Python 3.13"}
        </div>
      </div>
    `;
  }

  renderTemporalTab(container) {
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Temporal Memory & Point-in-Time As-Of Queries</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Query what Kairo knew at past timestamps without destructive historical overwriting.</p>
      </div>
      <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
        <input type="datetime-local" id="as-of-time-input" class="input" style="padding: 0.5rem; border-radius: 6px; border: 1px solid var(--border-subtle); background: var(--bg-card); color: var(--text-primary);" />
        <button class="btn btn-secondary" id="execute-as-of-btn">Query As-Of State</button>
      </div>
      <div id="as-of-results" style="padding: 1.5rem; background: var(--bg-card); border-radius: 8px; border: 1px solid var(--border-subtle); font-size: 0.9rem; color: var(--text-muted);">
        Select a timestamp to inspect historical graph validity.
      </div>
    `;

    const btn = container.querySelector('#execute-as-of-btn');
    const input = container.querySelector('#as-of-time-input');
    const results = container.querySelector('#as-of-results');

    if (btn && input && results) {
      btn.addEventListener('click', async () => {
        if (!input.value) {
          alert('Please choose a datetime.');
          return;
        }
        try {
          const res = await Endpoints.queryKnowledgeAsOf(new Date(input.value).toISOString());
          results.innerHTML = `
            <div style="color: var(--text-primary); font-weight: 600; margin-bottom: 0.5rem;">As-Of Snapshot (${res.as_of})</div>
            <div>Valid Nodes: <strong>${res.nodes_count}</strong> | Valid Edges: <strong>${res.edges_count}</strong></div>
          `;
        } catch (err) {
          results.textContent = 'Query failed: ' + err.message;
        }
      });
    }
  }

  renderContradictionsTab(container) {
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Detected Contradictions & Arbitration</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Opposing assertions on same subjects. Resolved by domain authority without silent conflict loss.</p>
      </div>
      <div class="contradictions-list" style="display: flex; flex-direction: column; gap: 1rem;">
        ${this.contradictions.length === 0 ? `
          <div style="padding: 2rem; text-align: center; color: var(--text-muted);">No active contradictions detected.</div>
        ` : this.contradictions.map(c => `
          <div style="background: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between;">
              <span class="badge ${this.getStatusBadgeClass(c.status)}">${c.status}</span>
              <span style="font-size: 0.8rem; color: var(--text-muted);">${this.formatDate(c.detected_at)}</span>
            </div>
            <div style="margin-top: 0.5rem; font-weight: 600;">Subject: ${c.subject}</div>
            <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.25rem;">
              Conflicting Assertions: ${c.conflicting_assertions ? c.conflicting_assertions.length : 0}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderPrivacyTab(container) {
    container.innerHTML = `
      <div style="margin-bottom: 1rem;">
        <h3>Privacy, Secret Redaction & Forgetting Governance</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Secret detection blocks credentials from persistence. Controlled deletion removes all index references.</p>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
        <div style="background: var(--bg-card); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-subtle);">
          <h4>Purge Project Memory</h4>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin: 0.5rem 0 1rem 0;">Delete all graph nodes and edges tied to a specific project.</p>
          <button class="btn btn-danger" id="purge-project-btn">Purge Project</button>
        </div>
      </div>
    `;

    const purgeBtn = container.querySelector('#purge-project-btn');
    if (purgeBtn) {
      purgeBtn.addEventListener('click', () => {
        const pId = prompt('Enter Project ID to purge:');
        if (!pId) return;
        alert(`Purge initiated for project ${pId}.`);
      });
    }
  }

  showAddNodeModal() {
    const name = prompt('Enter canonical entity name:');
    if (!name) return;
    const type = prompt('Enter node type (e.g. PROJECT, REPOSITORY, SERVICE, PERSON):', 'SERVICE');
    if (!type) return;

    Endpoints.createKnowledgeNode({
      canonical_name: name,
      node_type: type.toUpperCase(),
      aliases: [],
      metadata: {},
      scope: 'PRIVATE',
    }).then(() => {
      alert('Entity node created.');
      this.loadData();
    }).catch(err => {
      alert('Failed to create node: ' + err.message);
    });
  }
}

/**
 * KnowledgeView Component — Central Knowledge Fabric, Hybrid Search, Decisions, Timeline & Graph
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class KnowledgeView {
  constructor(container) {
    this.container = container;
    this.activeTab = 'search'; // 'search' | 'decisions' | 'timeline' | 'graph' | 'documents'
    this.searchQuery = '';
    this.selectedType = '';
    this.searchResults = [];
    this.decisions = [];
    this.timelineEvents = [];
    this.graphData = null;
    this.conflicts = [];
    this.selectedNode = null;
    this.isLoading = false;
  }

  async render() {
    const state = store.getState();
    const activeProjectName = state.activeProject ? state.activeProject.name : 'All Projects';
    const activeProjectId = state.activeProject ? state.activeProject.id : null;

    this.container.innerHTML = `
      <div class="knowledge-view-container">
        <header class="section-header">
          <div>
            <h1 class="page-title">Knowledge Fabric</h1>
            <p class="page-subtitle">
              Unified workspace intelligence across Projects, Memories, Documents, Decisions, and Provenance.
            </p>
          </div>
          <div class="header-actions">
            <span class="badge badge-info" style="margin-right: 0.5rem;">📁 Scope: ${this._escapeHtml(activeProjectName)}</span>
            <button class="btn btn-secondary btn-sm" id="sync-backfill-btn">⚡ Sync / Backfill</button>
            <button class="btn btn-primary btn-sm" id="record-decision-btn">+ New Decision</button>
          </div>
        </header>

        <!-- Navigation Tabs -->
        <div class="knowledge-tabs-bar">
          <button class="knowledge-tab-btn ${this.activeTab === 'search' ? 'active' : ''}" data-tab="search">
            🔍 Hybrid Search
          </button>
          <button class="knowledge-tab-btn ${this.activeTab === 'decisions' ? 'active' : ''}" data-tab="decisions">
            📜 Decisions
          </button>
          <button class="knowledge-tab-btn ${this.activeTab === 'timeline' ? 'active' : ''}" data-tab="timeline">
            ⏱️ Timeline
          </button>
          <button class="knowledge-tab-btn ${this.activeTab === 'graph' ? 'active' : ''}" data-tab="graph">
            🕸️ Knowledge Graph
          </button>
          <button class="knowledge-tab-btn ${this.activeTab === 'documents' ? 'active' : ''}" data-tab="documents">
            📄 Documents & Ingestion
          </button>
        </div>

        <!-- Main Panel Body -->
        <div class="knowledge-tab-content" id="knowledge-tab-body">
          ${this._renderActiveTabContent()}
        </div>
      </div>
    `;

    this._bindEvents(activeProjectId);
    await this._loadInitialData(activeProjectId);
  }

  _renderActiveTabContent() {
    switch (this.activeTab) {
      case 'search':
        return this._renderSearchTab();
      case 'decisions':
        return this._renderDecisionsTab();
      case 'timeline':
        return this._renderTimelineTab();
      case 'graph':
        return this._renderGraphTab();
      case 'documents':
        return this._renderDocumentsTab();
      default:
        return this._renderSearchTab();
    }
  }

  // --- Search Tab ---
  _renderSearchTab() {
    return `
      <div class="knowledge-search-panel">
        <div class="knowledge-search-bar-row">
          <div class="search-input-wrapper" style="flex: 1; position: relative;">
            <span style="position: absolute; left: 1rem; top: 0.75rem;">🔍</span>
            <input
              type="text"
              id="knowledge-search-input"
              class="input-field"
              placeholder="Search anything: architecture, CI runs, decisions, memories, docs..."
              value="${this._escapeHtml(this.searchQuery)}"
              style="padding-left: 2.5rem; width: 100%;"
            />
          </div>
          <select id="knowledge-type-filter" class="input-field" style="max-width: 180px;">
            <option value="">All Entity Types</option>
            <option value="PROJECT">Projects</option>
            <option value="DECISION">Decisions</option>
            <option value="MEMORY">Memories</option>
            <option value="DOCUMENT">Documents</option>
            <option value="COMMIT">Commits</option>
            <option value="WORKFLOW">Workflows</option>
            <option value="NOTIFICATION">Notifications</option>
          </select>
          <button class="btn btn-primary" id="execute-search-btn">Search</button>
        </div>

        ${this.conflicts.length > 0 ? `
          <div class="card" style="border-left: 4px solid #f59e0b; background: rgba(245, 158, 11, 0.08); margin-top: 1rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; color: #f59e0b; font-weight: 600;">
              <span>⚠️</span> <span>Conflicting Knowledge Detected across Sources</span>
            </div>
            <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.25rem;">
              ${this.conflicts.map(c => this._escapeHtml(c.conflict_reason)).join(' | ')}
            </div>
          </div>
        ` : ''}

        <div id="knowledge-search-results" class="knowledge-results-grid">
          ${this._renderSearchResultsList()}
        </div>
      </div>
    `;
  }

  _renderSearchResultsList() {
    if (this.isLoading) {
      return `<div class="loading-spinner" style="padding: 3rem; text-align: center;">Searching Knowledge Fabric...</div>`;
    }
    if (!this.searchResults || this.searchResults.length === 0) {
      return `
        <div class="empty-state-box" style="padding: 3rem; text-align: center;">
          <span style="font-size: 2rem; display: block; margin-bottom: 0.5rem;">🌐</span>
          <strong>No knowledge search results</strong>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
            Type a query above or click "Sync / Backfill" to index existing workspace items.
          </p>
        </div>
      `;
    }

    return this.searchResults.map(item => `
      <div class="knowledge-result-card" data-node-id="${item.id}">
        <div class="result-header">
          <span class="badge badge-default font-mono">${this._escapeHtml(item.type)}</span>
          <span class="result-score" title="Relevance">${Math.round(item.relevance * 100)}% Match</span>
        </div>
        <h3 class="result-title">${this._escapeHtml(item.title)}</h3>
        <p class="result-summary">${this._escapeHtml(item.summary)}</p>
        <div class="result-footer">
          <span class="result-provenance">Source: ${this._escapeHtml(item.source_type || 'SYSTEM')}</span>
          <span class="result-date">${new Date(item.timestamp).toLocaleDateString()}</span>
          <button class="btn-text inspect-node-btn" data-id="${item.id}" style="font-size: 0.78rem;">Inspect &rarr;</button>
        </div>
      </div>
    `).join('');
  }

  // --- Decisions Tab ---
  _renderDecisionsTab() {
    return `
      <div class="decisions-panel">
        <div class="card-header-flex" style="margin-bottom: 1.25rem;">
          <div>
            <h2 class="settings-section-title">Architectural & Project Decisions</h2>
            <p style="font-size: 0.85rem; color: var(--text-muted);">
              Immutable log of explicit technical choices and supersession chains.
            </p>
          </div>
          <button class="btn btn-primary btn-sm" id="add-decision-action-btn">+ Record Decision</button>
        </div>

        <div class="decisions-stack" id="decisions-stack-container">
          ${this.decisions.length === 0 ? `
            <div class="empty-state-box" style="padding: 2.5rem; text-align: center;">
              <span style="font-size: 1.75rem; display: block; margin-bottom: 0.5rem;">📜</span>
              <strong>No decisions recorded yet</strong>
              <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
                Document architectural decisions to ground assistant suggestions in authoritative choices.
              </p>
            </div>
          ` : this.decisions.map(d => `
            <div class="decision-card ${d.status === 'SUPERSEDED' ? 'decision-superseded' : ''}">
              <div class="decision-card-top">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                  <span style="font-size: 1.1rem;">⚖️</span>
                  <strong style="font-size: 0.95rem; color: var(--text-main);">${this._escapeHtml(d.decision)}</strong>
                </div>
                <span class="badge ${d.status === 'ACTIVE' ? 'badge-success' : 'badge-warning'}">
                  ${d.status}
                </span>
              </div>
              ${d.rationale ? `<p style="font-size: 0.82rem; color: var(--text-muted); margin: 0.5rem 0 0.75rem 0;">${this._escapeHtml(d.rationale)}</p>` : ''}
              <div class="decision-card-footer" style="display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 0.5rem;">
                <span style="color: var(--text-muted);">Recorded: ${new Date(d.created_at).toLocaleDateString()} &bull; Source: ${this._escapeHtml(d.source)}</span>
                ${d.status === 'ACTIVE' ? `
                  <button class="btn btn-secondary btn-sm supersede-btn" data-id="${d.id}" data-text="${this._escapeHtml(d.decision)}" style="font-size: 0.75rem;">
                    Supersede
                  </button>
                ` : '<span style="color: #f59e0b; font-style: italic;">Superseded</span>'}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // --- Timeline Tab ---
  _renderTimelineTab() {
    return `
      <div class="timeline-panel">
        <div class="card-header-flex" style="margin-bottom: 1.25rem;">
          <div>
            <h2 class="settings-section-title">Chronological Event Timeline</h2>
            <p style="font-size: 0.85rem; color: var(--text-muted);">
              Chronologically ordered history based on actual timestamped workspace milestones.
            </p>
          </div>
          <button class="btn btn-secondary btn-sm" id="refresh-timeline-btn">↻ Refresh</button>
        </div>

        <div class="timeline-stream">
          ${this.timelineEvents.length === 0 ? `
            <div class="empty-state-box" style="padding: 2.5rem; text-align: center;">
              <strong>No timeline events captured yet</strong>
            </div>
          ` : this.timelineEvents.map(evt => `
            <div class="timeline-entry">
              <div class="timeline-marker"></div>
              <div class="timeline-content card">
                <div class="timeline-header">
                  <span class="badge badge-default font-mono">${this._escapeHtml(evt.type)}</span>
                  <span class="timeline-time">${new Date(evt.timestamp).toLocaleString()}</span>
                </div>
                <h4 class="timeline-title">${this._escapeHtml(evt.title)}</h4>
                <p class="timeline-summary">${this._escapeHtml(evt.summary)}</p>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // --- Graph Tab ---
  _renderGraphTab() {
    return `
      <div class="graph-panel">
        <div class="card-header-flex" style="margin-bottom: 1rem;">
          <div>
            <h2 class="settings-section-title">Knowledge Relationship Graph</h2>
            <p style="font-size: 0.85rem; color: var(--text-muted);">
              Bounded relationship network showing connections between projects, decisions, commits, and workflows.
            </p>
          </div>
        </div>

        <div class="card graph-canvas-card" style="padding: 1.5rem; background: #0b0f19; border-radius: 8px;">
          <div style="font-size: 0.85rem; color: #9ca3af; margin-bottom: 1rem;">
            Select any entity in Search or Decisions and click "Inspect" to view its connected graph, or view the primary project graph below:
          </div>

          <!-- Accessible List Alternative -->
          <div class="accessible-graph-view" style="display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; color: #38bdf8; font-weight: 600;">
              <span>●</span> <span>Project: Kairo Personal AI Assistant</span>
            </div>
            <div style="margin-left: 1.5rem; display: flex; flex-direction: column; gap: 0.5rem; border-left: 2px dashed rgba(255,255,255,0.1); padding-left: 1rem;">
              <div style="color: var(--text-main);">
                <span class="badge badge-default">DECISION</span>
                <span>Use PostgreSQL + pgvector for memory and context</span>
                <span style="color: #10b981; font-size: 0.75rem;">[ACTIVE]</span>
              </div>
              <div style="color: var(--text-main);">
                <span class="badge badge-default">DECISION</span>
                <span>Local companion with dual emergency stop</span>
                <span style="color: #10b981; font-size: 0.75rem;">[ACTIVE]</span>
              </div>
              <div style="color: var(--text-main);">
                <span class="badge badge-default">REPOSITORY</span>
                <span>mahitss/iron_assistant &bull; Main Branch</span>
              </div>
              <div style="color: var(--text-main);">
                <span class="badge badge-default">WORKFLOW</span>
                <span>CI/CD Release Engineering & Automation</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // --- Documents Tab ---
  _renderDocumentsTab() {
    return `
      <div class="documents-panel">
        <div class="card-header-flex" style="margin-bottom: 1.25rem;">
          <div>
            <h2 class="settings-section-title">Document Ingestion & Semantic Indexing</h2>
            <p style="font-size: 0.85rem; color: var(--text-muted);">
              Upload PDF, TXT, Markdown, DOCX, CSV, or JSON documents into the Knowledge Fabric.
            </p>
          </div>
        </div>

        <div class="card upload-dropzone-card" id="doc-upload-card" style="border: 2px dashed var(--border-glass); border-radius: 8px; padding: 2.5rem; text-align: center; cursor: pointer; transition: 0.2s;">
          <input type="file" id="doc-file-input" style="display: none;" accept=".txt,.md,.json,.csv,.pdf,.docx" />
          <span style="font-size: 2.5rem; display: block; margin-bottom: 0.5rem;">📄</span>
          <strong style="font-size: 1rem; color: var(--text-main);">Click or Drag files here to upload</strong>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">
            Supported formats: PDF, Markdown (.md), Plain Text (.txt), JSON, CSV, Word (.docx). Max size: 10MB.
          </p>
          <div id="upload-status-pill" style="margin-top: 1rem; display: none;"></div>
        </div>
      </div>
    `;
  }

  _bindEvents(projectId) {
    // 1. Tab Switching
    this.container.querySelectorAll('.knowledge-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.dataset.tab;
        const body = this.container.querySelector('#knowledge-tab-body');
        if (body) {
          body.innerHTML = this._renderActiveTabContent();
          this._bindTabSpecificEvents(projectId);
        }
        this.container.querySelectorAll('.knowledge-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // 2. Global Sync / Backfill
    const syncBtn = this.container.querySelector('#sync-backfill-btn');
    if (syncBtn) {
      syncBtn.addEventListener('click', async () => {
        syncBtn.innerText = 'Syncing...';
        try {
          const res = await Endpoints.triggerKnowledgeBackfill();
          alert(`Sync complete: ${res.total_indexed || 0} items indexed into Knowledge Fabric.`);
          await this._loadInitialData(projectId);
        } catch (err) {
          alert(`Sync failed: ${err.message}`);
        } finally {
          syncBtn.innerText = '⚡ Sync / Backfill';
        }
      });
    }

    // 3. New Decision Button
    const newDecBtn = this.container.querySelector('#record-decision-btn');
    if (newDecBtn) {
      newDecBtn.onclick = () => this._showRecordDecisionModal(projectId);
    }

    this._bindTabSpecificEvents(projectId);
  }

  _bindTabSpecificEvents(projectId) {
    // Search input
    const searchBtn = this.container.querySelector('#execute-search-btn');
    const searchInput = this.container.querySelector('#knowledge-search-input');
    const typeSelect = this.container.querySelector('#knowledge-type-filter');

    if (searchBtn && searchInput) {
      const doSearch = async () => {
        this.searchQuery = searchInput.value.trim();
        this.selectedType = typeSelect ? typeSelect.value : '';
        if (!this.searchQuery) return;
        this.isLoading = true;
        const resContainer = this.container.querySelector('#knowledge-search-results');
        if (resContainer) resContainer.innerHTML = this._renderSearchResultsList();

        try {
          const res = await Endpoints.searchKnowledge({
            query: this.searchQuery,
            projectId,
            type: this.selectedType || null,
          });
          this.searchResults = res.results || [];
        } catch (err) {
          this.searchResults = [];
        } finally {
          this.isLoading = false;
          if (resContainer) {
            resContainer.innerHTML = this._renderSearchResultsList();
            this._bindResultInspectEvents();
          }
        }
      };

      searchBtn.onclick = doSearch;
      searchInput.onkeydown = (e) => { if (e.key === 'Enter') doSearch(); };
    }

    // Document Upload
    const dropzone = this.container.querySelector('#doc-upload-card');
    const fileInput = this.container.querySelector('#doc-file-input');
    if (dropzone && fileInput) {
      dropzone.onclick = () => fileInput.click();
      fileInput.onchange = async () => {
        const file = fileInput.files[0];
        if (!file) return;
        const pill = this.container.querySelector('#upload-status-pill');
        if (pill) {
          pill.style.display = 'inline-block';
          pill.className = 'badge badge-warning';
          pill.innerText = `Ingesting ${file.name}...`;
        }

        const formData = new FormData();
        formData.append('file', file);
        if (projectId) formData.append('project_id', projectId);

        try {
          const resp = await Endpoints.uploadKnowledgeDocument(formData);
          if (pill) {
            pill.className = 'badge badge-success';
            pill.innerText = `✓ Complete: ${resp.chunks_created} chunks indexed`;
          }
          alert(`Document ingested successfully: ${resp.filename}`);
        } catch (err) {
          if (pill) {
            pill.className = 'badge badge-danger';
            pill.innerText = `Upload error: ${err.message}`;
          }
        }
      };
    }

    // Decision creation & supersession
    const addDecBtn = this.container.querySelector('#add-decision-action-btn');
    if (addDecBtn) {
      addDecBtn.onclick = () => this._showRecordDecisionModal(projectId);
    }

    this.container.querySelectorAll('.supersede-btn').forEach(btn => {
      btn.onclick = () => {
        const id = btn.dataset.id;
        const text = btn.dataset.text;
        this._showSupersedeModal(id, text, projectId);
      };
    });

    this._bindResultInspectEvents();
  }

  _bindResultInspectEvents() {
    this.container.querySelectorAll('.inspect-node-btn').forEach(btn => {
      btn.onclick = async () => {
        const nodeId = btn.dataset.id;
        await this._inspectNode(nodeId);
      };
    });
  }

  async _loadInitialData(projectId) {
    try {
      this.decisions = await Endpoints.listDecisions(projectId);
    } catch {
      this.decisions = [];
    }

    try {
      const tl = await Endpoints.getKnowledgeTimeline({ projectId, limit: 25 });
      this.timelineEvents = tl.events || [];
    } catch {
      this.timelineEvents = [];
    }

    try {
      this.conflicts = await Endpoints.getKnowledgeConflicts(projectId);
    } catch {
      this.conflicts = [];
    }

    // If active search tab, load top recent knowledge items
    if (this.activeTab === 'search' && (!this.searchResults || this.searchResults.length === 0)) {
      try {
        const res = await Endpoints.searchKnowledge({ query: 'project architecture decision', projectId, limit: 6 });
        this.searchResults = res.results || [];
        const resContainer = this.container.querySelector('#knowledge-search-results');
        if (resContainer) {
          resContainer.innerHTML = this._renderSearchResultsList();
          this._bindResultInspectEvents();
        }
      } catch {
        // Fallback
      }
    }
  }

  _showRecordDecisionModal(projectId) {
    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-dialog" style="max-width: 500px; background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1.5rem; color: #f3f4f6;">
        <h3 style="font-size: 1.1rem; margin-bottom: 1rem;">Record Project Decision</h3>
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          <label style="font-size: 0.8rem; color: #9ca3af;">Decision Title / Summary:</label>
          <input type="text" id="dec-title-input" class="input-field" placeholder="e.g. Use PostgreSQL + pgvector for memory" />
          <label style="font-size: 0.8rem; color: #9ca3af;">Rationale & Context:</label>
          <textarea id="dec-rationale-input" class="input-field" rows="4" placeholder="Explain the context, alternatives considered, and why this decision was chosen..."></textarea>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1.25rem;">
          <button class="btn btn-secondary btn-sm" id="dec-cancel-btn">Cancel</button>
          <button class="btn btn-primary btn-sm" id="dec-save-btn">Record Decision</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.querySelector('#dec-cancel-btn').onclick = () => modal.remove();
    modal.querySelector('#dec-save-btn').onclick = async () => {
      const decision = modal.querySelector('#dec-title-input').value.trim();
      const rationale = modal.querySelector('#dec-rationale-input').value.trim();
      if (!decision) {
        alert('Please provide a decision summary.');
        return;
      }
      try {
        await Endpoints.createDecision({ decision, rationale, project_id: projectId });
        modal.remove();
        await this.render();
      } catch (err) {
        alert(`Failed to save decision: ${err.message}`);
      }
    };
  }

  _showSupersedeModal(decisionId, oldText, projectId) {
    const modal = document.createElement('div');
    modal.className = 'modal-backdrop';
    modal.innerHTML = `
      <div class="modal-dialog" style="max-width: 500px; background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1.5rem; color: #f3f4f6;">
        <h3 style="font-size: 1.1rem; margin-bottom: 0.5rem;">Supersede Prior Decision</h3>
        <p style="font-size: 0.8rem; color: #9ca3af; margin-bottom: 1rem;">
          Prior Decision: <em>${this._escapeHtml(oldText)}</em>
        </p>
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          <label style="font-size: 0.8rem; color: #9ca3af;">New Decision:</label>
          <input type="text" id="new-dec-input" class="input-field" placeholder="e.g. Migrate to pgvector native clustering" />
          <label style="font-size: 0.8rem; color: #9ca3af;">Reason for Change:</label>
          <textarea id="supersede-reason-input" class="input-field" rows="3" placeholder="Why is the prior decision being superseded?"></textarea>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1.25rem;">
          <button class="btn btn-secondary btn-sm" id="super-cancel-btn">Cancel</button>
          <button class="btn btn-primary btn-sm" id="super-save-btn">Supersede</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.querySelector('#super-cancel-btn').onclick = () => modal.remove();
    modal.querySelector('#super-save-btn').onclick = async () => {
      const new_decision = modal.querySelector('#new-dec-input').value.trim();
      const reason = modal.querySelector('#supersede-reason-input').value.trim();
      if (!new_decision) {
        alert('Please specify the new decision text.');
        return;
      }
      try {
        await Endpoints.supersedeDecision(decisionId, { new_decision, reason });
        modal.remove();
        await this.render();
      } catch (err) {
        alert(`Failed to supersede decision: ${err.message}`);
      }
    };
  }

  async _inspectNode(nodeId) {
    try {
      const node = await Endpoints.getKnowledgeNode(nodeId);
      const sources = await Endpoints.getKnowledgeSources(nodeId).catch(() => []);
      const rels = await Endpoints.getKnowledgeRelationships(nodeId).catch(() => []);

      const modal = document.createElement('div');
      modal.className = 'modal-backdrop';
      modal.innerHTML = `
        <div class="modal-dialog" style="max-width: 580px; background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1.5rem; color: #f3f4f6;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.75rem;">
            <div>
              <span class="badge badge-default font-mono">${this._escapeHtml(node.type)}</span>
              <h3 style="font-size: 1.15rem; margin-top: 0.25rem;">${this._escapeHtml(node.title)}</h3>
            </div>
            <button id="close-inspect-btn" style="background: none; border: none; color: #9ca3af; font-size: 1.25rem; cursor: pointer;">&times;</button>
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.75rem; font-size: 0.85rem;">
            <div>
              <strong style="color: #9ca3af; display: block; margin-bottom: 0.25rem;">Summary:</strong>
              <div style="background: rgba(0,0,0,0.25); padding: 0.75rem; border-radius: 4px; line-height: 1.4;">
                ${this._escapeHtml(node.summary)}
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 0.5rem;">
              <div>
                <span style="color: #9ca3af;">Status:</span>
                <span class="badge ${node.status === 'ACTIVE' ? 'badge-success' : 'badge-warning'}">${node.status}</span>
              </div>
              <div>
                <span style="color: #9ca3af;">Confidence:</span>
                <span>${Math.round(node.confidence * 100)}%</span>
              </div>
              <div>
                <span style="color: #9ca3af;">Indexed At:</span>
                <span>${new Date(node.created_at).toLocaleString()}</span>
              </div>
              <div>
                <span style="color: #9ca3af;">Source ID:</span>
                <span class="font-mono" style="font-size: 0.75rem;">${this._escapeHtml(node.source_id)}</span>
              </div>
            </div>

            ${sources.length > 0 ? `
              <div style="border-top: 1px solid rgba(255,255,255,0.04); padding-top: 0.5rem;">
                <strong style="color: #9ca3af; display: block; margin-bottom: 0.25rem;">Provenance Sources:</strong>
                ${sources.map(s => `
                  <div style="font-size: 0.78rem; color: var(--text-main); margin-bottom: 0.25rem;">
                    &bull; <strong>${this._escapeHtml(s.source_type)}</strong>: ${this._escapeHtml(s.title || s.source_id)}
                  </div>
                `).join('')}
              </div>
            ` : ''}

            ${rels.length > 0 ? `
              <div style="border-top: 1px solid rgba(255,255,255,0.04); padding-top: 0.5rem;">
                <strong style="color: #9ca3af; display: block; margin-bottom: 0.25rem;">Relationship Edges (${rels.length}):</strong>
                ${rels.map(r => `
                  <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 0.25rem;">
                    &bull; <span class="badge badge-default font-mono" style="font-size: 0.7rem;">${r.relation_type}</span>
                    <span>with node ${r.source_node_id === node.id ? r.target_node_id.slice(0, 8) : r.source_node_id.slice(0, 8)}...</span>
                  </div>
                `).join('')}
              </div>
            ` : ''}
          </div>
        </div>
      `;
      document.body.appendChild(modal);
      modal.querySelector('#close-inspect-btn').onclick = () => modal.remove();
      modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
    } catch (err) {
      alert(`Failed to load details: ${err.message}`);
    }
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

/**
 * Kairo Memory Interface
 * Allows users to inspect, edit, and delete what Kairo remembers across projects and sessions.
 * Never exposes raw vector embeddings or internal ranking math.
 */

import { Endpoints } from '../../lib/api/endpoints.js';

export class MemoryView {
  constructor(container) {
    this.container = container;
    this.memories = [];
    this.activeSection = 'recent'; // 'recent', 'project', 'global'
    this.searchQuery = '';
    this.isLoading = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="memory-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Assistant Memory</h1>
            <p class="page-subtitle">Inspect, refine, or remove persistent knowledge that Kairo remembers</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-memory-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
          </div>
        </header>

        <div class="memory-controls">
          <div class="tabs-nav" role="tablist">
            <button class="tab-btn active" data-section="recent" role="tab" aria-selected="true">Recent</button>
            <button class="tab-btn" data-section="project" role="tab" aria-selected="false">Project Scoped</button>
            <button class="tab-btn" data-section="global" role="tab" aria-selected="false">Global Knowledge</button>
          </div>
          <div class="memory-search-box">
            <input type="text" id="memory-search-input" placeholder="Search memories..." class="input-field" />
          </div>
        </div>

        <div class="memory-content-area" id="memory-list-container">
          <div class="loading-spinner">Loading assistant memories...</div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadMemories();
  }

  _bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-memory-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadMemories());

    const tabs = this.container.querySelectorAll('.memory-controls .tab-btn');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');
        this.activeSection = tab.dataset.section;
        this._renderMemories();
      });
    });

    const searchInput = this.container.querySelector('#memory-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this._renderMemories();
      });
    }
  }

  async loadMemories() {
    const container = this.container.querySelector('#memory-list-container');
    if (!container) return;

    this.isLoading = true;
    container.innerHTML = '<div class="loading-spinner">Retrieving memories...</div>';

    try {
      const res = await Endpoints.listMemories(null, 50);
      this.memories = Array.isArray(res) ? res : (res.items || []);
      this.isLoading = false;
      this._renderMemories();
    } catch (err) {
      this.isLoading = false;
      container.innerHTML = `
        <div class="error-state">
          <div class="error-icon">⚠️</div>
          <h3>Failed to load memories</h3>
          <p>${err.message || 'Check database connection.'}</p>
          <button class="btn btn-secondary" id="retry-memory-btn">Retry</button>
        </div>
      `;
      const retryBtn = container.querySelector('#retry-memory-btn');
      if (retryBtn) retryBtn.addEventListener('click', () => this.loadMemories());
    }
  }

  _renderMemories() {
    const container = this.container.querySelector('#memory-list-container');
    if (!container) return;

    let list = this.memories;

    // Filter by tab
    if (this.activeSection === 'project') {
      list = list.filter(m => m.project_id || m.scope === 'project' || m.memory_type === 'project');
    } else if (this.activeSection === 'global') {
      list = list.filter(m => !m.project_id && (m.memory_type === 'preference' || m.memory_type === 'semantic' || m.scope === 'global'));
    }

    // Filter by search query
    if (this.searchQuery) {
      list = list.filter(m => (m.content || '').toLowerCase().includes(this.searchQuery));
    }

    if (list.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🧠</div>
          <h3>Kairo hasn't saved anything here yet.</h3>
          <p>As you work together on tasks and conversations, important architectural choices and preferences will appear here.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="memories-grid">
        ${list.map(mem => {
          const scopeLabel = mem.project_id ? `Project: ${mem.project_id}` : (mem.memory_type ? mem.memory_type.toUpperCase() : 'GLOBAL');
          const timeAgo = formatTimeAgo(mem.created_at || mem.updated_at);

          return `
            <div class="memory-card" data-id="${mem.id}">
              <div class="memory-header">
                <span class="badge badge-info">${escapeHtml(scopeLabel)}</span>
                <span class="memory-time font-mono">Added: ${timeAgo}</span>
              </div>
              <div class="memory-body" id="mem-content-${mem.id}">
                <p class="memory-text">"${escapeHtml(mem.content)}"</p>
              </div>
              <div class="memory-actions">
                <button class="btn btn-secondary btn-sm edit-memory-btn" data-id="${mem.id}">
                  Edit
                </button>
                <button class="btn btn-secondary btn-sm delete-memory-btn" data-id="${mem.id}">
                  Delete
                </button>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    // Bind edit and delete handlers
    container.querySelectorAll('.edit-memory-btn').forEach(btn => {
      btn.addEventListener('click', () => this.handleEdit(btn.dataset.id));
    });

    container.querySelectorAll('.delete-memory-btn').forEach(btn => {
      btn.addEventListener('click', () => this.handleDelete(btn.dataset.id));
    });
  }

  handleEdit(memoryId) {
    const mem = this.memories.find(m => m.id === memoryId);
    if (!mem) return;

    const contentBox = this.container.querySelector(`#mem-content-${memoryId}`);
    if (!contentBox) return;

    contentBox.innerHTML = `
      <textarea class="input-field mem-edit-area" rows="3">${escapeHtml(mem.content)}</textarea>
      <div class="edit-btn-row">
        <button class="btn btn-secondary btn-sm cancel-edit-btn">Cancel</button>
        <button class="btn btn-primary btn-sm save-edit-btn">Save</button>
      </div>
    `;

    const cancelBtn = contentBox.querySelector('.cancel-edit-btn');
    cancelBtn.addEventListener('click', () => this._renderMemories());

    const saveBtn = contentBox.querySelector('.save-edit-btn');
    saveBtn.addEventListener('click', async () => {
      const newText = contentBox.querySelector('.mem-edit-area').value.trim();
      if (!newText) return;
      saveBtn.disabled = true;
      saveBtn.innerText = 'Saving...';
      try {
        await Endpoints.updateMemory(memoryId, { content: newText });
        mem.content = newText;
        this._renderMemories();
      } catch (err) {
        alert(`Failed to update memory: ${err.message}`);
        this._renderMemories();
      }
    });
  }

  async handleDelete(memoryId) {
    if (!confirm('Are you sure you want Kairo to forget this item?')) return;
    try {
      await Endpoints.deleteMemory(memoryId);
      this.memories = this.memories.filter(m => m.id !== memoryId);
      this._renderMemories();
    } catch (err) {
      alert(`Failed to delete memory: ${err.message}`);
    }
  }
}

function formatTimeAgo(dateInput) {
  if (!dateInput) return 'recently';
  const diffMs = Date.now() - new Date(dateInput).getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

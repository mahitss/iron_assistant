/**
 * Kairo Memory & Learning Interface (Task 29)
 * Comprehensive Memory, Preference, Correction, and Experience Management Dashboard.
 * 
 * Supports:
 * - Memories (persistent facts & statements)
 * - Preferences (explicit user/project preferences, safe & non-sensitive)
 * - Corrections (explicit scoped corrections with supersession)
 * - Experience (task outcomes, successes, failures, bounded metadata)
 * - Feedback (user ratings, comments, and audit)
 * - Learning Candidates (human-in-the-loop review pipeline)
 * - User Control: Experience Learning ON/OFF toggle
 * - Safe Structured Data Export
 */

import { Endpoints } from '../../lib/api/endpoints.js';

export class MemoryView {
  constructor(container) {
    this.container = container;
    this.activeTab = 'memories'; // 'memories', 'preferences', 'corrections', 'experience', 'feedback', 'candidates'
    this.memories = [];
    this.preferences = [];
    this.corrections = [];
    this.experiences = [];
    this.feedbacks = [];
    this.candidates = [];
    this.searchQuery = '';
    this.isLoading = false;
    const stored = typeof localStorage !== 'undefined' && localStorage ? localStorage.getItem('kairo_learning_enabled') : null;
    this.isLearningEnabled = stored !== 'false';
  }

  async render() {
    this.container.innerHTML = `
      <div class="memory-view">
        <header class="section-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <div>
            <h1 class="page-title">Memory & Learning</h1>
            <p class="page-subtitle">Inspect, refine, or remove persistent knowledge, scoped preferences, and task experience</p>
          </div>
          <div class="header-actions" style="display: flex; align-items: center; gap: 0.75rem;">
            <!-- User Learning Control (Section 38) -->
            <label class="learning-toggle-label" style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; background: var(--bg-surface, #1e293b); padding: 0.35rem 0.75rem; border-radius: 9999px; border: 1px solid var(--border-color, #334155); cursor: pointer;" title="Toggle whether assistant learns from task outcomes and feedback">
              <span>Experience Learning:</span>
              <input type="checkbox" id="learning-toggle-chk" ${this.isLearningEnabled ? 'checked' : ''} style="cursor: pointer;" />
              <strong id="learning-status-txt" style="color: ${this.isLearningEnabled ? '#10b981' : '#94a3b8'};">
                ${this.isLearningEnabled ? 'Active' : 'Disabled'}
              </strong>
            </label>

            <button class="btn btn-secondary btn-sm" id="export-learning-btn" title="Safe structured export of memories, preferences, and experiences">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
              Export Data
            </button>

            <button class="btn btn-secondary btn-sm" id="refresh-memory-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
          </div>
        </header>

        <div class="memory-controls" style="margin-top: 1rem;">
          <div class="tabs-nav" role="tablist" style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button class="tab-btn ${this.activeTab === 'memories' ? 'active' : ''}" data-tab="memories" role="tab">Memories</button>
            <button class="tab-btn ${this.activeTab === 'preferences' ? 'active' : ''}" data-tab="preferences" role="tab">Preferences</button>
            <button class="tab-btn ${this.activeTab === 'corrections' ? 'active' : ''}" data-tab="corrections" role="tab">Corrections</button>
            <button class="tab-btn ${this.activeTab === 'experience' ? 'active' : ''}" data-tab="experience" role="tab">Experience</button>
            <button class="tab-btn ${this.activeTab === 'feedback' ? 'active' : ''}" data-tab="feedback" role="tab">Feedback</button>
            <button class="tab-btn ${this.activeTab === 'candidates' ? 'active' : ''}" data-tab="candidates" role="tab">Learning Candidates</button>
          </div>
          <div class="memory-search-box" style="margin-top: 0.75rem;">
            <input type="text" id="memory-search-input" placeholder="Search across ${this.activeTab}..." class="input-field" value="${escapeHtml(this.searchQuery)}" />
          </div>
        </div>

        <div class="memory-content-area" id="memory-tab-container" style="margin-top: 1rem;">
          <div class="loading-spinner">Loading...</div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadActiveTabData();
  }

  _bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-memory-btn');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadActiveTabData());

    const exportBtn = this.container.querySelector('#export-learning-btn');
    if (exportBtn) exportBtn.addEventListener('click', () => this.handleExport());

    const toggleChk = this.container.querySelector('#learning-toggle-chk');
    if (toggleChk) {
      toggleChk.addEventListener('change', (e) => {
        this.isLearningEnabled = e.target.checked;
        if (typeof localStorage !== 'undefined' && localStorage) {
          localStorage.setItem('kairo_learning_enabled', this.isLearningEnabled ? 'true' : 'false');
        }
        const txt = this.container.querySelector('#learning-status-txt');
        if (txt) {
          txt.innerText = this.isLearningEnabled ? 'Active' : 'Disabled';
          txt.style.color = this.isLearningEnabled ? '#10b981' : '#94a3b8';
        }
      });
    }

    const tabs = this.container.querySelectorAll('.memory-controls .tab-btn');
    tabs.forEach(tab => {
      tab.addEventListener('click', async () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        this.activeTab = tab.dataset.tab;
        const searchInput = this.container.querySelector('#memory-search-input');
        if (searchInput) searchInput.placeholder = `Search across ${this.activeTab}...`;
        await this.loadActiveTabData();
      });
    });

    const searchInput = this.container.querySelector('#memory-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this._renderCurrentTabContent();
      });
    }
  }

  async loadActiveTabData() {
    const container = this.container.querySelector('#memory-tab-container');
    if (!container) return;

    this.isLoading = true;
    container.innerHTML = '<div class="loading-spinner">Retrieving records...</div>';

    try {
      if (this.activeTab === 'memories') {
        const res = await Endpoints.listMemories(null, 50);
        this.memories = Array.isArray(res) ? res : (res.items || []);
      } else if (this.activeTab === 'preferences') {
        const res = await Endpoints.listPreferences();
        this.preferences = Array.isArray(res) ? res : [];
      } else if (this.activeTab === 'corrections') {
        const res = await Endpoints.listExperiences({ type: 'USER_CORRECTION' });
        this.corrections = Array.isArray(res) ? res : [];
      } else if (this.activeTab === 'experience') {
        const res = await Endpoints.listExperiences();
        this.experiences = Array.isArray(res) ? res : [];
      } else if (this.activeTab === 'feedback') {
        const res = await Endpoints.listFeedback();
        this.feedbacks = Array.isArray(res) ? res : [];
      } else if (this.activeTab === 'candidates') {
        const res = await Endpoints.listLearningCandidates();
        this.candidates = Array.isArray(res) ? res : [];
      }
      this.isLoading = false;
      this._renderCurrentTabContent();
    } catch (err) {
      this.isLoading = false;
      container.innerHTML = `
        <div class="error-state">
          <div class="error-icon">⚠️</div>
          <h3>Failed to load ${this.activeTab}</h3>
          <p>${escapeHtml(err.message || 'Check database connection.')}</p>
          <button class="btn btn-secondary btn-sm" id="retry-tab-btn">Retry</button>
        </div>
      `;
      const retryBtn = container.querySelector('#retry-tab-btn');
      if (retryBtn) retryBtn.addEventListener('click', () => this.loadActiveTabData());
    }
  }

  _renderCurrentTabContent() {
    if (this.activeTab === 'memories') this._renderMemories();
    else if (this.activeTab === 'preferences') this._renderPreferences();
    else if (this.activeTab === 'corrections') this._renderCorrections();
    else if (this.activeTab === 'experience') this._renderExperiences();
    else if (this.activeTab === 'feedback') this._renderFeedbacks();
    else if (this.activeTab === 'candidates') this._renderCandidates();
  }

  // --- 1. Memories Tab ---
  _renderMemories() {
    const container = this.container.querySelector('#memory-tab-container');
    if (!container) return;

    let list = this.memories;
    if (this.searchQuery) {
      list = list.filter(m => (m.content || '').toLowerCase().includes(this.searchQuery));
    }

    if (list.length === 0) {
      container.innerHTML = this._emptyStateHtml('No memories found', 'Explicit long-term memories will appear here.');
      return;
    }

    container.innerHTML = `
      <div class="memories-grid">
        ${list.map(mem => `
          <div class="memory-card" data-id="${mem.id}">
            <div class="memory-header">
              <span class="badge badge-info">${escapeHtml(mem.project_id ? `Project: ${mem.project_id}` : (mem.memory_type || 'GLOBAL').toUpperCase())}</span>
              <span class="memory-time font-mono">${formatTimeAgo(mem.created_at || mem.updated_at)}</span>
            </div>
            <div class="memory-body" id="mem-content-${mem.id}">
              <p class="memory-text">"${escapeHtml(mem.content)}"</p>
            </div>
            <div class="memory-actions">
              <button class="btn btn-secondary btn-sm delete-mem-btn" data-id="${mem.id}">Delete</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.querySelectorAll('.delete-mem-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Forget this memory?')) return;
        try {
          await Endpoints.deleteMemory(btn.dataset.id);
          this.memories = this.memories.filter(m => m.id !== btn.dataset.id);
          this._renderMemories();
        } catch (e) {
          alert('Failed to delete: ' + e.message);
        }
      });
    });
  }

  // --- 2. Preferences Tab ---
  _renderPreferences() {
    const container = this.container.querySelector('#memory-tab-container');
    if (!container) return;

    let list = this.preferences;
    if (this.searchQuery) {
      list = list.filter(p => p.key.toLowerCase().includes(this.searchQuery) || JSON.stringify(p.value).toLowerCase().includes(this.searchQuery));
    }

    const newPrefForm = `
      <div class="card" style="background: var(--bg-surface, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
        <h4 style="margin-top: 0; font-size: 0.9rem;">+ Add Explicit User Preference</h4>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem;">
          <input type="text" id="new-pref-key" placeholder="Key (e.g. preferred_language)" class="input-field" style="flex: 1; min-width: 150px;" />
          <input type="text" id="new-pref-val" placeholder="Value (e.g. Python)" class="input-field" style="flex: 1; min-width: 150px;" />
          <select id="new-pref-scope" class="input-field" style="width: 120px;">
            <option value="USER">User</option>
            <option value="PROJECT">Project</option>
            <option value="GLOBAL">Global</option>
          </select>
          <button class="btn btn-primary btn-sm" id="save-new-pref-btn">Save Preference</button>
        </div>
      </div>
    `;

    if (list.length === 0) {
      container.innerHTML = newPrefForm + this._emptyStateHtml('No preferences configured', 'Durable, safe user preferences will appear here.');
      this._bindNewPrefEvents(container);
      return;
    }

    container.innerHTML = newPrefForm + `
      <div class="memories-grid">
        ${list.map(pref => `
          <div class="memory-card" data-id="${pref.id}">
            <div class="memory-header">
              <span class="badge badge-success">${escapeHtml(pref.scope)}</span>
              <span class="badge badge-secondary">${escapeHtml(pref.confidence)}</span>
              <span class="memory-time font-mono">${formatTimeAgo(pref.updated_at)}</span>
            </div>
            <div class="memory-body">
              <strong style="color: var(--text-main); font-family: monospace;">${escapeHtml(pref.key)}</strong>
              <p class="memory-text" style="margin-top: 0.25rem;">${escapeHtml(typeof pref.value === 'object' ? JSON.stringify(pref.value) : String(pref.value))}</p>
            </div>
            <div class="memory-actions">
              <button class="btn btn-secondary btn-sm delete-pref-btn" data-key="${pref.key}" data-scope="${pref.scope}">Delete</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    this._bindNewPrefEvents(container);

    container.querySelectorAll('.delete-pref-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm(`Delete preference '${btn.dataset.key}'?`)) return;
        try {
          await Endpoints.deletePreference(btn.dataset.key, btn.dataset.scope);
          this.preferences = this.preferences.filter(p => p.key !== btn.dataset.key);
          this._renderPreferences();
        } catch (e) {
          alert('Failed to delete preference: ' + e.message);
        }
      });
    });
  }

  _bindNewPrefEvents(container) {
    const saveBtn = container.querySelector('#save-new-pref-btn');
    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        const key = container.querySelector('#new-pref-key').value.trim();
        const val = container.querySelector('#new-pref-val').value.trim();
        const scope = container.querySelector('#new-pref-scope').value;
        if (!key || !val) {
          alert('Please enter key and value');
          return;
        }
        try {
          saveBtn.disabled = true;
          saveBtn.innerText = 'Saving...';
          const created = await Endpoints.setPreference({ key, value: val, scope, source: 'USER_EXPLICIT' });
          this.preferences.unshift(created);
          this._renderPreferences();
        } catch (e) {
          alert('Failed to save preference: ' + e.message);
          saveBtn.disabled = false;
          saveBtn.innerText = 'Save Preference';
        }
      });
    }
  }

  // --- 3. Corrections Tab ---
  _renderCorrections() {
    const container = this.container.querySelector('#memory-tab-container');
    if (!container) return;

    let list = this.corrections;
    if (this.searchQuery) {
      list = list.filter(c => c.summary.toLowerCase().includes(this.searchQuery));
    }

    if (list.length === 0) {
      container.innerHTML = this._emptyStateHtml('No corrections recorded', 'Explicit user corrections ("No, use SQLite for this project") will appear here.');
      return;
    }

    container.innerHTML = `
      <div class="memories-grid">
        ${list.map(cor => {
          const isStale = cor.status === 'STALE' || cor.status === 'SUPERSEDED';
          return `
            <div class="memory-card" data-id="${cor.id}" style="opacity: ${isStale ? '0.65' : '1.0'};">
              <div class="memory-header">
                <span class="badge ${isStale ? 'badge-secondary' : 'badge-warning'}">${escapeHtml(cor.status)}</span>
                <span class="badge badge-info">${escapeHtml(cor.scope)}</span>
                <span class="memory-time font-mono">${formatTimeAgo(cor.created_at)}</span>
              </div>
              <div class="memory-body">
                <p class="memory-text" style="font-weight: 500;">"${escapeHtml(cor.summary)}"</p>
                ${cor.evidence && cor.evidence.correction ? `
                  <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.25rem;">
                    Correction: ${escapeHtml(cor.evidence.correction)}
                  </p>
                ` : ''}
              </div>
              <div class="memory-actions">
                <button class="btn btn-secondary btn-sm delete-cor-btn" data-id="${cor.id}">Delete</button>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    container.querySelectorAll('.delete-cor-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Delete this correction?')) return;
        try {
          await Endpoints.deleteExperience(btn.dataset.id);
          this.corrections = this.corrections.filter(c => c.id !== btn.dataset.id);
          this._renderCorrections();
        } catch (e) {
          alert('Failed to delete correction: ' + e.message);
        }
      });
    });
  }

  // --- 4. Experience Tab (Section 68) ---
  _renderExperiences() {
    const container = this.container.querySelector('#memory-tab-container');
    if (!container) return;

    let list = this.experiences;
    if (this.searchQuery) {
      list = list.filter(e => e.summary.toLowerCase().includes(this.searchQuery) || e.type.toLowerCase().includes(this.searchQuery));
    }

    if (list.length === 0) {
      container.innerHTML = this._emptyStateHtml('No experiences recorded', 'Task execution outcomes and workflow observations will appear here.');
      return;
    }

    container.innerHTML = `
      <div class="memories-grid">
        ${list.map(exp => {
          const isSuccess = exp.type === 'TASK_SUCCESS';
          const isFailure = exp.type === 'TASK_FAILURE';
          const typeBadge = isSuccess ? 'badge-success' : (isFailure ? 'badge-danger' : 'badge-info');

          return `
            <div class="memory-card" data-id="${exp.id}">
              <div class="memory-header">
                <span class="badge ${typeBadge}">${escapeHtml(exp.type)}</span>
                <span class="badge badge-secondary">${escapeHtml(exp.status)}</span>
                <span class="memory-time font-mono">${formatTimeAgo(exp.created_at)}</span>
              </div>
              <div class="memory-body">
                <p class="memory-text" style="font-weight: 500;">${escapeHtml(exp.summary)}</p>
                <div style="margin-top: 0.5rem; font-size: 0.78rem; color: var(--text-muted); display: flex; gap: 1rem; flex-wrap: wrap;">
                  <span>Source: <strong>${escapeHtml(exp.source)}</strong></span>
                  <span>Scope: <strong>${escapeHtml(exp.scope)}</strong></span>
                  <span>Confidence: <strong>${escapeHtml(exp.confidence)}</strong></span>
                  ${exp.project_id ? `<span>Project: <strong>${escapeHtml(exp.project_id)}</strong></span>` : ''}
                </div>
              </div>
              <div class="memory-actions">
                <button class="btn btn-secondary btn-sm delete-exp-btn" data-id="${exp.id}">Delete</button>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    container.querySelectorAll('.delete-exp-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Delete this experience item?')) return;
        try {
          await Endpoints.deleteExperience(btn.dataset.id);
          this.experiences = this.experiences.filter(e => e.id !== btn.dataset.id);
          this._renderExperiences();
        } catch (e) {
          alert('Failed to delete experience: ' + e.message);
        }
      });
    });
  }

  // --- 5. Feedback Tab ---
  _renderFeedbacks() {
    const container = this.container.querySelector('#memory-tab-container');
    if (!container) return;

    let list = this.feedbacks;
    if (this.searchQuery) {
      list = list.filter(f => (f.comment || '').toLowerCase().includes(this.searchQuery) || (f.correction || '').toLowerCase().includes(this.searchQuery));
    }

    if (list.length === 0) {
      container.innerHTML = this._emptyStateHtml('No feedback submitted', 'Responses you rate with 👍 or 👎 will appear here.');
      return;
    }

    container.innerHTML = `
      <div class="memories-grid">
        ${list.map(fb => {
          const icon = fb.feedback_type === 'POSITIVE' ? '👍' : (fb.feedback_type === 'NEGATIVE' ? '👎' : '✏️');
          return `
            <div class="memory-card" data-id="${fb.id}">
              <div class="memory-header">
                <span class="badge ${fb.feedback_type === 'POSITIVE' ? 'badge-success' : 'badge-warning'}">${icon} ${escapeHtml(fb.feedback_type)}</span>
                ${fb.rating ? `<span class="badge badge-secondary">★ ${fb.rating}/5</span>` : ''}
                <span class="memory-time font-mono">${formatTimeAgo(fb.created_at)}</span>
              </div>
              <div class="memory-body">
                ${fb.comment ? `<p class="memory-text">"${escapeHtml(fb.comment)}"</p>` : ''}
                ${fb.correction ? `<p style="font-size: 0.8rem; color: #38bdf8; margin-top: 0.25rem;">Correction: ${escapeHtml(fb.correction)}</p>` : ''}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // --- 6. Learning Candidates Tab (Section 69) ---
  _renderCandidates() {
    const container = this.container.querySelector('#memory-tab-container');
    if (!container) return;

    let list = this.candidates;
    if (this.searchQuery) {
      list = list.filter(c => c.proposed_change.toLowerCase().includes(this.searchQuery));
    }

    if (list.length === 0) {
      container.innerHTML = this._emptyStateHtml('No learning candidates', 'System proposals generated from task failures and feedback patterns awaiting engineering review will appear here.');
      return;
    }

    container.innerHTML = `
      <div class="memories-grid">
        ${list.map(cand => `
          <div class="memory-card" data-id="${cand.id}">
            <div class="memory-header">
              <span class="badge badge-primary">${escapeHtml(cand.status)}</span>
              <span class="badge badge-secondary">${escapeHtml(cand.confidence)}</span>
              <span class="memory-time font-mono">${formatTimeAgo(cand.created_at)}</span>
            </div>
            <div class="memory-body">
              <strong style="color: var(--text-main);">${escapeHtml(cand.proposed_change)}</strong>
              <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.5rem;">
                <span>Source Event: <code>${escapeHtml(cand.source_event)}</code></span>
              </div>
            </div>
            ${cand.status === 'PROPOSED' ? `
              <div class="memory-actions">
                <button class="btn btn-primary btn-sm accept-cand-btn" data-id="${cand.id}">Accept (Add to Eval)</button>
                <button class="btn btn-secondary btn-sm reject-cand-btn" data-id="${cand.id}">Reject</button>
              </div>
            ` : `
              <div class="memory-actions">
                <span style="font-size: 0.78rem; color: var(--text-muted);">Reviewed by ${escapeHtml(cand.reviewer_id || 'human')}</span>
              </div>
            `}
          </div>
        `).join('')}
      </div>
    `;

    container.querySelectorAll('.accept-cand-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await Endpoints.reviewLearningCandidate(btn.dataset.id, 'ACCEPTED', 'Accepted for regression benchmark');
          await this.loadActiveTabData();
        } catch (e) {
          alert('Failed to review candidate: ' + e.message);
        }
      });
    });

    container.querySelectorAll('.reject-cand-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await Endpoints.reviewLearningCandidate(btn.dataset.id, 'REJECTED', 'Rejected during engineering review');
          await this.loadActiveTabData();
        } catch (e) {
          alert('Failed to reject candidate: ' + e.message);
        }
      });
    });
  }

  async handleExport() {
    try {
      const data = await Endpoints.exportExperienceData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `kairo_experience_export_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert('Export failed: ' + e.message);
    }
  }

  _emptyStateHtml(title, subtitle) {
    return `
      <div class="empty-state">
        <div class="empty-icon">🧠</div>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(subtitle)}</p>
      </div>
    `;
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

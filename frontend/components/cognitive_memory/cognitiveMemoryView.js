/**
 * Autonomous Cognitive Memory, Experience Consolidation & Lifelong Learning Fabric View (Task 103)
 * Provides comprehensive inspection of durable memories, provenance, conflicts, patterns, and replay.
 */

import { cognitiveMemoryApi } from '../../lib/api/endpoints.js';

export class CognitiveMemoryView {
  constructor(containerId) {
    this.container = typeof document !== 'undefined'
      ? (typeof containerId === 'string' ? document.getElementById(containerId) : containerId)
      : (typeof containerId === 'object' ? containerId : null);
    this.activeTab = 'memories'; // memories, conflicts, patterns, stale, replay
    this.status = null;
    this.memories = [];
    this.conflicts = [];
    this.patterns = [];
    this.staleMemories = [];
    this.selectedMemory = null;
    this.selectedEvidence = null;
    this.selectedHistory = null;
    this.replayResult = null;
    this.searchQuery = '';
    this.selectedScope = '';
    this.isLoading = false;
    this.error = null;
  }

  async init() {
    if (!this.container) return;
    this.renderSkeleton();
    await this.loadData();
  }

  async loadData() {
    this.isLoading = true;
    this.error = null;
    try {
      const [stat, mems, confs, pats] = await Promise.all([
        cognitiveMemoryApi.getStatus().catch(() => null),
        cognitiveMemoryApi.listMemories(this.selectedScope || null, null, null, 100).catch(() => []),
        cognitiveMemoryApi.listConflicts().catch(() => []),
        cognitiveMemoryApi.listPatterns().catch(() => []),
      ]);

      this.status = stat || {
        total_experiences: 0,
        total_memories: 0,
        active_memories: 0,
        candidate_memories: 0,
        stale_memories: 0,
        superseded_memories: 0,
        active_conflicts: 0,
        patterns_discovered: 0,
        total_applications: 0,
        feedback_recorded: 0,
      };
      this.memories = mems || [];
      this.conflicts = confs || [];
      this.patterns = pats || [];
      this.staleMemories = this.memories.filter(m => m.freshness === 'STALE');

      if (this.memories.length > 0 && !this.selectedMemory) {
        await this.selectMemory(this.memories[0].memory_id);
      }
    } catch (err) {
      console.error('Failed to load cognitive memory data:', err);
      this.error = err.message || 'Failed to connect to Cognitive Memory Service';
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async selectMemory(memoryId) {
    this.selectedMemory = this.memories.find(m => m.memory_id === memoryId) || null;
    if (this.selectedMemory) {
      try {
        const [ev, hist] = await Promise.all([
          cognitiveMemoryApi.getMemoryEvidence(memoryId).catch(() => null),
          cognitiveMemoryApi.getMemoryHistory(memoryId).catch(() => null),
        ]);
        this.selectedEvidence = ev;
        this.selectedHistory = hist;
      } catch {
        this.selectedEvidence = null;
        this.selectedHistory = null;
      }
    }
    this.render();
  }

  async handleSearch(query) {
    this.searchQuery = query;
    if (!query.trim()) {
      await this.loadData();
      return;
    }
    this.isLoading = true;
    try {
      this.memories = await cognitiveMemoryApi.searchMemories({
        query: query.trim(),
        scope: this.selectedScope || 'PROJECT',
        limit: 50,
      });
      if (this.memories.length > 0) {
        await this.selectMemory(this.memories[0].memory_id);
      } else {
        this.selectedMemory = null;
      }
    } catch (err) {
      this.error = 'Search failed: ' + err.message;
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async revalidateSelected() {
    if (!this.selectedMemory) return;
    this.isLoading = true;
    try {
      await cognitiveMemoryApi.revalidateMemory(this.selectedMemory.memory_id);
      await this.loadData();
    } catch (err) {
      this.error = 'Revalidation failed: ' + err.message;
      this.render();
    }
  }

  async invalidateSelected() {
    if (!this.selectedMemory) return;
    this.isLoading = true;
    try {
      await cognitiveMemoryApi.invalidateMemory(this.selectedMemory.memory_id, 'USER_INVALIDATION_UI');
      await this.loadData();
    } catch (err) {
      this.error = 'Invalidation failed: ' + err.message;
      this.render();
    }
  }

  async runReplay() {
    this.isLoading = true;
    try {
      this.replayResult = await cognitiveMemoryApi.replayMemories();
      this.activeTab = 'replay';
    } catch (err) {
      this.error = 'Deterministic replay failed: ' + err.message;
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async createSnapshot() {
    this.isLoading = true;
    try {
      const snap = await cognitiveMemoryApi.createSnapshot();
      alert(`Immutable snapshot created: ${snap.snapshot_id}`);
      await this.loadData();
    } catch (err) {
      this.error = 'Snapshot creation failed: ' + err.message;
      this.render();
    }
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  renderSkeleton() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="cognitive-memory-view loading-state">
        <div class="kairo-panel-header">
          <h2>🧠 Cognitive Memory & Lifelong Learning Fabric</h2>
          <span class="badge badge-info">Initializing...</span>
        </div>
        <div class="skeleton-loader" style="height: 300px; margin: 20px 0;"></div>
      </div>
    `;
  }

  render() {
    if (!this.container) return;

    const stat = this.status || {};
    const conflictColor = (stat.active_conflicts || 0) > 0 ? 'badge-danger' : 'badge-success';
    const staleColor = (stat.stale_memories || 0) > 0 ? 'badge-warning' : 'badge-success';

    let contentHtml = '';
    switch (this.activeTab) {
      case 'memories':
        contentHtml = this.renderMemoriesTab();
        break;
      case 'conflicts':
        contentHtml = this.renderConflictsTab();
        break;
      case 'patterns':
        contentHtml = this.renderPatternsTab();
        break;
      case 'stale':
        contentHtml = this.renderStaleTab();
        break;
      case 'replay':
        contentHtml = this.renderReplayTab();
        break;
      default:
        contentHtml = this.renderMemoriesTab();
    }

    this.container.innerHTML = `
      <div class="cognitive-memory-view">
        <!-- Header -->
        <div class="view-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
          <div>
            <h1 style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.25rem 0;">
              🧠 Cognitive Memory & Lifelong Learning Fabric
            </h1>
            <p style="font-size: 0.875rem; color: var(--text-secondary); margin: 0;">
              Evidence-based experience consolidation, scope isolation, and anti-hallucination knowledge fabric.
            </p>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button class="kairo-btn kairo-btn-secondary" id="btn-snapshot">📸 Create Snapshot</button>
            <button class="kairo-btn kairo-btn-primary" id="btn-run-replay">🔄 Replay Evolution</button>
            <button class="kairo-btn kairo-btn-secondary" id="btn-refresh">↻ Refresh</button>
          </div>
        </div>

        ${this.error ? `<div class="alert alert-danger" style="margin-bottom: 1rem;">${this.error}</div>` : ''}

        <!-- Metrics Grid -->
        <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem;">
          <div class="stat-card" style="background: var(--surface-secondary); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; color: var(--text-muted);">EXPERIENCES</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: var(--text-primary);">${stat.total_experiences ?? 0}</div>
          </div>
          <div class="stat-card" style="background: var(--surface-secondary); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; color: var(--text-muted);">TOTAL MEMORIES</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: var(--text-primary);">${stat.total_memories ?? 0}</div>
          </div>
          <div class="stat-card" style="background: var(--surface-secondary); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; color: var(--text-muted);">ACTIVE MEMORIES</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: #10b981;">${stat.active_memories ?? 0}</div>
          </div>
          <div class="stat-card" style="background: var(--surface-secondary); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; color: var(--text-muted);">CANDIDATES</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: #3b82f6;">${stat.candidate_memories ?? 0}</div>
          </div>
          <div class="stat-card" style="background: var(--surface-secondary); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; color: var(--text-muted);">STALE</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: ${(stat.stale_memories || 0) > 0 ? '#f59e0b' : '#10b981'};">${stat.stale_memories ?? 0}</div>
          </div>
          <div class="stat-card" style="background: var(--surface-secondary); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; color: var(--text-muted);">CONFLICTS</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: ${(stat.active_conflicts || 0) > 0 ? '#ef4444' : '#10b981'};">${stat.active_conflicts ?? 0}</div>
          </div>
          <div class="stat-card" style="background: var(--surface-secondary); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; color: var(--text-muted);">PATTERNS</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: #8b5cf6;">${stat.patterns_discovered ?? 0}</div>
          </div>
          <div class="stat-card" style="background: var(--surface-secondary); padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; color: var(--text-muted);">APPLICATIONS</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: var(--text-primary);">${stat.total_applications ?? 0}</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs-nav" style="display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-color); margin-bottom: 1rem;">
          <button class="tab-btn ${this.activeTab === 'memories' ? 'active' : ''}" data-tab="memories" style="padding: 0.5rem 1rem; background: none; border: none; border-bottom: 2px solid ${this.activeTab === 'memories' ? 'var(--primary-color, #3b82f6)' : 'transparent'}; color: ${this.activeTab === 'memories' ? 'var(--text-primary)' : 'var(--text-muted)'}; cursor: pointer; font-weight: 600;">
            📚 Memory Explorer (${this.memories.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'conflicts' ? 'active' : ''}" data-tab="conflicts" style="padding: 0.5rem 1rem; background: none; border: none; border-bottom: 2px solid ${this.activeTab === 'conflicts' ? 'var(--primary-color, #3b82f6)' : 'transparent'}; color: ${this.activeTab === 'conflicts' ? 'var(--text-primary)' : 'var(--text-muted)'}; cursor: pointer; font-weight: 600;">
            ⚔️ Conflicts (${this.conflicts.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'patterns' ? 'active' : ''}" data-tab="patterns" style="padding: 0.5rem 1rem; background: none; border: none; border-bottom: 2px solid ${this.activeTab === 'patterns' ? 'var(--primary-color, #3b82f6)' : 'transparent'}; color: ${this.activeTab === 'patterns' ? 'var(--text-primary)' : 'var(--text-muted)'}; cursor: pointer; font-weight: 600;">
            🧩 Patterns (${this.patterns.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'stale' ? 'active' : ''}" data-tab="stale" style="padding: 0.5rem 1rem; background: none; border: none; border-bottom: 2px solid ${this.activeTab === 'stale' ? 'var(--primary-color, #3b82f6)' : 'transparent'}; color: ${this.activeTab === 'stale' ? 'var(--text-primary)' : 'var(--text-muted)'}; cursor: pointer; font-weight: 600;">
            ⏳ Stale & Revalidation (${this.staleMemories.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'replay' ? 'active' : ''}" data-tab="replay" style="padding: 0.5rem 1rem; background: none; border: none; border-bottom: 2px solid ${this.activeTab === 'replay' ? 'var(--primary-color, #3b82f6)' : 'transparent'}; color: ${this.activeTab === 'replay' ? 'var(--text-primary)' : 'var(--text-muted)'}; cursor: pointer; font-weight: 600;">
            🧬 Deterministic Replay
          </button>
        </div>

        <!-- Tab Content -->
        <div class="tab-content">
          ${contentHtml}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  renderMemoriesTab() {
    const selected = this.selectedMemory;
    const ev = this.selectedEvidence;
    const hist = this.selectedHistory;

    return `
      <div style="display: grid; grid-template-columns: 360px 1fr; gap: 1.25rem;">
        <!-- Left: Search & Memory List -->
        <div style="background: var(--surface-secondary); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 0.75rem;">
          <div style="display: flex; gap: 0.5rem;">
            <input type="text" id="memory-search-input" placeholder="Search memories..." value="${this.searchQuery}" style="flex: 1; padding: 0.4rem 0.6rem; border-radius: 4px; border: 1px solid var(--border-color); background: var(--surface-primary); color: var(--text-primary); font-size: 0.85rem;" />
            <button class="kairo-btn kairo-btn-secondary" id="btn-search-exec" style="padding: 0.4rem 0.8rem;">Go</button>
          </div>

          <div style="max-height: 560px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.5rem;">
            ${this.memories.length === 0 ? '<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 2rem 0;">No memories found.</div>' : ''}
            ${this.memories.map(m => {
              const isSel = selected && selected.memory_id === m.memory_id;
              const fColor = m.freshness === 'CURRENT' ? '#10b981' : (m.freshness === 'RECENT' ? '#3b82f6' : '#f59e0b');
              return `
                <div class="memory-card" data-id="${m.memory_id}" style="padding: 0.75rem; border-radius: 6px; border: 1px solid ${isSel ? 'var(--primary-color, #3b82f6)' : 'var(--border-color)'}; background: ${isSel ? 'rgba(59, 130, 246, 0.08)' : 'var(--surface-primary)'}; cursor: pointer; transition: all 0.15s ease;">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                    <span style="font-size: 0.75rem; font-weight: 700; color: var(--primary-color, #3b82f6);">${m.memory_type}</span>
                    <span style="font-size: 0.7rem; padding: 1px 6px; border-radius: 4px; background: rgba(0,0,0,0.2); color: ${fColor}; font-weight: 600;">${m.freshness}</span>
                  </div>
                  <div style="font-size: 0.85rem; color: var(--text-primary); margin-bottom: 0.35rem; line-height: 1.3;">
                    ${m.content.length > 80 ? m.content.substring(0, 80) + '...' : m.content}
                  </div>
                  <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-muted);">
                    <span>Scope: ${m.scope}</span>
                    <span>Conf: ${(m.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <!-- Right: Memory Detail & Inspection -->
        <div style="background: var(--surface-secondary); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border-color);">
          ${selected ? `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
              <div>
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                  <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0;">${selected.memory_id}</h3>
                  <span class="badge" style="background: rgba(59, 130, 246, 0.2); color: #3b82f6; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px;">v${selected.version}</span>
                  <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px;">${selected.lifecycle_state}</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">
                  Observed: ${selected.observed_at} | Last Verified: ${selected.last_verified_at || 'Never'}
                </div>
              </div>
              <div style="display: flex; gap: 0.5rem;">
                <button class="kairo-btn kairo-btn-secondary" id="btn-revalidate" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">Revalidate</button>
                <button class="kairo-btn kairo-btn-secondary" id="btn-invalidate" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; color: #ef4444;">Retire</button>
              </div>
            </div>

            <!-- Content Banner -->
            <div style="background: var(--surface-primary); padding: 1rem; border-radius: 6px; border-left: 4px solid #3b82f6; margin-bottom: 1.25rem;">
              <div style="font-size: 0.95rem; color: var(--text-primary); line-height: 1.4;">${selected.content}</div>
            </div>

            <!-- Attributes Grid -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1.25rem;">
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-color);">
                <div style="font-size: 0.7rem; color: var(--text-muted);">PROVENANCE & TRUST</div>
                <div style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem;">${selected.provenance_trust}</div>
              </div>
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-color);">
                <div style="font-size: 0.7rem; color: var(--text-muted);">SCOPE & TENANT</div>
                <div style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem;">${selected.scope} (${selected.scope_id || 'global'})</div>
              </div>
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--border-color);">
                <div style="font-size: 0.7rem; color: var(--text-muted);">EVIDENCE-BACKED CONFIDENCE</div>
                <div style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem;">${(selected.confidence * 100).toFixed(1)}%</div>
              </div>
            </div>

            <!-- Empirical Evidence Section -->
            <div style="margin-bottom: 1.25rem;">
              <h4 style="font-size: 0.9rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.5rem 0;">Empirical Evidence & Verifications</h4>
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4;">
                ${ev ? `
                  <div><strong>Evidence Summary:</strong> ${ev.confidence_evidence || 'Direct observation record'}</div>
                  <div style="margin-top: 0.35rem;"><strong>Source Experiences:</strong> ${ev.evidence_experience_ids?.join(', ') || 'Direct capture'}</div>
                  <div style="margin-top: 0.35rem;"><strong>Empirical Record:</strong> ${ev.useful_count} successful applications, ${ev.error_count} error feedback</div>
                ` : 'No direct empirical records attached.'}
              </div>
            </div>

            <!-- Lineage & Provenance Trail -->
            <div>
              <h4 style="font-size: 0.9rem; font-weight: 700; color: var(--text-primary); margin: 0 0 0.5rem 0;">Lineage & Provenance Trail</h4>
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px; font-size: 0.78rem; font-family: monospace; color: var(--text-secondary);">
                ${selected.provenance_trail?.length > 0 ? selected.provenance_trail.map(t => `<div>• ${t}</div>`).join('') : '<div>• Genesis capture record</div>'}
              </div>
            </div>
          ` : `
            <div style="text-align: center; padding: 4rem 0; color: var(--text-muted);">
              Select a memory to inspect its details, evidence, and provenance lineage.
            </div>
          `}
        </div>
      </div>
    `;
  }

  renderConflictsTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="font-size: 0.85rem; color: var(--text-secondary);">
          Active dialectic contradictions identified between durable memories. In accordance with invariant #21, <strong>Current World-State unconditionally overrules historical memory</strong>.
        </div>
        ${this.conflicts.length === 0 ? `
          <div style="text-align: center; padding: 3rem 0; background: var(--surface-secondary); border-radius: 8px; color: var(--text-muted);">
            ✨ No active memory conflicts detected. Memory fabric is coherent.
          </div>
        ` : this.conflicts.map(c => `
          <div style="background: var(--surface-secondary); border: 1px solid rgba(239, 68, 68, 0.3); border-left: 4px solid #ef4444; border-radius: 6px; padding: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
              <span style="font-weight: 700; color: #ef4444; font-size: 0.85rem;">[${c.conflict_id}] ${c.discrepancy_summary}</span>
              <span style="font-size: 0.75rem; color: var(--text-muted);">Entity: ${c.entity_reference} | Scope: ${c.scope}</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 0.5rem;">
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 4px;">
                <div style="font-size: 0.7rem; color: var(--text-muted); font-weight: 700;">MEMORY A: ${c.competing_memory_a}</div>
                <div style="font-size: 0.85rem; color: var(--text-primary); margin-top: 0.25rem;">${c.memory_a_claim || 'Claim record'}</div>
              </div>
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 4px;">
                <div style="font-size: 0.7rem; color: var(--text-muted); font-weight: 700;">MEMORY B: ${c.competing_memory_b}</div>
                <div style="font-size: 0.85rem; color: var(--text-primary); margin-top: 0.25rem;">${c.memory_b_claim || 'Claim record'}</div>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderPatternsTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="font-size: 0.85rem; color: var(--text-secondary);">
          Recurring patterns consolidated from clustered operational occurrences. <strong>Pattern ≠ Truth</strong> (patterns are candidate hypotheses).
        </div>
        ${this.patterns.length === 0 ? `
          <div style="text-align: center; padding: 3rem 0; background: var(--surface-secondary); border-radius: 8px; color: var(--text-muted);">
            No consolidated patterns discovered yet.
          </div>
        ` : this.patterns.map(p => `
          <div style="background: var(--surface-secondary); border: 1px solid var(--border-color); border-left: 4px solid #8b5cf6; border-radius: 6px; padding: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
              <span style="font-weight: 700; color: #8b5cf6; font-size: 0.95rem;">${p.title}</span>
              <span class="badge" style="background: rgba(139, 92, 246, 0.2); color: #8b5cf6; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px;">Recurrence: ${p.recurrence_count}x</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-primary); line-height: 1.4; margin-bottom: 0.5rem;">
              ${p.pattern_summary}
            </div>
            <div style="display: flex; gap: 1rem; font-size: 0.75rem; color: var(--text-muted);">
              <span>Confidence: ${(p.confidence * 100).toFixed(0)}%</span>
              <span>Scope: ${p.scope}</span>
              <span>Exceptions: ${p.known_exceptions?.length ? p.known_exceptions.join(', ') : 'None'}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderStaleTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="font-size: 0.85rem; color: var(--text-secondary);">
          Memories exceeding their temporal decay threshold or invalidated by environment drift. These require empirical revalidation before reasoning engine consumption.
        </div>
        ${this.staleMemories.length === 0 ? `
          <div style="text-align: center; padding: 3rem 0; background: var(--surface-secondary); border-radius: 8px; color: var(--text-muted);">
            ✨ All durable memories are current and fresh.
          </div>
        ` : this.staleMemories.map(m => `
          <div style="background: var(--surface-secondary); border: 1px solid rgba(245, 158, 11, 0.4); border-left: 4px solid #f59e0b; border-radius: 6px; padding: 1rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 700; color: #f59e0b; font-size: 0.85rem;">[${m.memory_id}] ${m.memory_type}</div>
              <div style="font-size: 0.85rem; color: var(--text-primary); margin-top: 0.25rem;">${m.content}</div>
              <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Observed at: ${m.observed_at} | Scope: ${m.scope}</div>
            </div>
            <button class="kairo-btn kairo-btn-primary btn-stale-reval" data-id="${m.memory_id}" style="padding: 0.35rem 0.8rem; font-size: 0.8rem;">
              Revalidate
            </button>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderReplayTab() {
    const res = this.replayResult;
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="font-size: 0.85rem; color: var(--text-secondary);">
          Deterministic historical replay of memory evolution. Reconstructs candidates, consolidations, and conflicts <strong>without triggering any external side-effects</strong>.
        </div>
        ${res ? `
          <div style="background: var(--surface-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
              <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin: 0;">Replay Simulation Result</h4>
              <span class="badge badge-success" style="background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem;">Completed (Zero Side-Effects)</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1rem;">
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px;">
                <div style="font-size: 0.7rem; color: var(--text-muted);">EXPERIENCES REPLAYED</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--text-primary);">${res.total_experiences_replayed}</div>
              </div>
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px;">
                <div style="font-size: 0.7rem; color: var(--text-muted);">CANDIDATES FORMED</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #3b82f6;">${res.candidates_formed}</div>
              </div>
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px;">
                <div style="font-size: 0.7rem; color: var(--text-muted);">MEMORIES CONSOLIDATED</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #10b981;">${res.memories_consolidated}</div>
              </div>
              <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px;">
                <div style="font-size: 0.7rem; color: var(--text-muted);">CONFLICTS DETECTED</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: #ef4444;">${res.conflicts_detected}</div>
              </div>
            </div>
            <div style="background: var(--surface-primary); padding: 0.75rem; border-radius: 6px; font-family: monospace; font-size: 0.75rem; color: var(--text-secondary); max-height: 240px; overflow-y: auto;">
              ${res.simulated_evolution?.length ? res.simulated_evolution.map(step => `<div>• [${step.timestamp}] ${step.event}: ${step.detail}</div>`).join('') : '<div>Zero mutations recorded in replay sequence.</div>'}
            </div>
          </div>
        ` : `
          <div style="text-align: center; padding: 4rem 0; background: var(--surface-secondary); border-radius: 8px; color: var(--text-muted);">
            Click "Replay Evolution" in the header to run a deterministic reconstruction of the memory graph.
          </div>
        `}
      </div>
    `;
  }

  attachEventListeners() {
    // Tabs
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        if (tab) this.setTab(tab);
      });
    });

    // Action buttons
    const btnRefresh = this.container.querySelector('#btn-refresh');
    if (btnRefresh) btnRefresh.addEventListener('click', () => this.loadData());

    const btnSnapshot = this.container.querySelector('#btn-snapshot');
    if (btnSnapshot) btnSnapshot.addEventListener('click', () => this.createSnapshot());

    const btnReplay = this.container.querySelector('#btn-run-replay');
    if (btnReplay) btnReplay.addEventListener('click', () => this.runReplay());

    const btnSearch = this.container.querySelector('#btn-search-exec');
    const searchInput = this.container.querySelector('#memory-search-input');
    if (btnSearch && searchInput) {
      btnSearch.addEventListener('click', () => this.handleSearch(searchInput.value));
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') this.handleSearch(searchInput.value);
      });
    }

    // Memory cards selection
    this.container.querySelectorAll('.memory-card').forEach(card => {
      card.addEventListener('click', () => {
        const mid = card.dataset.id;
        if (mid) this.selectMemory(mid);
      });
    });

    // Revalidate & Invalidate in detail view
    const btnReval = this.container.querySelector('#btn-revalidate');
    if (btnReval) btnReval.addEventListener('click', () => this.revalidateSelected());

    const btnInval = this.container.querySelector('#btn-invalidate');
    if (btnInval) btnInval.addEventListener('click', () => this.invalidateSelected());

    // Stale item revalidate
    this.container.querySelectorAll('.btn-stale-reval').forEach(btn => {
      btn.addEventListener('click', async () => {
        const mid = btn.dataset.id;
        if (mid) {
          await cognitiveMemoryApi.revalidateMemory(mid);
          await this.loadData();
        }
      });
    });
  }
}

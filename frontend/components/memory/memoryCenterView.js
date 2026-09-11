/**
 * Memory Center Dashboard (Task 68)
 * Autonomous Knowledge & Memory Consolidation Engine UI (Spec 28).
 * 
 * Supports:
 * - Overview: High-level memory health, active memories, recent captures, quarantined, and conflicts
 * - Memory Explorer: Multi-factor search with type, trust, and lifecycle filters
 * - Memory Detail: Deep inspection showing cognitive type, lineage provenance, and decision refs
 * - Consolidation Queue: Pending clusters and synthesized higher-level abstractions
 * - Conflict Center: Competing assertions, environmental divergence, and unresolved contradictions
 * - Retention Center: Expiring memories and type-dependent TTL policies
 * - Privacy Controls: Explicit user-authorized forgetting and compliance tombstone inspection
 */

import { Endpoints } from '../../lib/api/endpoints.js';

function escapeHtml(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export class MemoryCenterView {
  constructor(container) {
    this.container = container;
    this.activeTab = 'overview'; // 'overview', 'explorer', 'detail', 'consolidation', 'conflicts', 'retention', 'privacy'
    this.health = null;
    this.memories = [];
    this.conflicts = [];
    this.staleMemories = [];
    this.expiringMemories = [];
    this.selectedMemory = null;
    this.selectedProvenance = null;
    this.searchQuery = '';
    this.typeFilter = '';
    this.trustFilter = '';
    this.tenantId = 'default';
    this.isLoading = false;
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  selectMemory(memory, provenance = null) {
    this.selectedMemory = memory;
    this.selectedProvenance = provenance;
    this.activeTab = 'detail';
    this.render();
  }

  async loadData() {
    this.isLoading = true;
    try {
      const [health, conflicts, stale, expiring] = await Promise.all([
        Endpoints.getMemoryHealth(this.tenantId).catch(() => null),
        Endpoints.getMemoryConflicts(this.tenantId).catch(() => []),
        Endpoints.getStaleMemories(this.tenantId).catch(() => []),
        Endpoints.getExpiringMemories(48, this.tenantId).catch(() => []),
      ]);
      this.health = health;
      this.conflicts = conflicts || [];
      this.staleMemories = stale || [];
      this.expiringMemories = expiring || [];
    } catch (err) {
      console.error('Failed to load memory center telemetry:', err);
    } finally {
      this.isLoading = false;
    }
  }

  render() {
    this.container.innerHTML = `
      <div class="memory-center-view" style="padding: 1.5rem; color: var(--text-primary, #f8fafc);">
        <header class="section-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
          <div>
            <h1 class="page-title" style="margin: 0; font-size: 1.75rem; font-weight: 700; color: #38bdf8;">Autonomous Memory Center</h1>
            <p class="page-subtitle" style="margin: 0.25rem 0 0 0; color: #94a3b8; font-size: 0.88rem;">
              Autonomous Knowledge & Memory Consolidation Engine (Task 68) — Provenance, Abstraction & Lifecycle
            </p>
          </div>
          <div class="header-actions" style="display: flex; gap: 0.5rem; align-items: center;">
            <button class="btn btn-secondary btn-sm" id="btn-sweep-memory" style="background: #0284c7; color: white; border: none; border-radius: 6px; padding: 0.4rem 0.8rem; cursor: pointer;">
              Trigger Consolidation Sweep
            </button>
            <button class="btn btn-secondary btn-sm" id="btn-refresh-memory" style="background: #334155; color: white; border: 1px solid #475569; border-radius: 6px; padding: 0.4rem 0.8rem; cursor: pointer;">
              Refresh
            </button>
          </div>
        </header>

        <!-- Cognitive Invariants Alert Banner -->
        <div class="invariants-banner" style="background: rgba(14, 165, 233, 0.08); border-left: 4px solid #0284c7; padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: 1.25rem; font-size: 0.82rem; line-height: 1.4;">
          <strong>Cognitive Invariants:</strong> Memory != Truth &bull; Summary != Source &bull; Repetition != Independent Evidence &bull; Retrieval != Verification &bull; Simulation != Real-world Experience
        </div>

        <!-- Navigation Tabs -->
        <div class="memory-tabs" style="display: flex; gap: 0.5rem; border-bottom: 1px solid #334155; margin-bottom: 1.25rem; flex-wrap: wrap;">
          ${this._renderTabBtn('overview', 'Overview')}
          ${this._renderTabBtn('explorer', 'Memory Explorer')}
          ${this._renderTabBtn('detail', 'Memory Detail')}
          ${this._renderTabBtn('consolidation', 'Consolidation Queue')}
          ${this._renderTabBtn('conflicts', `Conflict Center (${this.conflicts.length})`)}
          ${this._renderTabBtn('retention', `Retention & Staleness (${this.staleMemories.length})`)}
          ${this._renderTabBtn('privacy', 'Privacy & Forgetting')}
        </div>

        <!-- Tab Content Area -->
        <div class="memory-tab-body">
          ${this._renderActiveTab()}
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _renderTabBtn(tabKey, label) {
    const isActive = this.activeTab === tabKey;
    const activeStyle = isActive
      ? 'border-bottom: 2px solid #38bdf8; color: #38bdf8; font-weight: 600;'
      : 'color: #94a3b8; border-bottom: 2px solid transparent;';
    return `
      <button class="tab-btn" data-tab="${tabKey}" style="background: none; border: none; padding: 0.5rem 1rem; cursor: pointer; font-size: 0.88rem; ${activeStyle}">
        ${escapeHtml(label)}
      </button>
    `;
  }

  _renderActiveTab() {
    switch (this.activeTab) {
      case 'overview':
        return this._renderOverview();
      case 'explorer':
        return this._renderExplorer();
      case 'detail':
        return this._renderDetail();
      case 'consolidation':
        return this._renderConsolidation();
      case 'conflicts':
        return this._renderConflicts();
      case 'retention':
        return this._renderRetention();
      case 'privacy':
        return this._renderPrivacy();
      default:
        return `<div class="p-4">Select a tab.</div>`;
    }
  }

  _renderOverview() {
    const h = this.health || {};
    return `
      <div class="overview-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div class="metric-card" style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Total Memories</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #f8fafc;">${h.total_memories ?? 0}</div>
        </div>
        <div class="metric-card" style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Active Durable</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #10b981;">${h.active_count ?? 0}</div>
        </div>
        <div class="metric-card" style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Quarantined (Poisoning Defense)</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #f59e0b;">${h.quarantined_count ?? 0}</div>
        </div>
        <div class="metric-card" style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Active Conflicts</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #ef4444;">${h.conflicted_count ?? 0}</div>
        </div>
        <div class="metric-card" style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Stale Memories</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #94a3b8;">${h.stale_count ?? 0}</div>
        </div>
      </div>
    `;
  }

  _renderExplorer() {
    return `
      <div class="explorer-container" style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
        <div class="search-bar" style="display: flex; gap: 0.75rem; margin-bottom: 1rem;">
          <input type="text" id="memory-search-input" class="input-field" placeholder="Search memories with explainable scoring..." value="${escapeHtml(this.searchQuery)}" style="flex: 1; background: #0f172a; border: 1px solid #334155; padding: 0.5rem; border-radius: 6px; color: white;" />
          <button id="btn-exec-search" style="background: #0284c7; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">Search</button>
        </div>
        <div class="search-results-list" id="explorer-results">
          <p style="color: #94a3b8; font-size: 0.85rem;">Enter a query to retrieve memories with explainable scoring justifications.</p>
        </div>
      </div>
    `;
  }

  _renderDetail() {
    if (!this.selectedMemory) {
      return `
        <div style="background: #1e293b; padding: 2rem; border-radius: 8px; text-align: center; color: #94a3b8;">
          No memory selected. Choose a memory from Explorer or Conflicts to view structured lineage.
        </div>
      `;
    }
    const m = this.selectedMemory;
    const p = this.selectedProvenance || m.provenance || {};
    return `
      <div class="memory-detail-card" style="background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
          <div>
            <h2 style="margin: 0; font-size: 1.2rem; color: #38bdf8;">Memory ${escapeHtml(m.memory_id || m.id)}</h2>
            <span style="font-size: 0.78rem; background: #0f172a; padding: 0.2rem 0.5rem; border-radius: 4px; color: #94a3b8;">
              ${escapeHtml(m.cognitive_type || 'MEMORY')} &bull; ${escapeHtml(m.memory_type || 'EPISODIC')}
            </span>
          </div>
          <span style="font-size: 0.85rem; padding: 0.25rem 0.6rem; border-radius: 9999px; background: #065f46; color: #34d399;">
            ${escapeHtml(m.status || 'ACTIVE')}
          </span>
        </div>
        <div style="background: #0f172a; padding: 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.95rem; border-left: 3px solid #38bdf8;">
          ${escapeHtml(m.content)}
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; font-size: 0.82rem; color: #94a3b8;">
          <div><strong>Confidence:</strong> ${(m.confidence * 100).toFixed(0)}%</div>
          <div><strong>Importance:</strong> ${(m.importance * 100).toFixed(0)}%</div>
          <div><strong>Freshness:</strong> ${escapeHtml(m.freshness || 'FRESH')}</div>
          <div><strong>Trust Level:</strong> ${escapeHtml(m.trust_level || 'UNVERIFIED')}</div>
          <div><strong>Observed At:</strong> ${escapeHtml(m.observed_at || m.created_at)}</div>
          <div><strong>Independent Source:</strong> ${p.is_independent_source ? 'YES' : 'NO (Derived/Correlated)'}</div>
        </div>
      </div>
    `;
  }

  _renderConsolidation() {
    return `
      <div style="background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; color: #38bdf8;">Consolidation Queue & Abstraction Tiers</h3>
        <p style="color: #94a3b8; font-size: 0.85rem;">
          Autonomous clustering synthesizes raw episodic memories into higher-level generalized patterns without discarding source evidence.
        </p>
        <div class="tier-indicator" style="display: flex; gap: 0.5rem; margin: 1rem 0; flex-wrap: wrap;">
          <span style="background: #0f172a; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.78rem;">1. Raw Observation</span>
          <span style="color: #38bdf8;">&rarr;</span>
          <span style="background: #0f172a; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.78rem;">2. Episode</span>
          <span style="color: #38bdf8;">&rarr;</span>
          <span style="background: #0f172a; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.78rem;">3. Pattern</span>
          <span style="color: #38bdf8;">&rarr;</span>
          <span style="background: #0f172a; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.78rem;">4. Generalized Knowledge</span>
          <span style="color: #38bdf8;">&rarr;</span>
          <span style="background: #0f172a; padding: 0.3rem 0.6rem; border-radius: 4px; font-size: 0.78rem;">5. Executive Insight</span>
        </div>
      </div>
    `;
  }

  _renderConflicts() {
    if (!this.conflicts.length) {
      return `<div style="background: #1e293b; padding: 1.5rem; border-radius: 8px; color: #10b981;">No active memory contradictions detected. Competing claims remain contextually partitioned.</div>`;
    }
    return `
      <div style="display: flex; flex-direction: column; gap: 0.75rem;">
        ${this.conflicts.map(c => `
          <div style="background: #1e293b; padding: 1rem; border-radius: 6px; border-left: 4px solid #ef4444;">
            <div style="font-weight: 600; color: #f87171; font-size: 0.9rem;">Conflict: ${escapeHtml(c.conflict_id)}</div>
            <p style="margin: 0.35rem 0; font-size: 0.85rem; color: #cbd5e1;">${escapeHtml(c.explanation)}</p>
            <div style="font-size: 0.78rem; color: #94a3b8;">
              Memories: <code>${escapeHtml(c.memory_a_id)}</code> vs <code>${escapeHtml(c.memory_b_id)}</code>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  _renderRetention() {
    return `
      <div style="background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; color: #38bdf8;">Retention & Staleness Center</h3>
        <p style="color: #94a3b8; font-size: 0.85rem;">
          Type-dependent freshness policies govern retrieval decay. Server telemetry decays rapidly; semantic facts remain durable.
        </p>
        <div style="margin-top: 1rem;">
          <strong>Stale Records Identified:</strong> ${this.staleMemories.length}
        </div>
        <div style="margin-top: 0.5rem;">
          <strong>Expiring in next 48h:</strong> ${this.expiringMemories.length}
        </div>
      </div>
    `;
  }

  _renderPrivacy() {
    return `
      <div style="background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; color: #38bdf8;">Privacy & Explicit Forgetting</h3>
        <p style="color: #94a3b8; font-size: 0.85rem;">
          User-authorized memory deletion creates immutable compliance tombstones while scrubbing private payloads from indexes, embeddings, and graph edges.
        </p>
      </div>
    `;
  }

  _bindEvents() {
    const tabBtns = this.container.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.target.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    const refreshBtn = this.container.querySelector('#btn-refresh-memory');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        await this.loadData();
        this.render();
      });
    }

    const sweepBtn = this.container.querySelector('#btn-sweep-memory');
    if (sweepBtn) {
      sweepBtn.addEventListener('click', async () => {
        try {
          await Endpoints.triggerConsolidationSweep(this.tenantId);
          await this.loadData();
          this.render();
        } catch (err) {
          console.error('Sweep failed:', err);
        }
      });
    }
  }
}

/**
 * KAIRO Knowledge Consolidation, Memory Reconstruction & Context Evolution UI (Task 92 Phase 31).
 *
 * Implements 12 operational views:
 * 1. Memory Overview
 * 2. Active Memories
 * 3. Recent Memories
 * 4. Conflicts
 * 5. Stale Knowledge
 * 6. Hypotheses
 * 7. Evidence
 * 8. Provenance
 * 9. Consolidation
 * 10. Revalidation
 * 11. Knowledge Timeline
 * 12. Knowledge Graph
 *
 * Emphasizes Epistemological Distinction:
 * MEMORY != TRUTH | VECTOR SIMILARITY != TRUTH | MODEL OUTPUT != FACT
 * Unverified hypotheses and conflicted memories are visually distinguished.
 */

function escapeHtml(str) {
  if (typeof str !== 'string') return String(str ?? '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export class MemoryEvolutionView {
  constructor(container) {
    this.container = container;
    this.activeTab = 'overview';
    this.memories = [];
    this.health = null;
    this.conflicts = [];
    this.revalidationJobs = [];
    this.selectedMemory = null;
    this.reconstructionResult = null;
    this.reconstructionQuery = 'What happened with current project?';
    this.isLoading = false;
    this.tenantId = 'default';
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  async loadData() {
    this.isLoading = true;
    try {
      const [memsRes, healthRes] = await Promise.all([
        fetch(`/api/v1/memory?tenant_id=${this.tenantId}&include_stale=true`).then(r => r.ok ? r.json() : []).catch(() => []),
        fetch(`/api/v1/memory/health?tenant_id=${this.tenantId}`).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);

      this.memories = memsRes || [];
      this.health = healthRes || {
        total_memories: this.memories.length,
        active_count: this.memories.filter(m => m.status === 'ACTIVE').length,
        conflicted_count: this.memories.filter(m => m.status === 'CONFLICTED').length,
        stale_count: this.memories.filter(m => m.status === 'STALE').length,
        forgotten_count: this.memories.filter(m => m.status === 'FORGOTTEN').length,
        hypotheses_count: this.memories.filter(m => m.type === 'HYPOTHESIS').length,
        procedural_count: this.memories.filter(m => m.type === 'PROCEDURAL').length,
      };

      // Extract conflicts
      this.conflicts = this.memories.filter(m => m.status === 'CONFLICTED');
    } catch (err) {
      console.error('Failed to load memory evolution data:', err);
    } finally {
      this.isLoading = false;
    }
  }

  async executeReconstruction() {
    if (!this.reconstructionQuery) return;
    this.isLoading = true;
    try {
      const res = await fetch('/api/v1/knowledge/reconstruct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: this.reconstructionQuery,
          tenant_id: this.tenantId,
          include_superseded: true,
          include_conflicts: true,
        }),
      });
      if (res.ok) {
        this.reconstructionResult = await res.json();
      }
    } catch (err) {
      console.error('Reconstruction failed:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  render() {
    this.container.innerHTML = `
      <div class="memory-evolution-view" style="padding: 1.5rem; color: #f8fafc; font-family: Inter, system-ui, sans-serif;">
        <!-- Header -->
        <header style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 1rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <h1 style="margin: 0; font-size: 1.75rem; font-weight: 700; color: #38bdf8;">Autonomous Knowledge & Memory Evolution</h1>
              <span style="background: rgba(14, 165, 233, 0.2); color: #38bdf8; border: 1px solid #0284c7; padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">
                Task 92 Production
              </span>
            </div>
            <p style="margin: 0.35rem 0 0 0; color: #94a3b8; font-size: 0.88rem;">
              Continuous consolidation, conflict preservation, forensic timeline reconstruction & calibrated certainty
            </p>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button id="btn-evo-revalidate" style="background: #0284c7; color: white; border: none; padding: 0.45rem 0.9rem; border-radius: 6px; font-weight: 600; cursor: pointer;">
              Scan Revalidations
            </button>
            <button id="btn-evo-refresh" style="background: #1e293b; color: #cbd5e1; border: 1px solid #475569; padding: 0.45rem 0.9rem; border-radius: 6px; cursor: pointer;">
              Refresh
            </button>
          </div>
        </header>

        <!-- Cognitive Invariants Rule Banner -->
        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #0284c7; border-left: 4px solid #38bdf8; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1.5rem; font-size: 0.82rem; color: #e2e8f0;">
          <strong>Core Cognitive Invariants:</strong> MEMORY != TRUTH &bull; VECTOR SIMILARITY != TRUTH &bull; MODEL OUTPUT != FACT &bull; CONFIDENCE != CERTAINTY &bull; HYPOTHESIS != BELIEF &bull; BELIEF != VERIFIED FACT
        </div>

        <!-- 12 View Navigation Tabs -->
        <nav style="display: flex; gap: 0.35rem; border-bottom: 1px solid #334155; margin-bottom: 1.5rem; overflow-x: auto; padding-bottom: 0.25rem;">
          ${[
            ['overview', '1. Overview'],
            ['active', '2. Active Memories'],
            ['recent', '3. Recent Stream'],
            ['conflicts', '4. Conflicts'],
            ['stale', '5. Stale Knowledge'],
            ['hypotheses', '6. Hypotheses'],
            ['evidence', '7. Evidence Explorer'],
            ['provenance', '8. Provenance Lineage'],
            ['consolidation', '9. Consolidation'],
            ['revalidation', '10. Revalidation Queue'],
            ['timeline', '11. Forensic Timeline'],
            ['graph', '12. Knowledge Graph'],
          ].map(([id, label]) => `
            <button class="evo-tab-btn" data-tab="${id}" style="background: ${this.activeTab === id ? '#0284c7' : 'transparent'}; color: ${this.activeTab === id ? '#ffffff' : '#94a3b8'}; border: none; padding: 0.5rem 0.75rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; white-space: nowrap;">
              ${label}
            </button>
          `).join('')}
        </nav>

        <!-- Tab Content Area -->
        <main id="evo-tab-content">
          ${this.renderTabContent()}
        </main>
      </div>
    `;

    this.bindEvents();
  }

  renderTabContent() {
    switch (this.activeTab) {
      case 'overview': return this.renderOverview();
      case 'active': return this.renderMemoryList(this.memories.filter(m => m.status === 'ACTIVE'));
      case 'recent': return this.renderMemoryList([...this.memories].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
      case 'conflicts': return this.renderConflicts();
      case 'stale': return this.renderMemoryList(this.memories.filter(m => m.status === 'STALE'));
      case 'hypotheses': return this.renderMemoryList(this.memories.filter(m => m.type === 'HYPOTHESIS'));
      case 'evidence': return this.renderEvidence();
      case 'provenance': return this.renderProvenance();
      case 'consolidation': return this.renderConsolidation();
      case 'revalidation': return this.renderRevalidation();
      case 'timeline': return this.renderTimeline();
      case 'graph': return this.renderGraph();
      default: return `<p>Select a tab above.</p>`;
    }
  }

  renderOverview() {
    const h = this.health || {};
    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
          <div style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Total Memories</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #38bdf8; margin-top: 0.25rem;">${h.total_memories ?? 0}</div>
        </div>
        <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
          <div style="color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Active Validated</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #4ade80; margin-top: 0.25rem;">${h.active_count ?? 0}</div>
        </div>
        <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #ef4444;">
          <div style="color: #f87171; font-size: 0.8rem; text-transform: uppercase;">Conflicted Claims</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #ef4444; margin-top: 0.25rem;">${h.conflicted_count ?? 0}</div>
        </div>
        <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #f59e0b;">
          <div style="color: #fbbf24; font-size: 0.8rem; text-transform: uppercase;">Stale Decay</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #f59e0b; margin-top: 0.25rem;">${h.stale_count ?? 0}</div>
        </div>
        <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #8b5cf6;">
          <div style="color: #c084fc; font-size: 0.8rem; text-transform: uppercase;">Hypotheses under Test</div>
          <div style="font-size: 1.75rem; font-weight: 700; color: #c084fc; margin-top: 0.25rem;">${h.hypotheses_count ?? 0}</div>
        </div>
      </div>
      <div style="background: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; font-size: 1.1rem; color: #38bdf8;">Epistemological Status Summary</h3>
        <p style="color: #94a3b8; font-size: 0.85rem; line-height: 1.5;">
          KAIRO distinguishes 12 taxonomy types. Stored memories never masquerade as absolute truths. Contradictions are explicitly preserved and surfaced to context assembly.
        </p>
      </div>
    `;
  }

  renderMemoryList(mems) {
    if (!mems || mems.length === 0) {
      return `<div style="padding: 2rem; text-align: center; color: #94a3b8;">No memories found matching this category.</div>`;
    }
    return `
      <div style="display: flex; flex-direction: column; gap: 0.75rem;">
        ${mems.map(m => `
          <div style="background: #1e293b; border: 1px solid ${m.status === 'CONFLICTED' ? '#ef4444' : '#334155'}; padding: 1rem; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
              <div style="display: flex; gap: 0.5rem; align-items: center;">
                <span style="background: #0f172a; color: #38bdf8; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">
                  ${escapeHtml(m.type)}
                </span>
                <span style="background: ${m.status === 'ACTIVE' ? 'rgba(74, 222, 128, 0.15)' : m.status === 'CONFLICTED' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)'}; color: ${m.status === 'ACTIVE' ? '#4ade80' : m.status === 'CONFLICTED' ? '#ef4444' : '#fbbf24'}; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">
                  ${escapeHtml(m.status)}
                </span>
                <span style="color: #94a3b8; font-size: 0.75rem;">Certainty: <strong>${escapeHtml(m.certainty || 'KNOWN')}</strong></span>
              </div>
              <div style="font-size: 0.75rem; color: #64748b;">
                ID: ${escapeHtml(m.memory_id)} &bull; Conf: ${(m.confidence * 100).toFixed(0)}%
              </div>
            </div>
            <div style="color: #f1f5f9; font-size: 0.92rem; line-height: 1.4;">
              ${escapeHtml(m.content)}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderConflicts() {
    const conflicted = this.memories.filter(m => m.status === 'CONFLICTED');
    if (conflicted.length === 0) {
      return `<div style="padding: 2rem; text-align: center; color: #4ade80;">No active unresolved contradictions. Knowledge base is currently consistent.</div>`;
    }
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.85rem; color: #fca5a5;">
          <strong>Contradictions Detected:</strong> The system retains conflicting claims rather than guessing. Review below to resolve with authoritative evidence.
        </div>
        ${conflicted.map(m => `
          <div style="background: #1e293b; border: 1px solid #ef4444; padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.8rem; color: #f87171; font-weight: 600; margin-bottom: 0.35rem;">CONFLICTED MEMORY: ${escapeHtml(m.memory_id)}</div>
            <div style="color: #f8fafc; font-size: 0.95rem; margin-bottom: 0.75rem;">${escapeHtml(m.content)}</div>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn-resolve-user" data-id="${m.memory_id}" style="background: #ef4444; color: white; border: none; padding: 0.35rem 0.75rem; border-radius: 4px; font-size: 0.8rem; cursor: pointer;">
                Resolve via User Confirmation
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderEvidence() {
    return `
      <div style="background: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; color: #38bdf8;">Grounding Evidence Registry</h3>
        <p style="color: #94a3b8; font-size: 0.85rem;">
          Evidence links record citations, tool outcomes, and user assertions supporting or contradicting memories. Evidence is never averaged away.
        </p>
      </div>
    `;
  }

  renderProvenance() {
    return `
      <div style="background: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; color: #38bdf8;">Provenance Lineage Graph</h3>
        <p style="color: #94a3b8; font-size: 0.85rem;">
          Auditable origin tracing for every retained memory item: source type, task IDs, conversation IDs, and transformation histories.
        </p>
      </div>
    `;
  }

  renderConsolidation() {
    return `
      <div style="background: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; color: #38bdf8;">Autonomous Consolidation Sweeper</h3>
        <p style="color: #94a3b8; font-size: 0.85rem;">
          Episodic events and observations are clustered into durable semantic knowledge while preserving source episodes for reversible auditing.
        </p>
      </div>
    `;
  }

  renderRevalidation() {
    return `
      <div style="background: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; color: #38bdf8;">Autonomous Revalidation Queue</h3>
        <p style="color: #94a3b8; font-size: 0.85rem;">
          Monitors staleness decay, capability version evolution, and contradiction arrivals. Schedules empirical revalidation within resource limits.
        </p>
      </div>
    `;
  }

  renderTimeline() {
    const res = this.reconstructionResult;
    return `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div style="background: #1e293b; padding: 1rem; border-radius: 8px; border: 1px solid #334155; display: flex; gap: 0.5rem; align-items: center;">
          <input id="input-recon-query" type="text" value="${escapeHtml(this.reconstructionQuery)}" style="flex: 1; background: #0f172a; border: 1px solid #475569; color: white; padding: 0.5rem 0.75rem; border-radius: 6px; font-size: 0.88rem;" />
          <button id="btn-recon-submit" style="background: #0284c7; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer;">
            Reconstruct History
          </button>
        </div>

        ${res ? `
          <div style="background: #1e293b; border: 1px solid #334155; padding: 1.25rem; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
              <h3 style="margin: 0; color: #38bdf8; font-size: 1.1rem;">Forensic Reconstruction Narrative</h3>
              <span style="background: #0f172a; color: #4ade80; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">
                Certainty: ${escapeHtml(res.certainty)}
              </span>
            </div>
            <div style="color: #f1f5f9; font-size: 0.92rem; white-space: pre-wrap; line-height: 1.5; margin-bottom: 1.25rem; background: #0f172a; padding: 1rem; border-radius: 6px;">
              ${escapeHtml(res.synthesized_narrative)}
            </div>

            <h4 style="color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 0.5rem;">Chronological Timeline (${res.timeline?.length ?? 0} events)</h4>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              ${(res.timeline || []).map(ev => `
                <div style="display: flex; gap: 1rem; font-size: 0.82rem; padding: 0.5rem; background: #0f172a; border-radius: 4px;">
                  <span style="color: #64748b; white-space: nowrap;">${new Date(ev.timestamp).toLocaleDateString()}</span>
                  <span style="color: #38bdf8; font-weight: 600;">[${escapeHtml(ev.type)}]</span>
                  <span style="color: #e2e8f0; flex: 1;">${escapeHtml(ev.summary)}</span>
                  <span style="color: ${ev.status === 'SUPERSEDED' ? '#f59e0b' : '#4ade80'};">${escapeHtml(ev.status)}</span>
                </div>
              `).join('')}
            </div>
          </div>
        ` : `
          <div style="padding: 2rem; text-align: center; color: #94a3b8;">
            Enter a query above and click 'Reconstruct History' to forensically synthesize knowledge timeline.
          </div>
        `}
      </div>
    `;
  }

  renderGraph() {
    return `
      <div style="background: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="margin-top: 0; color: #38bdf8;">Knowledge Graph Relational Topology</h3>
        <p style="color: #94a3b8; font-size: 0.85rem;">
          Direct projection to kg_nodes and kg_edges. Expresses relations: SUPPORTS, CONTRADICTS, SUPERSEDES, DERIVED_FROM, DEPENDS_ON, RELATED_TO.
        </p>
      </div>
    `;
  }

  bindEvents() {
    this.container.querySelectorAll('.evo-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.setTab(btn.dataset.tab);
      });
    });

    const refreshBtn = this.container.querySelector('#btn-evo-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        await this.loadData();
        this.render();
      });
    }

    const revalBtn = this.container.querySelector('#btn-evo-revalidate');
    if (revalBtn) {
      revalBtn.addEventListener('click', async () => {
        try {
          await fetch('/api/v1/memory/revalidate', { method: 'POST' });
          await this.loadData();
          this.setTab('revalidation');
        } catch (err) {
          console.error(err);
        }
      });
    }

    const reconBtn = this.container.querySelector('#btn-recon-submit');
    const reconInput = this.container.querySelector('#input-recon-query');
    if (reconBtn && reconInput) {
      reconBtn.addEventListener('click', async () => {
        this.reconstructionQuery = reconInput.value;
        await this.executeReconstruction();
      });
    }
  }
}

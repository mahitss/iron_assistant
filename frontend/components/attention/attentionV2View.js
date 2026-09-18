/**
 * AttentionV2View Component (Task 109)
 * Full interactive cockpit for Kairo Autonomous Attention, Cognitive Resource Allocation,
 * Focus Management & Interruption Governance Engine.
 */

import { attentionV2Api } from '../../lib/api/endpoints.js';

export class AttentionV2View {
  constructor(options = {}) {
    this.container = options.container || null;
    this.activeTab = options.initialTab || 'candidates';
    this.tenantId = options.tenantId || 'default';

    // Internal reactive state
    this.candidates = [];
    this.activeFocus = null;
    this.stack = [];
    this.health = null;
    this.snapshot = null;
    this.selectedCandidate = null;
    this.filterLifecycle = '';
    this.filterType = '';
    this.loading = false;
    this.errorMessage = null;
  }

  async init() {
    await this.refresh();
  }

  async refresh() {
    this.loading = true;
    this.errorMessage = null;
    try {
      const [cands, health, snap] = await Promise.all([
        attentionV2Api.listCandidates(this.filterLifecycle || null, this.filterType || null, 100),
        attentionV2Api.getHealth(),
        attentionV2Api.getSnapshot(),
      ]);

      this.candidates = Array.isArray(cands) ? cands : [];
      this.health = health || null;
      this.snapshot = snap || null;

      if (snap) {
        this.activeFocus = snap.active_session || null;
        this.stack = snap.nested_stack || [];
      }
    } catch (err) {
      this.errorMessage = `Failed to refresh Attention Engine: ${err.message || err}`;
      console.error('AttentionV2View refresh error:', err);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  setFilters(lifecycle, type) {
    this.filterLifecycle = lifecycle;
    this.filterType = type;
    this.refresh();
  }

  async selectCandidate(candidateId) {
    try {
      this.selectedCandidate = await attentionV2Api.getCandidate(candidateId);
      this.render();
    } catch (err) {
      console.error('Error fetching candidate details:', err);
    }
  }

  async handleRequestFocus(candidateId, targetName) {
    try {
      await attentionV2Api.requestFocus({
        candidate_id: candidateId,
        target: {
          target_id: `target_${candidateId}`,
          target_type: 'PRIMARY',
          name: targetName || 'Focus Target',
        },
        reason: 'USER_REQUEST',
        allow_interruption: true,
      });
      await this.refresh();
    } catch (err) {
      alert(`Focus transition rejected: ${err.message}`);
    }
  }

  async handleCompleteFocus(success = true) {
    try {
      await attentionV2Api.completeFocus({
        outcome: success ? 'SUCCESS' : 'FAILURE',
        residual_context: { notes: 'User acknowledged completion' },
      });
      await this.refresh();
    } catch (err) {
      alert(`Could not complete focus: ${err.message}`);
    }
  }

  async handleAbortFocus(reason) {
    try {
      await attentionV2Api.abortFocus({
        reason: reason || 'Operator Abort',
      });
      await this.refresh();
    } catch (err) {
      alert(`Could not abort focus: ${err.message}`);
    }
  }

  async handleFairnessSweep() {
    try {
      await attentionV2Api.runFairnessSweep();
      await this.refresh();
    } catch (err) {
      alert(`Sweep failed: ${err.message}`);
    }
  }

  render() {
    const html = this._renderHtml();
    if (this.container) {
      this.container.innerHTML = html;
      this._bindEvents();
    }
    return html;
  }

  _renderHtml() {
    return `
      <div class="attention-v2-container card bg-base-900 border border-base-700 p-6 rounded-xl space-y-6">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-base-800 pb-4">
          <div>
            <h2 class="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
              <span class="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">⚡</span>
              Attention & Focus Management Engine
              <span class="text-xs px-2.5 py-1 bg-indigo-900/60 text-indigo-300 rounded-full border border-indigo-700/50">Task 109</span>
            </h2>
            <p class="text-sm text-base-400 mt-1">Autonomous cognitive resource allocation, nested focus stack & bounded interruption governance</p>
          </div>
          <div class="flex items-center gap-3">
            <button id="attn-btn-sweep" class="btn btn-sm btn-outline text-amber-300 border-amber-500/40 hover:bg-amber-950/40">
              ⏳ Run Fairness Aging Sweep
            </button>
            <button id="attn-btn-refresh" class="btn btn-sm btn-primary bg-indigo-600 hover:bg-indigo-500">
              🔄 Refresh
            </button>
          </div>
        </div>

        <!-- Health Banner -->
        ${this._renderHealthBanner()}

        <!-- Active Focus & Stack Cards -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="lg:col-span-2">
            ${this._renderActiveFocusCard()}
          </div>
          <div class="lg:col-span-1">
            ${this._renderStackCard()}
          </div>
        </div>

        <!-- Tab Navigation -->
        <div class="flex border-b border-base-800 gap-4 text-sm font-medium">
          <button class="attn-tab-btn pb-2 border-b-2 ${this.activeTab === 'candidates' ? 'border-indigo-500 text-indigo-400 font-bold' : 'border-transparent text-base-400 hover:text-base-200'}" data-tab="candidates">
            Attention Candidates (${this.candidates.length})
          </button>
          <button class="attn-tab-btn pb-2 border-b-2 ${this.activeTab === 'watches' ? 'border-indigo-500 text-indigo-400 font-bold' : 'border-transparent text-base-400 hover:text-base-200'}" data-tab="watches">
            Condition Watches (${this.snapshot?.active_watches?.length || 0})
          </button>
          <button class="attn-tab-btn pb-2 border-b-2 ${this.activeTab === 'snapshot' ? 'border-indigo-500 text-indigo-400 font-bold' : 'border-transparent text-base-400 hover:text-base-200'}" data-tab="snapshot">
            Point-in-Time Snapshot
          </button>
        </div>

        <!-- Tab Content -->
        <div class="tab-body">
          ${this.activeTab === 'candidates' ? this._renderCandidatesTab() : ''}
          ${this.activeTab === 'watches' ? this._renderWatchesTab() : ''}
          ${this.activeTab === 'snapshot' ? this._renderSnapshotTab() : ''}
        </div>
      </div>
    `;
  }

  _renderHealthBanner() {
    if (!this.health) return '';
    const status = this.health.health_status || 'HEALTHY';
    const statusColor = status === 'HEALTHY' ? 'text-emerald-400 bg-emerald-950/40 border-emerald-500/40' :
                        status === 'ELEVATED' ? 'text-amber-400 bg-amber-950/40 border-amber-500/40' :
                        'text-rose-400 bg-rose-950/40 border-rose-500/40';

    return `
      <div class="flex items-center justify-between p-4 rounded-lg border ${statusColor}">
        <div class="flex items-center gap-3">
          <div class="font-bold tracking-wide">STATUS: ${status}</div>
          <div class="text-xs text-base-300">Fragmentation: ${(this.health.cognitive_fragmentation_score || 0).toFixed(2)}</div>
          <div class="text-xs text-base-300">Queue: ${this.health.queued_candidates || 0} | Watching: ${this.health.watching_candidates || 0} | Deferred: ${this.health.deferred_candidates || 0}</div>
        </div>
        <div class="text-xs text-base-400 italic">
          ${this.health.churn_details || ''}
        </div>
      </div>
    `;
  }

  _renderActiveFocusCard() {
    if (!this.activeFocus) {
      return `
        <div class="card bg-base-800/40 border border-base-700/60 p-5 rounded-lg flex flex-col justify-center items-center py-10 text-center">
          <span class="text-3xl text-base-500 mb-2">💤</span>
          <h4 class="text-base font-semibold text-base-200">System is in IDLE Focus</h4>
          <p class="text-xs text-base-400 mt-1 max-w-sm">No cognitive resources actively committed. Select a queued candidate below to transition focus.</p>
        </div>
      `;
    }

    const s = this.activeFocus;
    const target = s.primary_target || {};
    const budget = s.resource_budget || {};

    return `
      <div class="card bg-base-800/60 border border-indigo-500/40 p-5 rounded-lg space-y-4">
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <h3 class="text-lg font-bold text-white">${target.name || 'Active Focus Session'}</h3>
              <span class="text-xs px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-700">Depth ${s.depth}</span>
            </div>
            <p class="text-xs text-base-400 mt-1 font-mono">${s.candidate_id} | Session: ${s.session_id}</p>
          </div>
          <div class="flex items-center gap-2">
            <button id="attn-btn-complete-focus" class="btn btn-xs btn-success bg-emerald-600 hover:bg-emerald-500 text-white">
              ✓ Complete
            </button>
            <button id="attn-btn-abort-focus" class="btn btn-xs btn-error bg-rose-600 hover:bg-rose-500 text-white">
              ✕ Abort
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-base-900/60 p-3 rounded-lg text-xs">
          <div>
            <span class="text-base-400 block">Token Budget</span>
            <span class="font-mono text-base-200 font-semibold">${budget.tokens_allocated || 0} tok</span>
          </div>
          <div>
            <span class="text-base-400 block">Time Allocated</span>
            <span class="font-mono text-base-200 font-semibold">${budget.time_seconds_allocated || 0}s</span>
          </div>
          <div>
            <span class="text-base-400 block">Context Window</span>
            <span class="font-mono text-base-200 font-semibold">${s.allocated_context_window_tokens || 0} tok</span>
          </div>
          <div>
            <span class="text-base-400 block">Allow Interruptions</span>
            <span class="font-mono ${s.allow_interruption ? 'text-emerald-400' : 'text-amber-400'} font-semibold">
              ${s.allow_interruption ? 'YES (Governed)' : 'NO (Atomic)'}
            </span>
          </div>
        </div>
      </div>
    `;
  }

  _renderStackCard() {
    return `
      <div class="card bg-base-800/40 border border-base-700/60 p-5 rounded-lg h-full flex flex-col">
        <div class="flex items-center justify-between mb-3 border-b border-base-700/50 pb-2">
          <h4 class="text-sm font-bold text-white flex items-center gap-2">
            <span>📚</span> Interrupted Stack
          </h4>
          <span class="text-xs text-base-400 font-mono">Max Depth: 5</span>
        </div>

        <div class="flex-1 space-y-2 overflow-y-auto max-h-48">
          ${this.stack.length === 0 ? `
            <div class="text-xs text-base-500 italic text-center py-6">Stack empty (no suspended contexts)</div>
          ` : this.stack.map(item => `
            <div class="p-2.5 rounded bg-base-900/80 border border-base-700 text-xs">
              <div class="flex justify-between items-center font-medium text-base-200">
                <span>${item.primary_target?.name || item.candidate_id}</span>
                <span class="text-indigo-400 font-mono text-[10px]">Lvl ${item.depth}</span>
              </div>
              <div class="text-[10px] text-base-400 mt-0.5 truncate font-mono">Cand: ${item.candidate_id}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderCandidatesTab() {
    return `
      <div class="space-y-4">
        <!-- Filter bar -->
        <div class="flex flex-wrap items-center justify-between gap-3 bg-base-800/40 p-3 rounded-lg text-xs">
          <div class="flex items-center gap-2">
            <span class="text-base-400 font-medium">Lifecycle:</span>
            <select id="attn-filter-lifecycle" class="select select-xs bg-base-900 border-base-700 text-base-200">
              <option value="">All Lifecycles</option>
              <option value="QUEUED" ${this.filterLifecycle === 'QUEUED' ? 'selected' : ''}>QUEUED</option>
              <option value="FOCUSED" ${this.filterLifecycle === 'FOCUSED' ? 'selected' : ''}>FOCUSED</option>
              <option value="INTERRUPTED" ${this.filterLifecycle === 'INTERRUPTED' ? 'selected' : ''}>INTERRUPTED</option>
              <option value="WAITING" ${this.filterLifecycle === 'WAITING' ? 'selected' : ''}>WAITING</option>
              <option value="DEFERRED" ${this.filterLifecycle === 'DEFERRED' ? 'selected' : ''}>DEFERRED</option>
              <option value="COMPLETED" ${this.filterLifecycle === 'COMPLETED' ? 'selected' : ''}>COMPLETED</option>
            </select>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-base-400 font-medium">Type:</span>
            <select id="attn-filter-type" class="select select-xs bg-base-900 border-base-700 text-base-200">
              <option value="">All Types</option>
              <option value="USER_REQUEST">USER_REQUEST</option>
              <option value="DEADLINE">DEADLINE</option>
              <option value="MISSION_BLOCKER">MISSION_BLOCKER</option>
              <option value="SAFETY">SAFETY</option>
              <option value="SECURITY">SECURITY</option>
              <option value="FAILURE">FAILURE</option>
            </select>
          </div>
        </div>

        <!-- Table -->
        <div class="overflow-x-auto rounded-lg border border-base-800">
          <table class="table table-compact w-full text-xs">
            <thead class="bg-base-950/80 text-base-400">
              <tr>
                <th class="py-2.5">Candidate</th>
                <th>Type</th>
                <th>Lifecycle</th>
                <th>Composite Salience</th>
                <th>Aging Boost</th>
                <th>Safety/Risk</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-base-800/60 bg-base-900/40">
              ${this.candidates.length === 0 ? `
                <tr><td colspan="7" class="text-center py-8 text-base-500 italic">No candidates matching filters.</td></tr>
              ` : this.candidates.map(cand => {
                const score = cand.score || {};
                const salience = score.composite_salience != null ? score.composite_salience.toFixed(2) : '0.00';
                const aging = cand.aging_boost != null ? cand.aging_boost.toFixed(2) : '0.00';
                const risk = score.risk != null ? score.risk.toFixed(2) : '0.00';
                const isDampened = cand.is_adversarial_dampened;

                return `
                  <tr class="hover:bg-base-800/30 transition-colors">
                    <td class="font-medium text-white max-w-xs truncate">
                      <div>${cand.title}</div>
                      <div class="text-[10px] text-base-400 font-mono">${cand.candidate_id}</div>
                    </td>
                    <td>
                      <span class="px-2 py-0.5 rounded bg-base-800 text-base-300 font-mono text-[10px]">${cand.type}</span>
                    </td>
                    <td>
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold ${this._getLifecycleBadgeClass(cand.lifecycle)}">
                        ${cand.lifecycle}
                      </span>
                    </td>
                    <td class="font-mono font-bold text-indigo-300">
                      ${salience}
                      ${isDampened ? '<span class="text-rose-400 ml-1" title="Adversarial Dampening Applied">🛡️</span>' : ''}
                    </td>
                    <td class="font-mono text-amber-300">+${aging}</td>
                    <td class="font-mono text-base-300">${risk}</td>
                    <td>
                      <button class="btn btn-xs btn-outline border-indigo-500/50 text-indigo-300 hover:bg-indigo-950/60 attn-focus-btn" data-id="${cand.candidate_id}" data-title="${encodeURIComponent(cand.title)}">
                        Focus ➔
                      </button>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  _renderWatchesTab() {
    const watches = this.snapshot?.active_watches || [];
    return `
      <div class="space-y-4">
        <div class="text-xs text-base-400">Zero-cost condition watches consume minimal resources until triggered by external signals or time.</div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          ${watches.length === 0 ? `
            <div class="col-span-2 text-center py-8 text-base-500 italic">No active condition watches.</div>
          ` : watches.map(w => `
            <div class="p-4 rounded-lg bg-base-900 border border-base-800 space-y-2">
              <div class="flex justify-between items-start">
                <span class="text-xs font-mono font-bold text-indigo-300">${w.condition_type}</span>
                <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700">Active</span>
              </div>
              <p class="text-xs text-base-200 font-mono bg-base-950 p-2 rounded">${w.condition_expr}</p>
              <div class="text-[10px] text-base-400">Candidate: <span class="font-mono text-base-300">${w.candidate_id}</span></div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderSnapshotTab() {
    return `
      <div class="p-4 rounded-lg bg-base-950 font-mono text-xs text-base-300 overflow-x-auto max-h-96">
        <pre>${JSON.stringify(this.snapshot, null, 2)}</pre>
      </div>
    `;
  }

  _getLifecycleBadgeClass(lifecycle) {
    switch (lifecycle) {
      case 'FOCUSED': return 'bg-emerald-950 text-emerald-300 border border-emerald-700';
      case 'QUEUED': return 'bg-sky-950 text-sky-300 border border-sky-700';
      case 'INTERRUPTED': return 'bg-amber-950 text-amber-300 border border-amber-700';
      case 'WAITING': return 'bg-indigo-950 text-indigo-300 border border-indigo-700';
      case 'DEFERRED': return 'bg-purple-950 text-purple-300 border border-purple-700';
      case 'COMPLETED': return 'bg-base-800 text-base-300';
      default: return 'bg-base-800 text-base-400';
    }
  }

  _bindEvents() {
    if (!this.container) return;

    this.container.querySelectorAll('.attn-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.setTab(btn.dataset.tab);
      });
    });

    const refreshBtn = this.container.querySelector('#attn-btn-refresh');
    if (refreshBtn) refreshBtn.addEventListener('click', () => this.refresh());

    const sweepBtn = this.container.querySelector('#attn-btn-sweep');
    if (sweepBtn) sweepBtn.addEventListener('click', () => this.handleFairnessSweep());

    const completeBtn = this.container.querySelector('#attn-btn-complete-focus');
    if (completeBtn) completeBtn.addEventListener('click', () => this.handleCompleteFocus(true));

    const abortBtn = this.container.querySelector('#attn-btn-abort-focus');
    if (abortBtn) abortBtn.addEventListener('click', () => this.handleAbortFocus('Operator Aborted'));

    const lifecycleFilter = this.container.querySelector('#attn-filter-lifecycle');
    if (lifecycleFilter) {
      lifecycleFilter.addEventListener('change', (e) => this.setFilters(e.target.value, this.filterType));
    }

    this.container.querySelectorAll('.attn-focus-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        const title = decodeURIComponent(btn.dataset.title);
        this.handleRequestFocus(id, title);
      });
    });
  }
}

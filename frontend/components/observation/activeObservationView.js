/**
 * Kairo Autonomous Active Observation, Value-of-Information, Information Acquisition & Uncertainty Reduction View.
 * Task 114.
 *
 * Implements an interactive "What Does KAIRO Need to Know?" interface for identifying epistemic gaps,
 * evaluating decision sensitivity, calculating Value-of-Information (VoI), balancing costs and risks,
 * deciding whether to ACT NOW, WAIT, OBSERVE, or ASK USER, and verifying acquired empirical evidence.
 */

import { observationsApi } from '../../lib/api/endpoints.js';

export class ActiveObservationView {
  constructor(options = {}) {
    this.container = options.container || null;
    this.planId = options.planId || null;
    this.activeTab = options.activeTab || 'matrix'; // matrix, gaps, options, verification, history
    this.plan = null;
    this.history = [];
    this.loading = false;
    this.error = null;
  }

  async init() {
    if (this.planId) {
      await this.loadPlan(this.planId);
    } else {
      await this.loadHistory();
      if (this.history.length > 0) {
        await this.loadPlan(this.history[0].plan_id);
      }
    }
    this.render();
  }

  async loadPlan(id) {
    this.loading = true;
    this.error = null;
    try {
      const res = await observationsApi.getPlan(id);
      this.plan = res.plan || res;
      this.planId = id;
    } catch (err) {
      this.error = err.message || 'Failed to load observation plan';
    } finally {
      this.loading = false;
      this.render();
    }
  }

  async loadHistory() {
    try {
      this.history = await observationsApi.getHistory(20);
    } catch (err) {
      console.warn('Could not load observation history:', err);
    }
  }

  async executeObservation(candidateId = null) {
    if (!this.planId) return;
    this.loading = true;
    try {
      const res = await observationsApi.executePlan(this.planId, { candidate_id: candidateId });
      this.plan = res.plan || res;
      this.activeTab = 'verification';
    } catch (err) {
      this.error = err.message || 'Execution failed';
    } finally {
      this.loading = false;
      this.render();
    }
  }

  switchTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  render() {
    if (!this.container) return;

    if (this.loading) {
      this.container.innerHTML = `
        <div class="p-8 text-center text-slate-400">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500 mb-4"></div>
          <p class="text-sm">Evaluating epistemic uncertainty & Value-of-Information (VoI)...</p>
        </div>
      `;
      return;
    }

    const stance = this.plan ? this.plan.recommended_stance : 'OBSERVE';
    const stanceBadge = this._getStanceBadge(stance);

    this.container.innerHTML = `
      <div class="kairo-active-observation p-6 bg-slate-900 text-slate-100 rounded-xl border border-slate-800 shadow-2xl font-sans max-w-7xl mx-auto">
        <!-- Top Header -->
        <div class="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-800">
          <div>
            <div class="flex items-center gap-3">
              <span class="px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wider bg-cyan-900/50 text-cyan-300 border border-cyan-700/50">Task 114</span>
              <h1 class="text-xl font-bold text-white tracking-tight">Active Observation & Value-of-Information</h1>
              ${this.plan && this.plan.is_stale ? '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-red-950 text-red-400 border border-red-800">STALE</span>' : ''}
            </div>
            <p class="text-xs text-slate-400 mt-1">Autonomous epistemic uncertainty reduction, decision sensitivity, and purpose-driven evidence acquisition.</p>
          </div>

          <div class="flex items-center gap-3">
            <div class="text-right">
              <span class="text-xs text-slate-400 block">Recommended Stance</span>
              ${stanceBadge}
            </div>
            <button id="btn-new-plan" class="px-3.5 py-1.5 text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors shadow-sm">
              New Plan
            </button>
          </div>
        </div>

        ${this.error ? `
          <div class="mt-4 p-4 bg-red-950/60 border border-red-800/80 rounded-lg text-red-200 text-xs flex justify-between items-center">
            <span><strong>Error:</strong> ${this.error}</span>
            <button id="btn-dismiss-err" class="text-red-400 hover:text-white font-bold ml-4">✕</button>
          </div>
        ` : ''}

        ${this.plan ? `
          <!-- Plan Context Bar -->
          <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700/60 text-xs">
            <div>
              <span class="text-slate-400 block">Target Entity</span>
              <span class="font-semibold text-cyan-300">${this.plan.target_entity}</span>
            </div>
            <div>
              <span class="text-slate-400 block">Confidence (Pre → Post)</span>
              <span class="font-semibold text-slate-200">
                ${(this.plan.uncertainty_before?.overall_confidence * 100 || 50).toFixed(0)}% → 
                <span class="text-emerald-400">${(this.plan.uncertainty_after?.overall_confidence * 100 || 50).toFixed(0)}%</span>
              </span>
            </div>
            <div>
              <span class="text-slate-400 block">Information Gaps</span>
              <span class="font-semibold text-slate-200">${this.plan.gaps?.length || 0} (${this.plan.gaps?.filter(g => g.is_resolved_by_existing_data).length || 0} internal)</span>
            </div>
            <div>
              <span class="text-slate-400 block">Budget Units</span>
              <span class="font-semibold text-slate-200">${this.plan.budget?.spent_units || 0} / ${this.plan.budget?.allocated_units || 10}</span>
            </div>
            <div>
              <span class="text-slate-400 block">Stop Condition</span>
              <span class="font-semibold text-amber-300">${this.plan.stop_reason || 'IN PROGRESS'}</span>
            </div>
          </div>

          <!-- Navigation Tabs -->
          <div class="flex border-b border-slate-800 mt-6 gap-2 text-xs">
            <button data-tab="matrix" class="tab-btn px-4 py-2 font-medium border-b-2 transition-colors ${this.activeTab === 'matrix' ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              15D Uncertainty Matrix
            </button>
            <button data-tab="gaps" class="tab-btn px-4 py-2 font-medium border-b-2 transition-colors ${this.activeTab === 'gaps' ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              Information Gaps (${this.plan.gaps?.length || 0})
            </button>
            <button data-tab="options" class="tab-btn px-4 py-2 font-medium border-b-2 transition-colors ${this.activeTab === 'options' ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              Observation Candidates (${this.plan.candidates?.length || 0})
            </button>
            <button data-tab="verification" class="tab-btn px-4 py-2 font-medium border-b-2 transition-colors ${this.activeTab === 'verification' ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              Evidence & Verification (${this.plan.outcomes?.length || 0})
            </button>
            <button data-tab="history" class="tab-btn px-4 py-2 font-medium border-b-2 transition-colors ${this.activeTab === 'history' ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              History
            </button>
          </div>

          <!-- Tab Content Panes -->
          <div class="mt-4">
            ${this._renderActiveTab()}
          </div>
        ` : `
          <div class="p-12 text-center text-slate-400">
            <p class="text-sm">No observation plan loaded. Create a plan or select one from history.</p>
          </div>
        `}
      </div>
    `;

    this._wireEvents();
  }

  _renderActiveTab() {
    switch (this.activeTab) {
      case 'matrix':
        return this._renderUncertaintyMatrix();
      case 'gaps':
        return this._renderInformationGaps();
      case 'options':
        return this._renderCandidates();
      case 'verification':
        return this._renderVerification();
      case 'history':
        return this._renderHistory();
      default:
        return this._renderUncertaintyMatrix();
    }
  }

  _renderUncertaintyMatrix() {
    const dims = this.plan.uncertainty_after?.dimensions || this.plan.uncertainty_before?.dimensions || {};
    const entries = Object.entries(dims);

    return `
      <div>
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-white">Epistemic Uncertainty Dimensions (15 Categories)</h3>
          <span class="text-xs text-slate-400">Hard Invariant: UNKNOWN ≠ FALSE | MISSING DATA ≠ NO CHANGE</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          ${entries.map(([name, dim]) => {
            const levelClass = {
              KNOWN: 'bg-emerald-950/50 text-emerald-300 border-emerald-800',
              LIKELY: 'bg-cyan-950/50 text-cyan-300 border-cyan-800',
              UNCERTAIN: 'bg-amber-950/50 text-amber-300 border-amber-800',
              CONTESTED: 'bg-purple-950/50 text-purple-300 border-purple-800',
              UNKNOWN: 'bg-slate-800 text-slate-400 border-slate-700',
              STALE: 'bg-red-950/50 text-red-300 border-red-800',
            }[dim.level] || 'bg-slate-800 text-slate-300 border-slate-700';

            return `
              <div class="p-3 bg-slate-800/40 rounded-lg border border-slate-700/60 flex flex-col justify-between">
                <div class="flex items-center justify-between mb-1.5">
                  <span class="font-bold text-xs text-slate-200 uppercase tracking-wide">${dim.dimension}</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${levelClass}">${dim.level}</span>
                </div>
                <p class="text-[11px] text-slate-400 line-clamp-2">${dim.description || 'No description'}</p>
                <div class="mt-2 pt-2 border-t border-slate-700/40 flex items-center justify-between text-[10px] text-slate-400">
                  <span>Conf: ${(dim.confidence * 100).toFixed(0)}%</span>
                  ${dim.is_critical ? '<span class="text-rose-400 font-semibold">CRITICAL</span>' : ''}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  _renderInformationGaps() {
    const gaps = this.plan.gaps || [];
    if (gaps.length === 0) {
      return `<p class="text-xs text-slate-400 p-4 bg-slate-800/30 rounded">No critical information gaps flagged.</p>`;
    }

    return `
      <div class="space-y-3">
        ${gaps.map(g => {
          const sens = this.plan.sensitivities?.[g.gap_id];
          return `
            <div class="p-4 bg-slate-800/40 rounded-lg border border-slate-700/60 flex flex-col gap-2 text-xs">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${g.severity === 'CRITICAL' ? 'bg-red-900/60 text-red-300 border border-red-700' : 'bg-amber-900/40 text-amber-300 border border-amber-700'}">
                    ${g.severity}
                  </span>
                  <span class="font-semibold text-slate-200">${g.question}</span>
                </div>
                ${g.is_resolved_by_existing_data ? `
                  <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                    RESOLVED INTERNALLY (${g.existing_evidence_id})
                  </span>
                ` : `
                  <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${sens?.is_decision_sensitive ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-slate-800 text-slate-400'}">
                    ${sens?.is_decision_sensitive ? 'DECISION SENSITIVE' : 'INSENSITIVE'}
                  </span>
                `}
              </div>

              <p class="text-slate-400">${g.why_it_matters}</p>

              <div class="flex flex-wrap items-center gap-4 text-[11px] text-slate-400 pt-2 border-t border-slate-700/30">
                <span>State: <strong class="text-slate-300">${g.affected_state}</strong></span>
                <span>Freshness SLA: <strong class="text-slate-300">${g.freshness_requirement_seconds}s</strong></span>
                ${sens ? `<span>Sensitivity Score: <strong class="text-cyan-400">${(sens.sensitivity_score * 100).toFixed(0)}%</strong></span>` : ''}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  _renderCandidates() {
    const candidates = this.plan.candidates || [];
    if (candidates.length === 0) {
      return `<p class="text-xs text-slate-400 p-4 bg-slate-800/30 rounded">No observation candidates generated.</p>`;
    }

    return `
      <div class="space-y-3">
        ${candidates.map(c => {
          const voi = c.value_estimate;
          const tierColor = {
            VERY_HIGH: 'bg-emerald-950 text-emerald-300 border-emerald-800',
            HIGH: 'bg-cyan-950 text-cyan-300 border-cyan-800',
            MODERATE: 'bg-blue-950 text-blue-300 border-blue-800',
            LOW: 'bg-slate-800 text-slate-300 border-slate-700',
            VERY_LOW: 'bg-slate-900 text-slate-500 border-slate-800',
          }[voi?.tier] || 'bg-slate-800 text-slate-400';

          return `
            <div class="p-4 bg-slate-800/40 rounded-lg border ${c.is_selected ? 'border-cyan-500 bg-cyan-950/10' : 'border-slate-700/60'} text-xs">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-700 text-slate-200 uppercase">${c.method}</span>
                  <span class="font-bold text-slate-100">${c.name}</span>
                  <span class="text-slate-400">→ Source: <strong class="text-slate-300">${c.target_source}</strong></span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${tierColor}">VoI: ${voi?.tier || 'N/A'}</span>
                  <button data-candidate-id="${c.candidate_id}" class="btn-exec-cand px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium transition-colors">
                    Observe
                  </button>
                </div>
              </div>

              <p class="text-slate-400 mb-2">${voi?.justification || 'No justification provided'}</p>

              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-700/30 text-[11px]">
                <div><span class="text-slate-500">Net Value:</span> <strong class="text-cyan-400">${(voi?.net_value_score || 0).toFixed(2)}</strong></div>
                <div><span class="text-slate-500">Latency:</span> <strong class="text-slate-300">${c.expected_latency_seconds}s</strong></div>
                <div><span class="text-slate-500">Compute Cost:</span> <strong class="text-slate-300">${c.cost.compute_units} units</strong></div>
                <div><span class="text-slate-500">Risk Level:</span> <strong class="text-slate-300">${c.risk.security_risk_level}</strong></div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  _renderVerification() {
    const outcomes = this.plan.outcomes || [];
    if (outcomes.length === 0) {
      return `<p class="text-xs text-slate-400 p-4 bg-slate-800/30 rounded">No observations have been executed yet.</p>`;
    }

    return `
      <div class="space-y-4">
        ${outcomes.map(out => {
          const veri = this.plan.verifications?.[out.outcome_id];
          return `
            <div class="p-4 bg-slate-800/40 rounded-lg border border-slate-700/60 text-xs">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-slate-100">${out.summary}</span>
                  <span class="text-[10px] text-slate-400">Method: ${out.method}</span>
                </div>
                <div class="flex items-center gap-2">
                  ${out.conflicts_with_existing ? `
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-800">
                      CONFLICT DETECTED
                    </span>
                  ` : ''}
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold ${veri?.status === 'VERIFIED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-red-950 text-red-300 border border-red-800'}">
                    ${veri?.status || 'PENDING'}
                  </span>
                </div>
              </div>

              <div class="p-2.5 bg-slate-900 rounded font-mono text-[11px] text-cyan-300 mb-2 overflow-x-auto">
                ${JSON.stringify(out.data_payload, null, 2)}
              </div>

              ${out.conflicts_with_existing ? `
                <div class="p-2 bg-amber-950/40 border border-amber-800/60 rounded text-[11px] text-amber-200 mb-2">
                  ${out.conflict_details}
                </div>
              ` : ''}

              <div class="flex flex-wrap items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-700/30">
                <span>Provenance: <code>${out.provenance_hash.slice(0, 16)}...</code></span>
                <span>Confidence: <strong>${(out.confidence * 100).toFixed(0)}%</strong></span>
                <span>Audited: ${veri?.verified_at ? new Date(veri.verified_at).toLocaleTimeString() : 'N/A'}</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  _renderHistory() {
    if (this.history.length === 0) {
      return `<p class="text-xs text-slate-400 p-4 bg-slate-800/30 rounded">No historical observation plans found.</p>`;
    }

    return `
      <div class="divide-y divide-slate-800">
        ${this.history.map(item => `
          <div class="py-3 flex items-center justify-between text-xs hover:bg-slate-800/30 px-2 rounded cursor-pointer btn-load-plan" data-plan-id="${item.plan_id}">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-200">${item.target_entity}</span>
                <span class="text-slate-400">(${item.plan_id})</span>
              </div>
              <p class="text-[11px] text-slate-400">${item.objective}</p>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-[11px] text-slate-400">${new Date(item.created_at).toLocaleTimeString()}</span>
              ${this._getStanceBadge(item.recommended_stance)}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  _getStanceBadge(stance) {
    const map = {
      'ACT NOW': 'bg-emerald-950/80 text-emerald-300 border-emerald-800',
      'WAIT': 'bg-amber-950/80 text-amber-300 border-amber-800',
      'OBSERVE': 'bg-cyan-950/80 text-cyan-300 border-cyan-800',
      'ASK USER': 'bg-purple-950/80 text-purple-300 border-purple-800',
      'NO FURTHER INFORMATION NEEDED': 'bg-slate-800 text-slate-300 border-slate-700',
    };
    const cls = map[stance] || 'bg-slate-800 text-slate-300 border-slate-700';
    return `<span class="px-2.5 py-1 rounded-md text-xs font-bold border ${cls}">${stance}</span>`;
  }

  _wireEvents() {
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.switchTab(btn.dataset.tab);
      });
    });

    const newPlanBtn = this.container.querySelector('#btn-new-plan');
    if (newPlanBtn) {
      newPlanBtn.addEventListener('click', async () => {
        const target = prompt('Enter target entity to analyze for uncertainty (e.g. "payment_service"):', 'payment_service');
        if (!target) return;
        this.loading = true;
        try {
          const res = await observationsApi.createPlan({ target_entity: target });
          await this.loadPlan(res.plan_id);
        } catch (err) {
          alert('Error creating plan: ' + err.message);
        } finally {
          this.loading = false;
          this.render();
        }
      });
    }

    this.container.querySelectorAll('.btn-exec-cand').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const candId = e.target.dataset.candidateId;
        this.executeObservation(candId);
      });
    });

    this.container.querySelectorAll('.btn-load-plan').forEach(btn => {
      btn.addEventListener('click', () => {
        const pid = btn.dataset.planId;
        if (pid) this.loadPlan(pid);
      });
    });

    const dismissBtn = this.container.querySelector('#btn-dismiss-err');
    if (dismissBtn) {
      dismissBtn.addEventListener('click', () => {
        this.error = null;
        this.render();
      });
    }
  }
}

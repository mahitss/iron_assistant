/**
 * Kairo Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning View.
 * Task 113.
 *
 * Implements an interactive "What If?" interface for evaluating candidate interventions
 * side-by-side against NO_ACTION with strict simulation sandboxing, explicit assumptions,
 * sensitivity/robustness metrics, and prediction-vs-reality calibration.
 */

import { counterfactualsApi } from '../../lib/api/endpoints.js';

export class CounterfactualAnalysisView {
  constructor(options = {}) {
    this.container = options.container || null;
    this.analysisId = options.analysisId || null;
    this.activeTab = options.activeTab || 'comparison'; // comparison, pathways, sensitivity, experiments, verification
    this.analysis = null;
    this.loading = false;
    this.error = null;
  }

  async init() {
    if (this.analysisId) {
      await this.loadAnalysis(this.analysisId);
    }
    this.render();
  }

  async loadAnalysis(id) {
    this.loading = true;
    this.error = null;
    try {
      this.analysis = await counterfactualsApi.get(id);
      this.analysisId = id;
    } catch (err) {
      this.error = err.message || 'Failed to load counterfactual analysis';
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
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500 mb-4"></div>
          <p class="text-sm">Running sandboxed what-if simulation & evaluating counterfactuals...</p>
        </div>
      `;
      return;
    }

    if (this.error) {
      this.container.innerHTML = `
        <div class="p-6 bg-rose-950/40 border border-rose-800/60 rounded-xl text-rose-300">
          <h3 class="font-semibold text-lg mb-2">Counterfactual Error</h3>
          <p class="text-sm">${this.error}</p>
        </div>
      `;
      return;
    }

    if (!this.analysis) {
      this.container.innerHTML = `
        <div class="p-8 bg-slate-900 border border-slate-800 rounded-xl text-center text-slate-400">
          <h2 class="text-xl font-bold text-slate-200 mb-2">What-If & Counterfactual Simulation Engine</h2>
          <p class="text-sm max-w-xl mx-auto mb-6">
            Explore hypothetical pasts and alternate futures without mutating production state.
            Evaluate candidate interventions side-by-side against NO_ACTION with explicit causal assumptions.
          </p>
          <div class="flex justify-center gap-3">
            <input type="text" id="target-entity-input" placeholder="e.g. payment_gateway, worker_cluster" class="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-200 w-80" />
            <button id="run-what-if-btn" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm transition">
              Run What-If Analysis
            </button>
          </div>
        </div>
      `;
      const btn = this.container.querySelector('#run-what-if-btn');
      const input = this.container.querySelector('#target-entity-input');
      if (btn && input) {
        btn.onclick = async () => {
          const val = input.value.trim();
          if (val) {
            this.loading = true;
            this.render();
            try {
              const res = await counterfactualsApi.create({
                target_entity: val,
                question: `What would happen if we intervene on ${val}?`,
                include_no_action: true,
              });
              await this.loadAnalysis(res.analysis_id);
            } catch (err) {
              this.error = err.message || 'Simulation creation failed';
              this.loading = false;
              this.render();
            }
          }
        };
      }
      return;
    }

    const a = this.analysis;
    const stageColor = a.lifecycle_stage === 'VERIFIED' ? 'emerald' : (a.lifecycle_stage === 'BLOCKED' ? 'rose' : 'indigo');

    this.container.innerHTML = `
      <div class="space-y-6">
        <!-- Header -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
          <div class="flex items-start justify-between">
            <div>
              <div class="flex items-center gap-2 mb-2">
                <span class="px-2.5 py-1 text-xs font-mono rounded-full bg-${stageColor}-900/50 text-${stageColor}-300 border border-${stageColor}-700/50">
                  ${a.lifecycle_stage}
                </span>
                <span class="px-2 py-0.5 text-xs font-semibold rounded bg-amber-950/80 text-amber-300 border border-amber-800/60">
                  SIMULATION_ONLY [HYPOTHETICAL]
                </span>
                ${a.is_stale ? '<span class="px-2 py-0.5 text-xs font-semibold rounded bg-rose-950 text-rose-300 border border-rose-800">STALE</span>' : ''}
              </div>
              <h2 class="text-xl font-bold text-slate-100">${a.question || 'What-If Simulation Inquiry'}</h2>
              <p class="text-sm text-slate-400 mt-1">Target Entity: <span class="text-slate-200 font-mono">${a.target_entity}</span> | ID: <span class="text-slate-400 font-mono text-xs">${a.analysis_id}</span></p>
            </div>
            <div class="text-right text-xs text-slate-400 font-mono">
              <div>Type: ${a.counterfactual_type}</div>
              <div>Causal Model: ${a.causal_model_version}</div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="flex border-b border-slate-800 mt-6 gap-6 text-sm">
            <button class="nav-tab pb-3 font-medium transition border-b-2 ${this.activeTab === 'comparison' ? 'text-indigo-400 border-indigo-500' : 'text-slate-400 border-transparent hover:text-slate-200'}" data-tab="comparison">
              Side-by-Side Comparison
            </button>
            <button class="nav-tab pb-3 font-medium transition border-b-2 ${this.activeTab === 'pathways' ? 'text-indigo-400 border-indigo-500' : 'text-slate-400 border-transparent hover:text-slate-200'}" data-tab="pathways">
              Causal Pathways & Assumptions
            </button>
            <button class="nav-tab pb-3 font-medium transition border-b-2 ${this.activeTab === 'sensitivity' ? 'text-indigo-400 border-indigo-500' : 'text-slate-400 border-transparent hover:text-slate-200'}" data-tab="sensitivity">
              Sensitivity & Robustness
            </button>
            <button class="nav-tab pb-3 font-medium transition border-b-2 ${this.activeTab === 'experiments' ? 'text-indigo-400 border-indigo-500' : 'text-slate-400 border-transparent hover:text-slate-200'}" data-tab="experiments">
              Information Gain & Experiments
            </button>
            <button class="nav-tab pb-3 font-medium transition border-b-2 ${this.activeTab === 'verification' ? 'text-indigo-400 border-indigo-500' : 'text-slate-400 border-transparent hover:text-slate-200'}" data-tab="verification">
              Prediction vs Reality
            </button>
          </div>
        </div>

        <!-- Tab Content -->
        <div id="tab-content" class="min-h-[300px]">
          ${this.renderTabContent()}
        </div>
      </div>
    `;

    this.attachEvents();
  }

  renderTabContent() {
    const a = this.analysis;
    if (this.activeTab === 'comparison') {
      const cmp = a.comparison;
      const items = cmp ? cmp.items : [];
      return `
        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-${Math.min(3, Math.max(2, items.length))} gap-4">
            ${items.map(item => `
              <div class="bg-slate-900 border ${item.is_no_action ? 'border-slate-700 bg-slate-900/60' : 'border-indigo-900/60 bg-indigo-950/20'} rounded-xl p-5 space-y-3">
                <div class="flex items-center justify-between">
                  <h4 class="font-semibold text-slate-100">${item.scenario_name}</h4>
                  <span class="px-2 py-0.5 text-xs font-mono rounded ${item.is_no_action ? 'bg-slate-800 text-slate-300' : 'bg-indigo-900/50 text-indigo-300'}">
                    ${item.is_no_action ? 'NO_ACTION (BASELINE)' : 'INTERVENTION'}
                  </span>
                </div>
                <div class="text-sm text-slate-300 font-mono bg-slate-950 p-3 rounded border border-slate-800">
                  ${item.predicted_summary}
                </div>
                <div class="grid grid-cols-2 gap-2 text-xs text-slate-400">
                  <div>Risk: <span class="font-semibold text-slate-200">${item.risk_level}</span></div>
                  <div>Reversibility: <span class="font-semibold text-slate-200">${item.reversibility}</span></div>
                  <div>Uncertainty: <span class="font-semibold text-slate-200">${item.uncertainty_level}</span></div>
                  <div>Confidence: <span class="font-semibold text-slate-200">${Math.round(item.confidence * 100)}%</span></div>
                </div>
                <div class="text-xs text-slate-400 border-t border-slate-800/80 pt-2">
                  ${item.resource_cost_summary}
                </div>
              </div>
            `).join('')}
          </div>

          ${cmp && cmp.tradeoff_summary ? `
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
              <h4 class="font-medium text-slate-200 text-sm mb-2">Trade-off Analysis & Recommendation for Decision Support:</h4>
              <p class="text-sm text-slate-300 whitespace-pre-line leading-relaxed">${cmp.tradeoff_summary}</p>
              <div class="mt-4 flex items-center justify-between text-xs text-slate-400 pt-3 border-t border-slate-800">
                <span>Recommended Option: <strong class="text-indigo-400">${cmp.recommended_option_for_decision || 'NO_ACTION'}</strong></span>
                <span>NO_ACTION Viable: <strong class="text-emerald-400">${cmp.no_action_viable ? 'YES' : 'NO'}</strong></span>
              </div>
            </div>
          ` : ''}
        </div>
      `;
    }

    if (this.activeTab === 'pathways') {
      const scens = a.scenarios || [];
      return `
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
          <h3 class="text-base font-semibold text-slate-100">Causal Mechanisms & Underlying Assumptions</h3>
          <div class="space-y-4">
            ${scens.map(s => `
              <div class="border border-slate-800 rounded-lg p-4 bg-slate-950/40">
                <div class="font-medium text-sm text-slate-200 mb-2">${s.scenario_name}</div>
                ${s.interventions.map(i => `
                  <div class="space-y-2 text-xs">
                    <div class="text-slate-400">Target: <span class="font-mono text-slate-200">${i.target}</span></div>
                    <div class="text-slate-400">Scope: <span class="font-mono text-slate-200">${i.scope}</span> | Reversible: <span class="text-slate-200">${i.is_reversible ? 'YES' : 'NO'}</span></div>
                    <div class="mt-2">
                      <div class="font-medium text-slate-300 mb-1">Causal Assumptions:</div>
                      <ul class="list-disc list-inside space-y-1 text-slate-400">
                        ${i.assumptions.map(asm => `
                          <li>[${asm.status}] ${asm.description} (sensitivity weight: ${asm.sensitivity_weight})</li>
                        `).join('')}
                      </ul>
                    </div>
                  </div>
                `).join('')}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    if (this.activeTab === 'sensitivity') {
      const sens = a.sensitivity;
      const rob = a.robustness;
      return `
        <div class="space-y-4">
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 class="text-base font-semibold text-slate-100 mb-2">Parameter Sensitivity Analysis</h3>
            <p class="text-sm text-slate-400 mb-4">${sens ? sens.summary : 'No sensitivity data available.'}</p>
            ${sens && sens.influential_parameters ? `
              <div class="space-y-2">
                ${sens.influential_parameters.map(p => `
                  <div class="flex items-center justify-between text-xs p-2.5 bg-slate-950 rounded border border-slate-800">
                    <span class="font-mono text-slate-300">${p.parameter}</span>
                    <div class="flex items-center gap-4">
                      <span class="text-slate-400">Nominal: ${p.nominal_value}</span>
                      <span class="font-mono text-indigo-400">Elasticity: ${p.elasticity}</span>
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold ${p.impact_level === 'HIGH' ? 'bg-amber-950 text-amber-300' : 'bg-slate-800 text-slate-300'}">${p.impact_level}</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            ` : ''}
          </div>

          <div class="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 class="text-base font-semibold text-slate-100 mb-2">Scenario Robustness Classification</h3>
            <div class="flex items-center gap-4">
              <span class="text-lg font-bold text-indigo-400 font-mono">${rob ? rob.classification : 'UNKNOWN'}</span>
              <span class="text-xs text-slate-400">Stability Score: ${rob ? Math.round(rob.stability_score * 100) : 0}%</span>
            </div>
            ${rob && rob.vulnerabilities && rob.vulnerabilities.length > 0 ? `
              <ul class="mt-3 list-disc list-inside text-xs text-amber-400 space-y-1">
                ${rob.vulnerabilities.map(v => `<li>${v}</li>`).join('')}
              </ul>
            ` : ''}
          </div>
        </div>
      `;
    }

    if (this.activeTab === 'experiments') {
      const props = a.information_gain_proposals || [];
      return `
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <h3 class="text-base font-semibold text-slate-100">Information Gain & Causal Experiment Planning</h3>
          <p class="text-sm text-slate-400">Candidate observations and experiments designed to maximally reduce uncertainty between competing hypotheses.</p>
          <div class="space-y-3 mt-4">
            ${props.map(p => `
              <div class="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
                <div class="flex items-center justify-between">
                  <span class="text-sm font-semibold text-slate-200">${p.discriminating_observation}</span>
                  <span class="px-2 py-0.5 text-xs font-mono rounded bg-indigo-950 text-indigo-300 border border-indigo-800">${p.candidate_experiment_type}</span>
                </div>
                <div class="flex gap-4 text-xs text-slate-400">
                  <div>Expected Information Gain: <strong class="text-indigo-400">${Math.round(p.expected_information_gain * 100)}%</strong></div>
                  <div>Safety Risk: <strong class="text-slate-300">${p.safety_risk}</strong></div>
                  <div>Cost Estimate: <strong class="text-slate-300">${p.cost_estimate}</strong></div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    if (this.activeTab === 'verification') {
      const ver = a.verification;
      return `
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <h3 class="text-base font-semibold text-slate-100">Prediction vs Reality Calibration</h3>
          ${ver ? `
            <div class="space-y-3">
              <div class="flex items-center gap-3">
                <span class="px-3 py-1 text-xs font-bold rounded ${ver.outcome === 'VERIFIED' ? 'bg-emerald-950 text-emerald-300' : 'bg-rose-950 text-rose-300'}">
                  ${ver.outcome}
                </span>
                <span class="text-xs text-slate-400">Mean Deviation: ${(ver.state_deviation_score * 100).toFixed(1)}%</span>
              </div>
              <p class="text-sm text-slate-300 bg-slate-950 p-4 rounded border border-slate-800">${ver.explanation_of_deviation}</p>
              <div class="text-xs text-slate-400">Verified at: ${new Date(ver.verified_at).toLocaleString()}</div>
            </div>
          ` : `
            <div class="text-sm text-slate-400">
              No real-world execution telemetry observed yet. When an authorized intervention is executed, subsequent observations are compared against this counterfactual prediction for calibration.
            </div>
          `}
        </div>
      `;
    }

    return '';
  }

  attachEvents() {
    const tabs = this.container.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
      tab.onclick = () => this.switchTab(tab.dataset.tab);
    });
  }
}

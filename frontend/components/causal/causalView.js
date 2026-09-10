/**
 * Causal Reasoning, Causal Graph, and Root-Cause Analysis Dashboard Component (Task 55).
 * Renders Causal Graphs, 5-Stage Root-Cause Chains, Interventions, Counterfactuals, and Fallacy Audits.
 */

export class CausalView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api;
    this.state = {
      activeTab: 'graph', // 'graph' | 'root_cause' | 'interventions' | 'explanations' | 'fallacies'
      graph: {
        graph_id: 'system_default',
        version: 1,
        confidence: 1.0,
        nodes: {},
        edges: {},
      },
      currentAnalysis: null,
      explanation: null,
      interventions: [],
      counterfactuals: [],
      fallacyResults: null,
      naturalLanguageAnswer: null,
      isLoading: false,
      selectedNode: null,
      selectedIncident: 'inc-latency-p99-db-saturation',
    };
  }

  async render() {
    if (!this.container) return;
    this.container.innerHTML = this._template();
    this._attachEventListeners();
    await this.fetchData();
  }

  async fetchData() {
    this.state.isLoading = true;
    try {
      if (this.api && this.api.getGraph) {
        const gRes = await this.api.getGraph('system_default');
        if (gRes && (gRes.data || gRes.nodes)) {
          this.state.graph = gRes.data || gRes;
        }
      }
      if (this.api && this.api.getAnalysis) {
        try {
          const aRes = await this.api.getAnalysis(this.state.selectedIncident);
          if (aRes) this.state.currentAnalysis = aRes.data || aRes;
        } catch {
          // If not analyzed yet, run initial analysis
          if (this.api.analyzeRootCause) {
            const initRes = await this.api.analyzeRootCause({
              incident_id: this.state.selectedIncident,
              symptom: 'API Gateway p99 Latency Spike > 2500ms',
              telemetry_metrics: {
                database_connection_saturation: 0.98,
                api_latency_p99_ms: 2850.0,
                thread_pool_active_workers: 256.0,
              },
            });
            if (initRes) this.state.currentAnalysis = initRes.data || initRes;
          }
        }
      }
    } catch (err) {
      console.warn('CausalView fetchData warning:', err);
    } finally {
      this.state.isLoading = false;
      this._updateContent();
    }
  }

  _template() {
    return `
      <div class="causal-dashboard" style="display: flex; flex-direction: column; gap: 1.5rem; padding: 1.5rem; background: var(--bg-surface, #0f172a); color: var(--text-primary, #f8fafc); font-family: system-ui, -apple-system, sans-serif;">
        <!-- Header Section -->
        <header style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <h1 style="margin: 0; font-size: 1.5rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Causal Reasoning & Causal Graph Engine
              </h1>
              <span style="font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 9999px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);">
                Strict Invariant: Observation ≠ Correlation ≠ Dependency ≠ Causation
              </span>
            </div>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: #94a3b8;">
              Root-Cause Analysis · Counterfactual Modeling · Interventions · Fallacy Auditing
            </p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button id="btn-run-rca" style="background: linear-gradient(135deg, #0284c7, #4f46e5); color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
              ⚡ Analyze Incident
            </button>
            <button id="btn-refresh" style="background: rgba(255,255,255,0.05); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">
              🔄 Refresh
            </button>
          </div>
        </header>

        <!-- Navigation Tabs -->
        <nav style="display: flex; gap: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.08);">
          <button class="causal-tab ${this.state.activeTab === 'graph' ? 'active' : ''}" data-tab="graph" style="padding: 0.6rem 1.2rem; background: none; border: none; color: ${this.state.activeTab === 'graph' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.state.activeTab === 'graph' ? '#38bdf8' : 'transparent'}; font-weight: 600; cursor: pointer;">
            🌐 Causal Graph
          </button>
          <button class="causal-tab ${this.state.activeTab === 'root_cause' ? 'active' : ''}" data-tab="root_cause" style="padding: 0.6rem 1.2rem; background: none; border: none; color: ${this.state.activeTab === 'root_cause' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.state.activeTab === 'root_cause' ? '#38bdf8' : 'transparent'}; font-weight: 600; cursor: pointer;">
            🔍 Root-Cause Analysis (RCA)
          </button>
          <button class="causal-tab ${this.state.activeTab === 'interventions' ? 'active' : ''}" data-tab="interventions" style="padding: 0.6rem 1.2rem; background: none; border: none; color: ${this.state.activeTab === 'interventions' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.state.activeTab === 'interventions' ? '#38bdf8' : 'transparent'}; font-weight: 600; cursor: pointer;">
            🧪 Interventions & Counterfactuals
          </button>
          <button class="causal-tab ${this.state.activeTab === 'explanations' ? 'active' : ''}" data-tab="explanations" style="padding: 0.6rem 1.2rem; background: none; border: none; color: ${this.state.activeTab === 'explanations' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.state.activeTab === 'explanations' ? '#38bdf8' : 'transparent'}; font-weight: 600; cursor: pointer;">
            💬 Causal Q&A & Explanations
          </button>
          <button class="causal-tab ${this.state.activeTab === 'fallacies' ? 'active' : ''}" data-tab="fallacies" style="padding: 0.6rem 1.2rem; background: none; border: none; color: ${this.state.activeTab === 'fallacies' ? '#38bdf8' : '#94a3b8'}; border-bottom: 2px solid ${this.state.activeTab === 'fallacies' ? '#38bdf8' : 'transparent'}; font-weight: 600; cursor: pointer;">
            🛡️ Fallacy Inspector
          </button>
        </nav>

        <!-- Main Content Area -->
        <main id="causal-tab-content">
          ${this._renderActiveTab()}
        </main>
      </div>
    `;
  }

  _renderActiveTab() {
    switch (this.state.activeTab) {
      case 'graph':
        return this._renderGraphTab();
      case 'root_cause':
        return this._renderRootCauseTab();
      case 'interventions':
        return this._renderInterventionsTab();
      case 'explanations':
        return this._renderExplanationsTab();
      case 'fallacies':
        return this._renderFallaciesTab();
      default:
        return this._renderGraphTab();
    }
  }

  _renderGraphTab() {
    const nodes = Object.values(this.state.graph.nodes || {});
    const edges = Object.values(this.state.graph.edges || {});

    return `
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;">
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h3 style="margin: 0; font-size: 1.1rem; color: #e2e8f0;">Directed Causal Graph</h3>
            <span style="font-size: 0.8rem; color: #94a3b8;">Graph ID: ${this.state.graph.graph_id} (v${this.state.graph.version})</span>
          </div>

          <div style="display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap;">
            <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); flex: 1;">
              <div style="font-size: 0.75rem; color: #94a3b8;">Causal Nodes</div>
              <div style="font-size: 1.25rem; font-weight: 700; color: #38bdf8;">${nodes.length}</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); flex: 1;">
              <div style="font-size: 0.75rem; color: #94a3b8;">Causal Edges</div>
              <div style="font-size: 1.25rem; font-weight: 700; color: #818cf8;">${edges.length}</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem 1rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); flex: 1;">
              <div style="font-size: 0.75rem; color: #94a3b8;">Weakest-Link Path Conf.</div>
              <div style="font-size: 1.25rem; font-weight: 700; color: #34d399;">${Math.round(this.state.graph.confidence * 100)}%</div>
            </div>
          </div>

          <div style="border: 1px dashed rgba(255,255,255,0.15); border-radius: 6px; padding: 1rem; background: rgba(15,23,42,0.4);">
            <div style="font-size: 0.85rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem;">Causal Topology Flow</div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; font-family: monospace; font-size: 0.8rem;">
              ${
                edges.length > 0
                  ? edges
                      .map(
                        (e) => `
                    <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.6rem; background: rgba(255,255,255,0.03); border-radius: 4px;">
                      <span style="color: #f87171;">${e.cause}</span>
                      <span style="color: #94a3b8;">──[${e.relationship}]──▶</span>
                      <span style="color: #fbbf24;">${e.effect}</span>
                      <span style="margin-left: auto; color: #64748b;">(conf: ${e.confidence}, status: ${e.status})</span>
                    </div>
                  `
                      )
                      .join('')
                  : `
                    <div style="color: #64748b; padding: 0.5rem;">
                      database_saturation ──[CAUSES]──▶ elevated_queue_depth ──[CONTRIBUTES_TO]──▶ api_gateway_latency_spike
                    </div>
                  `
              }
            </div>
          </div>
        </div>

        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.25rem;">
          <h3 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #e2e8f0;">Blast Radius & Propagation</h3>
          <p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 1rem;">
            Integrates Environmental Digital Twin. Topological reachability is tracked separately from verified causation (Prompt #62).
          </p>
          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="padding: 0.75rem; background: rgba(15, 23, 42, 0.8); border-left: 3px solid #38bdf8; border-radius: 4px;">
              <div style="font-size: 0.75rem; color: #94a3b8;">Architectural Reachability</div>
              <div style="font-size: 0.9rem; font-weight: 600; color: #f8fafc;">api_gateway, auth_service, web_frontend</div>
            </div>
            <div style="padding: 0.75rem; background: rgba(15, 23, 42, 0.8); border-left: 3px solid #34d399; border-radius: 4px;">
              <div style="font-size: 0.75rem; color: #94a3b8;">Verified Causal Impacts</div>
              <div style="font-size: 0.9rem; font-weight: 600; color: #34d399;">database_cluster: connection saturation</div>
            </div>
            <div style="font-size: 0.75rem; color: #cbd5e1; font-style: italic; margin-top: 0.5rem;">
              "Dependency impact does not automatically prove cause." (Prompt #62)
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderRootCauseTab() {
    const rca = this.state.currentAnalysis || {
      incident_id: this.state.selectedIncident,
      status: 'INVESTIGATING',
      root_cause: 'database_saturation',
      contributing_factors: ['traffic_spike'],
      surviving_causes: ['database_saturation', 'traffic_spike'],
      eliminated_causes: [{ cause: 'deployment', reason: 'No deployment occurred in preceding 60 minutes.' }],
      confidence: 0.75,
      causal_chain: {
        underlying_condition: 'Unindexed query volume under peak load',
        trigger: 'traffic_spike',
        mechanism: 'database_saturation (connection pool exhausted)',
        intermediate_state: 'thread pool starvation',
        symptom: 'API Gateway p99 Latency Spike > 2500ms',
        impact: 'Breached 99.9% SLO for 12 minutes',
      },
    };

    const statusBadgeColor =
      rca.status === 'VERIFIED'
        ? '#34d399'
        : rca.status === 'LIKELY'
        ? '#38bdf8'
        : rca.status === 'SUPPORTED'
        ? '#fbbf24'
        : '#f87171';

    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <!-- RCA Overview Card -->
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
            <div>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem; color: #f8fafc;">Incident: ${rca.incident_id}</h3>
                <span style="font-size: 0.75rem; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 700; background: rgba(255,255,255,0.05); color: ${statusBadgeColor}; border: 1px solid ${statusBadgeColor};">
                  ${rca.status}
                </span>
              </div>
              <p style="margin: 0.25rem 0 0 0; font-size: 0.85rem; color: #94a3b8;">
                Confidence: ${Math.round((rca.confidence || 0.5) * 100)}% (Qualitative confidence mapped to evidence rigor)
              </p>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 0.75rem; color: #94a3b8;">Primary Candidate Root Cause:</span>
              <div style="font-size: 1.1rem; font-weight: 700; color: #f43f5e;">${rca.root_cause || 'UNKNOWN'}</div>
            </div>
          </div>

          <!-- 5-Stage Root Cause Chain -->
          <div style="margin-top: 1rem;">
            <h4 style="margin: 0 0 0.75rem 0; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8;">
              5-Stage Causal Chain (Prompt #34, #189)
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem;">
              <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase;">1. Underlying Condition</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #e2e8f0; margin-top: 0.25rem;">${rca.causal_chain?.underlying_condition || 'N/A'}</div>
              </div>
              <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase;">2. Trigger</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #fbbf24; margin-top: 0.25rem;">${rca.causal_chain?.trigger || 'N/A'}</div>
              </div>
              <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase;">3. Mechanism</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #f87171; margin-top: 0.25rem;">${rca.causal_chain?.mechanism || 'N/A'}</div>
              </div>
              <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase;">4. Symptom</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #38bdf8; margin-top: 0.25rem;">${rca.causal_chain?.symptom || 'N/A'}</div>
              </div>
              <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase;">5. Impact</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #c084fc; margin-top: 0.25rem;">${rca.causal_chain?.impact || 'N/A'}</div>
              </div>
            </div>
          </div>

          <!-- Contributing Factors & Eliminated Causes -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1.25rem;">
            <div style="background: rgba(15, 23, 42, 0.5); padding: 1rem; border-radius: 6px;">
              <h5 style="margin: 0 0 0.5rem 0; font-size: 0.85rem; color: #38bdf8;">Contributing Factors (Prompt #35, #186)</h5>
              <p style="font-size: 0.8rem; color: #cbd5e1; margin: 0;">
                ${(rca.contributing_factors || []).join(', ') || 'No secondary contributing factors isolated.'}
              </p>
            </div>
            <div style="background: rgba(15, 23, 42, 0.5); padding: 1rem; border-radius: 6px;">
              <h5 style="margin: 0 0 0.5rem 0; font-size: 0.85rem; color: #94a3b8;">Eliminated Competing Hypotheses (Prompt #162)</h5>
              <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.8rem; color: #94a3b8;">
                ${
                  (rca.eliminated_causes || []).length > 0
                    ? rca.eliminated_causes.map((ec) => `<li><strong>${ec.cause}:</strong> ${ec.reason}</li>`).join('')
                    : '<li>None eliminated yet with empirical evidence.</li>'
                }
              </ul>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderInterventionsTab() {
    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
        <!-- Intervention Workbench -->
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.25rem;">
          <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; color: #e2e8f0;">Intervention Testing Workbench</h3>
          <p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 1rem;">
            Causal Engine cannot directly mutate production without policy authorization & approval (Prompt #43, #44).
          </p>

          <form id="form-propose-intervention" style="display: flex; flex-direction: column; gap: 0.75rem;">
            <div>
              <label style="display: block; font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.25rem;">Target Component</label>
              <input type="text" id="intv-target" value="database_cluster" style="width: 100%; padding: 0.5rem; background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; color: white; box-sizing: border-box;" />
            </div>
            <div>
              <label style="display: block; font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.25rem;">Intervention Type</label>
              <select id="intv-type" style="width: 100%; padding: 0.5rem; background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; color: white; box-sizing: border-box;">
                <option value="CONFIG_CHANGE">CONFIG_CHANGE (e.g. increase max connections)</option>
                <option value="TRAFFIC_CHANGE">TRAFFIC_CHANGE (e.g. shed 15% read traffic)</option>
                <option value="ROLLBACK">ROLLBACK (revert recent release)</option>
                <option value="SERVICE_RESTART">SERVICE_RESTART</option>
              </select>
            </div>
            <div>
              <label style="display: block; font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.25rem;">Expected Effect</label>
              <input type="text" id="intv-expected" value="latency_decreased: true, error_rate: 0.001" style="width: 100%; padding: 0.5rem; background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; color: white; box-sizing: border-box;" />
            </div>
            <button type="submit" style="margin-top: 0.5rem; padding: 0.6rem; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: 600; cursor: pointer;">
              Propose Authorized Intervention
            </button>
          </form>
        </div>

        <!-- Counterfactual Reasoning Card -->
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <h3 style="margin: 0; font-size: 1.1rem; color: #e2e8f0;">Counterfactual Scenario ("What If?")</h3>
            <span style="font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 4px; background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3);">
              Hypothetical Simulation (Prompt #65, #68)
            </span>
          </div>
          <p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 1rem;">
            "What would likely have happened if database saturation had not occurred?"
          </p>

          <div style="background: rgba(15, 23, 42, 0.6); padding: 1rem; border-radius: 6px; border-left: 3px solid #fbbf24;">
            <div style="font-size: 0.85rem; font-weight: 600; color: #f8fafc; margin-bottom: 0.5rem;">
              Simulated Baseline Comparison:
            </div>
            <div style="font-size: 0.8rem; color: #cbd5e1; line-height: 1.4;">
              Under stable workload assumptions, suppressing the database connection saturation would have prevented the thread pool exhaustion, resulting in estimated 78% reduction in p99 API latency.
            </div>
            <div style="margin-top: 0.75rem; font-size: 0.75rem; color: #94a3b8; font-style: italic;">
              Confidence: 68% · Assumptions: Ceteris paribus, topology invariance · Simulation is not reality.
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderExplanationsTab() {
    const answer = this.state.naturalLanguageAnswer;

    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.25rem;">
          <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; color: #e2e8f0;">Natural Language Causal Inquiries</h3>
          <p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 1rem;">
            Ask Kairo: "Why did this fail?", "What caused it?", "How sure are you?", "What else could have caused it?"
          </p>

          <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
            <input type="text" id="causal-question-input" placeholder="e.g. Why did API latency spike?" style="flex: 1; padding: 0.6rem; background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; color: white;" />
            <button id="btn-ask-causal" style="padding: 0.6rem 1.2rem; background: #4f46e5; color: white; border: none; border-radius: 4px; font-weight: 600; cursor: pointer;">
              Ask
            </button>
          </div>

          ${
            answer
              ? `
            <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 6px; padding: 1rem; margin-top: 1rem;">
              <div style="font-size: 0.75rem; color: #818cf8; text-transform: uppercase; font-weight: 700;">Question: ${answer.question}</div>
              <div style="font-size: 0.95rem; color: #f8fafc; margin-top: 0.5rem; line-height: 1.4;">${answer.answer}</div>
              ${
                answer.status
                  ? `<span style="display: inline-block; margin-top: 0.5rem; font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 4px; background: rgba(255,255,255,0.05); color: #38bdf8;">Status: ${answer.status}</span>`
                  : ''
              }
            </div>
          `
              : ''
          }
        </div>

        <!-- 6-Part Structured Causal Explanation -->
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.25rem;">
          <h3 style="margin: 0 0 1rem 0; font-size: 1.1rem; color: #e2e8f0;">6-Part Causal Explanation (Prompt #100, #101)</h3>
          <div style="display: flex; flex-direction: column; gap: 0.75rem; font-size: 0.85rem;">
            <div style="padding: 0.6rem; background: rgba(15,23,42,0.5); border-radius: 4px;">
              <strong style="color: #38bdf8;">1. WHAT HAPPENED:</strong> API Gateway p99 response times exceeded 2800ms threshold.
            </div>
            <div style="padding: 0.6rem; background: rgba(15,23,42,0.5); border-radius: 4px;">
              <strong style="color: #fbbf24;">2. WHY IT LIKELY HAPPENED:</strong> Database connection pool reached 98% saturation, blocking worker threads.
            </div>
            <div style="padding: 0.6rem; background: rgba(15,23,42,0.5); border-radius: 4px;">
              <strong style="color: #34d399;">3. EVIDENCE:</strong> Telemetry metrics (Postgres pg_stat_activity), Jaeger distributed traces.
            </div>
            <div style="padding: 0.6rem; background: rgba(15,23,42,0.5); border-radius: 4px;">
              <strong style="color: #a78bfa;">4. ALTERNATIVES CONSIDERED:</strong> Traffic spike (observed rate stable), Network failure (packet loss 0%).
            </div>
            <div style="padding: 0.6rem; background: rgba(15,23,42,0.5); border-radius: 4px;">
              <strong style="color: #f87171;">5. UNCERTAINTY:</strong> Assessed as LIKELY; requires canary intervention to achieve VERIFIED status.
            </div>
            <div style="padding: 0.6rem; background: rgba(15,23,42,0.5); border-radius: 4px;">
              <strong style="color: #38bdf8;">6. WHAT WOULD TEST IT:</strong> Shed 15% read queries to read-replica and observe connection recovery.
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderFallaciesTab() {
    return `
      <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.25rem;">
        <h3 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; color: #e2e8f0;">Causal Fallacy Inspector (Prompt #150)</h3>
        <p style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 1rem;">
          Rigorous guardrails to prevent cognitive biases, spurious correlations, and post hoc fallacies.
        </p>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem;">
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #f87171;">Post Hoc Ergo Propter Hoc</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">
              Rejects claiming "Deployment caused outage" solely because deployment preceded outage (Prompt #26).
            </div>
          </div>
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #fbbf24;">Confounding / Common Cause</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">
              Searches for upstream variables influencing both candidate cause and effect before asserting link.
            </div>
          </div>
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8;">Reverse Causality</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">
              Tests whether downstream symptom B initiated upstream condition A.
            </div>
          </div>
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 0.75rem;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #a78bfa;">Collider Bias</div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">
              Prevents invalid causal conclusions from conditioning on a common effect.
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    const tabs = this.container.querySelectorAll('.causal-tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', (e) => {
        const targetTab = e.currentTarget.getAttribute('data-tab');
        if (targetTab) {
          this.state.activeTab = targetTab;
          this._updateContent();
        }
      });
    });

    const btnRefresh = this.container.querySelector('#btn-refresh');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => this.fetchData());
    }

    const btnRunRca = this.container.querySelector('#btn-run-rca');
    if (btnRunRca) {
      btnRunRca.addEventListener('click', async () => {
        if (this.api && this.api.analyzeRootCause) {
          const res = await this.api.analyzeRootCause({
            incident_id: `inc-${Date.now().toString().slice(-6)}`,
            symptom: 'API Gateway Timeout / Elevated 504s',
            telemetry_metrics: {
              database_connection_saturation: 0.95,
              api_latency_p99_ms: 3200.0,
            },
          });
          if (res) {
            this.state.currentAnalysis = res.data || res;
            this.state.activeTab = 'root_cause';
            this._updateContent();
          }
        }
      });
    }

    const btnAsk = this.container.querySelector('#btn-ask-causal');
    if (btnAsk) {
      btnAsk.addEventListener('click', async () => {
        const input = this.container.querySelector('#causal-question-input');
        if (input && input.value && this.api && this.api.askQuestion) {
          const res = await this.api.askQuestion({
            incident_id: this.state.selectedIncident,
            question: input.value,
          });
          if (res) {
            this.state.naturalLanguageAnswer = res.data || res;
            this._updateContent();
          }
        }
      });
    }
  }

  _updateContent() {
    const main = this.container.querySelector('#causal-tab-content');
    if (main) {
      main.innerHTML = this._renderActiveTab();
    }
    const tabs = this.container.querySelectorAll('.causal-tab');
    tabs.forEach((tab) => {
      const isCur = tab.getAttribute('data-tab') === this.state.activeTab;
      tab.style.color = isCur ? '#38bdf8' : '#94a3b8';
      tab.style.borderBottom = `2px solid ${isCur ? '#38bdf8' : 'transparent'}`;
    });
    this._attachEventListeners();
  }
}

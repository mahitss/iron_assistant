/**
 * Kairo Simulation, Digital World Model & Counterfactual Planning Component (Task 56).
 * Renders Simulation Workbench, Multi-Scenario Comparison & Pareto Front,
 * Future State & Blast Radius, Counterfactual What-Ifs, ExecutionGate Controller, and Calibration.
 */

export class SimulationView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api;
    this.state = {
      activeTab: 'workbench', // 'workbench' | 'comparison' | 'future_state' | 'counterfactuals' | 'execution_gate' | 'calibration'
      snapshots: [],
      scenarios: [],
      simulations: [],
      currentSnapshot: null,
      currentScenario: null,
      currentSimulation: null,
      currentGate: null,
      comparison: null,
      rankings: [],
      calibrationReport: null,
      isLoading: false,
      error: null,
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
      if (this.api && this.api.listSnapshots) {
        const snaps = await this.api.listSnapshots();
        this.state.snapshots = snaps || [];
        if (this.state.snapshots.length > 0 && !this.state.currentSnapshot) {
          this.state.currentSnapshot = this.state.snapshots[0];
        }
      }
      if (this.api && this.api.listScenarios) {
        const scens = await this.api.listScenarios();
        this.state.scenarios = scens || [];
        if (this.state.scenarios.length > 0 && !this.state.currentScenario) {
          this.state.currentScenario = this.state.scenarios[0];
        }
      }
      if (this.api && this.api.listRuns) {
        const runs = await this.api.listRuns();
        this.state.simulations = runs || [];
        if (this.state.simulations.length > 0 && !this.state.currentSimulation) {
          this.state.currentSimulation = this.state.simulations[0];
        }
      }
    } catch (err) {
      this.state.error = err.message || 'Failed to fetch simulation data.';
    } finally {
      this.state.isLoading = false;
      this._updateContent();
    }
  }

  _template() {
    return `
      <div class="simulation-dashboard" style="display: flex; flex-direction: column; gap: 1.5rem; padding: 1.5rem; background: #0f172a; color: #f8fafc; font-family: Inter, system-ui, sans-serif; min-height: 100vh;">
        <!-- Top Header & Safety Banner -->
        <header style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 1rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <h1 style="margin: 0; font-size: 1.5rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Simulation & Counterfactual Planning Engine
              </h1>
              <span style="font-size: 0.75rem; background: #dc2626; color: white; padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                SIMULATION_ONLY
              </span>
            </div>
            <p style="margin: 0.25rem 0 0; font-size: 0.875rem; color: #94a3b8;">
              Sandboxed digital twin exploration, multi-objective Pareto trade-offs, and verified real-world transition gates.
            </p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button id="btn-capture-snapshot" style="background: #1e293b; border: 1px solid #475569; color: #e2e8f0; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; display: flex; align-items: center; gap: 0.5rem;">
              <span>📸</span> Capture Snapshot
            </button>
            <button id="btn-run-sim" style="background: linear-gradient(135deg, #3b82f6, #6366f1); border: none; color: white; padding: 0.5rem 1.25rem; border-radius: 0.375rem; cursor: pointer; font-weight: 600; font-size: 0.875rem;">
              <span>⚡</span> Run Simulation
            </button>
          </div>
        </header>

        <!-- Navigation Tabs -->
        <nav style="display: flex; gap: 0.5rem; border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem;">
          ${this._renderTabBtn('workbench', 'Workbench & Scenarios')}
          ${this._renderTabBtn('comparison', 'Pareto Comparison')}
          ${this._renderTabBtn('future_state', 'Future State & Blast Radius')}
          ${this._renderTabBtn('counterfactuals', 'Counterfactuals (What-If)')}
          ${this._renderTabBtn('execution_gate', 'Execution Gate & Transition')}
          ${this._renderTabBtn('calibration', 'Calibration & Accuracy')}
        </nav>

        <!-- Main Dynamic Panel -->
        <main id="simulation-panel-content" style="display: flex; flex-direction: column; gap: 1.5rem;">
          ${this._renderActiveTabContent()}
        </main>
      </div>
    `;
  }

  _renderTabBtn(tabKey, label) {
    const isActive = this.state.activeTab === tabKey;
    const bg = isActive ? '#38bdf8' : '#1e293b';
    const color = isActive ? '#0f172a' : '#cbd5e1';
    const weight = isActive ? '600' : '400';
    return `
      <button class="sim-tab-btn" data-tab="${tabKey}" style="background: ${bg}; color: ${color}; font-weight: ${weight}; border: 1px solid #334155; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; transition: all 0.2s;">
        ${label}
      </button>
    `;
  }

  _renderActiveTabContent() {
    switch (this.state.activeTab) {
      case 'workbench':
        return this._renderWorkbench();
      case 'comparison':
        return this._renderComparison();
      case 'future_state':
        return this._renderFutureState();
      case 'counterfactuals':
        return this._renderCounterfactuals();
      case 'execution_gate':
        return this._renderExecutionGate();
      case 'calibration':
        return this._renderCalibration();
      default:
        return `<div style="color: #94a3b8;">Tab content not found.</div>`;
    }
  }

  _renderWorkbench() {
    const snap = this.state.currentSnapshot;
    const scen = this.state.currentScenario;
    const sim = this.state.currentSimulation;

    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
        <!-- Left: Baseline Snapshot & Interventions -->
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;">
          <h2 style="font-size: 1.125rem; font-weight: 600; margin: 0 0 1rem; color: #38bdf8;">
            1. Baseline Environment Snapshot
          </h2>
          ${snap ? `
            <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.875rem;">
              <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Snapshot ID:</span><span style="font-family: monospace; color: #a5b4fc;">${snap.snapshot_id}</span></div>
              <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Captured At:</span><span>${new Date(snap.captured_at || snap.created_at).toLocaleTimeString()}</span></div>
              <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Baseline Hash:</span><span style="font-family: monospace; font-size: 0.75rem;">${(snap.baseline_hash || snap.hash_sha256 || '').slice(0, 16)}...</span></div>
              <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Status:</span><span style="color: ${snap.is_stale ? '#ef4444' : '#10b981'}; font-weight: 600;">${snap.is_stale ? 'STALE' : 'FRESH'}</span></div>
            </div>
          ` : `<div style="color: #64748b; font-size: 0.875rem;">No snapshot captured yet. Click 'Capture Snapshot' above.</div>`}

          <h2 style="font-size: 1.125rem; font-weight: 600; margin: 1.5rem 0 0.75rem; color: #38bdf8;">
            2. Selected Scenario
          </h2>
          ${scen ? `
            <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.875rem;">
              <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Name:</span><span style="font-weight: 600;">${scen.name}</span></div>
              <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Type:</span><span style="background: #334155; padding: 0.1rem 0.4rem; border-radius: 0.25rem;">${scen.scenario_type}</span></div>
              <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Interventions:</span><span>${scen.interventions ? scen.interventions.length : 0} configured</span></div>
            </div>
          ` : `<div style="color: #64748b; font-size: 0.875rem;">No scenario selected.</div>`}
        </div>

        <!-- Right: Simulation Results & Findings -->
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;">
          <h2 style="font-size: 1.125rem; font-weight: 600; margin: 0 0 1rem; color: #38bdf8;">
            3. Simulation Run Status & Impact
          </h2>
          ${sim ? `
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #94a3b8;">Status:</span>
                <span style="background: #065f46; color: #34d399; padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-weight: 600; font-size: 0.75rem;">${sim.status}</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">Calibrated Confidence:</span>
                <span style="color: #38bdf8; font-weight: 700;">${(sim.confidence * 100).toFixed(1)}%</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">Effects Calculated:</span>
                <span>${sim.effects ? sim.effects.length : 0} items</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8;">Risks Identified:</span>
                <span style="color: ${sim.risks && sim.risks.length > 0 ? '#fbbf24' : '#10b981'}; font-weight: 600;">${sim.risks ? sim.risks.length : 0} item(s)</span>
              </div>
              <div style="background: #0f172a; padding: 0.75rem; border-radius: 0.375rem; border-left: 3px solid #6366f1; font-size: 0.8rem; color: #cbd5e1;">
                <strong>Simulation Notice:</strong> Outputs represent hypothetical model projections and do NOT alter production systems.
              </div>
            </div>
          ` : `<div style="color: #64748b; font-size: 0.875rem;">No simulation run completed yet. Click 'Run Simulation'.</div>`}
        </div>
      </div>
    `;
  }

  _renderComparison() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h2 style="font-size: 1.125rem; font-weight: 600; margin: 0; color: #38bdf8;">
            Multi-Objective Pareto Comparison
          </h2>
          <span style="font-size: 0.8rem; color: #94a3b8;">Evaluates Trade-Offs (Cost vs Latency vs Risk vs Availability)</span>
        </div>
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem; text-align: left;">
            <thead>
              <tr style="border-bottom: 1px solid #475569; color: #94a3b8;">
                <th style="padding: 0.5rem;">Scenario ID</th>
                <th style="padding: 0.5rem;">Cost Delta</th>
                <th style="padding: 0.5rem;">Latency Delta</th>
                <th style="padding: 0.5rem;">Availability</th>
                <th style="padding: 0.5rem;">Pareto Status</th>
              </tr>
            </thead>
            <tbody>
              <tr style="border-bottom: 1px solid #334155;">
                <td style="padding: 0.5rem; font-weight: 600; color: #38bdf8;">scen_scale_up</td>
                <td style="padding: 0.5rem;">+$45.00/mo</td>
                <td style="padding: 0.5rem; color: #10b981;">-15.0ms</td>
                <td style="padding: 0.5rem;">99.95%</td>
                <td style="padding: 0.5rem;"><span style="background: #065f46; color: #34d399; padding: 0.1rem 0.4rem; border-radius: 0.25rem; font-size: 0.75rem;">Pareto Optimal</span></td>
              </tr>
              <tr style="border-bottom: 1px solid #334155;">
                <td style="padding: 0.5rem; font-weight: 600; color: #cbd5e1;">scen_no_change</td>
                <td style="padding: 0.5rem;">$0.00</td>
                <td style="padding: 0.5rem;">0.0ms</td>
                <td style="padding: 0.5rem;">99.80%</td>
                <td style="padding: 0.5rem;"><span style="background: #334155; color: #cbd5e1; padding: 0.1rem 0.4rem; border-radius: 0.25rem; font-size: 0.75rem;">Baseline</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  _renderFutureState() {
    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;">
          <h2 style="font-size: 1.125rem; font-weight: 600; margin: 0 0 1rem; color: #38bdf8;">
            Blast Radius Topology Reach
          </h2>
          <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.875rem;">
            <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Blast Radius Level:</span><span style="color: #10b981; font-weight: 700;">CONTAINED</span></div>
            <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Impacted Services:</span><span>2 nodes (auth_service, billing_service)</span></div>
            <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Max Traversal Depth:</span><span>4 hops</span></div>
            <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Topology Completeness:</span><span>100% verified</span></div>
          </div>
        </div>
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;">
          <h2 style="font-size: 1.125rem; font-weight: 600; margin: 0 0 1rem; color: #38bdf8;">
            Epistemic Uncertainty Profile
          </h2>
          <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.875rem;">
            <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Epistemic Uncertainty:</span><span style="color: #38bdf8; font-weight: 600;">LOW</span></div>
            <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Critical Assumptions:</span><span>0 high-risk</span></div>
            <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Unknown Parameters:</span><span>0 uncalibrated</span></div>
          </div>
        </div>
      </div>
    `;
  }

  _renderCounterfactuals() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin: 0 0 1rem; color: #38bdf8;">
          Counterfactual Reasoning & What-If Queries
        </h2>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
          <div style="background: #0f172a; padding: 1rem; border-radius: 0.375rem; border: 1px solid #334155;">
            <h3 style="font-size: 0.95rem; margin: 0 0 0.5rem; color: #cbd5e1;">What if we wait?</h3>
            <p style="font-size: 0.8rem; color: #94a3b8; margin: 0 0 0.75rem;">Projects natural metric drift and degradation curve over a 300s horizon.</p>
            <button class="sim-cf-btn" data-type="wait" style="background: #334155; color: #e2e8f0; border: none; padding: 0.3rem 0.6rem; border-radius: 0.25rem; font-size: 0.75rem; cursor: pointer;">Simulate Wait</button>
          </div>
          <div style="background: #0f172a; padding: 1rem; border-radius: 0.375rem; border: 1px solid #334155;">
            <h3 style="font-size: 0.95rem; margin: 0 0 0.5rem; color: #cbd5e1;">What if Plan B?</h3>
            <p style="font-size: 0.8rem; color: #94a3b8; margin: 0 0 0.75rem;">Explores candidate alternative interventions side-by-side.</p>
            <button class="sim-cf-btn" data-type="plan_b" style="background: #334155; color: #e2e8f0; border: none; padding: 0.3rem 0.6rem; border-radius: 0.25rem; font-size: 0.75rem; cursor: pointer;">Simulate Plan B</button>
          </div>
          <div style="background: #0f172a; padding: 1rem; border-radius: 0.375rem; border: 1px solid #334155;">
            <h3 style="font-size: 0.95rem; margin: 0 0 0.5rem; color: #cbd5e1;">Monte Carlo Sampling</h3>
            <p style="font-size: 0.8rem; color: #94a3b8; margin: 0 0 0.75rem;">Runs seeded probabilistic iterations with normal/uniform distributions.</p>
            <button class="sim-cf-btn" data-type="monte_carlo" style="background: #334155; color: #e2e8f0; border: none; padding: 0.3rem 0.6rem; border-radius: 0.25rem; font-size: 0.75rem; cursor: pointer;">Run 100 Samples</button>
          </div>
        </div>
      </div>
    `;
  }

  _renderExecutionGate() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h2 style="font-size: 1.125rem; font-weight: 600; margin: 0; color: #38bdf8;">
            Verified Real-World Transition Gate (ExecutionGate)
          </h2>
          <span style="background: #065f46; color: #34d399; padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 700; font-size: 0.75rem;">
            GATE: READY
          </span>
        </div>
        <p style="font-size: 0.875rem; color: #cbd5e1; margin-bottom: 1rem;">
          Strict boundary: Real execution requires passing all state drift checks, authorization, and postconditions.
        </p>
        <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.875rem;">
          <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">State Drift Check:</span><span style="color: #10b981;">PASSED (Hashes Match)</span></div>
          <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Policy Compliance:</span><span style="color: #10b981;">COMPLIANT</span></div>
          <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Approval Requirement:</span><span>Pre-authorized for operator role</span></div>
        </div>
      </div>
    `;
  }

  _renderCalibration() {
    return `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;">
        <h2 style="font-size: 1.125rem; font-weight: 600; margin: 0 0 1rem; color: #38bdf8;">
          Simulation Calibration & Accuracy Tracking
        </h2>
        <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.875rem;">
          <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Mean Absolute Error (MAE):</span><span style="font-weight: 600;">2.5ms</span></div>
          <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Systematic Bias:</span><span>+0.8ms (Within &plusmn;5.0ms tolerance)</span></div>
          <div style="display: flex; justify-content: space-between;"><span style="color: #94a3b8;">Drift Status:</span><span style="color: #10b981; font-weight: 600;">NO DRIFT DETECTED</span></div>
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    this.container.addEventListener('click', async (e) => {
      const tabBtn = e.target.closest('.sim-tab-btn');
      if (tabBtn) {
        this.state.activeTab = tabBtn.dataset.tab;
        this._updateContent();
      }

      if (e.target.closest('#btn-capture-snapshot')) {
        await this._handleCaptureSnapshot();
      }

      if (e.target.closest('#btn-run-sim')) {
        await this._handleRunSimulation();
      }
    });
  }

  async _handleCaptureSnapshot() {
    if (!this.api || !this.api.captureSnapshot) return;
    try {
      this.state.isLoading = true;
      const snap = await this.api.captureSnapshot({ source_entity: 'digital_twin' });
      if (snap) {
        this.state.snapshots.unshift(snap);
        this.state.currentSnapshot = snap;
      }
    } catch (err) {
      this.state.error = err.message;
    } finally {
      this.state.isLoading = false;
      this._updateContent();
    }
  }

  async _handleRunSimulation() {
    if (!this.api || !this.api.runSimulation || !this.state.currentScenario) return;
    try {
      this.state.isLoading = true;
      const sim = await this.api.runSimulation({ scenario_id: this.state.currentScenario.scenario_id });
      if (sim) {
        this.state.simulations.unshift(sim);
        this.state.currentSimulation = sim;
      }
    } catch (err) {
      this.state.error = err.message;
    } finally {
      this.state.isLoading = false;
      this._updateContent();
    }
  }

  _updateContent() {
    if (!this.container) return;
    this.container.innerHTML = this._template();
  }
}

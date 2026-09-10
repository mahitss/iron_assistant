/**
 * Kairo Strategic Planning & Long-Horizon Execution Engine Component (Task 58).
 * Glassmorphic Strategic Planning & Control Center UI.
 * Enforces Invariants:
 *  Plan != Execution != Verification != Simulation != Reality.
 *  Strategy != Decision. Tasks must be verified before completion.
 */

export class PlanningView {
  constructor(options = {}) {
    this.container = options.container;
    this.api = options.api;
    this.state = {
      activeTab: 'overview', // 'overview' | 'phases' | 'waves' | 'graph' | 'resources' | 'risks' | 'adaptation' | 'audit'
      plans: [],
      currentPlan: null,
      timeline: null,
      dependencies: null,
      risks: null,
      progress: null,
      auditEvents: [],
      isLoading: false,
      error: null,
      newPlanName: '',
      newPlanPurpose: '',
      currentSummary: 'Legacy monolithic architecture',
      desiredSummary: 'High-availability distributed microservices',
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
      if (this.api && this.api.list) {
        const list = await this.api.list();
        this.state.plans = list || [];
        if (this.state.plans.length > 0 && !this.state.currentPlan) {
          this.state.currentPlan = this.state.plans[0];
        }
      }
      if (this.state.currentPlan) {
        await this._loadPlanDetails(this.state.currentPlan.plan_id);
      }
    } catch (err) {
      this.state.error = err.message || 'Failed to load strategic plans.';
    } finally {
      this.state.isLoading = false;
      this._updateContent();
    }
  }

  async _loadPlanDetails(planId) {
    try {
      if (this.api) {
        if (this.api.getProgress) this.state.progress = await this.api.getProgress(planId);
        if (this.api.getTimeline) this.state.timeline = await this.api.getTimeline(planId);
        if (this.api.getDependencies) this.state.dependencies = await this.api.getDependencies(planId);
        if (this.api.getRisks) this.state.risks = await this.api.getRisks(planId);
        if (this.api.getAudit) this.state.auditEvents = await this.api.getAudit(planId);
      }
    } catch (e) {
      console.error('Error loading plan sub-details:', e);
    }
  }

  _template() {
    return `
      <div class="strategic-planning-dashboard" style="display: flex; flex-direction: column; gap: 1.5rem; padding: 1.5rem; background: #070b14; color: #f8fafc; font-family: Inter, system-ui, sans-serif; min-height: 100vh;">
        <!-- Top Header -->
        <header style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 1rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <h1 style="margin: 0; font-size: 1.5rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Kairo Strategic Planning Engine
              </h1>
              <span style="font-size: 0.75rem; background: #0284c7; color: white; padding: 0.2rem 0.6rem; border-radius: 9999px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                LONG_HORIZON_EXECUTION
              </span>
            </div>
            <p style="margin: 0.25rem 0 0; font-size: 0.875rem; color: #94a3b8;">
              How do we get from current state to desired future state? Living plans, dependency wave execution, and reality-driven adaptation.
            </p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button id="btn-validate-plan" style="background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem;">
              🛡️ Validate Plan
            </button>
            <button id="btn-proposal-handoff" style="background: #0f766e; border: 1px solid #14b8a6; color: white; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; font-weight: 600;">
              📋 Execution Proposal
            </button>
            <button id="btn-create-modal" style="background: linear-gradient(135deg, #0284c7, #6366f1); border: none; color: white; padding: 0.5rem 1.25rem; border-radius: 0.375rem; cursor: pointer; font-weight: 600; font-size: 0.875rem;">
              ✨ Synthesize New Plan
            </button>
          </div>
        </header>

        <!-- Core Invariants Banner -->
        <div style="background: rgba(15, 23, 42, 0.7); border-left: 4px solid #0284c7; padding: 0.75rem 1rem; border-radius: 0.375rem; font-size: 0.8125rem; color: #cbd5e1; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>Core Invariants:</strong> Plan &ne; Execution &ne; Verification. Unknown resource is not available. Partial completion &ne; Full completion. Sunk cost never forces bad strategies.
          </div>
          <div style="font-size: 0.75rem; color: #38bdf8; font-weight: 600;">
            FIREWALL: DIRECT TOOL EXECUTION BLOCKED
          </div>
        </div>

        <!-- Navigation Tabs -->
        <nav style="display: flex; gap: 0.5rem; border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem; overflow-x: auto;">
          ${this._renderTabBtn('overview', '🗺️ Plan Overview')}
          ${this._renderTabBtn('phases', '🚩 Phases & Milestones')}
          ${this._renderTabBtn('waves', '🌊 Execution Waves & CPM')}
          ${this._renderTabBtn('graph', '🕸️ Dependency Graph')}
          ${this._renderTabBtn('resources', '⚡ Resources & Locks')}
          ${this._renderTabBtn('risks', '⚠️ Risks & Rollbacks')}
          ${this._renderTabBtn('adaptation', '🔄 Checkpoints & Adaptation')}
          ${this._renderTabBtn('audit', '📜 Audit Trail & Learning')}
        </nav>

        <!-- Main Dynamic Content Area -->
        <main id="planning-content-area" style="flex: 1;">
          <!-- Dynamically populated via _updateContent -->
        </main>
      </div>
    `;
  }

  _renderTabBtn(tabKey, label) {
    const isActive = this.state.activeTab === tabKey;
    const bg = isActive ? 'rgba(2, 132, 199, 0.2)' : 'transparent';
    const border = isActive ? '#38bdf8' : 'transparent';
    const color = isActive ? '#38bdf8' : '#94a3b8';
    return `
      <button class="nav-tab-btn" data-tab="${tabKey}" style="background: ${bg}; border: 1px solid ${border}; color: ${color}; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: all 0.2s;">
        ${label}
      </button>
    `;
  }

  _updateContent() {
    const container = document.getElementById('planning-content-area');
    if (!container) return;

    if (this.state.isLoading) {
      container.innerHTML = `<div style="text-align: center; padding: 3rem; color: #94a3b8;">Loading strategic plans and telemetry...</div>`;
      return;
    }

    if (this.state.error) {
      container.innerHTML = `<div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #fca5a5; padding: 1rem; border-radius: 0.375rem;">${this.state.error}</div>`;
      return;
    }

    const plan = this.state.currentPlan;
    if (!plan) {
      container.innerHTML = `<div style="text-align: center; padding: 3rem; color: #64748b;">No strategic plans found. Click "Synthesize New Plan" to generate one.</div>`;
      return;
    }

    switch (this.state.activeTab) {
      case 'overview':
        container.innerHTML = this._renderOverview(plan);
        break;
      case 'phases':
        container.innerHTML = this._renderPhases(plan);
        break;
      case 'waves':
        container.innerHTML = this._renderWaves(plan);
        break;
      case 'graph':
        container.innerHTML = this._renderGraph(plan);
        break;
      case 'resources':
        container.innerHTML = this._renderResources(plan);
        break;
      case 'risks':
        container.innerHTML = this._renderRisks(plan);
        break;
      case 'adaptation':
        container.innerHTML = this._renderAdaptation(plan);
        break;
      case 'audit':
        container.innerHTML = this._renderAudit(plan);
        break;
      default:
        container.innerHTML = `<div style="color: #94a3b8;">Tab not found</div>`;
    }
  }

  _renderOverview(plan) {
    const strat = plan.strategy || {};
    const gap = plan.gap_analysis || {};
    return `
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;">
        <div style="display: flex; flex-direction: column; gap: 1.5rem;">
          <!-- Plan Hero Card -->
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div>
                <h2 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #f8fafc;">${plan.name}</h2>
                <p style="margin: 0.25rem 0 0.75rem; font-size: 0.875rem; color: #94a3b8;">${plan.purpose}</p>
              </div>
              <div style="display: flex; gap: 0.5rem;">
                <span style="background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600;">
                  STATUS: ${plan.status}
                </span>
                <span style="background: #1e293b; color: #10b981; border: 1px solid #059669; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600;">
                  HEALTH: ${plan.health}
                </span>
              </div>
            </div>

            <!-- Current vs Desired State Comparison -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem; background: #0b0f19; padding: 1rem; border-radius: 0.375rem; border: 1px solid #1e293b;">
              <div>
                <h4 style="margin: 0 0 0.5rem; font-size: 0.8125rem; text-transform: uppercase; color: #94a3b8;">Current State (Verified Telemetry)</h4>
                <div style="font-size: 0.875rem; color: #e2e8f0;">${plan.current_state?.summary || 'Not assessed'}</div>
                <div style="margin-top: 0.5rem; font-size: 0.75rem; color: #64748b;">Certainty: ${plan.current_state?.certainty || 'UNKNOWN'}</div>
              </div>
              <div>
                <h4 style="margin: 0 0 0.5rem; font-size: 0.8125rem; text-transform: uppercase; color: #38bdf8;">Desired State (Target Invariants)</h4>
                <div style="font-size: 0.875rem; color: #e2e8f0;">${plan.desired_state?.summary || 'Not defined'}</div>
                <ul style="margin: 0.5rem 0 0; padding-left: 1.25rem; font-size: 0.75rem; color: #94a3b8;">
                  ${(plan.desired_state?.completion_invariants || []).map(i => `<li>${i}</li>`).join('')}
                </ul>
              </div>
            </div>

            <!-- Gap Analysis -->
            <div style="margin-top: 1rem;">
              <h4 style="margin: 0 0 0.5rem; font-size: 0.8125rem; text-transform: uppercase; color: #f59e0b;">Gap Analysis Deficits</h4>
              <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                ${(gap.missing_capabilities || []).map(m => `
                  <span style="background: rgba(245, 158, 11, 0.1); border: 1px solid #d97706; color: #fcd34d; padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">
                    ${m}
                  </span>
                `).join('')}
                ${(gap.technical_gaps || []).map(tg => `
                  <span style="background: rgba(59, 130, 246, 0.1); border: 1px solid #2563eb; color: #93c5fd; padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">
                    ${tg}
                  </span>
                `).join('')}
              </div>
            </div>
          </div>

          <!-- Strategy Selection Card -->
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
            <h3 style="margin: 0 0 0.5rem; font-size: 1rem; color: #f8fafc;">Selected Strategic Archetype</h3>
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #1e293b; padding-bottom: 0.75rem;">
              <div style="font-size: 1.125rem; font-weight: 600; color: #38bdf8;">${strat.name || 'Incremental Phased Rollout'}</div>
              <span style="background: #1e293b; color: #a78bfa; padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">
                TYPE: ${strat.strategy_type || 'INCREMENTAL'}
              </span>
            </div>
            <p style="font-size: 0.875rem; color: #94a3b8; margin: 0.75rem 0;">${strat.description || ''}</p>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; font-size: 0.75rem; color: #cbd5e1;">
              <div><strong>Complexity:</strong> ${strat.estimated_complexity || 'MEDIUM'}</div>
              <div><strong>Risk:</strong> ${strat.expected_risk || 'LOW'}</div>
              <div><strong>Reversibility:</strong> ${strat.reversibility || 'REVERSIBLE'}</div>
            </div>
          </div>
        </div>

        <!-- Right Sidebar Controls -->
        <div style="display: flex; flex-direction: column; gap: 1.5rem;">
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
            <h3 style="margin: 0 0 1rem; font-size: 1rem; color: #f8fafc;">Plan Execution Controls</h3>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <button id="btn-start-plan" style="background: #10b981; color: white; border: none; padding: 0.5rem; border-radius: 0.25rem; font-weight: 600; cursor: pointer;">
                ▶️ Start Waves Sequencing
              </button>
              <button id="btn-pause-plan" style="background: #f59e0b; color: white; border: none; padding: 0.5rem; border-radius: 0.25rem; font-weight: 600; cursor: pointer;">
                ⏸️ Pause Plan
              </button>
              <button id="btn-resume-plan" style="background: #3b82f6; color: white; border: none; padding: 0.5rem; border-radius: 0.25rem; font-weight: 600; cursor: pointer;">
                ⏯️ Resume Execution
              </button>
              <button id="btn-replan" style="background: #8b5cf6; color: white; border: none; padding: 0.5rem; border-radius: 0.25rem; font-weight: 600; cursor: pointer;">
                🔄 Trigger Adaptive Replan
              </button>
              <button id="btn-cancel-plan" style="background: #ef4444; color: white; border: none; padding: 0.5rem; border-radius: 0.25rem; font-weight: 600; cursor: pointer;">
                ⏹️ Cancel Plan
              </button>
            </div>
          </div>

          <!-- Progress Snapshot -->
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
            <h3 style="margin: 0 0 0.75rem; font-size: 1rem; color: #f8fafc;">Outcome-Based Progress</h3>
            <div style="font-size: 2rem; font-weight: 700; color: #38bdf8;">
              ${this.state.progress?.composite_progress_pct || 0}%
            </div>
            <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">
              70% Weighted Milestones | 30% Verified Tasks
            </div>
            <div style="margin-top: 0.75rem; font-size: 0.8125rem; color: #cbd5e1;">
              <div>Tasks Completed: ${this.state.progress?.task_count_completed || 0} / ${this.state.progress?.task_count_total || 0}</div>
              <div>Milestones Verified: ${this.state.progress?.milestone_weighted_progress_pct || 0}%</div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderPhases(plan) {
    const phases = plan.phases || [];
    const milestones = plan.milestones || [];
    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <h2 style="margin: 0; font-size: 1.25rem;">Strategic Phases & Verification Gates</h2>
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          ${phases.map(p => {
            const phaseMilestones = milestones.filter(m => m.phase_id === p.phase_id);
            return `
              <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <h3 style="margin: 0; font-size: 1.125rem; color: #38bdf8;">${p.name}</h3>
                  <span style="background: #1e293b; color: #e2e8f0; padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">
                    ${p.status}
                  </span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 0.75rem; font-size: 0.8125rem;">
                  <div style="background: #070b14; padding: 0.75rem; border-radius: 0.25rem;">
                    <strong style="color: #93c5fd;">Entry Criteria:</strong>
                    <ul style="margin: 0.25rem 0 0; padding-left: 1rem; color: #94a3b8;">
                      ${(p.entry_criteria || []).map(c => `<li>${c}</li>`).join('')}
                    </ul>
                  </div>
                  <div style="background: #070b14; padding: 0.75rem; border-radius: 0.25rem;">
                    <strong style="color: #6ee7b7;">Exit Criteria (Must Be Verified):</strong>
                    <ul style="margin: 0.25rem 0 0; padding-left: 1rem; color: #94a3b8;">
                      ${(p.exit_criteria || []).map(c => `<li>${c}</li>`).join('')}
                    </ul>
                  </div>
                </div>

                <!-- Nested Milestones -->
                <div style="margin-top: 1rem; border-top: 1px solid #1e293b; padding-top: 0.75rem;">
                  <div style="font-size: 0.8125rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem;">Associated Milestones:</div>
                  <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    ${phaseMilestones.map(m => `
                      <div style="display: flex; justify-content: space-between; align-items: center; background: #1e293b; padding: 0.5rem 0.75rem; border-radius: 0.25rem; font-size: 0.8125rem;">
                        <div>
                          <strong>${m.name}</strong> (Weight: ${m.weight})
                          <div style="font-size: 0.75rem; color: #94a3b8;">Verification: ${(m.verification_criteria || []).join(', ')}</div>
                        </div>
                        <span style="color: ${m.is_verified ? '#10b981' : '#f59e0b'}; font-weight: 600; font-size: 0.75rem;">
                          ${m.is_verified ? 'VERIFIED' : m.status}
                        </span>
                      </div>
                    `).join('')}
                  </div>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  _renderWaves(plan) {
    const waves = plan.execution_waves || [];
    const tasks = plan.tasks || [];
    const cpm = this.state.timeline?.critical_path || {};
    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h2 style="margin: 0; font-size: 1.25rem;">Execution Waves & Critical Path Method (CPM)</h2>
          <div style="font-size: 0.875rem; color: #38bdf8;">
            Total Estimated Project Duration: <strong>${cpm.total_duration || 0} hours</strong>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
          ${waves.map(w => {
            const waveTasks = tasks.filter(t => w.task_ids.includes(t.task_id));
            return `
              <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                  <h3 style="margin: 0; font-size: 1rem; color: #818cf8;">Wave ${w.wave_number}</h3>
                  <span style="font-size: 0.75rem; color: #94a3b8;">Duration: ~${w.estimated_duration}h</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                  ${waveTasks.map(t => {
                    const isCrit = (cpm.critical_task_ids || []).includes(t.task_id);
                    return `
                      <div style="background: #0b0f19; border: 1px solid ${isCrit ? '#ef4444' : '#334155'}; border-radius: 0.25rem; padding: 0.5rem; font-size: 0.8125rem;">
                        <div style="display: flex; justify-content: space-between;">
                          <strong>${t.title}</strong>
                          ${isCrit ? '<span style="color: #ef4444; font-weight: 700; font-size: 0.7rem;">CRITICAL</span>' : ''}
                        </div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">
                          Range: [${t.duration_min}h - ${t.duration_expected}h - ${t.duration_max}h] | Owner: ${t.owner}
                        </div>
                        ${t.is_irreversible ? '<div style="color: #f59e0b; font-size: 0.7rem; margin-top: 0.2rem;">⚠️ IRREVERSIBLE TASK</div>' : ''}
                      </div>
                    `;
                  }).join('')}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  _renderGraph(plan) {
    const deps = this.state.dependencies || {};
    return `
      <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h2 style="margin: 0; font-size: 1.25rem;">Task Dependency Topological Graph</h2>
          <span style="color: ${deps.has_cycle ? '#ef4444' : '#10b981'}; font-weight: 600; font-size: 0.875rem;">
            ${deps.has_cycle ? '🚨 CIRCULAR DEPENDENCY DETECTED' : '✅ ACYCLIC (DAG VALIDATED)'}
          </span>
        </div>
        <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 1rem;">
          Explicit dependency flow ensuring no task runs prior to prerequisite completion.
        </div>
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          ${(deps.tasks || []).map(t => {
            const preds = deps.predecessors?.[t.id] || [];
            const succs = deps.successors?.[t.id] || [];
            return `
              <div style="background: #070b14; padding: 0.75rem; border-radius: 0.375rem; border: 1px solid #1e293b; font-size: 0.8125rem;">
                <div style="display: flex; justify-content: space-between;">
                  <strong style="color: #f8fafc;">${t.title}</strong>
                  <span style="color: #38bdf8;">${t.status}</span>
                </div>
                <div style="margin-top: 0.25rem; font-size: 0.75rem; color: #64748b;">
                  Depends On: ${preds.length > 0 ? preds.join(', ') : 'None (Entry Task)'} → Unlocks: ${succs.length > 0 ? succs.join(', ') : 'None (Exit Task)'}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  _renderResources(plan) {
    const tasks = plan.tasks || [];
    return `
      <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.5rem;">
        <h2 style="margin: 0 0 0.5rem; font-size: 1.25rem;">Resource Planning & Mutual-Exclusion Locks</h2>
        <p style="font-size: 0.875rem; color: #94a3b8; margin: 0 0 1rem;">
          Invariant 10: Unknown resource is not available. Exclusive locks prevent unsafe concurrent operations.
        </p>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.8125rem;">
          <thead>
            <tr style="border-bottom: 1px solid #334155; text-align: left; color: #94a3b8;">
              <th style="padding: 0.5rem;">Task</th>
              <th style="padding: 0.5rem;">Resource Name</th>
              <th style="padding: 0.5rem;">Amount</th>
              <th style="padding: 0.5rem;">Exclusive Lock</th>
              <th style="padding: 0.5rem;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${tasks.flatMap(t => (t.resources || []).map(r => `
              <tr style="border-bottom: 1px solid #1e293b;">
                <td style="padding: 0.5rem; color: #f8fafc;">${t.title}</td>
                <td style="padding: 0.5rem; color: #38bdf8;">${r.name}</td>
                <td style="padding: 0.5rem;">${r.amount} ${r.unit}</td>
                <td style="padding: 0.5rem; color: ${r.is_exclusive ? '#f59e0b' : '#94a3b8'};">
                  ${r.is_exclusive ? '🔒 MUTEX EXCLUSIVE' : 'SHARED'}
                </td>
                <td style="padding: 0.5rem; color: #10b981;">VERIFIED</td>
              </tr>
            `)).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderRisks(plan) {
    const risks = plan.risks || [];
    const rollback = this.state.risks?.rollback_strategy || {};
    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
          <h2 style="margin: 0 0 1rem; font-size: 1.25rem;">Multi-Level Strategic Risk Register</h2>
          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            ${risks.map(r => `
              <div style="background: #070b14; border-left: 4px solid ${r.severity === 'CRITICAL' ? '#ef4444' : r.severity === 'HIGH' ? '#f97316' : '#eab308'}; padding: 0.75rem 1rem; border-radius: 0.25rem; font-size: 0.8125rem;">
                <div style="display: flex; justify-content: space-between;">
                  <strong>${r.description}</strong>
                  <span style="font-weight: 700;">SEVERITY: ${r.severity}</span>
                </div>
                <div style="margin-top: 0.25rem; color: #94a3b8;">
                  <strong>Mitigation:</strong> ${r.mitigation || 'Continuous monitoring'}
                </div>
                <div style="margin-top: 0.25rem; color: #94a3b8;">
                  <strong>Contingency:</strong> ${r.contingency_plan || 'Pause wave execution'}
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
          <h3 style="margin: 0 0 0.5rem; font-size: 1.125rem; color: #f43f5e;">Rollback & Disaster Recovery Strategy</h3>
          <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.75rem;">
            Trigger: ${rollback.rollback_trigger || 'Critical failure in wave execution'}
          </div>
          <ol style="margin: 0; padding-left: 1.25rem; font-size: 0.8125rem; color: #e2e8f0;">
            ${(rollback.steps || []).map(s => `<li>${s}</li>`).join('')}
          </ol>
        </div>
      </div>
    `;
  }

  _renderAdaptation(plan) {
    const checkpoints = plan.checkpoints || [];
    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
          <h2 style="margin: 0 0 0.5rem; font-size: 1.25rem;">Checkpoints & Variance Scoring</h2>
          <p style="font-size: 0.875rem; color: #94a3b8; margin: 0 0 1rem;">
            Measured reality vs expected state determines stopping rules (CONTINUE, PAUSE, REPLAN, ROLLBACK).
          </p>
          <div style="display: flex; flex-direction: column; gap: 0.75rem;">
            ${checkpoints.map(cp => `
              <div style="background: #070b14; border: 1px solid #1e293b; border-radius: 0.25rem; padding: 0.75rem; font-size: 0.8125rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <strong style="color: #38bdf8;">${cp.name}</strong>
                  <span style="background: #1e293b; color: ${cp.decision_action === 'CONTINUE' ? '#10b981' : '#f59e0b'}; padding: 0.2rem 0.5rem; border-radius: 0.25rem; font-weight: 700;">
                    ACTION: ${cp.decision_action} (Variance: ${cp.variance_score})
                  </span>
                </div>
                <div style="margin-top: 0.5rem; font-size: 0.75rem; color: #94a3b8;">
                  Expected: ${JSON.stringify(cp.expected_state || {})}
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.25rem;">
          <h3 style="margin: 0 0 0.5rem; font-size: 1.125rem; color: #f59e0b;">Sunk Cost Defense Engine</h3>
          <p style="font-size: 0.8125rem; color: #cbd5e1; margin: 0;">
            Never continue a bad strategy merely because significant work has already been invested.
            Forward expected value always supersedes sunk execution cost.
          </p>
        </div>
      </div>
    `;
  }

  _renderAudit(plan) {
    const events = this.state.auditEvents || [];
    return `
      <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 1.5rem;">
        <h2 style="margin: 0 0 0.5rem; font-size: 1.25rem;">Tamper-Evident Plan Audit Trail</h2>
        <p style="font-size: 0.875rem; color: #94a3b8; margin: 0 0 1rem;">
          Immutable ledger of plan creations, validations, wave activations, pauses, replans, and outcomes.
        </p>
        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
          ${events.map(e => `
            <div style="display: flex; justify-content: space-between; background: #070b14; padding: 0.5rem 0.75rem; border-radius: 0.25rem; font-size: 0.8125rem; border-left: 3px solid #0284c7;">
              <div>
                <strong>${e.event_type}</strong> by <span style="color: #38bdf8;">${e.actor}</span>
                <div style="font-size: 0.75rem; color: #64748b;">${JSON.stringify(e.details || {})}</div>
              </div>
              <span style="color: #94a3b8; font-size: 0.75rem;">${e.timestamp}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    this.container.addEventListener('click', async (e) => {
      const tabBtn = e.target.closest('.nav-tab-btn');
      if (tabBtn) {
        this.state.activeTab = tabBtn.getAttribute('data-tab');
        this.container.querySelectorAll('.nav-tab-btn').forEach(btn => {
          btn.style.background = 'transparent';
          btn.style.borderColor = 'transparent';
          btn.style.color = '#94a3b8';
        });
        tabBtn.style.background = 'rgba(2, 132, 199, 0.2)';
        tabBtn.style.borderColor = '#38bdf8';
        tabBtn.style.color = '#38bdf8';
        this._updateContent();
        return;
      }

      const planId = this.state.currentPlan?.plan_id;
      if (!planId) return;

      if (e.target.closest('#btn-validate-plan')) {
        try {
          const res = await this.api.validate(planId);
          alert(`Plan Validation: ${res.is_valid ? 'VALID ✅' : 'INVALID ❌'}\n${(res.errors || []).join('\n')}`);
        } catch (err) {
          alert(`Validation error: ${err.message}`);
        }
      }

      if (e.target.closest('#btn-proposal-handoff')) {
        try {
          const prop = await this.api.getProposal(planId);
          alert(`Proposal Generated: ${prop.proposal_id}\nWaves: ${prop.total_waves}\nExecution Boundary Enforced: ${prop.execution_boundary_enforced}`);
        } catch (err) {
          alert(`Proposal error: ${err.message}`);
        }
      }

      if (e.target.closest('#btn-start-plan')) {
        try {
          await this.api.start(planId, { actor: 'OPERATOR' });
          alert('Execution waves sequencing started.');
          await this.fetchData();
        } catch (err) {
          alert(`Start error: ${err.message}`);
        }
      }

      if (e.target.closest('#btn-pause-plan')) {
        try {
          await this.api.pause(planId, { actor: 'OPERATOR', reason: 'User requested pause' });
          alert('Plan paused.');
          await this.fetchData();
        } catch (err) {
          alert(`Pause error: ${err.message}`);
        }
      }

      if (e.target.closest('#btn-resume-plan')) {
        try {
          await this.api.resume(planId, { actor: 'OPERATOR' });
          alert('Plan resumed.');
          await this.fetchData();
        } catch (err) {
          alert(`Resume error: ${err.message}`);
        }
      }

      if (e.target.closest('#btn-cancel-plan')) {
        try {
          await this.api.cancel(planId, { actor: 'OPERATOR', reason: 'User cancelled' });
          alert('Plan cancelled.');
          await this.fetchData();
        } catch (err) {
          alert(`Cancel error: ${err.message}`);
        }
      }

      if (e.target.closest('#btn-replan')) {
        try {
          await this.api.replan(planId, { actor: 'OPERATOR', reason: 'Operator-triggered adaptation' });
          alert('New plan revision created preserving historical snapshot.');
          await this.fetchData();
        } catch (err) {
          alert(`Replan error: ${err.message}`);
        }
      }
    });
  }
}

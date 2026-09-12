/**
 * Kairo Autonomous Resource Economy, Capability Allocation & Cognitive Budget View (Task 77).
 *
 * Views:
 * 1. ECONOMY OVERVIEW: Capacity saturation gauge, total headroom, active degradation tier.
 * 2. COGNITIVE BUDGET MATRIX: Multi-scope limits vs consumed progress bars, 7-state lifecycle badges.
 * 3. PREEMPTION & QUEUE MANAGER: Running, paused, checkpointed tasks, wait time, resume actions.
 * 4. DEADLOCK & CONTENTION GRAPH: Bipartite wait-for graph, cycle detection, victim task resolution.
 * 5. EFFICIENCY & DEGRADATION INSIGHTS: Multi-objective Pareto trade-offs (Quality, Latency, Cost, Risk, Resource).
 * 6. STARVATION & FAIR SHARE MONITOR: Anti-starvation aging indicators, Gini coefficient curve.
 *
 * STRICT SAFETY LABELS:
 * Clearly distinguishes AVAILABLE, RESERVED, ALLOCATED, CONSUMED, PROJECTED, DEGRADED, UNAVAILABLE.
 */

import { resourceEconomyApi } from '../../lib/api/endpoints.js';

export class ResourceCenterView {
  constructor(container) {
    this.container = container;
    this.activeSubTab = 'overview'; // 'overview', 'budgets', 'preemption', 'deadlock', 'tradeoffs', 'fairness'
    this.overviewData = null;
    this.budgetsData = [];
    this.preemptionsData = [];
    this.deadlocksData = [];
    this.fairnessData = null;
    this.isLoading = false;
    this.statusMessage = null;
  }

  setSubTab(tab) {
    this.activeSubTab = tab;
    this.render();
  }

  formatSafetyBadge(status) {
    const s = (status || 'AVAILABLE').toUpperCase();
    let color = '#10b981'; // Green default for AVAILABLE

    if (s.includes('RESERVED')) {
      color = '#f59e0b'; // Amber
    } else if (s.includes('ALLOCATED')) {
      color = '#3b82f6'; // Blue
    } else if (s.includes('CONSUMED')) {
      color = '#64748b'; // Slate
    } else if (s.includes('PROJECTED')) {
      color = '#8b5cf6'; // Purple
    } else if (s.includes('DEGRADED') || s.includes('NEAR_LIMIT')) {
      color = '#ea580c'; // Orange
    } else if (s.includes('UNAVAILABLE') || s.includes('EXHAUSTED') || s.includes('OVERCOMMITTED')) {
      color = '#ef4444'; // Red
    }

    return `
      <span style="display:inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; background-color: ${color}20; color: ${color}; border: 1px solid ${color}60;">
        ${s}
      </span>
    `;
  }

  async loadData() {
    this.isLoading = true;
    this.render();

    try {
      const [overview, budgets, preemptions, deadlocks, fairness] = await Promise.allSettled([
        resourceEconomyApi.getOverview(),
        resourceEconomyApi.listBudgets(),
        resourceEconomyApi.listPreemptions(),
        resourceEconomyApi.detectDeadlocks(),
        resourceEconomyApi.getFairnessMetrics(),
      ]);

      if (overview.status === 'fulfilled') this.overviewData = overview.value;
      if (budgets.status === 'fulfilled') this.budgetsData = Array.isArray(budgets.value) ? budgets.value : [];
      if (preemptions.status === 'fulfilled') this.preemptionsData = Array.isArray(preemptions.value) ? preemptions.value : [];
      if (deadlocks.status === 'fulfilled') this.deadlocksData = Array.isArray(deadlocks.value) ? deadlocks.value : [];
      if (fairness.status === 'fulfilled') this.fairnessData = fairness.value;
    } catch (err) {
      this.statusMessage = `Error loading resource economy: ${err.message}`;
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async handleResumeTask(taskId) {
    try {
      await resourceEconomyApi.resumeTask(taskId);
      this.statusMessage = `Task ${taskId} resumed successfully.`;
      await this.loadData();
    } catch (err) {
      this.statusMessage = `Failed to resume task: ${err.message}`;
      this.render();
    }
  }

  async handleResolveDeadlocks() {
    try {
      const res = await resourceEconomyApi.resolveDeadlocks();
      this.statusMessage = `Deadlock cycle resolved.`;
      await this.loadData();
    } catch (err) {
      this.statusMessage = `Failed to resolve deadlocks: ${err.message}`;
      this.render();
    }
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="resource-economy-view" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #e2e8f0; background: #0f172a; min-height: 100vh; padding: 24px;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 16px; margin-bottom: 20px;">
          <div>
            <h1 style="font-size: 24px; font-weight: 700; margin: 0 0 6px 0; color: #f8fafc;">
              Autonomous Resource Economy & Cognitive Budget Center
            </h1>
            <div style="font-size: 13px; color: #94a3b8;">
              Finite Capacity Reasoning • Hierarchical Budgets • Preemption & Checkpointing • Deadlock Cycles • Fair Share
            </div>
          </div>
          <div>
            <button id="btn-refresh-economy" style="background: #1e293b; border: 1px solid #334155; color: #f8fafc; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500;">
              ${this.isLoading ? 'Refreshing...' : '↻ Refresh State'}
            </button>
          </div>
        </div>

        <!-- Notification Banner -->
        ${this.statusMessage ? `
          <div style="background: #1e293b; border-left: 4px solid #3b82f6; padding: 10px 16px; margin-bottom: 20px; border-radius: 4px; font-size: 13px;">
            ${this.statusMessage}
          </div>
        ` : ''}

        <!-- Sub-Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid #1e293b; margin-bottom: 24px; overflow-x: auto;">
          ${this.renderSubTab('overview', '1. Economy Overview')}
          ${this.renderSubTab('budgets', '2. Cognitive Budgets')}
          ${this.renderSubTab('preemption', '3. Preemption & Queue')}
          ${this.renderSubTab('deadlock', '4. Deadlock & Contention')}
          ${this.renderSubTab('tradeoffs', '5. Trade-Offs & Degradation')}
          ${this.renderSubTab('fairness', '6. Starvation & Fair Share')}
        </div>

        <!-- Active View Content -->
        <div class="tab-content">
          ${this.renderActiveTabContent()}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  renderSubTab(tabKey, label) {
    const isActive = this.activeSubTab === tabKey;
    return `
      <button class="subtab-btn" data-tab="${tabKey}" style="
        background: transparent;
        border: none;
        border-bottom: 2px solid ${isActive ? '#3b82f6' : 'transparent'};
        color: ${isActive ? '#f8fafc' : '#94a3b8'};
        padding: 10px 16px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        white-space: nowrap;
      ">
        ${label}
      </button>
    `;
  }

  renderActiveTabContent() {
    if (this.isLoading && !this.overviewData) {
      return '<div style="padding: 40px; text-align: center; color: #94a3b8;">Loading resource economy telemetry...</div>';
    }

    switch (this.activeSubTab) {
      case 'overview':
        return this.renderOverviewTab();
      case 'budgets':
        return this.renderBudgetsTab();
      case 'preemption':
        return this.renderPreemptionTab();
      case 'deadlock':
        return this.renderDeadlockTab();
      case 'tradeoffs':
        return this.renderTradeoffsTab();
      case 'fairness':
        return this.renderFairnessTab();
      default:
        return this.renderOverviewTab();
    }
  }

  renderOverviewTab() {
    const data = this.overviewData || {
      total_resources: 0,
      capacity_saturation_pct: 0.0,
      saturation_state: 'HEALTHY',
      active_budgets_count: 0,
      exhausted_budgets_count: 0,
      preempted_tasks_count: 0,
      active_deadlocks_count: 0,
      fairness_gini: 0.0,
      active_degradation_tier: 'FULL_FIDELITY',
    };

    const satPct = Math.round((data.capacity_saturation_pct || 0) * 100);

    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px;">
        <div style="background: #1e293b; padding: 18px; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px;">Capacity Saturation</div>
          <div style="display: flex; align-items: baseline; gap: 8px;">
            <span style="font-size: 28px; font-weight: 700; color: #f8fafc;">${satPct}%</span>
            ${this.formatSafetyBadge(data.saturation_state)}
          </div>
          <div style="width: 100%; background: #0f172a; border-radius: 4px; height: 8px; margin-top: 12px; overflow: hidden;">
            <div style="width: ${satPct}%; height: 100%; background: ${satPct > 85 ? '#ef4444' : satPct > 70 ? '#f59e0b' : '#10b981'};"></div>
          </div>
        </div>

        <div style="background: #1e293b; padding: 18px; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px;">Active Degradation Tier</div>
          <div style="margin-top: 4px;">
            ${this.formatSafetyBadge(data.active_degradation_tier)}
          </div>
          <div style="font-size: 12px; color: #94a3b8; margin-top: 10px;">
            Tier dictates prompt compression and model class.
          </div>
        </div>

        <div style="background: #1e293b; padding: 18px; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px;">Cognitive Budgets</div>
          <div style="display: flex; gap: 12px; align-items: baseline;">
            <span style="font-size: 28px; font-weight: 700; color: #10b981;">${data.active_budgets_count}</span>
            <span style="font-size: 12px; color: #94a3b8;">Active</span>
            <span style="font-size: 28px; font-weight: 700; color: #ef4444;">${data.exhausted_budgets_count}</span>
            <span style="font-size: 12px; color: #94a3b8;">Exhausted</span>
          </div>
        </div>

        <div style="background: #1e293b; padding: 18px; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 6px;">Preemptions & Deadlocks</div>
          <div style="display: flex; gap: 12px; align-items: baseline;">
            <span style="font-size: 28px; font-weight: 700; color: #f59e0b;">${data.preempted_tasks_count}</span>
            <span style="font-size: 12px; color: #94a3b8;">Preempted</span>
            <span style="font-size: 28px; font-weight: 700; color: #8b5cf6;">${data.active_deadlocks_count}</span>
            <span style="font-size: 12px; color: #94a3b8;">Cycles</span>
          </div>
        </div>
      </div>
    `;
  }

  renderBudgetsTab() {
    if (!this.budgetsData || this.budgetsData.length === 0) {
      return '<div style="padding: 30px; text-align: center; color: #94a3b8; background: #1e293b; border-radius: 8px;">No cognitive budgets registered.</div>';
    }

    return `
      <div style="display: grid; gap: 16px;">
        ${this.budgetsData.map((b) => {
          const dims = Object.keys(b.limits || {});
          return `
            <div style="background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <div>
                  <span style="font-weight: 700; font-size: 16px; color: #f8fafc;">${b.scope}: ${b.scope_id}</span>
                  <span style="font-size: 12px; color: #94a3b8; margin-left: 8px;">ID: ${b.budget_id}</span>
                </div>
                <div>${this.formatSafetyBadge(b.state)}</div>
              </div>

              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
                ${dims.map((dim) => {
                  const limit = b.limits[dim] || 1;
                  const consumed = (b.consumed && b.consumed[dim]) || 0;
                  const pct = Math.min(100, Math.round((consumed / limit) * 100));
                  return `
                    <div style="background: #0f172a; padding: 12px; border-radius: 6px;">
                      <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px;">
                        <span style="color: #cbd5e1; font-weight: 500;">${dim}</span>
                        <span style="color: #94a3b8;">${consumed.toLocaleString()} / ${limit.toLocaleString()} (${pct}%)</span>
                      </div>
                      <div style="width: 100%; background: #1e293b; height: 6px; border-radius: 3px; overflow: hidden;">
                        <div style="width: ${pct}%; height: 100%; background: ${pct >= 100 ? '#ef4444' : pct >= 85 ? '#f59e0b' : '#3b82f6'};"></div>
                      </div>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  renderPreemptionTab() {
    if (!this.preemptionsData || this.preemptionsData.length === 0) {
      return `
        <div style="padding: 30px; text-align: center; color: #94a3b8; background: #1e293b; border-radius: 8px;">
          No tasks currently preempted or paused. Safe execution queue is clear.
        </div>
      `;
    }

    return `
      <div style="display: grid; gap: 12px;">
        ${this.preemptionsData.map((p) => `
          <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; color: #f8fafc; font-size: 14px;">Task: ${p.task_id} (Priority: ${p.priority})</div>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Preempted by: ${p.preempted_by_task_id || 'System Overcommit'} • Checkpoint: ${p.checkpoint_token || 'In-Memory'} • Wait: ${p.wait_time_s}s
              </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
              ${this.formatSafetyBadge(p.state)}
              <button class="btn-resume-task" data-task-id="${p.task_id}" style="background: #3b82f6; border: none; color: #fff; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;">
                Resume Task
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderDeadlockTab() {
    const hasCycles = this.deadlocksData && this.deadlocksData.length > 0;

    return `
      <div style="background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div>
            <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 4px 0; color: #f8fafc;">Bipartite Wait-For Graph Cycles</h3>
            <div style="font-size: 12px; color: #94a3b8;">Deterministic cycle detection and bounded victim task selection</div>
          </div>
          ${hasCycles ? `
            <button id="btn-resolve-deadlocks" style="background: #ef4444; border: none; color: #fff; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600;">
              Resolve Cycles Now
            </button>
          ` : '<span style="color: #10b981; font-size: 13px; font-weight: 600;">✓ No Deadlocks Detected</span>'}
        </div>

        ${hasCycles ? `
          <div style="display: grid; gap: 10px;">
            ${this.deadlocksData.map((c) => `
              <div style="background: #0f172a; padding: 14px; border-radius: 6px; border-left: 3px solid #ef4444;">
                <div style="font-weight: 600; color: #f8fafc; font-size: 13px;">Cycle ID: ${c.cycle_id}</div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                  Tasks: ${c.involved_tasks.join(' → ')} | Resources: ${c.involved_resources.join(' ↔ ')}
                </div>
              </div>
            `).join('')}
          </div>
        ` : `
          <div style="padding: 20px; text-align: center; color: #94a3b8; font-size: 13px;">
            Graph dependencies are acyclic. Resource allocations proceed concurrently without deadlock.
          </div>
        `}
      </div>
    `;
  }

  renderTradeoffsTab() {
    return `
      <div style="background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155;">
        <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 8px 0; color: #f8fafc;">Pareto Trade-Off Evaluation & Degraded Modes</h3>
        <div style="font-size: 13px; color: #94a3b8; margin-bottom: 20px;">
          Autonomous trade-offs optimize across 5 objectives: Quality vs Latency vs Cost vs Risk vs Resource Use.
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px;">
          <div style="background: #0f172a; padding: 14px; border-radius: 6px;">
            <div style="font-weight: 600; color: #10b981; font-size: 13px;">FULL_FIDELITY</div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">100% Context • Frontier Reasoning Model • Uncompressed</div>
          </div>
          <div style="background: #0f172a; padding: 14px; border-radius: 6px;">
            <div style="font-weight: 600; color: #3b82f6; font-size: 13px;">MODERATE_COMPRESSION</div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">70% Context • Fast Model • -30% Token Footprint</div>
          </div>
          <div style="background: #0f172a; padding: 14px; border-radius: 6px;">
            <div style="font-weight: 600; color: #f59e0b; font-size: 13px;">AGGRESSIVE_THROTTLE</div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">40% Context • Free/Local Model • Single-Turn Execution</div>
          </div>
          <div style="background: #0f172a; padding: 14px; border-radius: 6px;">
            <div style="font-weight: 600; color: #ef4444; font-size: 13px;">EMERGENCY_MINIMAL</div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Deterministic Rules • Zero LLM Spend • Essential Safety Only</div>
          </div>
        </div>
      </div>
    `;
  }

  renderFairnessTab() {
    const f = this.fairnessData || {
      gini_coefficient: 0.0,
      max_min_ratio: 1.0,
      starvation_count: 0,
      average_wait_time_s: 0.0,
      aging_boost_active_count: 0,
    };

    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;">
        <div style="background: #1e293b; padding: 18px; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">Fairness Gini Index</div>
          <div style="font-size: 28px; font-weight: 700; color: #f8fafc; margin-top: 6px;">
            ${f.gini_coefficient}
          </div>
          <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
            ${f.gini_coefficient < 0.3 ? '✓ Equitable resource distribution' : 'Contention skew detected'}
          </div>
        </div>

        <div style="background: #1e293b; padding: 18px; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">Starvation Incidents</div>
          <div style="font-size: 28px; font-weight: 700; color: ${f.starvation_count > 0 ? '#ef4444' : '#10b981'}; margin-top: 6px;">
            ${f.starvation_count}
          </div>
          <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
            Tasks waiting &gt; 60 seconds
          </div>
        </div>

        <div style="background: #1e293b; padding: 18px; border-radius: 8px; border: 1px solid #334155;">
          <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase;">Active Aging Boosts</div>
          <div style="font-size: 28px; font-weight: 700; color: #3b82f6; margin-top: 6px;">
            ${f.aging_boost_active_count}
          </div>
          <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
            Anti-starvation priority elevations
          </div>
        </div>
      </div>
    `;
  }

  attachEventListeners() {
    const refreshBtn = this.container.querySelector('#btn-refresh-economy');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    const subTabBtns = this.container.querySelectorAll('.subtab-btn');
    subTabBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const tab = e.target.getAttribute('data-tab');
        if (tab) this.setSubTab(tab);
      });
    });

    const resumeBtns = this.container.querySelectorAll('.btn-resume-task');
    resumeBtns.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const taskId = e.target.getAttribute('data-task-id');
        if (taskId) this.handleResumeTask(taskId);
      });
    });

    const resolveBtn = this.container.querySelector('#btn-resolve-deadlocks');
    if (resolveBtn) {
      resolveBtn.addEventListener('click', () => this.handleResolveDeadlocks());
    }
  }
}

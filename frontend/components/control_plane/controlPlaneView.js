/**
 * Autonomous Cognitive Control Plane & Unified Operating Loop View (Task 102)
 * Supervisory Command Center dashboard visualizing the full closed-loop cognitive cycle.
 */

import { controlPlaneApi } from '../../lib/api/endpoints.js';

export class ControlPlaneView {
  constructor(containerId) {
    this.container = typeof document !== 'undefined'
      ? (typeof containerId === 'string' ? document.getElementById(containerId) : containerId)
      : (typeof containerId === 'object' ? containerId : null);
    this.activeTab = 'cycles'; // cycles, timeline, loop_guard, replay
    this.status = null;
    this.cycles = [];
    this.selectedCycle = null;
    this.timeline = [];
    this.replayData = null;
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
      const [stat, cycs] = await Promise.all([
        controlPlaneApi.getStatus().catch(() => null),
        controlPlaneApi.listCycles(50).catch(() => []),
      ]);

      this.status = stat || {
        control_mode: 'BOUNDED_AUTONOMY',
        emergency_stop_active: false,
        queue_depth: 0,
        total_cycles_executed: 0,
        metrics: { completed_cycles: 0, blocked_cycles: 0, no_action_cycles: 0, circuit_breaker_tripped: false },
      };
      this.cycles = cycs || [];
      if (this.cycles.length > 0 && !this.selectedCycle) {
        await this.selectCycle(this.cycles[0].cycle_id);
      }
    } catch (err) {
      console.error('Failed to load control plane data:', err);
      this.error = err.message || 'Failed to connect to Control Plane Service';
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async selectCycle(cycleId) {
    this.selectedCycle = this.cycles.find(c => c.cycle_id === cycleId) || null;
    if (cycleId) {
      try {
        this.timeline = await controlPlaneApi.getTimeline(cycleId).catch(() => []);
      } catch {
        this.timeline = [];
      }
    }
    this.render();
  }

  async triggerReassessment() {
    this.isLoading = true;
    try {
      await controlPlaneApi.reassess();
      await this.loadData();
    } catch (err) {
      this.error = 'Reassessment failed: ' + err.message;
      this.render();
    }
  }

  async replaySelectedCycle() {
    if (!this.selectedCycle) return;
    this.isLoading = true;
    try {
      this.replayData = await controlPlaneApi.replayCycle(this.selectedCycle.cycle_id);
      this.activeTab = 'replay';
    } catch (err) {
      this.error = 'Replay failed: ' + err.message;
    } finally {
      this.isLoading = false;
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
      <div class="control-plane-loading" style="padding: 2.5rem; text-align: center; color: var(--text-muted, #94a3b8);">
        <div class="spinner" style="display: inline-block; width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.1); border-top-color: #38bdf8; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <p style="margin-top: 1rem; font-family: Inter, sans-serif;">Initializing Autonomous Cognitive Control Plane...</p>
      </div>
    `;
  }

  render() {
    if (!this.container) return;

    const s = this.status || {
      control_mode: 'BOUNDED_AUTONOMY',
      emergency_stop_active: false,
      queue_depth: 0,
      total_cycles_executed: 0,
      metrics: { completed_cycles: 0, blocked_cycles: 0, no_action_cycles: 0, circuit_breaker_tripped: false },
    };

    const isTripped = s.metrics?.circuit_breaker_tripped;
    const eStopActive = s.emergency_stop_active;

    this.container.innerHTML = `
      <div class="control-plane-view" style="display: flex; flex-direction: column; gap: 1.5rem; padding: 1.5rem; font-family: Inter, system-ui, sans-serif; color: #f8fafc;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 1.25rem;">
          <div>
            <h1 style="margin: 0; font-size: 1.5rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8 0%, #a855f7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Cognitive Control Plane & Unified Operating Loop
            </h1>
            <p style="margin: 0.25rem 0 0; font-size: 0.875rem; color: #94a3b8;">
              Central supervisory nervous system coordinating world, self, missions, decisions, and execution.
            </p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button id="cp-refresh-btn" style="background: rgba(255, 255, 255, 0.05); color: #cbd5e1; border: 1px solid rgba(255, 255, 255, 0.1); padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer;">
              Refresh
            </button>
            <button id="cp-reassess-btn" style="background: #2563eb; color: #ffffff; border: none; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer;">
              Trigger Reassessment
            </button>
          </div>
        </div>

        ${this.error ? `
          <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #fca5a5; padding: 0.75rem 1rem; border-radius: 6px;">
            ${this.error}
          </div>
        ` : ''}

        <!-- Top Metric Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Control Mode</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: #38bdf8;">${s.control_mode}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">Supervisory envelope</div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Emergency Stop</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: ${eStopActive ? '#ef4444' : '#10b981'};">
              ${eStopActive ? 'ACTIVE (Fail-Closed)' : 'INACTIVE'}
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">Kill-switch primacy</div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Loop Guard</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: ${isTripped ? '#ef4444' : '#10b981'};">
              ${isTripped ? 'CIRCUIT TRIPPED' : 'HEALTHY'}
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">Anti-thrashing defense</div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Cycles Completed</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: #f59e0b;">
              ${s.metrics?.completed_cycles || 0} / ${s.total_cycles_executed || 0}
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">${s.metrics?.no_action_cycles || 0} deliberate no-actions</div>
          </div>
        </div>

        <!-- Operating Loop Pipeline Visualizer -->
        <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 1rem;">
          <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; margin-bottom: 0.75rem; font-weight: 600;">
            Unified Operating Loop Stages
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; font-size: 0.75rem;">
            ${['OBSERVE', 'RECONCILE', 'ASSESS', 'PLAN', 'DECIDE', 'AUTHORIZE', 'ALLOCATE', 'EXECUTE', 'VERIFY', 'LEARN'].map((st, i) => `
              <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 0.3rem 0.6rem; border-radius: 4px; font-weight: 600;">
                ${i + 1}. ${st}
              </span>
              ${i < 9 ? '<span style="color: #64748b;">➔</span>' : ''}
            `).join('')}
          </div>
        </div>

        <!-- Tabs -->
        <div style="display: flex; gap: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 0.5rem;">
          ${this.renderTabButton('cycles', 'Control Cycles')}
          ${this.renderTabButton('timeline', 'Cycle Timeline')}
          ${this.renderTabButton('loop_guard', 'Loop Guard State')}
          ${this.renderTabButton('replay', 'Replay Inspection')}
        </div>

        <!-- Tab Body -->
        <div class="cp-tab-content">
          ${this.renderTabContent()}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderTabButton(tabId, label) {
    const active = this.activeTab === tabId;
    return `
      <button class="cp-tab-btn" data-tab="${tabId}" style="background: ${active ? 'rgba(56, 189, 248, 0.15)' : 'transparent'}; color: ${active ? '#38bdf8' : '#94a3b8'}; border: 1px solid ${active ? 'rgba(56, 189, 248, 0.4)' : 'transparent'}; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer;">
        ${label}
      </button>
    `;
  }

  renderTabContent() {
    switch (this.activeTab) {
      case 'cycles':
        return this.renderCycles();
      case 'timeline':
        return this.renderTimeline();
      case 'loop_guard':
        return this.renderLoopGuard();
      case 'replay':
        return this.renderReplay();
      default:
        return `<p>Select a tab.</p>`;
    }
  }

  renderCycles() {
    if (!this.cycles.length) {
      return `<p style="color: #94a3b8;">No control cycles recorded yet.</p>`;
    }

    return `
      <div style="overflow-x: auto; background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem; text-align: left;">
          <thead>
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); background: rgba(30, 41, 59, 0.5); color: #94a3b8;">
              <th style="padding: 0.75rem 1rem;">Cycle ID</th>
              <th style="padding: 0.75rem 1rem;">Trigger</th>
              <th style="padding: 0.75rem 1rem;">Status</th>
              <th style="padding: 0.75rem 1rem;">Result</th>
              <th style="padding: 0.75rem 1rem;">Duration</th>
              <th style="padding: 0.75rem 1rem;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${this.cycles.map(c => {
              const sColor = c.status === 'COMPLETED' ? '#10b981' : (c.status === 'NO_ACTION' ? '#38bdf8' : (c.status === 'WAITING' ? '#f59e0b' : '#ef4444'));
              const isSelected = this.selectedCycle?.cycle_id === c.cycle_id;
              return `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.04); background: ${isSelected ? 'rgba(56, 189, 248, 0.05)' : 'transparent'}; cursor: pointer;" class="cycle-row" data-id="${c.cycle_id}">
                  <td style="padding: 0.75rem 1rem; font-family: monospace; color: #38bdf8;">${c.cycle_id}</td>
                  <td style="padding: 0.75rem 1rem; color: #cbd5e1;">${c.trigger_type}</td>
                  <td style="padding: 0.75rem 1rem;">
                    <span style="background: ${sColor}22; color: ${sColor}; border: 1px solid ${sColor}55; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">
                      ${c.status}
                    </span>
                  </td>
                  <td style="padding: 0.75rem 1rem; color: #94a3b8;">${c.result || c.reason || '-'}</td>
                  <td style="padding: 0.75rem 1rem; color: #94a3b8;">${c.budget?.consumed_duration_s || 0}s</td>
                  <td style="padding: 0.75rem 1rem;">
                    <button class="inspect-btn" data-id="${c.cycle_id}" style="background: rgba(255,255,255,0.1); color: #fff; border: none; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; cursor: pointer;">
                      Timeline
                    </button>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  renderTimeline() {
    if (!this.selectedCycle) {
      return `<p style="color: #94a3b8;">Select a cycle to inspect its execution timeline.</p>`;
    }
    const c = this.selectedCycle;

    return `
      <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 0.75rem; margin-bottom: 1rem;">
          <div>
            <h3 style="margin: 0; color: #38bdf8; font-family: monospace;">Cycle: ${c.cycle_id}</h3>
            <div style="font-size: 0.8125rem; color: #94a3b8; margin-top: 0.25rem;">
              Trigger: <strong>${c.trigger_type}</strong> | Mode: <strong>${c.control_mode}</strong> | Result: <strong>${c.result || 'IN_PROGRESS'}</strong>
            </div>
          </div>
          <button id="cp-replay-action-btn" style="background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); padding: 0.4rem 0.8rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; cursor: pointer;">
            Replay Cycle (Safe Read-Only)
          </button>
        </div>

        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          ${(this.timeline || []).map((t, idx) => `
            <div style="display: flex; gap: 1rem; align-items: flex-start; padding: 0.75rem; background: rgba(30, 41, 59, 0.4); border-radius: 6px;">
              <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">
                ${idx + 1}
              </span>
              <div style="flex: 1;">
                <div style="font-weight: 600; color: #f8fafc; font-size: 0.875rem;">${t.stage}</div>
                <div style="font-size: 0.8125rem; color: #94a3b8; margin-top: 0.2rem;">${t.details || t.reason || t.status}</div>
              </div>
              <span style="font-size: 0.75rem; color: #64748b;">${t.status}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderLoopGuard() {
    const isTripped = this.status?.metrics?.circuit_breaker_tripped;
    return `
      <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid ${isTripped ? '#ef4444' : 'rgba(255,255,255,0.06)'}; border-radius: 8px; padding: 1.5rem;">
        <h3 style="margin-top: 0; color: ${isTripped ? '#ef4444' : '#10b981'};">
          Loop Guard Status: ${isTripped ? 'CIRCUIT BREAKER TRIPPED' : 'OPERATIONAL'}
        </h3>
        <p style="color: #cbd5e1; font-size: 0.875rem;">
          The Loop Guard monitors decision lineages, repetitive tool actions, and identical consecutive failures to guarantee that infinite autonomous loops cannot occur.
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
          <div style="background: rgba(30, 41, 59, 0.4); padding: 1rem; border-radius: 6px;">
            <div style="font-size: 0.75rem; color: #94a3b8;">Failure Threshold</div>
            <div style="font-size: 1.125rem; font-weight: 700; color: #f8fafc;">3 Consecutive</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.4); padding: 1rem; border-radius: 6px;">
            <div style="font-size: 0.75rem; color: #94a3b8;">Repetition Threshold</div>
            <div style="font-size: 1.125rem; font-weight: 700; color: #f8fafc;">3 Identical Steps</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.4); padding: 1rem; border-radius: 6px;">
            <div style="font-size: 0.75rem; color: #94a3b8;">Max Duration Envelope</div>
            <div style="font-size: 1.125rem; font-weight: 700; color: #f8fafc;">60 Seconds</div>
          </div>
        </div>
      </div>
    `;
  }

  renderReplay() {
    const r = this.replayData;
    if (!r) {
      return `<p style="color: #94a3b8;">No cycle replayed yet. Select a cycle from the Timeline tab and click "Replay Cycle".</p>`;
    }

    return `
      <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 8px; padding: 1.5rem;">
        <h3 style="margin-top: 0; color: #c084fc;">
          Deterministic Replay: ${r.replayed_cycle_id}
        </h3>
        <p style="color: #94a3b8; font-size: 0.8125rem;">
          Mode: <strong>${r.replay_mode}</strong> (Side effects executed: <strong>${r.side_effects_executed}</strong>)
        </p>
        <pre style="background: rgba(10, 15, 30, 0.8); padding: 1rem; border-radius: 6px; color: #a5f3fc; font-size: 0.8125rem; overflow-x: auto;">
${JSON.stringify(r, null, 2)}
        </pre>
      </div>
    `;
  }

  bindEvents() {
    if (!this.container || typeof this.container.querySelector !== 'function') return;
    const refBtn = this.container.querySelector('#cp-refresh-btn');
    if (refBtn) refBtn.onclick = () => this.loadData();

    const reassessBtn = this.container.querySelector('#cp-reassess-btn');
    if (reassessBtn) reassessBtn.onclick = () => this.triggerReassessment();

    const replayBtn = this.container.querySelector('#cp-replay-action-btn');
    if (replayBtn) replayBtn.onclick = () => this.replaySelectedCycle();

    const tabs = this.container.querySelectorAll('.cp-tab-btn');
    tabs.forEach(t => {
      t.onclick = () => this.setTab(t.getAttribute('data-tab'));
    });

    const rows = this.container.querySelectorAll('.cycle-row');
    rows.forEach(r => {
      r.onclick = () => this.selectCycle(r.getAttribute('data-id'));
    });

    const inspectBtns = this.container.querySelectorAll('.inspect-btn');
    inspectBtns.forEach(b => {
      b.onclick = (e) => {
        e.stopPropagation();
        this.selectCycle(b.getAttribute('data-id'));
        this.setTab('timeline');
      };
    });
  }
}

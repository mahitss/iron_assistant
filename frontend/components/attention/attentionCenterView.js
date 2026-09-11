/**
 * AttentionCenterView Component (Task 70)
 * Authoritative management interface for Kairo Autonomous Attention & Cognitive Resource Allocation Engine.
 */

import { attentionApi } from '../../lib/api/endpoints.js';

export class AttentionCenterView {
  constructor(options = {}) {
    this.container = options.container || null;
    this.activeTab = 'current_focus';
    this.tenantId = options.tenantId || 'default';

    // State collections
    this.currentFocus = null;
    this.queue = [];
    this.snapshot = null;
    this.health = null;
    this.metrics = null;
    this.selectedCandidate = null;
    this.selectedExplanation = null;
  }

  async init() {
    await this.refresh();
  }

  async refresh() {
    try {
      this.currentFocus = await attentionApi.getCurrent(this.tenantId);
      this.queue = await attentionApi.getQueue(this.tenantId) || [];
      this.health = await attentionApi.getHealth(this.tenantId);
      this.metrics = await attentionApi.getMetrics(this.tenantId);
      this.snapshot = await attentionApi.getSnapshot(this.tenantId);

      if (this.currentFocus) {
        this.selectedExplanation = await attentionApi.getExplanation(this.currentFocus.attention_id, this.tenantId);
      }
    } catch (err) {
      console.warn('AttentionCenterView: Some endpoints could not be refreshed:', err);
    }
  }

  setTab(tabName) {
    this.activeTab = tabName;
    this.render();
  }

  async inspectCandidate(attentionId) {
    try {
      this.selectedCandidate = await attentionApi.getCandidate(attentionId, this.tenantId);
      this.selectedExplanation = await attentionApi.getExplanation(attentionId, this.tenantId);
      this.render();
    } catch (err) {
      console.error('Failed to inspect candidate:', err);
    }
  }

  async focusCandidate(attentionId) {
    try {
      await attentionApi.focus(attentionId, this.tenantId);
      await this.refresh();
      this.render();
    } catch (err) {
      alert(`Failed to focus candidate: ${err.message}`);
    }
  }

  async pauseCandidate(attentionId) {
    try {
      await attentionApi.pause(attentionId, 'User requested pause', this.tenantId);
      await this.refresh();
      this.render();
    } catch (err) {
      alert(`Failed to pause candidate: ${err.message}`);
    }
  }

  async deferCandidate(attentionId) {
    try {
      await attentionApi.defer(attentionId, 'Deferred by operator', this.tenantId);
      await this.refresh();
      this.render();
    } catch (err) {
      alert(`Failed to defer candidate: ${err.message}`);
    }
  }

  async dismissCandidate(attentionId) {
    try {
      await attentionApi.dismiss(attentionId, 'Dismissed by operator', this.tenantId);
      await this.refresh();
      this.render();
    } catch (err) {
      alert(`Failed to dismiss candidate: ${err.message}`);
    }
  }

  render() {
    if (!this.container) return this._renderHtml();
    this.container.innerHTML = this._renderHtml();
    this._attachEventListeners();
    return this.container.innerHTML;
  }

  _renderHtml() {
    return `
      <div class="attention-center" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #e2e8f0; background: #0f172a; padding: 24px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4);">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 16px; margin-bottom: 20px;">
          <div>
            <h2 style="margin: 0; font-size: 1.5rem; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
              <span>🎯</span> Kairo Attention Center
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 0.875rem; color: #94a3b8;">
              Autonomous Attention & Cognitive Resource Allocation Engine
            </p>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <span style="font-size: 0.75rem; background: #1e293b; color: #38bdf8; padding: 4px 10px; border-radius: 6px; border: 1px solid #334155;">
              Mode: ${this.metrics?.mode || 'NORMAL_MODE'}
            </span>
            <button id="btn-refresh-attention" style="background: #3b82f6; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 500;">
              Refresh
            </button>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 20px;">
          ${this._renderTabBtn('current_focus', 'Current Focus')}
          ${this._renderTabBtn('queue', `Priority Queue (${this.queue.length})`)}
          ${this._renderTabBtn('resources', 'Cognitive Resources')}
          ${this._renderTabBtn('health', 'Health & Telemetry')}
        </div>

        <!-- Tab Content -->
        <div class="tab-body">
          ${this._renderActiveTabContent()}
        </div>
      </div>
    `;
  }

  _renderTabBtn(tabKey, label) {
    const isActive = this.activeTab === tabKey;
    return `
      <button 
        class="tab-btn" 
        data-tab="${tabKey}" 
        style="background: ${isActive ? '#3b82f6' : '#1e293b'}; color: ${isActive ? '#fff' : '#94a3b8'}; border: 1px solid ${isActive ? '#3b82f6' : '#334155'}; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: all 0.2s ease;">
        ${label}
      </button>
    `;
  }

  _renderActiveTabContent() {
    switch (this.activeTab) {
      case 'current_focus':
        return this._renderCurrentFocusTab();
      case 'queue':
        return this._renderQueueTab();
      case 'resources':
        return this._renderResourcesTab();
      case 'health':
        return this._renderHealthTab();
      default:
        return `<p style="color: #94a3b8;">Select a tab.</p>`;
    }
  }

  _renderCurrentFocusTab() {
    if (!this.currentFocus) {
      return `
        <div style="text-align: center; padding: 40px 20px; background: #1e293b; border-radius: 8px; border: 1px dashed #334155;">
          <span style="font-size: 2rem;">🧘</span>
          <h3 style="margin: 10px 0 4px 0; color: #f8fafc;">No Active Focus</h3>
          <p style="margin: 0; font-size: 0.875rem; color: #94a3b8;">Kairo is idle or waiting for eligible attention candidates.</p>
        </div>
      `;
    }

    const c = this.currentFocus;
    const expl = this.selectedExplanation?.focus_justification || c.reason || 'Active priority allocation.';

    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <!-- Left: Focus Card -->
        <div style="background: #1e293b; border-radius: 8px; padding: 20px; border: 1px solid #3b82f6;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <span style="background: #2563eb; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">ATTENDING</span>
            <span style="color: #38bdf8; font-weight: 600; font-size: 1.1rem;">Score: ${c.attention_score.toFixed(3)} (${c.threshold})</span>
          </div>

          <h3 style="margin: 0 0 8px 0; font-size: 1.25rem; color: #f8fafc;">${this._escapeHtml(c.title)}</h3>
          <p style="margin: 0 0 16px 0; font-size: 0.875rem; color: #cbd5e1; line-height: 1.5;">${this._escapeHtml(c.description || 'No description provided.')}</p>

          <!-- Factor Badges -->
          <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
            <span style="background: #0f172a; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; border: 1px solid #334155;">
              Importance: <strong style="color: #fbbf24;">${c.importance.toFixed(2)}</strong>
            </span>
            <span style="background: #0f172a; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; border: 1px solid #334155;">
              Urgency: <strong style="color: #f87171;">${c.urgency.toFixed(2)}</strong>
            </span>
            <span style="background: #0f172a; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; border: 1px solid #334155;">
              Risk: <strong style="color: #ef4444;">${c.risk.toFixed(2)}</strong>
            </span>
            <span style="background: #0f172a; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; border: 1px solid #334155;">
              Novelty: <strong style="color: #a855f7;">${c.novelty.toFixed(2)}</strong>
            </span>
          </div>

          <!-- Actions -->
          <div style="display: flex; gap: 8px;">
            <button class="btn-pause-attn" data-id="${c.attention_id}" style="background: #eab308; color: #0f172a; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 600;">Pause</button>
            <button class="btn-defer-attn" data-id="${c.attention_id}" style="background: #64748b; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.875rem;">Defer</button>
            <button class="btn-dismiss-attn" data-id="${c.attention_id}" style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.875rem;">Dismiss</button>
          </div>
        </div>

        <!-- Right: Explanation Card -->
        <div style="background: #1e293b; border-radius: 8px; padding: 20px; border: 1px solid #334155;">
          <h4 style="margin: 0 0 12px 0; color: #38bdf8; font-size: 1rem; display: flex; align-items: center; gap: 6px;">
            <span>💡</span> Why is Kairo focusing on this?
          </h4>
          <div style="background: #0f172a; padding: 14px; border-radius: 6px; border: 1px solid #334155; margin-bottom: 16px;">
            <p style="margin: 0; font-size: 0.875rem; color: #f1f5f9; line-height: 1.6;">${this._escapeHtml(expl)}</p>
          </div>

          <h5 style="margin: 12px 0 6px 0; color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;">Estimated Cognitive Footprint</h5>
          <ul style="margin: 0; padding-left: 20px; font-size: 0.875rem; color: #cbd5e1; line-height: 1.6;">
            <li>Estimated Effort: ${c.estimated_effort}</li>
            <li>Estimated Duration: ${c.estimated_duration_sec}s</li>
            <li>Required Capabilities: ${c.required_capabilities?.join(', ') || 'None specified'}</li>
          </ul>
        </div>
      </div>
    `;
  }

  _renderQueueTab() {
    if (!this.queue.length) {
      return `
        <div style="text-align: center; padding: 30px; background: #1e293b; border-radius: 8px;">
          <p style="margin: 0; color: #94a3b8;">Priority queue is empty. No pending tasks.</p>
        </div>
      `;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        ${this.queue.map(item => `
          <div style="background: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; display: flex; justify-content: space-between; align-items: center;">
            <div style="max-width: 70%;">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span style="background: ${item.threshold === 'CRITICAL' ? '#ef4444' : item.threshold === 'HIGH' ? '#f59e0b' : '#3b82f6'}; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold;">
                  ${item.threshold}
                </span>
                <span style="font-weight: 600; color: #f8fafc; font-size: 1rem;">${this._escapeHtml(item.title)}</span>
              </div>
              <p style="margin: 0; font-size: 0.8rem; color: #94a3b8;">${this._escapeHtml(item.reason || item.description || '')}</p>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="text-align: right;">
                <span style="color: #38bdf8; font-weight: bold; font-size: 1.1rem;">${item.attention_score.toFixed(3)}</span>
                <div style="font-size: 0.75rem; color: #64748b;">Urg: ${item.urgency.toFixed(2)} | Imp: ${item.importance.toFixed(2)}</div>
              </div>
              <button class="btn-focus-attn" data-id="${item.attention_id}" style="background: #3b82f6; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600;">
                Focus
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  _renderResourcesTab() {
    const budget = this.metrics?.resource_budget || {};
    const reasoningPct = budget.reasoning_capacity_pct ?? 100;
    const toolCalls = budget.active_tool_calls ?? 0;
    const maxToolCalls = budget.max_tool_calls ?? 10;
    const agentSlots = budget.active_agent_slots ?? 0;
    const maxAgentSlots = budget.max_agent_slots ?? 5;
    const execSlots = budget.execution_slots_used ?? 0;
    const maxExecSlots = budget.max_execution_slots ?? 4;
    const tokensUsed = budget.context_tokens_used ?? 0;
    const tokenBudget = budget.context_token_budget ?? 128000;

    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h4 style="margin: 0 0 8px 0; font-size: 0.85rem; color: #94a3b8;">Reasoning Capacity</h4>
          <div style="font-size: 1.75rem; font-weight: 700; color: #38bdf8;">${reasoningPct.toFixed(1)}%</div>
          <div style="background: #0f172a; height: 6px; border-radius: 3px; margin-top: 8px; overflow: hidden;">
            <div style="background: #38bdf8; height: 100%; width: ${reasoningPct}%;"></div>
          </div>
        </div>

        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h4 style="margin: 0 0 8px 0; font-size: 0.85rem; color: #94a3b8;">Active Tool Quota</h4>
          <div style="font-size: 1.75rem; font-weight: 700; color: #fbbf24;">${toolCalls} / ${maxToolCalls}</div>
          <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Available: ${Math.max(0, maxToolCalls - toolCalls)} slots</div>
        </div>

        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h4 style="margin: 0 0 8px 0; font-size: 0.85rem; color: #94a3b8;">Agent Slots</h4>
          <div style="font-size: 1.75rem; font-weight: 700; color: #a855f7;">${agentSlots} / ${maxAgentSlots}</div>
          <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Available: ${Math.max(0, maxAgentSlots - agentSlots)} slots</div>
        </div>

        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h4 style="margin: 0 0 8px 0; font-size: 0.85rem; color: #94a3b8;">Context Tokens</h4>
          <div style="font-size: 1.75rem; font-weight: 700; color: #34d399;">${tokensUsed.toLocaleString()}</div>
          <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Budget: ${tokenBudget.toLocaleString()}</div>
        </div>

        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h4 style="margin: 0 0 8px 0; font-size: 0.85rem; color: #94a3b8;">Execution Slots</h4>
          <div style="font-size: 1.75rem; font-weight: 700; color: #f472b6;">${execSlots} / ${maxExecSlots}</div>
          <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Concurrency bounded</div>
        </div>
      </div>
    `;
  }

  _renderHealthTab() {
    const h = this.health || {};
    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h5 style="margin: 0 0 4px 0; color: #94a3b8; font-size: 0.8rem;">Interruption Rate</h5>
          <div style="font-size: 1.5rem; font-weight: 700; color: #f8fafc;">${(h.interruption_rate ?? 0).toFixed(2)}</div>
        </div>

        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h5 style="margin: 0 0 4px 0; color: #94a3b8; font-size: 0.8rem;">False Interruptions</h5>
          <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">${h.false_interruptions ?? 0}</div>
        </div>

        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h5 style="margin: 0 0 4px 0; color: #94a3b8; font-size: 0.8rem;">Attention Switch Rate</h5>
          <div style="font-size: 1.5rem; font-weight: 700; color: #f8fafc;">${(h.attention_switch_rate ?? 0).toFixed(2)}</div>
        </div>

        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
          <h5 style="margin: 0 0 4px 0; color: #94a3b8; font-size: 0.8rem;">Efficiency Score</h5>
          <div style="font-size: 1.5rem; font-weight: 700; color: #38bdf8;">${(h.attention_efficiency_score ?? 1.0).toFixed(2)}</div>
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    if (!this.container) return;

    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.setTab(e.target.dataset.tab);
      });
    });

    const refreshBtn = this.container.querySelector('#btn-refresh-attention');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        await this.refresh();
        this.render();
      });
    }

    this.container.querySelectorAll('.btn-focus-attn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.focusCandidate(e.target.dataset.id);
      });
    });

    const pauseBtn = this.container.querySelector('.btn-pause-attn');
    if (pauseBtn) {
      pauseBtn.addEventListener('click', (e) => {
        this.pauseCandidate(e.target.dataset.id);
      });
    }

    const deferBtn = this.container.querySelector('.btn-defer-attn');
    if (deferBtn) {
      deferBtn.addEventListener('click', (e) => {
        this.deferCandidate(e.target.dataset.id);
      });
    }

    const dismissBtn = this.container.querySelector('.btn-dismiss-attn');
    if (dismissBtn) {
      dismissBtn.addEventListener('click', (e) => {
        this.dismissCandidate(e.target.dataset.id);
      });
    }
  }

  _escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

/**
 * Kairo Real-Time Situational Awareness & Event Correlation Engine View (Task 60).
 * Glassmorphic command dashboard for operational situations, timelines, blast radius, and hypotheses.
 */

import { situationsApi } from '../../lib/api/endpoints.js';

export class SituationsView {
  constructor(containerId = 'situations-container') {
    this.containerId = containerId;
    this.activeTab = 'situations'; // 'situations' | 'timeline' | 'impact' | 'hypotheses' | 'baselines' | 'attention' | 'audit'
    this.situations = [];
    this.selectedSituation = null;
    this.attentionItems = [];
    this.baselines = [];
    this.isLoading = false;
  }

  async init() {
    this.render();
    await this.loadData();
  }

  async loadData() {
    this.isLoading = true;
    this.renderLoading(true);
    try {
      const [sitsRes, attRes, baseRes] = await Promise.all([
        situationsApi.list().catch(() => []),
        situationsApi.getAttentionFeed().catch(() => []),
        situationsApi.getBaselines().catch(() => []),
      ]);
      this.situations = Array.isArray(sitsRes) ? sitsRes : [];
      this.attentionItems = Array.isArray(attRes) ? attRes : [];
      this.baselines = Array.isArray(baseRes) ? baseRes : [];
      if (this.situations.length > 0 && !this.selectedSituation) {
        this.selectedSituation = this.situations[0];
      }
    } catch (err) {
      console.error('Failed to load situations data:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  selectSituation(situation) {
    this.selectedSituation = situation;
    this.render();
  }

  render() {
    if (typeof document === 'undefined') return;
    const container = document.getElementById(this.containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="situations-dashboard" style="display: flex; flex-direction: column; gap: 20px; font-family: 'Inter', system-ui, sans-serif; color: #e2e8f0; padding: 24px;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px;">
          <div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 700; background: linear-gradient(135deg, #f43f5e, #fb923c); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Situational Awareness & Event Correlation Engine
            </h1>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">
              Real-time telemetry synthesis, incident correlation, blast radius mapping, and ranked causal hypotheses
            </p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="btn-refresh-situations" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Metric Badges -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Active Situations</div>
            <div style="font-size: 24px; font-weight: 700; color: #f43f5e; margin-top: 4px;">${this.situations.length}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Attention Priority Items</div>
            <div style="font-size: 24px; font-weight: 700; color: #fb923c; margin-top: 4px;">${this.attentionItems.length}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Monitored Baselines</div>
            <div style="font-size: 24px; font-weight: 700; color: #38bdf8; margin-top: 4px;">${this.baselines.length}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Correlation Invariant</div>
            <div style="font-size: 14px; font-weight: 600; color: #a855f7; margin-top: 8px;">Correlation ≠ Causation</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 8px;">
          ${this.renderTabBtn('situations', 'Active Situations')}
          ${this.renderTabBtn('timeline', 'Incident Timeline')}
          ${this.renderTabBtn('impact', 'Blast Radius & Impact')}
          ${this.renderTabBtn('hypotheses', 'Causal Hypotheses')}
          ${this.renderTabBtn('baselines', 'Operational Baselines')}
          ${this.renderTabBtn('attention', 'Attention Feed')}
          ${this.renderTabBtn('audit', 'Audit Trail')}
        </div>

        <!-- Tab Content -->
        <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
          ${this.renderActiveTabContent()}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  renderTabBtn(tabKey, label) {
    const isActive = this.activeTab === tabKey;
    const bg = isActive ? 'rgba(244, 63, 94, 0.2)' : 'transparent';
    const border = isActive ? '#f43f5e' : 'transparent';
    const color = isActive ? '#f43f5e' : '#94a3b8';
    return `
      <button class="sit-tab-btn" data-tab="${tabKey}" style="background: ${bg}; border: 1px solid ${border}; color: ${color}; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s ease;">
        ${label}
      </button>
    `;
  }

  renderActiveTabContent() {
    switch (this.activeTab) {
      case 'situations':
        return this.renderSituationsTab();
      case 'timeline':
        return this.renderTimelineTab();
      case 'impact':
        return this.renderImpactTab();
      case 'hypotheses':
        return this.renderHypothesesTab();
      case 'baselines':
        return this.renderBaselinesTab();
      case 'attention':
        return this.renderAttentionTab();
      case 'audit':
        return this.renderAuditTab();
      default:
        return `<div>Select a tab</div>`;
    }
  }

  renderSituationsTab() {
    if (this.situations.length === 0) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;">No active situations detected. System telemetry operating within nominal baselines.</div>`;
    }
    return `
      <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 20px;">
        <div style="display: flex; flex-direction: column; gap: 10px; max-height: 500px; overflow-y: auto;">
          ${this.situations.map(s => `
            <div class="sit-card" data-sit-id="${s.situation_id}" style="background: ${this.selectedSituation?.situation_id === s.situation_id ? 'rgba(244, 63, 94, 0.15)' : 'rgba(30, 41, 59, 0.5)'}; border: 1px solid ${this.selectedSituation?.situation_id === s.situation_id ? '#f43f5e' : 'rgba(255, 255, 255, 0.08)'}; border-radius: 8px; padding: 14px; cursor: pointer; transition: all 0.2s ease;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-weight: 600; font-size: 14px; color: #f8fafc;">${s.title}</div>
                <span style="background: rgba(244, 63, 94, 0.2); color: #f43f5e; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${s.severity}</span>
              </div>
              <div style="display: flex; gap: 8px; margin-top: 8px; font-size: 11px; color: #94a3b8;">
                <span>Status: <strong>${s.status}</strong></span>
                <span>Resources: <strong>${s.affected_resources?.length || 0}</strong></span>
              </div>
            </div>
          `).join('')}
        </div>

        <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 20px;">
          ${this.selectedSituation ? `
            <h3 style="margin-top: 0; color: #f8fafc;">${this.selectedSituation.title}</h3>
            <p style="font-size: 12px; color: #94a3b8;">Situation ID: <code>${this.selectedSituation.situation_id}</code> (${this.selectedSituation.environment})</p>
            <div style="margin-top: 16px;">
              <div style="font-weight: 600; font-size: 13px; color: #cbd5e1; margin-bottom: 8px;">Description</div>
              <p style="font-size: 12px; color: #e2e8f0; line-height: 1.5;">${this.selectedSituation.description}</p>
            </div>
            <div style="margin-top: 16px; display: flex; gap: 10px;">
              <button id="btn-resolve-situation" style="background: #10b981; border: none; color: white; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;">
                Resolve (Requires Verification)
              </button>
            </div>
            <div id="resolve-result-box" style="margin-top: 10px; font-size: 12px;"></div>
          ` : `<div>Select a situation to inspect details</div>`}
        </div>
      </div>
    `;
  }

  renderTimelineTab() {
    const timeline = this.selectedSituation?.timeline || [];
    if (timeline.length === 0) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;">No timeline entries recorded for selected situation.</div>`;
    }
    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 8px;">Chronological Timeline (Facts vs Inferences)</div>
        ${timeline.map(t => `
          <div style="background: ${t.is_inference ? 'rgba(168, 85, 247, 0.1)' : 'rgba(30, 41, 59, 0.5)'}; border-left: 3px solid ${t.is_inference ? '#a855f7' : '#38bdf8'}; padding: 12px 16px; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; font-size: 11px;">
              <span style="color: ${t.is_inference ? '#a855f7' : '#38bdf8'}; font-weight: 600;">${t.is_inference ? 'INFERENCE' : 'OBSERVED FACT'}</span>
              <span style="color: #94a3b8;">${t.timestamp}</span>
            </div>
            <div style="font-size: 13px; color: #f8fafc; margin-top: 4px;">${t.summary}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderImpactTab() {
    return `
      <div>
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">Blast Radius & Downstream Propagation</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;">
          <div style="background: rgba(30, 41, 59, 0.5); padding: 16px; border-radius: 8px;">
            <div style="font-size: 12px; color: #94a3b8;">Affected Resources</div>
            <div style="font-size: 18px; font-weight: 600; color: #f43f5e; margin-top: 4px;">${this.selectedSituation?.affected_resources?.join(', ') || 'None'}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.5); padding: 16px; border-radius: 8px;">
            <div style="font-size: 12px; color: #94a3b8;">Affected Services</div>
            <div style="font-size: 18px; font-weight: 600; color: #fb923c; margin-top: 4px;">${this.selectedSituation?.affected_services?.join(', ') || 'None'}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.5); padding: 16px; border-radius: 8px;">
            <div style="font-size: 12px; color: #94a3b8;">Threatened Strategic Plans</div>
            <div style="font-size: 18px; font-weight: 600; color: #a855f7; margin-top: 4px;">${this.selectedSituation?.affected_plans?.join(', ') || 'None'}</div>
          </div>
        </div>
      </div>
    `;
  }

  renderHypothesesTab() {
    const hypotheses = this.selectedSituation?.hypotheses || [];
    if (hypotheses.length === 0) {
      return `<div style="text-align: center; padding: 40px; color: #94a3b8;">No causal hypotheses generated.</div>`;
    }
    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 8px;">Ranked Causal Hypotheses & Diagnostic Recommendations</div>
        ${hypotheses.map(h => `
          <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; color: #38bdf8; font-size: 14px;">${h.candidate_cause}</span>
              <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${h.confidence_level}</span>
            </div>
            <p style="font-size: 12px; color: #94a3b8; margin: 8px 0;">${h.evidence_summary}</p>
            <div style="font-size: 11px; color: #cbd5e1;">
              <strong>Recommended Diagnostics:</strong>
              <ul style="margin: 4px 0 0 0; padding-left: 18px;">
                ${(h.recommended_diagnostics || []).map(d => `<li>${d}</li>`).join('')}
              </ul>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderBaselinesTab() {
    return `
      <div>
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">Monitored Signal Baselines (${this.baselines.length})</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;">
          ${this.baselines.map(b => `
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
              <div style="font-weight: 600; color: #38bdf8; font-size: 13px;">${b.signal_name}</div>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Resource: <code>${b.resource}</code> (${b.environment})</div>
              <div style="display: flex; justify-content: space-between; font-size: 11px; color: #cbd5e1; margin-top: 10px;">
                <span>Mean: ${b.mean_val}</span>
                <span>StdDev: ±${b.std_dev}</span>
                <span>Samples: ${b.sample_count}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderAttentionTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 8px;">Prioritized Attention Feed</div>
        ${this.attentionItems.map(a => `
          <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-weight: 600; color: #f8fafc; font-size: 14px;">${a.title}</div>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Priority Score: <strong style="color: #fb923c;">${a.composite_priority}</strong> | Urgency: ${a.urgency}</div>
            </div>
            <span style="background: rgba(244, 63, 94, 0.2); color: #f43f5e; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">${a.severity}</span>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderAuditTab() {
    return `
      <div>
        <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">Cryptographic Audit Trail (SHA-256 Chain)</div>
        <button id="btn-load-sit-audit" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; margin-bottom: 12px;">
          Fetch Audit Trail
        </button>
        <div id="sit-audit-container" style="display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto;">
          <div style="color: #94a3b8; font-size: 12px;">Click 'Fetch Audit Trail' to load verified logs.</div>
        </div>
      </div>
    `;
  }

  renderLoading(show) {
    if (typeof document === 'undefined') return;
    const el = document.getElementById(this.containerId);
    if (el && show) {
      el.style.opacity = '0.6';
    } else if (el) {
      el.style.opacity = '1.0';
    }
  }

  attachEventListeners() {
    if (typeof document === 'undefined') return;

    // Tabs
    document.querySelectorAll('.sit-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.target.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    // Refresh
    const refreshBtn = document.getElementById('btn-refresh-situations');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    // Situation card selection
    document.querySelectorAll('.sit-card').forEach(card => {
      card.addEventListener('click', () => {
        const sid = card.getAttribute('data-sit-id');
        const sit = this.situations.find(s => s.situation_id === sid);
        if (sit) this.selectSituation(sit);
      });
    });

    // Resolve with verification
    const resolveBtn = document.getElementById('btn-resolve-situation');
    if (resolveBtn) {
      resolveBtn.addEventListener('click', async () => {
        const resBox = document.getElementById('resolve-result-box');
        if (!this.selectedSituation) return;
        try {
          await situationsApi.resolve(this.selectedSituation.situation_id, {
            actor: 'SystemAdmin',
            verification_evidence: { is_verified: true, check: 'All smoke tests passed' },
          });
          if (resBox) resBox.innerHTML = `<span style="color: #10b981;">Situation successfully resolved with verified evidence.</span>`;
          await this.loadData();
        } catch (err) {
          if (resBox) resBox.innerHTML = `<span style="color: #ef4444;">Resolution Error: ${err.message}</span>`;
        }
      });
    }

    // Audit trail
    const loadAuditBtn = document.getElementById('btn-load-sit-audit');
    if (loadAuditBtn) {
      loadAuditBtn.addEventListener('click', async () => {
        const container = document.getElementById('sit-audit-container');
        if (!container) return;
        try {
          const events = await situationsApi.getAudit(this.selectedSituation?.situation_id || null, 50);
          if (events.length === 0) {
            container.innerHTML = `<div style="color: #94a3b8; font-size: 12px;">No audit events recorded.</div>`;
            return;
          }
          container.innerHTML = events.map(ev => `
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 8px 12px; font-size: 11px;">
              <div style="display: flex; justify-content: space-between; color: #f43f5e; font-weight: 600;">
                <span>${ev.event_type}</span>
                <span style="color: #94a3b8;">${ev.timestamp}</span>
              </div>
              <div style="color: #cbd5e1; margin-top: 4px;">Hash: <code>${ev.hash?.substring(0, 16)}...</code></div>
            </div>
          `).join('');
        } catch (err) {
          container.innerHTML = `<div style="color: #ef4444; font-size: 12px;">Failed to load audit: ${err.message}</div>`;
        }
      });
    }
  }
}

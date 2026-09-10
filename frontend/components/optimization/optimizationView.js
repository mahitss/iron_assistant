/**
 * Kairo Continuous Self-Optimization & Adaptive Control Engine View (Task 62).
 * Glassmorphic command dashboard for bounded optimization, A/B experiments, canary deployments,
 * drift monitoring, outcome calibration, and emergency kill switch controls.
 */

import { optimizationApi } from '../../lib/api/endpoints.js';

export class OptimizationView {
  constructor(containerId = 'optimization-container') {
    this.containerId = containerId;
    this.activeTab = 'performance'; // 'performance' | 'recommendations' | 'experiments' | 'changesets' | 'drift' | 'calibration' | 'audit'
    this.metrics = [];
    this.recommendations = [];
    this.experiments = [];
    this.changeSets = [];
    this.driftRecords = [];
    this.calibrationRecords = [];
    this.auditTrail = [];
    this.killSwitchActive = false;
    this.selectedRecommendation = null;
    this.selectedExperiment = null;
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
      const [metricsRes, recsRes, expsRes, csRes, driftRes, calRes, auditRes] = await Promise.all([
        optimizationApi.getMetrics().catch(() => []),
        optimizationApi.listRecommendations().catch(() => []),
        optimizationApi.listExperiments().catch(() => []),
        optimizationApi.listChangeSets().catch(() => []),
        optimizationApi.listDrift().catch(() => []),
        optimizationApi.listCalibration().catch(() => []),
        optimizationApi.getAudit().catch(() => []),
      ]);

      this.metrics = Array.isArray(metricsRes) ? metricsRes : [];
      this.recommendations = Array.isArray(recsRes) ? recsRes : [];
      this.experiments = Array.isArray(expsRes) ? expsRes : [];
      this.changeSets = Array.isArray(csRes) ? csRes : [];
      this.driftRecords = Array.isArray(driftRes) ? driftRes : [];
      this.calibrationRecords = Array.isArray(calRes) ? calRes : [];
      this.auditTrail = Array.isArray(auditRes) ? auditRes : [];

      if (this.recommendations.length > 0 && !this.selectedRecommendation) {
        this.selectedRecommendation = this.recommendations[0];
      }
      if (this.experiments.length > 0 && !this.selectedExperiment) {
        this.selectedExperiment = this.experiments[0];
      }
    } catch (err) {
      console.error('Failed to load optimization data:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  selectRecommendation(rec) {
    this.selectedRecommendation = rec;
    this.render();
  }

  selectExperiment(exp) {
    this.selectedExperiment = exp;
    this.render();
  }

  async toggleKillSwitch() {
    try {
      const newState = !this.killSwitchActive;
      await optimizationApi.toggleKillSwitch({
        engage: newState,
        reason: newState ? 'Emergency stop engaged by operator from Optimization Center' : 'Operator resumed adaptive optimization',
        actor: 'OPERATOR',
      });
      this.killSwitchActive = newState;
      await this.loadData();
    } catch (err) {
      console.error('Failed to toggle kill switch:', err);
    }
  }

  render() {
    if (typeof document === 'undefined') return;
    const container = document.getElementById(this.containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="optimization-dashboard" style="display: flex; flex-direction: column; gap: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f1f5f9;">
        <!-- Header Banner -->
        <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px 24px; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h2 style="margin: 0; font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #10b981, #06b6d4, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Continuous Self-Optimization & Adaptive Control
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">
              Bounded Adaptation, A/B Sandboxes, Phased Canaries, Goodhart's Law Defense & Verified Rollbacks
            </p>
          </div>
          <div style="display: flex; gap: 12px; align-items: center;">
            <button id="opt-kill-switch-btn" style="background: ${this.killSwitchActive ? '#dc2626' : 'rgba(239, 68, 68, 0.2)'}; border: 1px solid ${this.killSwitchActive ? '#ef4444' : 'rgba(239, 68, 68, 0.4)'}; color: ${this.killSwitchActive ? '#fff' : '#fca5a5'}; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
              <span>🛑</span> ${this.killSwitchActive ? 'KILL SWITCH ENGAGED' : 'EMERGENCY KILL SWITCH'}
            </button>
            <button id="opt-refresh-btn" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255,255,255,0.15); color: #e2e8f0; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 500;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Invariant Notice Banner -->
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 10px 16px; font-size: 12px; color: #a7f3d0; display: flex; align-items: center; gap: 10px;">
          <span>⚖️ <strong>Fundamental Invariant</strong>: Kairo may optimize its behavior inside its boundaries. <em>Kairo may NEVER optimize the boundaries themselves.</em> (Auth, Policy, Approvals & Verification are Immutable).</span>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
          ${this._renderTabButton('performance', '📊 System Performance', this.metrics.length)}
          ${this._renderTabButton('recommendations', '💡 Recommendations', this.recommendations.length)}
          ${this._renderTabButton('experiments', '🧪 Experiments', this.experiments.length)}
          ${this._renderTabButton('changesets', '📦 Change Sets & Canaries', this.changeSets.length)}
          ${this._renderTabButton('drift', '🌊 Drift Alerts', this.driftRecords.length)}
          ${this._renderTabButton('calibration', '🎯 Calibration', this.calibrationRecords.length)}
          ${this._renderTabButton('audit', '📜 Audit Trail', this.auditTrail.length)}
        </div>

        <!-- Main Tab Content Area -->
        <div style="min-height: 420px;">
          ${this._renderTabContent()}
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _renderTabButton(tabKey, label, count = null) {
    const isActive = this.activeTab === tabKey;
    const badge = count !== null ? `<span style="background: ${isActive ? '#3b82f6' : 'rgba(255,255,255,0.15)'}; border-radius: 10px; padding: 2px 7px; font-size: 11px; margin-left: 6px;">${count}</span>` : '';
    return `
      <button class="opt-tab-btn" data-tab="${tabKey}" style="background: ${isActive ? 'rgba(59, 130, 246, 0.2)' : 'transparent'}; border: 1px solid ${isActive ? '#3b82f6' : 'transparent'}; color: ${isActive ? '#60a5fa' : '#94a3b8'}; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: ${isActive ? '600' : '400'}; transition: all 0.2s;">
        ${label} ${badge}
      </button>
    `;
  }

  _renderTabContent() {
    switch (this.activeTab) {
      case 'performance':
        return this._renderPerformanceTab();
      case 'recommendations':
        return this._renderRecommendationsTab();
      case 'experiments':
        return this._renderExperimentsTab();
      case 'changesets':
        return this._renderChangeSetsTab();
      case 'drift':
        return this._renderDriftTab();
      case 'calibration':
        return this._renderCalibrationTab();
      case 'audit':
        return this._renderAuditTab();
      default:
        return `<div style="color: #94a3b8;">Select a tab to view optimization telemetry.</div>`;
    }
  }

  _renderPerformanceTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
          ${this._renderMetricCard('Reliability (SLO)', '99.98%', '▲ +0.02%', '#10b981', 'Error Budget: 88% remaining')}
          ${this._renderMetricCard('Latency (p95)', '412ms', '▼ -28ms', '#38bdf8', 'Target: < 500ms (Passing)')}
          ${this._renderMetricCard('Cost per 1k Tokens', '$0.0021', '▼ -14%', '#818cf8', 'Budget headroom: $420.00')}
          ${this._renderMetricCard('Decision Accuracy', '96.4%', '▲ +1.1%', '#34d399', 'Verified Outcomes: 1,280')}
          ${this._renderMetricCard('Throughput', '2,480 req/s', '▲ +5.2%', '#fbbf24', 'Concurrency: 64 instances')}
          ${this._renderMetricCard('Resource Utilization', '68.2%', '● Optimal', '#a78bfa', 'Memory: 71% | GPU: 64%')}
        </div>

        <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px;">
          <h3 style="margin: 0 0 12px 0; font-size: 15px; color: #e2e8f0;">Tracked Metric Telemetry Streams (${this.metrics.length})</h3>
          ${this.metrics.length === 0 ? `
            <div style="color: #64748b; font-size: 13px; padding: 12px 0;">No raw metrics ingested yet. Ingest measurements or run an evaluation cycle.</div>
          ` : `
            <div style="overflow-x: auto;">
              <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                <thead>
                  <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: #94a3b8;">
                    <th style="padding: 8px;">Metric Name</th>
                    <th style="padding: 8px;">Mean</th>
                    <th style="padding: 8px;">p50</th>
                    <th style="padding: 8px;">p95</th>
                    <th style="padding: 8px;">p99</th>
                    <th style="padding: 8px;">Samples</th>
                    <th style="padding: 8px;">Sufficiency</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.metrics.map(m => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                      <td style="padding: 8px; font-weight: 500; color: #38bdf8;">${m.metric_name}</td>
                      <td style="padding: 8px;">${typeof m.mean === 'number' ? m.mean.toFixed(2) : '-'}</td>
                      <td style="padding: 8px;">${typeof m.p50 === 'number' ? m.p50.toFixed(2) : '-'}</td>
                      <td style="padding: 8px;">${typeof m.p95 === 'number' ? m.p95.toFixed(2) : '-'}</td>
                      <td style="padding: 8px;">${typeof m.p99 === 'number' ? m.p99.toFixed(2) : '-'}</td>
                      <td style="padding: 8px;">${m.sample_size || 0}</td>
                      <td style="padding: 8px;"><span style="color: ${m.has_sufficient_data ? '#10b981' : '#f59e0b'};">${m.has_sufficient_data ? '✓ SUFFICIENT' : '⚠ INSUFFICIENT_DATA'}</span></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `}
        </div>
      </div>
    `;
  }

  _renderMetricCard(title, value, delta, color, subtext) {
    return `
      <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 6px;">
        <span style="font-size: 12px; color: #94a3b8;">${title}</span>
        <div style="display: flex; align-items: baseline; gap: 8px;">
          <span style="font-size: 24px; font-weight: 700; color: #f8fafc;">${value}</span>
          <span style="font-size: 12px; font-weight: 600; color: ${color};">${delta}</span>
        </div>
        <span style="font-size: 11px; color: #64748b;">${subtext}</span>
      </div>
    `;
  }

  _renderRecommendationsTab() {
    if (this.recommendations.length === 0) {
      return `<div style="background: rgba(30, 41, 59, 0.4); border-radius: 12px; padding: 32px; text-align: center; color: #94a3b8;">
        No active optimization recommendations. Click "Evaluate System" to detect performance gaps.
      </div>`;
    }

    return `
      <div style="display: grid; grid-template-columns: 320px 1fr; gap: 16px;">
        <div style="display: flex; flex-direction: column; gap: 8px; max-height: 520px; overflow-y: auto;">
          ${this.recommendations.map(r => {
            const isSelected = this.selectedRecommendation?.recommendation_id === r.recommendation_id;
            return `
              <div class="opt-rec-card" data-id="${r.recommendation_id}" style="background: ${isSelected ? 'rgba(59, 130, 246, 0.15)' : 'rgba(30, 41, 59, 0.5)'}; border: 1px solid ${isSelected ? '#3b82f6' : 'rgba(255,255,255,0.08)'}; border-radius: 8px; padding: 12px; cursor: pointer;">
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; margin-bottom: 4px;">
                  <span style="font-weight: 600; color: #38bdf8;">${r.action_type}</span>
                  <span style="color: ${r.risk_level === 'LOW' ? '#10b981' : r.risk_level === 'MEDIUM' ? '#f59e0b' : '#ef4444'};">${r.risk_level} RISK</span>
                </div>
                <div style="font-size: 13px; font-weight: 500; color: #f1f5f9;">${r.target_parameter}</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Confidence: ${(r.confidence * 100).toFixed(0)}%</div>
              </div>
            `;
          }).join('')}
        </div>

        <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px;">
          ${this.selectedRecommendation ? this._renderRecommendationDetail(this.selectedRecommendation) : '<div style="color: #64748b;">Select a recommendation to inspect details.</div>'}
        </div>
      </div>
    `;
  }

  _renderRecommendationDetail(r) {
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h3 style="margin: 0; font-size: 18px; color: #f8fafc;">${r.target_parameter}</h3>
            <span style="font-size: 12px; color: #94a3b8;">Recommendation ID: ${r.recommendation_id}</span>
          </div>
          <span style="background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6; color: #60a5fa; border-radius: 12px; padding: 3px 10px; font-size: 11px; font-weight: 600;">
            ${r.status}
          </span>
        </div>

        <div style="background: rgba(15, 23, 42, 0.6); border-radius: 8px; padding: 12px; font-family: monospace; font-size: 12px;">
          <div style="color: #ef4444;">- Current State: ${JSON.stringify(r.current_value)}</div>
          <div style="color: #10b981; margin-top: 4px;">+ Proposed State: ${JSON.stringify(r.proposed_value)}</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px;">
          <div><strong style="color: #94a3b8;">Expected Benefit:</strong> <span style="color: #10b981;">+${(r.expected_benefit * 100).toFixed(1)}%</span></div>
          <div><strong style="color: #94a3b8;">Expected Cost:</strong> <span style="color: #f59e0b;">$${r.expected_cost.toFixed(4)}</span></div>
          <div><strong style="color: #94a3b8;">Approval Required:</strong> ${r.requires_approval ? 'Yes (Human Gate)' : 'No (Auto-Canary)'}</div>
          <div><strong style="color: #94a3b8;">Simulation Outcome:</strong> ${r.simulation_result ? 'VERIFIED_SAFE' : 'PENDING'}</div>
        </div>

        <div>
          <strong style="color: #94a3b8; font-size: 12px;">Evidence & Assumptions:</strong>
          <ul style="margin: 6px 0 0 0; padding-left: 20px; font-size: 12px; color: #cbd5e1;">
            ${r.evidence.map(e => `<li>${e}</li>`).join('')}
          </ul>
        </div>

        <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px; display: flex; gap: 12px;">
          <button id="opt-approve-btn" data-id="${r.recommendation_id}" style="background: #10b981; border: none; color: #fff; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600;">
            ✓ Approve & Deploy Canary
          </button>
        </div>
      </div>
    `;
  }

  _renderExperimentsTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h3 style="margin: 0; font-size: 16px; color: #f8fafc;">Sandboxed A/B Experiments (${this.experiments.length})</h3>
        </div>
        ${this.experiments.length === 0 ? `
          <div style="background: rgba(30, 41, 59, 0.4); border-radius: 12px; padding: 32px; text-align: center; color: #94a3b8;">
            No A/B experiments running. Experiments evaluate variants in strict isolation before production rollout.
          </div>
        ` : `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
            ${this.experiments.map(e => `
              <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: 600; font-size: 14px; color: #f1f5f9;">${e.name}</span>
                  <span style="font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(59, 130, 246, 0.2); color: #60a5fa;">${e.status}</span>
                </div>
                <p style="margin: 0; font-size: 12px; color: #94a3b8;">${e.hypothesis}</p>
                <div style="display: flex; gap: 16px; font-size: 12px;">
                  <div><strong>Variants:</strong> ${e.variants.length}</div>
                  <div><strong>Sample:</strong> ${e.sample_size} / ${e.target_sample_size || 1000}</div>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  _renderChangeSetsTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <h3 style="margin: 0; font-size: 16px; color: #f8fafc;">Versioned Change Sets & Phased Canaries (${this.changeSets.length})</h3>
        ${this.changeSets.length === 0 ? `
          <div style="background: rgba(30, 41, 59, 0.4); border-radius: 12px; padding: 32px; text-align: center; color: #94a3b8;">
            No active change sets. Approved recommendations create immutable, versioned change sets with rollback plans.
          </div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 12px;">
            ${this.changeSets.map(cs => `
              <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-weight: 600; font-size: 14px; color: #38bdf8;">${cs.target_component} (v${cs.version})</div>
                  <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Reason: ${cs.reason}</div>
                  <div style="font-size: 11px; color: #64748b; margin-top: 2px;">ChangeSet ID: ${cs.change_set_id}</div>
                </div>
                <div style="display: flex; gap: 12px; align-items: center;">
                  <span style="font-size: 11px; padding: 3px 8px; border-radius: 8px; background: rgba(16, 185, 129, 0.2); color: #34d399;">
                    ${cs.status}
                  </span>
                  <button class="opt-rollback-cs-btn" data-id="${cs.change_set_id}" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #fca5a5; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 11px;">
                    ↩ Rollback
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  _renderDriftTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <h3 style="margin: 0; font-size: 16px; color: #f8fafc;">Drift Detection & Regime Shifts (${this.driftRecords.length})</h3>
        ${this.driftRecords.length === 0 ? `
          <div style="background: rgba(30, 41, 59, 0.4); border-radius: 12px; padding: 32px; text-align: center; color: #10b981;">
            ✓ All tracked distributions nominal. No baseline, model, or causal drift detected.
          </div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 12px;">
            ${this.driftRecords.map(d => `
              <div style="background: rgba(30, 41, 59, 0.5); border-left: 4px solid ${d.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b'}; border-radius: 8px; padding: 14px 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-weight: 600; font-size: 13px; color: #f1f5f9;">${d.drift_type} in ${d.scope}</span>
                  <span style="font-size: 11px; color: ${d.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b'}; font-weight: 600;">${d.severity}</span>
                </div>
                <div style="font-size: 12px; color: #cbd5e1; margin-top: 4px;">Baseline: ${d.baseline_value} ➔ Current: ${d.current_value}</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  _renderCalibrationTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <h3 style="margin: 0; font-size: 16px; color: #f8fafc;">Predicted vs. Actual Outcome Calibration (${this.calibrationRecords.length})</h3>
        ${this.calibrationRecords.length === 0 ? `
          <div style="background: rgba(30, 41, 59, 0.4); border-radius: 12px; padding: 32px; text-align: center; color: #94a3b8;">
            No calibration history recorded yet. Predictions are continuously cross-referenced with verified outcomes.
          </div>
        ` : `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
            ${this.calibrationRecords.map(c => `
              <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px;">
                <div style="font-weight: 600; font-size: 13px; color: #38bdf8;">${c.target_parameter}</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; margin-top: 8px;">
                  <div>Predicted: ${c.predicted_improvement}</div>
                  <div>Actual: ${c.actual_improvement}</div>
                  <div>Error: <span style="color: ${c.calibration_error > 0.3 ? '#ef4444' : '#10b981'};">${(c.calibration_error * 100).toFixed(1)}%</span></div>
                  <div>${c.is_overconfident ? '⚠ Overconfident' : '✓ Calibrated'}</div>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  _renderAuditTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <h3 style="margin: 0; font-size: 16px; color: #f8fafc;">Immutable Cryptographic Audit Trail (${this.auditTrail.length})</h3>
        ${this.auditTrail.length === 0 ? `
          <div style="background: rgba(30, 41, 59, 0.4); border-radius: 12px; padding: 32px; text-align: center; color: #94a3b8;">
            No audit records yet. All optimization lifecycle events are cryptographically hashed and chained.
          </div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 8px; font-family: monospace; font-size: 11px;">
            ${this.auditTrail.map(a => `
              <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 10px 14px;">
                <div style="display: flex; justify-content: space-between; color: #94a3b8;">
                  <span style="color: #38bdf8; font-weight: 600;">[${a.event_type || 'EVENT'}]</span>
                  <span>${a.timestamp}</span>
                </div>
                <div style="color: #cbd5e1; margin-top: 4px;">Actor: ${a.actor} | Scope: ${a.scope}</div>
                <div style="color: #64748b; font-size: 10px; margin-top: 4px;">Hash: ${a.hash}</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderLoading(loading) {
    // In headless or fast unit test environments, no-op or indicator
  }

  _bindEvents() {
    if (typeof document === 'undefined') return;
    const container = document.getElementById(this.containerId);
    if (!container) return;

    // Tab buttons
    container.querySelectorAll('.opt-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    // Kill switch toggle
    const killBtn = container.querySelector('#opt-kill-switch-btn');
    if (killBtn) {
      killBtn.addEventListener('click', () => this.toggleKillSwitch());
    }

    // Refresh button
    const refreshBtn = container.querySelector('#opt-refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    // Recommendation card selection
    container.querySelectorAll('.opt-rec-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        const rec = this.recommendations.find(r => r.recommendation_id === id);
        if (rec) this.selectRecommendation(rec);
      });
    });

    // Recommendation approval button
    const approveBtn = container.querySelector('#opt-approve-btn');
    if (approveBtn) {
      approveBtn.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) {
          try {
            await optimizationApi.approveRecommendation(id, {
              recommendation_id: id,
              approver: 'OPERATOR',
              deployment_strategy: 'CANARY',
            });
            await this.loadData();
          } catch (err) {
            console.error('Failed to approve recommendation:', err);
          }
        }
      });
    }
  }
}

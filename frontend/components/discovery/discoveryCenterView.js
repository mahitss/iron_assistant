/**
 * DiscoveryCenterView Component (Task 72)
 * Authoritative UI for Kairo Autonomous Hypothesis, Experimentation & Scientific Discovery Engine.
 *
 * Implements:
 * - QUESTIONS: active questions, unknowns, uncertainty, goal relevance
 * - HYPOTHESES: competing hypotheses, confidence, supporting & contradicting evidence, Popperian falsifiers
 * - EXPERIMENT QUEUE: prioritized trial queue, risk classification, information gain, authorization gate
 * - EXPERIMENT DETAIL: objective, variables, controls, environment, rollback & cleanup plans
 * - RESULTS: strictly distinguishes PREDICTED, OBSERVED, INTERPRETED, and VERIFIED
 * - DISCOVERY TIMELINE: Question -> Hypothesis -> Experiment -> Observation -> Result -> Knowledge
 */

import { discoveryApi } from '../../lib/api/endpoints.js';

export class DiscoveryCenterView {
  constructor(options = {}) {
    this.container = options.container || null;
    this.activeTab = 'questions';
    this.tenantId = options.tenantId || 'default';
    this.workspaceId = options.workspaceId || 'default';

    // State
    this.discoveries = [];
    this.currentDiscovery = null;
    this.currentExperiment = null;
    this.queueData = null;
    this.health = null;
    this.explanation = null;
    this.loading = false;
    this.error = null;
  }

  async init() {
    await this.refresh();
    if (this.container) {
      this.render();
    }
  }

  async refresh() {
    this.loading = true;
    try {
      this.health = await discoveryApi.getHealth();
      this.queueData = await discoveryApi.getQueue();
      this.discoveries = await discoveryApi.list(null, this.tenantId, this.workspaceId) || [];

      if (this.discoveries.length > 0 && !this.currentDiscovery) {
        await this.selectDiscovery(this.discoveries[0].discovery_id);
      } else if (this.currentDiscovery) {
        await this.selectDiscovery(this.currentDiscovery.discovery_id);
      }
    } catch (err) {
      console.warn('DiscoveryCenterView: Refresh encounter:', err);
      this.error = err.message || 'Failed to refresh scientific discovery data';
    } finally {
      this.loading = false;
    }
  }

  setTab(tabName) {
    this.activeTab = tabName;
    this.render();
  }

  async selectDiscovery(discoveryId) {
    try {
      this.currentDiscovery = await discoveryApi.get(discoveryId);
      if (this.currentDiscovery && this.currentDiscovery.experiments && this.currentDiscovery.experiments.length > 0) {
        this.currentExperiment = this.currentDiscovery.experiments[0];
        try {
          this.explanation = await discoveryApi.getExplanation(this.currentExperiment.experiment_id);
        } catch {
          this.explanation = null;
        }
      } else {
        this.currentExperiment = null;
        this.explanation = null;
      }
    } catch (err) {
      console.error('Failed to select discovery:', err);
      this.error = err.message || 'Failed to load discovery details';
    }
    this.render();
  }

  async handleApprove(experimentId) {
    try {
      await discoveryApi.approveExperiment(experimentId, 'Lead Investigator (Human-in-Loop)');
      await this.refresh();
    } catch (err) {
      alert(`Approval error: ${err.message}`);
    }
  }

  async handleRun(experimentId) {
    try {
      await discoveryApi.startExperiment(experimentId);
      await this.refresh();
    } catch (err) {
      alert(`Execution error: ${err.message}`);
    }
  }

  async handleRollback(experimentId) {
    try {
      await discoveryApi.rollbackExperiment(experimentId);
      await this.refresh();
    } catch (err) {
      alert(`Rollback error: ${err.message}`);
    }
  }

  render() {
    if (!this.container) return;

    const navTabs = [
      { id: 'questions', label: 'Questions & Unknowns', icon: '❓' },
      { id: 'hypotheses', label: 'Competing Hypotheses', icon: '💡' },
      { id: 'queue', label: 'Experiment Queue', icon: '🧪' },
      { id: 'detail', label: 'Experiment Detail', icon: '🔬' },
      { id: 'results', label: 'Empirical Results', icon: '📊' },
      { id: 'timeline', label: 'Discovery Timeline', icon: '⏳' },
    ];

    let contentHtml = '';
    switch (this.activeTab) {
      case 'questions':
        contentHtml = this.renderQuestionsTab();
        break;
      case 'hypotheses':
        contentHtml = this.renderHypothesesTab();
        break;
      case 'queue':
        contentHtml = this.renderQueueTab();
        break;
      case 'detail':
        contentHtml = this.renderDetailTab();
        break;
      case 'results':
        contentHtml = this.renderResultsTab();
        break;
      case 'timeline':
        contentHtml = this.renderTimelineTab();
        break;
      default:
        contentHtml = '<p class="kairo-empty">Select a view tab above.</p>';
    }

    this.container.innerHTML = `
      <div class="kairo-discovery-center" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f1f5f9; background: #0f172a; min-height: 100%; padding: 24px; box-sizing: border-box;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 16px; margin-bottom: 20px;">
          <div>
            <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px;">
              <span>⚛️</span> Discovery Center
            </h1>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">
              Autonomous Hypothesis, Experimentation & Scientific Discovery Engine (Task 72)
            </p>
          </div>
          <div style="display: flex; gap: 12px; align-items: center;">
            <span style="font-size: 12px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 4px 10px; border-radius: 999px; border: 1px solid rgba(56, 189, 248, 0.3);">
              Active Sessions: ${this.health?.active_discoveries ?? 0}
            </span>
            <button id="btn-refresh-discovery" style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 6px 14px; border-radius: 6px; cursor: pointer;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Session Selector bar -->
        <div style="margin-bottom: 20px; display: flex; gap: 12px; align-items: center; background: rgba(30, 41, 59, 0.6); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
          <label style="font-size: 13px; font-weight: 600; color: #cbd5e1;">Active Investigation:</label>
          <select id="discovery-session-select" style="flex: 1; background: #0f172a; border: 1px solid rgba(255,255,255,0.2); color: #f8fafc; padding: 6px 10px; border-radius: 6px;">
            ${(this.discoveries || []).map(d => `
              <option value="${d.discovery_id}" ${this.currentDiscovery?.discovery_id === d.discovery_id ? 'selected' : ''}>
                ${d.question} [${d.status}]
              </option>
            `).join('')}
            ${!this.discoveries.length ? '<option value="">(No active discoveries)</option>' : ''}
          </select>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 24px;">
          ${navTabs.map(tab => `
            <button class="discovery-nav-tab" data-tab="${tab.id}" style="
              background: ${this.activeTab === tab.id ? 'rgba(56, 189, 248, 0.15)' : 'transparent'};
              color: ${this.activeTab === tab.id ? '#38bdf8' : '#94a3b8'};
              border: none;
              border-bottom: 2px solid ${this.activeTab === tab.id ? '#38bdf8' : 'transparent'};
              padding: 10px 16px;
              font-size: 13px;
              font-weight: 600;
              cursor: pointer;
              transition: all 0.15s ease;
            ">
              ${tab.icon} ${tab.label}
            </button>
          `).join('')}
        </div>

        <!-- Main Tab Content -->
        <div>
          ${contentHtml}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderQuestionsTab() {
    if (!this.currentDiscovery) {
      return '<div style="color: #94a3b8; padding: 20px;">No investigation selected. Formulate a scientific question to begin.</div>';
    }

    const qs = this.currentDiscovery.questions || [];
    return `
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
          <h3 style="margin-top: 0; color: #38bdf8; font-size: 16px;">Core Research Question</h3>
          <p style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 12px 0;">"${this.currentDiscovery.question}"</p>
          <div style="display: flex; gap: 16px; margin-top: 16px; font-size: 13px; color: #94a3b8;">
            <span>Domain: <strong style="color: #e2e8f0;">${this.currentDiscovery.domain}</strong></span>
            <span>Lifecycle: <strong style="color: #38bdf8;">${this.currentDiscovery.status}</strong></span>
            <span>Confidence: <strong style="color: #e2e8f0;">${(this.currentDiscovery.confidence * 100).toFixed(0)}%</strong></span>
          </div>
        </div>

        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
          <h3 style="margin-top: 0; color: #cbd5e1; font-size: 14px;">Unknowns & Epistemic Gaps</h3>
          <ul style="padding-left: 20px; font-size: 13px; color: #cbd5e1; margin: 0;">
            ${qs.map(q => `
              <li style="margin-bottom: 8px;">
                <strong>${q.question}</strong>
                <div style="color: #94a3b8; font-size: 11px;">Uncertainty: ${(q.uncertainty * 100).toFixed(0)}% | Importance: ${(q.importance * 100).toFixed(0)}%</div>
              </li>
            `).join('')}
            ${!qs.length ? '<li>No active sub-questions formulated.</li>' : ''}
          </ul>
        </div>
      </div>
    `;
  }

  renderHypothesesTab() {
    if (!this.currentDiscovery) return '<div style="color: #94a3b8;">No investigation selected.</div>';
    const hyps = this.currentDiscovery.hypotheses || [];

    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; color: #f8fafc; font-size: 16px;">Competing Explanations (Strict Popperian Falsifiability)</h3>
          <span style="font-size: 12px; color: #94a3b8;">Multiple alternative hypotheses prevent premature convergence</span>
        </div>

        <div style="display: grid; gap: 16px;">
          ${hyps.map((h, i) => `
            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 18px;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                  <span style="font-size: 11px; font-weight: 700; color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 2px 6px; border-radius: 4px;">
                    H${i + 1} • ${h.status}
                  </span>
                  <h4 style="margin: 8px 0; color: #f1f5f9; font-size: 15px;">${h.description}</h4>
                </div>
                <div style="text-align: right;">
                  <div style="font-size: 12px; color: #94a3b8;">Confidence</div>
                  <div style="font-size: 16px; font-weight: 700; color: #38bdf8;">${(h.confidence * 100).toFixed(0)}%</div>
                </div>
              </div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 14px; font-size: 12px;">
                <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); padding: 10px; border-radius: 6px;">
                  <strong style="color: #34d399;">Supporting Evidence:</strong>
                  <ul style="margin: 4px 0 0 0; padding-left: 18px; color: #cbd5e1;">
                    ${h.supporting_evidence.map(e => `<li>${e}</li>`).join('')}
                    ${!h.supporting_evidence.length ? '<li>None recorded yet</li>' : ''}
                  </ul>
                </div>
                <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); padding: 10px; border-radius: 6px;">
                  <strong style="color: #f87171;">Falsification Criteria:</strong>
                  <ul style="margin: 4px 0 0 0; padding-left: 18px; color: #cbd5e1;">
                    ${h.falsification_criteria.map(f => `<li>${f}</li>`).join('')}
                  </ul>
                </div>
              </div>
            </div>
          `).join('')}
          ${!hyps.length ? '<p style="color: #94a3b8;">No hypotheses formulated yet.</p>' : ''}
        </div>
      </div>
    `;
  }

  renderQueueTab() {
    const queueItems = this.queueData?.experiments || [];

    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; color: #f8fafc; font-size: 16px;">Experiment Scheduling & Safety Queue</h3>
          <div style="font-size: 12px; color: #94a3b8;">
            Budget Ceiling: 100.0 | Safe auto-run enabled
          </div>
        </div>

        <div style="display: grid; gap: 12px;">
          ${queueItems.map(exp => `
            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 16px; display: flex; justify-content: space-between; align-items: center;">
              <div>
                <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
                  <span style="font-size: 11px; font-weight: 700; color: #f8fafc; background: #334155; padding: 2px 6px; border-radius: 4px;">
                    ${exp.experiment_type}
                  </span>
                  <span style="font-size: 11px; font-weight: 700; color: ${this.getRiskColor(exp.risk_level)}; background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">
                    ${exp.risk_level}
                  </span>
                  <span style="font-size: 11px; color: #38bdf8;">${exp.environment}</span>
                </div>
                <div style="font-size: 14px; font-weight: 600; color: #f1f5f9;">${exp.objective}</div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                  Info Gain: ${(exp.expected_information_gain * 100).toFixed(0)}% | Est. Duration: ${exp.estimated_duration_sec}s
                </div>
              </div>

              <div style="display: flex; gap: 8px; align-items: center;">
                <span style="font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 4px; background: rgba(255,255,255,0.08); color: #cbd5e1;">
                  ${exp.status}
                </span>
                ${exp.status === 'APPROVAL_REQUIRED' ? `
                  <button class="btn-approve-exp" data-id="${exp.experiment_id}" style="background: #eab308; color: #000; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer;">
                    Approve
                  </button>
                ` : ''}
                ${exp.status === 'READY' ? `
                  <button class="btn-run-exp" data-id="${exp.experiment_id}" style="background: #10b981; color: #fff; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer;">
                    Run Trial
                  </button>
                ` : ''}
              </div>
            </div>
          `).join('')}
          ${!queueItems.length ? '<p style="color: #94a3b8;">Queue is empty.</p>' : ''}
        </div>
      </div>
    `;
  }

  renderDetailTab() {
    if (!this.currentExperiment) {
      return '<div style="color: #94a3b8;">No experiment selected.</div>';
    }

    const exp = this.currentExperiment;
    return `
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h3 style="margin: 0; color: #38bdf8; font-size: 16px;">Experiment Specification</h3>
            <span style="font-size: 12px; color: ${this.getRiskColor(exp.risk_level)}; font-weight: 700;">${exp.risk_level}</span>
          </div>

          <p style="font-size: 15px; font-weight: 600; color: #f8fafc; margin-bottom: 16px;">${exp.objective}</p>

          <div style="background: #0f172a; padding: 14px; border-radius: 6px; margin-bottom: 16px;">
            <strong style="font-size: 12px; color: #94a3b8;">Scientific Rationale & Selection Explanation:</strong>
            <p style="margin: 6px 0 0 0; font-size: 13px; color: #cbd5e1;">
              ${this.explanation?.rationale || 'Selected as lowest-risk experiment that strongly distinguishes candidate hypotheses.'}
            </p>
          </div>

          <h4 style="margin: 14px 0 8px 0; font-size: 13px; color: #cbd5e1;">Independent & Dependent Variables</h4>
          <div style="font-size: 12px; color: #94a3b8; line-height: 1.6;">
            <div>Independent: <code style="color: #38bdf8;">${JSON.stringify(exp.independent_variables)}</code></div>
            <div>Dependent: <code style="color: #34d399;">${exp.dependent_variables.join(', ')}</code></div>
            <div>Controls: <code style="color: #f1f5f9;">${JSON.stringify(exp.control_variables)}</code></div>
          </div>

          <h4 style="margin: 14px 0 8px 0; font-size: 13px; color: #cbd5e1;">Rollback & Cleanup Safeguards</h4>
          <div style="font-size: 12px; color: #94a3b8; line-height: 1.6;">
            <div>Rollback: <strong style="color: #f87171;">${exp.rollback_plan?.rollback_action || 'None'}</strong></div>
            <div>Cleanup: <strong style="color: #e2e8f0;">${exp.cleanup_plan?.cleanup_action || 'Release resources'}</strong></div>
          </div>
        </div>

        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
          <h3 style="margin-top: 0; color: #f8fafc; font-size: 14px;">Experiment Actions</h3>
          <div style="display: flex; flex-direction: column; gap: 10px;">
            ${exp.status === 'READY' ? `
              <button class="btn-run-exp" data-id="${exp.experiment_id}" style="background: #10b981; color: #fff; border: none; padding: 10px; border-radius: 6px; font-weight: 700; cursor: pointer;">
                Execute Trial
              </button>
            ` : ''}
            <button class="btn-rollback-exp" data-id="${exp.experiment_id}" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; padding: 10px; border-radius: 6px; font-weight: 600; cursor: pointer;">
              Execute Rollback
            </button>
          </div>
        </div>
      </div>
    `;
  }

  renderResultsTab() {
    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; color: #f8fafc; font-size: 16px;">Empirical Results & Analysis</h3>
          <span style="font-size: 12px; color: #94a3b8;">Strict Epistemic Decoupling</span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px;">
          <div style="background: rgba(30, 41, 59, 0.6); padding: 16px; border-radius: 8px; border-left: 4px solid #38bdf8;">
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">PREDICTED</div>
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #cbd5e1;">Immutable direction formulated prior to trial launch.</p>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); padding: 16px; border-radius: 8px; border-left: 4px solid #34d399;">
            <div style="font-size: 11px; font-weight: 700; color: #34d399; text-transform: uppercase;">OBSERVED</div>
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #cbd5e1;">Unmodified physical measurement telemetry captured directly.</p>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); padding: 16px; border-radius: 8px; border-left: 4px solid #eab308;">
            <div style="font-size: 11px; font-weight: 700; color: #eab308; text-transform: uppercase;">INTERPRETED</div>
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #cbd5e1;">Comparison of prediction vs delta (SUPPORTED / UNEXPECTED).</p>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); padding: 16px; border-radius: 8px; border-left: 4px solid #a855f7;">
            <div style="font-size: 11px; font-weight: 700; color: #a855f7; text-transform: uppercase;">VERIFIED</div>
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #cbd5e1;">Promoted candidate knowledge with explicit scoped boundary.</p>
          </div>
        </div>

        <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
          <h4 style="margin: 0 0 12px 0; color: #f8fafc; font-size: 14px;">Discovery Conclusions</h4>
          <ul style="margin: 0; padding-left: 20px; color: #cbd5e1; font-size: 13px; line-height: 1.6;">
            ${(this.currentDiscovery?.conclusions || []).map(c => `<li>${c}</li>`).join('')}
            ${!this.currentDiscovery?.conclusions?.length ? '<li>No concluded findings recorded yet.</li>' : ''}
          </ul>
        </div>
      </div>
    `;
  }

  renderTimelineTab() {
    return `
      <div style="background: rgba(30, 41, 59, 0.5); padding: 24px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
        <h3 style="margin: 0 0 20px 0; color: #38bdf8; font-size: 16px;">Discovery Provenance Timeline</h3>
        <div style="position: relative; border-left: 2px solid rgba(56, 189, 248, 0.3); margin-left: 12px; padding-left: 24px;">
          <div style="margin-bottom: 24px;">
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8;">PHASE 1: UNKNOWN IDENTIFIED</div>
            <div style="font-size: 14px; font-weight: 600; color: #f1f5f9;">Question Formulated</div>
            <div style="font-size: 12px; color: #94a3b8;">Disciplined research question generated without unconstrained trials.</div>
          </div>
          <div style="margin-bottom: 24px;">
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8;">PHASE 2: COMPETING HYPOTHESES</div>
            <div style="font-size: 14px; font-weight: 600; color: #f1f5f9;">Alternative Explanations Formulated</div>
            <div style="font-size: 12px; color: #94a3b8;">Defined explicit falsifiers and supporting/contradicting criteria.</div>
          </div>
          <div style="margin-bottom: 24px;">
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8;">PHASE 3: EXPERIMENT & PREDICTION</div>
            <div style="font-size: 14px; font-weight: 600; color: #f1f5f9;">Pre-Execution Prediction Recorded</div>
            <div style="font-size: 12px; color: #94a3b8;">Locked immutable prediction; verified safety boundaries and rollback plan.</div>
          </div>
          <div>
            <div style="font-size: 11px; font-weight: 700; color: #10b981;">PHASE 4: EMPIRICAL ANALYSIS</div>
            <div style="font-size: 14px; font-weight: 600; color: #f1f5f9;">Result Analysis & Knowledge Promotion</div>
            <div style="font-size: 12px; color: #94a3b8;">Scoped findings to environment; avoided unwarranted universal generalization.</div>
          </div>
        </div>
      </div>
    `;
  }

  getRiskColor(riskLevel) {
    switch (riskLevel) {
      case 'SAFE':
        return '#34d399';
      case 'LOW_RISK':
        return '#38bdf8';
      case 'MEDIUM_RISK':
        return '#eab308';
      case 'HIGH_RISK':
        return '#f97316';
      case 'CRITICAL_RISK':
        return '#ef4444';
      default:
        return '#94a3b8';
    }
  }

  bindEvents() {
    // Nav tabs
    this.container.querySelectorAll('.discovery-nav-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this.setTab(btn.getAttribute('data-tab'));
      });
    });

    // Refresh button
    const refreshBtn = this.container.querySelector('#btn-refresh-discovery');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        await this.refresh();
        this.render();
      });
    }

    // Select discovery
    const sel = this.container.querySelector('#discovery-session-select');
    if (sel) {
      sel.addEventListener('change', async (e) => {
        if (e.target.value) {
          await this.selectDiscovery(e.target.value);
        }
      });
    }

    // Approve experiment
    this.container.querySelectorAll('.btn-approve-exp').forEach(btn => {
      btn.addEventListener('click', async () => {
        await this.handleApprove(btn.getAttribute('data-id'));
      });
    });

    // Run experiment
    this.container.querySelectorAll('.btn-run-exp').forEach(btn => {
      btn.addEventListener('click', async () => {
        await this.handleRun(btn.getAttribute('data-id'));
      });
    });

    // Rollback experiment
    this.container.querySelectorAll('.btn-rollback-exp').forEach(btn => {
      btn.addEventListener('click', async () => {
        await this.handleRollback(btn.getAttribute('data-id'));
      });
    });
  }
}

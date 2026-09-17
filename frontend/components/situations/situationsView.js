/**
 * Kairo Autonomous Situation Awareness, Signal Fusion & Proactive Response Workspace (Task 60 & Task 99).
 * Real-time telemetry synthesis, multi-dimensional correlation, attention prioritization,
 * empirical world-state verification, and proactive intervention governance.
 */

import { situationsApi } from '../../lib/api/endpoints.js';

export class SituationsView {
  constructor(containerId = 'situations-container') {
    this.containerId = containerId;
    this.activeTab = 'situations'; // 'situations' | 'timeline' | 'signals' | 'evidence' | 'interventions' | 'impact' | 'hypotheses' | 'baselines' | 'attention' | 'audit'
    this.situations = [];
    this.selectedSituation = null;
    this.attentionItems = [];
    this.baselines = [];
    this.stats = {
      total_situations: 0,
      active_situations: 0,
      escalating_situations: 0,
      interventions_active: 0,
      suppressed_situations: 0,
      resolved_situations: 0,
      unknown_situations: 0,
      signals_ingested: 0,
      patterns_detected: 0,
      emergency_stop_active: false,
    };
    this.filterState = 'ALL';
    this.filterSeverity = 'ALL';
    this.searchQuery = '';
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
      const [sitsRes, attRes, baseRes, statsRes] = await Promise.all([
        situationsApi.list().catch(() => []),
        situationsApi.getAttentionFeed().catch(() => []),
        situationsApi.getBaselines().catch(() => []),
        situationsApi.getStats().catch(() => null),
      ]);
      this.situations = Array.isArray(sitsRes) ? sitsRes : [];
      this.attentionItems = Array.isArray(attRes) ? attRes : [];
      this.baselines = Array.isArray(baseRes) ? baseRes : [];
      if (statsRes && typeof statsRes === 'object') {
        this.stats = { ...this.stats, ...statsRes };
      } else {
        this.stats.total_situations = this.situations.length;
        this.stats.active_situations = this.situations.filter(s => (s.lifecycle_state || s.status) === 'ACTIVE').length;
        this.stats.escalating_situations = this.situations.filter(s => (s.lifecycle_state || s.status) === 'ESCALATING').length;
        this.stats.resolved_situations = this.situations.filter(s => (s.lifecycle_state || s.status) === 'RESOLVED').length;
        this.stats.suppressed_situations = this.situations.filter(s => (s.lifecycle_state || s.status) === 'SUPPRESSED').length;
      }
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

  getFilteredSituations() {
    return this.situations.filter((s) => {
      const st = s.lifecycle_state || s.status || 'DETECTED';
      const sev = s.severity || 'MEDIUM';
      const title = (s.title || '').toLowerCase();
      const summary = (s.summary || s.description || '').toLowerCase();

      if (this.filterState !== 'ALL' && st !== this.filterState) return false;
      if (this.filterSeverity !== 'ALL' && sev !== this.filterSeverity) return false;
      if (this.searchQuery && !title.includes(this.searchQuery.toLowerCase()) && !summary.includes(this.searchQuery.toLowerCase())) {
        return false;
      }
      return true;
    });
  }

  async handleSuppress(situationId) {
    const reason = prompt('Enter auditable suppression reason (e.g. Scheduled Maintenance, Known Issue):');
    if (!reason) return;
    try {
      await situationsApi.suppress(situationId, {
        reason,
        duration_seconds: 3600,
        suppressed_by: 'OPERATOR_UI',
      });
      alert('Situation suppressed successfully.');
      await this.loadData();
    } catch (e) {
      alert(`Failed to suppress situation: ${e.message}`);
    }
  }

  async handleReopen(situationId) {
    try {
      await situationsApi.reopen(situationId, {
        reason: 'Reopened from Situations Workspace UI',
        actor: 'OPERATOR_UI',
      });
      alert('Situation reopened successfully.');
      await this.loadData();
    } catch (e) {
      alert(`Failed to reopen situation: ${e.message}`);
    }
  }

  async handleRefresh(situationId) {
    try {
      await situationsApi.refresh(situationId);
      alert('Situation deliberate & reality reconciliation cycle triggered.');
      await this.loadData();
    } catch (e) {
      alert(`Failed to refresh situation: ${e.message}`);
    }
  }

  async handleInvestigate(situationId) {
    try {
      const res = await situationsApi.investigate(situationId, { scope: 'comprehensive' });
      alert(`Swarm Investigation dispatched: ${res.evidence_count || 0} evidence items collected.`);
      await this.loadData();
    } catch (e) {
      alert(`Investigation failed: ${e.message}`);
    }
  }

  render() {
    if (typeof document === 'undefined') return;
    const container = document.getElementById(this.containerId);
    if (!container) return;

    const filtered = this.getFilteredSituations();
    const sel = this.selectedSituation;

    container.innerHTML = `
      <div class="situations-dashboard" style="display: flex; flex-direction: column; gap: 20px; font-family: 'Inter', system-ui, sans-serif; color: #e2e8f0; padding: 24px;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px;">
          <div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <h1 style="margin: 0; font-size: 24px; font-weight: 700; background: linear-gradient(135deg, #f43f5e, #fb923c); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Kairo Autonomous Situation Awareness & Signal Fusion
              </h1>
              <span style="background: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.4); color: #38bdf8; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 9999px;">
                TASK 99
              </span>
              ${this.stats.emergency_stop_active ? `
                <span style="background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #f87171; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">
                  EMERGENCY STOP ACTIVE
                </span>
              ` : ''}
            </div>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">
              Transforming heterogeneous signals into bounded, explainable operational situations with governed proactive response
            </p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="btn-refresh-situations" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500;">
              ↻ Refresh Data
            </button>
          </div>
        </div>

        <!-- Metric Badges / Stats Bar -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px;">
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Active Situations</div>
            <div style="font-size: 22px; font-weight: 700; color: #f43f5e; margin-top: 4px;">${this.stats.active_situations}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Escalating</div>
            <div style="font-size: 22px; font-weight: 700; color: #fb923c; margin-top: 4px;">${this.stats.escalating_situations}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Interventions Active</div>
            <div style="font-size: 22px; font-weight: 700; color: #38bdf8; margin-top: 4px;">${this.stats.interventions_active}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Resolved</div>
            <div style="font-size: 22px; font-weight: 700; color: #34d399; margin-top: 4px;">${this.stats.resolved_situations}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Signals Ingested</div>
            <div style="font-size: 22px; font-weight: 700; color: #a855f7; margin-top: 4px;">${this.stats.signals_ingested || this.situations.reduce((acc, s) => acc + (s.signal_count || 1), 0)}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Core Invariant</div>
            <div style="font-size: 13px; font-weight: 600; color: #e2e8f0; margin-top: 8px;">Execution ≠ Verified State</div>
          </div>
        </div>

        <!-- Operational Filters Bar -->
        <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; background: rgba(15, 23, 42, 0.5); padding: 12px 16px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.06);">
          <input
            type="text"
            id="input-sit-search"
            placeholder="Search by title, subject, entity..."
            value="${this.searchQuery}"
            style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 13px; width: 260px;"
          />
          <select id="select-sit-state" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 13px;">
            <option value="ALL" ${this.filterState === 'ALL' ? 'selected' : ''}>State: All</option>
            <option value="DETECTED" ${this.filterState === 'DETECTED' ? 'selected' : ''}>Detected</option>
            <option value="FORMING" ${this.filterState === 'FORMING' ? 'selected' : ''}>Forming</option>
            <option value="ACTIVE" ${this.filterState === 'ACTIVE' ? 'selected' : ''}>Active</option>
            <option value="ESCALATING" ${this.filterState === 'ESCALATING' ? 'selected' : ''}>Escalating</option>
            <option value="INTERVENTION_ACTIVE" ${this.filterState === 'INTERVENTION_ACTIVE' ? 'selected' : ''}>Intervention Active</option>
            <option value="OBSERVING" ${this.filterState === 'OBSERVING' ? 'selected' : ''}>Observing</option>
            <option value="STABILIZING" ${this.filterState === 'STABILIZING' ? 'selected' : ''}>Stabilizing</option>
            <option value="RESOLVED" ${this.filterState === 'RESOLVED' ? 'selected' : ''}>Resolved</option>
            <option value="SUPPRESSED" ${this.filterState === 'SUPPRESSED' ? 'selected' : ''}>Suppressed</option>
          </select>
          <select id="select-sit-severity" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 6px 12px; border-radius: 6px; font-size: 13px;">
            <option value="ALL" ${this.filterSeverity === 'ALL' ? 'selected' : ''}>Severity: All</option>
            <option value="CRITICAL" ${this.filterSeverity === 'CRITICAL' ? 'selected' : ''}>Critical</option>
            <option value="HIGH" ${this.filterSeverity === 'HIGH' ? 'selected' : ''}>High</option>
            <option value="MEDIUM" ${this.filterSeverity === 'MEDIUM' ? 'selected' : ''}>Medium</option>
            <option value="LOW" ${this.filterSeverity === 'LOW' ? 'selected' : ''}>Low</option>
          </select>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px;">
          ${this.renderTabBtn('situations', 'Inbox & Workspace')}
          ${this.renderTabBtn('timeline', 'Temporal Timeline')}
          ${this.renderTabBtn('signals', 'Normalized Signals')}
          ${this.renderTabBtn('evidence', 'Evidence Graph')}
          ${this.renderTabBtn('interventions', 'Proactive Interventions')}
          ${this.renderTabBtn('impact', 'Blast Radius & Impact')}
          ${this.renderTabBtn('hypotheses', 'Causal Hypotheses')}
          ${this.renderTabBtn('baselines', 'Baselines')}
          ${this.renderTabBtn('attention', 'Attention Feed')}
          ${this.renderTabBtn('audit', 'Audit Log')}
        </div>

        <!-- Tab Content -->
        <div class="situations-tab-content">
          ${this.renderActiveTab(filtered, sel)}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  renderTabBtn(tabKey, label) {
    const isActive = this.activeTab === tabKey;
    const bg = isActive ? 'linear-gradient(135deg, rgba(244, 63, 94, 0.2), rgba(251, 146, 60, 0.2))' : 'transparent';
    const color = isActive ? '#fb923c' : '#94a3b8';
    const border = isActive ? '1px solid rgba(251, 146, 60, 0.4)' : '1px solid transparent';
    return `
      <button class="tab-btn" data-tab="${tabKey}" style="background: ${bg}; color: ${color}; border: ${border}; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s;">
        ${label}
      </button>
    `;
  }

  renderActiveTab(filtered, selected) {
    switch (this.activeTab) {
      case 'situations':
        return this.renderWorkspace(filtered, selected);
      case 'timeline':
        return this.renderTimeline(selected);
      case 'signals':
        return this.renderSignals(selected);
      case 'evidence':
        return this.renderEvidence(selected);
      case 'interventions':
        return this.renderInterventions(selected);
      case 'impact':
        return this.renderImpact(selected);
      case 'hypotheses':
        return this.renderHypotheses(selected);
      case 'baselines':
        return this.renderBaselines();
      case 'attention':
        return this.renderAttentionFeed();
      case 'audit':
        return this.renderAudit();
      default:
        return `<div style="padding: 20px; color: #94a3b8;">Tab content coming soon.</div>`;
    }
  }

  renderWorkspace(situations, selected) {
    return `
      <div style="display: grid; grid-template-columns: 360px 1fr; gap: 20px; min-height: 520px;">
        <!-- Left: Situation Inbox List -->
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; max-height: 650px; overflow-y: auto;">
          <div style="font-size: 13px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">
            Situation Inbox (${situations.length})
          </div>
          ${situations.length === 0 ? `
            <div style="text-align: center; color: #64748b; padding: 40px 10px; font-size: 13px;">
              No situations matching active filter criteria.
            </div>
          ` : situations.map(s => {
            const isSel = selected && (selected.id === s.id || selected.situation_id === s.situation_id);
            const sevColor = this.getSeverityColor(s.severity);
            const stateColor = this.getStateColor(s.lifecycle_state || s.status);
            return `
              <div class="sit-card" data-id="${s.id || s.situation_id}" style="background: ${isSel ? 'rgba(30, 41, 59, 0.9)' : 'rgba(30, 41, 59, 0.4)'}; border: 1px solid ${isSel ? 'rgba(251, 146, 60, 0.5)' : 'rgba(255, 255, 255, 0.06)'}; border-radius: 8px; padding: 12px; cursor: pointer; transition: border-color 0.2s;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                  <span style="background: ${sevColor}22; border: 1px solid ${sevColor}66; color: ${sevColor}; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">
                    ${s.severity || 'MEDIUM'}
                  </span>
                  <span style="background: ${stateColor}22; border: 1px solid ${stateColor}66; color: ${stateColor}; font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px;">
                    ${s.lifecycle_state || s.status || 'DETECTED'}
                  </span>
                </div>
                <div style="font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 4px; line-height: 1.3;">
                  ${s.title}
                </div>
                <div style="font-size: 12px; color: #94a3b8; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 8px;">
                  ${s.summary || s.description || 'No description provided.'}
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b;">
                  <span>Signals: ${s.signal_count || 1}</span>
                  <span>Priority: ${((s.priority || 0.5) * 100).toFixed(0)}%</span>
                  <span>${s.situation_type || 'INCIDENT'}</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>

        <!-- Right: Situation Detail Panel -->
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; overflow-y: auto; max-height: 650px;">
          ${!selected ? `
            <div style="text-align: center; color: #64748b; padding: 80px 20px;">
              Select a situation from the inbox to inspect operational details.
            </div>
          ` : this.renderDetailPanel(selected)}
        </div>
      </div>
    `;
  }

  renderDetailPanel(s) {
    const sevColor = this.getSeverityColor(s.severity);
    const stateColor = this.getStateColor(s.lifecycle_state || s.status);
    const sitId = s.id || s.situation_id;

    return `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <!-- Top Title & Quick Actions -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
              <span style="background: ${sevColor}22; border: 1px solid ${sevColor}66; color: ${sevColor}; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;">
                ${s.severity || 'MEDIUM'}
              </span>
              <span style="background: ${stateColor}22; border: 1px solid ${stateColor}66; color: ${stateColor}; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;">
                ${s.lifecycle_state || s.status || 'DETECTED'}
              </span>
              <span style="font-size: 11px; color: #94a3b8; font-family: monospace;">ID: ${sitId}</span>
            </div>
            <h2 style="margin: 0; font-size: 20px; font-weight: 700; color: #f8fafc;">
              ${s.title}
            </h2>
            <p style="margin: 6px 0 0 0; font-size: 13px; color: #cbd5e1;">
              ${s.summary || s.description}
            </p>
          </div>

          <!-- Actions -->
          <div style="display: flex; gap: 8px;">
            <button class="btn-action-refresh" data-id="${sitId}" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">
              ⚡ Reconcile
            </button>
            <button class="btn-action-investigate" data-id="${sitId}" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(168, 85, 247, 0.4); color: #c084fc; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">
              🔍 Investigate
            </button>
            ${(s.lifecycle_state || s.status) !== 'SUPPRESSED' ? `
              <button class="btn-action-suppress" data-id="${sitId}" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                🔇 Suppress
              </button>
            ` : `
              <button class="btn-action-reopen" data-id="${sitId}" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(52, 211, 153, 0.4); color: #34d399; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                🔄 Reopen
              </button>
            `}
          </div>
        </div>

        <!-- Evaluation Dimensions -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; background: rgba(30, 41, 59, 0.4); padding: 12px; border-radius: 8px;">
          <div>
            <div style="font-size: 11px; color: #94a3b8;">Priority</div>
            <div style="font-size: 16px; font-weight: 700; color: #fb923c;">${((s.priority || 0.5) * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div style="font-size: 11px; color: #94a3b8;">Confidence</div>
            <div style="font-size: 16px; font-weight: 700; color: #38bdf8;">${((s.confidence || 1.0) * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div style="font-size: 11px; color: #94a3b8;">Urgency</div>
            <div style="font-size: 16px; font-weight: 700; color: #f43f5e;">${((s.urgency || 0.5) * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div style="font-size: 11px; color: #94a3b8;">State Reconciliation</div>
            <div style="font-size: 13px; font-weight: 600; color: #34d399; margin-top: 2px;">${s.state_reconciliation_status || 'UNRECONCILED'}</div>
          </div>
        </div>

        <!-- Scope & Lineage -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
          <div style="background: rgba(30, 41, 59, 0.3); padding: 14px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
            <div style="font-size: 12px; font-weight: 600; color: #cbd5e1; margin-bottom: 8px;">Affected Entities & Resources</div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
              ${(s.affected_entities && s.affected_entities.length > 0)
                ? s.affected_entities.map(e => `<span style="background: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.3); color: #38bdf8; font-size: 11px; padding: 2px 8px; border-radius: 4px;">${e}</span>`).join('')
                : (s.affected_resources && s.affected_resources.length > 0)
                  ? s.affected_resources.map(r => `<span style="background: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.3); color: #38bdf8; font-size: 11px; padding: 2px 8px; border-radius: 4px;">${r}</span>`).join('')
                  : '<span style="font-size: 12px; color: #64748b;">No entity dependencies registered.</span>'
              }
            </div>
          </div>

          <div style="background: rgba(30, 41, 59, 0.3); padding: 14px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
            <div style="font-size: 12px; font-weight: 600; color: #cbd5e1; margin-bottom: 8px;">Authoritative Governance Boundary</div>
            <div style="font-size: 12px; color: #94a3b8; display: flex; flex-direction: column; gap: 4px;">
              <div>Decision ID: <span style="font-family: monospace; color: #e2e8f0;">${s.current_decision_id || 'None (deliberation pending)'}</span></div>
              <div>Action Tx ID: <span style="font-family: monospace; color: #e2e8f0;">${s.current_action_transaction_id || 'None (no active execution)'}</span></div>
              <div>Recommended Next: <span style="color: #fb923c;">${s.recommended_next_step || 'Continue monitoring'}</span></div>
            </div>
          </div>
        </div>

        <!-- Recent Timeline Snippet -->
        <div>
          <div style="font-size: 13px; font-weight: 600; color: #cbd5e1; margin-bottom: 10px;">Recent Chronological Events (${(s.timeline || []).length})</div>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${(s.timeline && s.timeline.length > 0) ? s.timeline.slice(-4).map(e => `
              <div style="display: flex; gap: 12px; align-items: baseline; font-size: 12px; padding: 8px 12px; background: rgba(30, 41, 59, 0.3); border-radius: 6px; border-left: 3px solid #38bdf8;">
                <span style="font-family: monospace; color: #64748b;">${new Date(e.timestamp).toLocaleTimeString()}</span>
                <span style="font-weight: 600; color: #38bdf8;">[${e.evidence_type || 'OBSERVED'}]</span>
                <span style="color: #cbd5e1; flex: 1;">${e.summary || e.event_type}</span>
                <span style="color: #64748b; font-size: 11px;">${e.source}</span>
              </div>
            `).join('') : '<div style="font-size: 12px; color: #64748b;">No timeline entries recorded yet.</div>'}
          </div>
        </div>
      </div>
    `;
  }

  renderTimeline(s) {
    if (!s) return `<div style="padding: 20px; color: #94a3b8;">Select a situation to view its timeline.</div>`;
    const timeline = s.timeline || [];
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
          Temporal Evolution & Reality Verification Pipeline (${timeline.length} entries)
        </h3>
        <div style="display: flex; flex-direction: column; gap: 12px; position: relative; padding-left: 20px; border-left: 2px solid rgba(255, 255, 255, 0.1);">
          ${timeline.map(e => {
            const evColor = e.evidence_type === 'OBSERVED' ? '#34d399' : e.evidence_type === 'PREDICTED' ? '#fb923c' : '#38bdf8';
            return `
              <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                  <span style="color: ${evColor}; font-weight: 600;">[${e.evidence_type || 'OBSERVED'}] ${e.event_type || 'SIGNAL'}</span>
                  <span style="color: #64748b; font-family: monospace;">${new Date(e.timestamp).toISOString()}</span>
                </div>
                <div style="font-size: 13px; color: #e2e8f0; margin-bottom: 4px;">${e.summary}</div>
                <div style="font-size: 11px; color: #94a3b8;">Source: ${e.source} | Severity: ${e.severity || 'INFO'}</div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  renderSignals(s) {
    if (!s) return `<div style="padding: 20px; color: #94a3b8;">Select a situation to view correlated signals.</div>`;
    const signals = s.signals || [];
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
          Correlated Canonical Signals (${signals.length} total)
        </h3>
        ${signals.length === 0 ? `
          <div style="color: #64748b; font-size: 13px;">No explicit signals loaded in memory for this situation.</div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 10px;">
            ${signals.map(sig => `
              <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px;">
                  <span style="font-weight: 600; color: #38bdf8;">${sig.signal_type}</span>
                  <span style="color: #94a3b8;">Confidence: ${(sig.confidence * 100).toFixed(0)}%</span>
                </div>
                <div style="font-size: 13px; color: #f8fafc; margin-bottom: 4px;">${sig.subject}</div>
                <div style="font-size: 11px; color: #64748b;">Source: ${sig.source_type} (${sig.source_id}) | Trust: ${sig.trust_classification || 'INTERNAL'}</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderEvidence(s) {
    if (!s) return `<div style="padding: 20px; color: #94a3b8;">Select a situation to inspect evidence.</div>`;
    const evidence = s.evidence || [];
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
            Evidence Graph & Epistemic Trust (${evidence.length} items)
          </h3>
          <div style="display: flex; gap: 6px; font-size: 11px;">
            <span style="color: #34d399;">● Observed</span>
            <span style="color: #38bdf8;">● Correlated</span>
            <span style="color: #fb923c;">● Predicted</span>
            <span style="color: #c084fc;">● Inferred</span>
          </div>
        </div>
        ${evidence.length === 0 ? `
          <div style="color: #64748b; font-size: 13px;">No explicit evidence graph nodes recorded.</div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 10px;">
            ${evidence.map((ev, i) => `
              <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px;">
                <div style="font-size: 12px; font-weight: 600; color: #38bdf8; margin-bottom: 4px;">
                  #${i + 1} [${ev.type || 'OBSERVED'}] ${ev.source || 'telemetry'}
                </div>
                <div style="font-size: 13px; color: #e2e8f0;">${ev.detail || ev.finding || JSON.stringify(ev)}</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderInterventions(s) {
    if (!s) return `<div style="padding: 20px; color: #94a3b8;">Select a situation to view proactive interventions.</div>`;
    const interventions = s.interventions || [];
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
          Proactive Interventions & Action Governance (${interventions.length} records)
        </h3>
        <p style="font-size: 12px; color: #94a3b8; margin: 0 0 16px 0;">
          All autonomous actions require explicit ActionTransaction boundaries. Execution success does NOT equal verified reality.
        </p>
        ${interventions.length === 0 ? `
          <div style="color: #64748b; font-size: 13px;">No proactive interventions initiated for this situation.</div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 12px;">
            ${interventions.map(iv => `
              <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 14px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px;">
                  <span style="font-weight: 600; color: #fb923c;">${iv.proposed_action || 'Remediation Action'}</span>
                  <span style="background: rgba(14, 165, 233, 0.2); color: #38bdf8; padding: 2px 6px; border-radius: 4px;">
                    ${iv.execution_state || 'PROPOSED'}
                  </span>
                </div>
                <div style="font-size: 12px; color: #94a3b8;">Transaction: <span style="font-family: monospace; color: #f8fafc;">${iv.action_transaction_id || 'N/A'}</span></div>
                <div style="font-size: 12px; color: #94a3b8;">Approval: <span style="color: #34d399;">${iv.approval_status || 'NOT_REQUIRED'}</span></div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderImpact(s) {
    if (!s) return `<div style="padding: 20px; color: #94a3b8;">Select a situation to view blast radius.</div>`;
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
          Blast Radius & Propagation Mapping
        </h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
          <div style="background: rgba(30, 41, 59, 0.3); padding: 14px; border-radius: 8px;">
            <div style="font-size: 12px; font-weight: 600; color: #cbd5e1; margin-bottom: 8px;">Affected Services</div>
            <div style="font-size: 13px; color: #94a3b8;">${(s.affected_services || []).join(', ') || 'None directly isolated'}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.3); padding: 14px; border-radius: 8px;">
            <div style="font-size: 12px; font-weight: 600; color: #cbd5e1; margin-bottom: 8px;">Threatened Goals</div>
            <div style="font-size: 13px; color: #94a3b8;">${(s.affected_goals || []).join(', ') || 'No strategic goals blocked'}</div>
          </div>
        </div>
      </div>
    `;
  }

  renderHypotheses(s) {
    if (!s) return `<div style="padding: 20px; color: #94a3b8;">Select a situation to view causal hypotheses.</div>`;
    const hypotheses = s.hypotheses || [];
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
          Ranked Causal Explanations (${hypotheses.length})
        </h3>
        ${hypotheses.length === 0 ? `
          <div style="color: #64748b; font-size: 13px;">No candidate hypotheses formulated.</div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 10px;">
            ${hypotheses.map(h => `
              <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px;">
                <div style="font-size: 14px; font-weight: 600; color: #fb923c; margin-bottom: 4px;">${h.candidate_cause}</div>
                <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 6px;">${h.evidence_summary}</div>
                <div style="font-size: 11px; color: #94a3b8;">Confidence: ${h.confidence_level}</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderBaselines() {
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
          Monitored Signal Baselines (${this.baselines.length})
        </h3>
        ${this.baselines.length === 0 ? `
          <div style="color: #64748b; font-size: 13px;">No statistical baselines registered.</div>
        ` : `
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px;">
            ${this.baselines.map(b => `
              <div style="background: rgba(30, 41, 59, 0.4); padding: 12px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.06);">
                <div style="font-size: 13px; font-weight: 600; color: #38bdf8;">${b.signal_name}</div>
                <div style="font-size: 11px; color: #94a3b8;">Resource: ${b.resource}</div>
                <div style="font-size: 12px; color: #cbd5e1; margin-top: 4px;">Mean: ${b.mean_val} (±${b.std_dev})</div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderAttentionFeed() {
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
          Attention Engine Feed (${this.attentionItems.length})
        </h3>
        ${this.attentionItems.length === 0 ? `
          <div style="color: #64748b; font-size: 13px;">No attention priority items active.</div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 10px;">
            ${this.attentionItems.map(item => `
              <div style="background: rgba(30, 41, 59, 0.4); padding: 12px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.06); display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-size: 14px; font-weight: 600; color: #f8fafc;">${item.title}</div>
                  <div style="font-size: 12px; color: #94a3b8;">${item.reason || 'Calculated by Attention Engine'}</div>
                </div>
                <div style="font-size: 18px; font-weight: 700; color: #fb923c;">
                  ${((item.composite_priority || 0.5) * 100).toFixed(0)}%
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderAudit() {
    return `
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: #f8fafc;">
          Immutable Situational Audit Trail
        </h3>
        <p style="font-size: 12px; color: #94a3b8;">Cryptographically chained audit events documenting all detections, transitions, interventions, and suppressions.</p>
      </div>
    `;
  }

  getSeverityColor(sev) {
    switch (sev) {
      case 'CRITICAL': return '#ef4444';
      case 'HIGH': return '#f43f5e';
      case 'MEDIUM': return '#fb923c';
      case 'LOW': return '#38bdf8';
      default: return '#94a3b8';
    }
  }

  getStateColor(st) {
    switch (st) {
      case 'ACTIVE': return '#f43f5e';
      case 'ESCALATING': return '#fb923c';
      case 'INTERVENTION_ACTIVE': return '#38bdf8';
      case 'RESOLVED': return '#34d399';
      case 'SUPPRESSED': return '#64748b';
      default: return '#a855f7';
    }
  }

  attachEventListeners() {
    const container = document.getElementById(this.containerId);
    if (!container) return;

    // Tab buttons
    container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    // Situation card selection
    container.querySelectorAll('.sit-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        const sit = this.situations.find(s => (s.id === id || s.situation_id === id));
        if (sit) this.selectSituation(sit);
      });
    });

    // Refresh data button
    const btnRefresh = container.querySelector('#btn-refresh-situations');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => this.loadData());
    }

    // Filter selects & search input
    const selectState = container.querySelector('#select-sit-state');
    if (selectState) {
      selectState.addEventListener('change', (e) => {
        this.filterState = e.target.value;
        this.render();
      });
    }

    const selectSev = container.querySelector('#select-sit-severity');
    if (selectSev) {
      selectSev.addEventListener('change', (e) => {
        this.filterSeverity = e.target.value;
        this.render();
      });
    }

    const inputSearch = container.querySelector('#input-sit-search');
    if (inputSearch) {
      inputSearch.addEventListener('input', (e) => {
        this.searchQuery = e.target.value;
        this.render();
      });
    }

    // Detail Action Buttons
    container.querySelectorAll('.btn-action-refresh').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) this.handleRefresh(id);
      });
    });

    container.querySelectorAll('.btn-action-investigate').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) this.handleInvestigate(id);
      });
    });

    container.querySelectorAll('.btn-action-suppress').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) this.handleSuppress(id);
      });
    });

    container.querySelectorAll('.btn-action-reopen').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) this.handleReopen(id);
      });
    });
  }

  renderLoading(isLoading) {
    // Optional indicator
  }
}

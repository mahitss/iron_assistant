/**
 * Kairo Incident Response & Recovery Autonomy Engine View (Task 61).
 * Glassmorphic command dashboard for operational incidents, triage, diagnostics, recovery checkpoints, and postmortems.
 */

import { incidentsApi } from '../../lib/api/endpoints.js';

export class IncidentsView {
  constructor(containerId = 'incidents-container') {
    this.containerId = containerId;
    this.activeTab = 'incidents'; // 'incidents' | 'investigation' | 'hypotheses' | 'options' | 'recovery' | 'postmortem' | 'audit'
    this.incidents = [];
    this.selectedIncident = null;
    this.auditEvents = [];
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
      const [incRes, auditRes] = await Promise.all([
        incidentsApi.list().catch(() => []),
        incidentsApi.getAudit().catch(() => []),
      ]);
      this.incidents = Array.isArray(incRes) ? incRes : [];
      this.auditEvents = Array.isArray(auditRes) ? auditRes : [];
      if (this.incidents.length > 0 && !this.selectedIncident) {
        this.selectedIncident = this.incidents[0];
      }
    } catch (err) {
      console.error('Failed to load incidents data:', err);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  setTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  selectIncident(incident) {
    this.selectedIncident = incident;
    this.render();
  }

  render() {
    if (typeof document === 'undefined') return;
    const container = document.getElementById(this.containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="incidents-dashboard" style="display: flex; flex-direction: column; gap: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f1f5f9;">
        <!-- Header Banner -->
        <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px 24px; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h2 style="margin: 0; font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #f43f5e, #fb923c, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Incident Response & Recovery Autonomy
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8;">
              Operational Triage, Diagnostic Investigation, Gated Mitigations & Verified Recovery Checkpoints
            </p>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button id="inc-refresh-btn" style="background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255,255,255,0.15); color: #e2e8f0; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 500;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Invariant Notice Banner -->
        <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 8px; padding: 10px 16px; font-size: 12px; color: #fda4af; display: flex; align-items: center; gap: 10px;">
          <span>🛡️ <strong>Safety Invariant</strong>: Diagnostics & Mitigations coordinate via Policy/Auth/Approval gates. <em>Silence $\ne$ Recovery; closure strictly requires verification evidence.</em></span>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
          ${this._renderTabButton('incidents', '🚨 Incidents Feed', this.incidents.length)}
          ${this._renderTabButton('investigation', '🔍 Investigation Plan')}
          ${this._renderTabButton('hypotheses', '🧬 Hypotheses & Evidence')}
          ${this._renderTabButton('options', '⚡ Response Options')}
          ${this._renderTabButton('recovery', '🔄 Recovery Stepper')}
          ${this._renderTabButton('postmortem', '📝 Postmortem')}
          ${this._renderTabButton('audit', '📜 Audit Trail', this.auditEvents.length)}
        </div>

        <!-- Main Tab Content Area -->
        <div style="min-height: 420px;">
          ${this._renderTabContent()}
        </div>
      </div>
    `;

    this._bindEvents(container);
  }

  _renderTabButton(tabKey, label, count = null) {
    const isActive = this.activeTab === tabKey;
    const activeStyle = isActive
      ? 'background: rgba(56, 189, 248, 0.2); border: 1px solid rgba(56, 189, 248, 0.5); color: #38bdf8;'
      : 'background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.05); color: #94a3b8;';
    const badge = count !== null ? `<span style="margin-left: 6px; padding: 2px 6px; background: rgba(255,255,255,0.1); border-radius: 10px; font-size: 11px;">${count}</span>` : '';

    return `
      <button class="inc-tab-btn" data-tab="${tabKey}" style="${activeStyle} padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s ease;">
        ${label}${badge}
      </button>
    `;
  }

  _renderTabContent() {
    if (this.isLoading) {
      return `<div style="padding: 40px; text-align: center; color: #94a3b8;">Loading incident response state...</div>`;
    }

    switch (this.activeTab) {
      case 'incidents':
        return this._renderIncidentsFeed();
      case 'investigation':
        return this._renderInvestigationTab();
      case 'hypotheses':
        return this._renderHypothesesTab();
      case 'options':
        return this._renderOptionsTab();
      case 'recovery':
        return this._renderRecoveryTab();
      case 'postmortem':
        return this._renderPostmortemTab();
      case 'audit':
        return this._renderAuditTab();
      default:
        return `<div style="padding: 20px; color: #94a3b8;">Select a tab to view operational details.</div>`;
    }
  }

  _renderIncidentsFeed() {
    if (this.incidents.length === 0) {
      return `
        <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 40px; text-align: center; color: #94a3b8;">
          <p style="font-size: 16px; margin: 0;">No active incidents recorded.</p>
          <p style="font-size: 13px; margin: 8px 0 0 0; color: #64748b;">Systems are operating within nominal baseline envelopes.</p>
        </div>
      `;
    }

    return `
      <div style="display: grid; grid-template-columns: 1fr 1.6fr; gap: 20px;">
        <!-- Left: Incident List -->
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${this.incidents.map((inc) => this._renderIncidentCard(inc)).join('')}
        </div>

        <!-- Right: Incident Detail View -->
        <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px;">
          ${this.selectedIncident ? this._renderSelectedIncidentDetail(this.selectedIncident) : '<div style="color:#64748b;">Select an incident on the left to view response telemetry.</div>'}
        </div>
      </div>
    `;
  }

  _renderIncidentCard(inc) {
    const isSelected = this.selectedIncident && this.selectedIncident.incident_id === inc.incident_id;
    const border = isSelected ? 'border: 1px solid #38bdf8;' : 'border: 1px solid rgba(255,255,255,0.08);';
    const bg = isSelected ? 'background: rgba(30, 41, 59, 0.85);' : 'background: rgba(15, 23, 42, 0.6);';

    return `
      <div class="inc-card" data-id="${inc.incident_id}" style="${bg} ${border} backdrop-filter: blur(12px); border-radius: 10px; padding: 16px; cursor: pointer; transition: transform 0.15s ease;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
          <span style="font-size: 14px; font-weight: 600; color: #f8fafc;">${inc.title}</span>
          ${this._renderSeverityPill(inc.severity)}
        </div>
        <div style="display: flex; gap: 8px; font-size: 12px; color: #94a3b8; margin-bottom: 8px;">
          <span>Status: <strong>${inc.status}</strong></span>
          <span>•</span>
          <span>Urgency: <strong>${inc.urgency}</strong></span>
          <span>•</span>
          <span>Env: <strong>${inc.environment}</strong></span>
        </div>
        <div style="font-size: 11px; color: #64748b;">
          Resources: ${(inc.affected_resources || []).join(', ') || 'N/A'}
        </div>
      </div>
    `;
  }

  _renderSelectedIncidentDetail(inc) {
    return `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 14px; margin-bottom: 16px;">
          <div>
            <h3 style="margin: 0; font-size: 18px; color: #f8fafc;">${inc.title}</h3>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #94a3b8;">ID: ${inc.incident_id} • Situation: ${inc.situation_id || 'Direct'}</p>
          </div>
          <div style="display: flex; gap: 8px;">
            ${this._renderSeverityPill(inc.severity)}
            <span style="padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; background: rgba(56, 189, 248, 0.15); color: #38bdf8;">${inc.status}</span>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
          <div style="background: rgba(0,0,0,0.25); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
            <div style="font-size: 11px; color: #94a3b8;">Urgency</div>
            <div style="font-size: 14px; font-weight: 600; color: #f1f5f9;">${inc.urgency}</div>
          </div>
          <div style="background: rgba(0,0,0,0.25); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
            <div style="font-size: 11px; color: #94a3b8;">Automation Level</div>
            <div style="font-size: 14px; font-weight: 600; color: #f1f5f9;">${inc.automation_level}</div>
          </div>
          <div style="background: rgba(0,0,0,0.25); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
            <div style="font-size: 11px; color: #94a3b8;">Incident Commander</div>
            <div style="font-size: 14px; font-weight: 600; color: #f1f5f9;">${inc.incident_commander || 'Unassigned'}</div>
          </div>
        </div>

        <div style="margin-bottom: 16px;">
          <div style="font-size: 13px; font-weight: 600; color: #e2e8f0; margin-bottom: 6px;">Affected Scope</div>
          <div style="font-size: 12px; color: #94a3b8; display: flex; flex-direction: column; gap: 4px;">
            <div>• Services: ${(inc.affected_services || []).join(', ') || 'None reported'}</div>
            <div>• Resources: ${(inc.affected_resources || []).join(', ') || 'None reported'}</div>
            <div>• Strategic Plans: ${(inc.affected_plans || []).join(', ') || 'None impacted'}</div>
            <div>• Goals Threatened: ${(inc.affected_goals || []).join(', ') || 'None threatened'}</div>
          </div>
        </div>

        <div>
          <div style="font-size: 13px; font-weight: 600; color: #e2e8f0; margin-bottom: 6px;">Recent Incident Timeline</div>
          <div style="max-height: 160px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px;">
            ${(inc.timeline || []).slice(-4).map((t) => `
              <div style="background: rgba(0,0,0,0.2); padding: 8px 10px; border-radius: 6px; font-size: 12px; display: flex; justify-content: space-between;">
                <span style="color: #cbd5e1;">${t.summary || t.event}</span>
                <span style="color: #64748b; font-family: monospace; font-size: 11px;">${new Date(t.timestamp).toLocaleTimeString()}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  _renderInvestigationTab() {
    if (!this.selectedIncident || !this.selectedIncident.investigation) {
      return `<div style="padding: 20px; color: #94a3b8;">Select an incident with an active investigation plan.</div>`;
    }
    const inv = this.selectedIncident.investigation;

    return `
      <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 24px;">
        <h3 style="margin: 0 0 12px 0; font-size: 17px; color: #f8fafc;">Diagnostic Tasks (Prioritized by Value of Information)</h3>
        <p style="margin: 0 0 16px 0; font-size: 12px; color: #94a3b8;">
          Diagnostics are strictly safe, read-only inspections designed to confirm or refute competing hypotheses without modifying production.
        </p>

        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${(inv.tasks || []).map((t, idx) => `
            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px; display: flex; justify-content: space-between; align-items: center;">
              <div>
                <div style="display: flex; gap: 8px; align-items: center;">
                  <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-weight: 700; font-size: 11px; padding: 2px 6px; border-radius: 4px;">#${idx + 1}</span>
                  <span style="font-weight: 600; font-size: 14px; color: #f1f5f9;">${t.name}</span>
                  ${t.is_read_only ? '<span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; font-size: 11px; padding: 2px 6px; border-radius: 4px;">READ ONLY</span>' : ''}
                </div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">${t.purpose}</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Target: <code>${t.target_resource}</code></div>
              </div>
              <div style="text-align: right;">
                <div style="font-size: 11px; color: #94a3b8;">VOI Score</div>
                <div style="font-size: 15px; font-weight: 700; color: #38bdf8;">${(t.voi_score * 100).toFixed(0)}%</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderHypothesesTab() {
    if (!this.selectedIncident || !this.selectedIncident.hypotheses) {
      return `<div style="padding: 20px; color: #94a3b8;">Select an incident to view candidate causal hypotheses.</div>`;
    }

    return `
      <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 24px;">
        <h3 style="margin: 0 0 8px 0; font-size: 17px; color: #f8fafc;">Candidate Causal Hypotheses & Evidence Graph</h3>
        <p style="margin: 0 0 16px 0; font-size: 12px; color: #94a3b8;">
          Evidence conflicts are explicitly maintained. Root cause is never forced: <code>ROOT_CAUSE_UNKNOWN</code> is valid when telemetry is inconclusive.
        </p>

        <div style="display: flex; flex-direction: column; gap: 14px;">
          ${this.selectedIncident.hypotheses.map((h) => `
            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <div style="font-size: 15px; font-weight: 600; color: #f8fafc;">${h.candidate_cause}</div>
                <span style="background: rgba(148, 163, 184, 0.2); color: #e2e8f0; font-size: 12px; font-weight: 600; padding: 3px 8px; border-radius: 4px;">
                  ${h.status} (${(h.confidence * 100).toFixed(0)}% Conf)
                </span>
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 12px; margin-top: 10px;">
                <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 6px; padding: 8px;">
                  <div style="color: #4ade80; font-weight: 600; margin-bottom: 4px;">Supporting Evidence (${(h.evidence_supporting || []).length})</div>
                  <div style="color: #cbd5e1; font-size: 11px;">${(h.evidence_supporting || []).map((e) => `• ${e.source}: ${e.trust_level}`).join('<br>') || 'No supporting evidence yet'}</div>
                </div>
                <div style="background: rgba(244, 63, 94, 0.08); border: 1px solid rgba(244, 63, 94, 0.2); border-radius: 6px; padding: 8px;">
                  <div style="color: #fb7185; font-weight: 600; margin-bottom: 4px;">Contradictory Evidence (${(h.evidence_contradictory || []).length})</div>
                  <div style="color: #cbd5e1; font-size: 11px;">${(h.evidence_contradictory || []).map((e) => `• ${e.source}: ${e.trust_level}`).join('<br>') || 'No contradictory evidence recorded'}</div>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderOptionsTab() {
    if (!this.selectedIncident || !this.selectedIncident.response_options) {
      return `<div style="padding: 20px; color: #94a3b8;">Select an incident to view evaluated response options.</div>`;
    }

    return `
      <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 24px;">
        <h3 style="margin: 0 0 8px 0; font-size: 17px; color: #f8fafc;">Response Strategies & Capability Validation</h3>
        <p style="margin: 0 0 16px 0; font-size: 12px; color: #94a3b8;">
          All options are ranked by benefit, reversibility, and estimated risk. Gated by Decision Engine and human approval.
        </p>

        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${this.selectedIncident.response_options.map((opt) => `
            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 16px; display: flex; justify-content: space-between; align-items: center;">
              <div>
                <div style="display: flex; gap: 8px; align-items: center;">
                  <span style="font-weight: 600; font-size: 14px; color: #f8fafc;">${opt.title}</span>
                  ${opt.is_capability_available ? '<span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; font-size: 10px; padding: 2px 6px; border-radius: 4px;">CAPABLE</span>' : '<span style="background: rgba(244, 63, 94, 0.15); color: #fb7185; font-size: 10px; padding: 2px 6px; border-radius: 4px;">UNAVAILABLE</span>'}
                  ${opt.is_reversible ? '<span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 10px; padding: 2px 6px; border-radius: 4px;">REVERSIBLE</span>' : '<span style="background: rgba(245, 158, 11, 0.15); color: #f59e0b; font-size: 10px; padding: 2px 6px; border-radius: 4px;">IRREVERSIBLE</span>'}
                </div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">${opt.description}</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Expected Benefit: ${opt.expected_benefit} • Risk: ${opt.estimated_risk}</div>
              </div>
              <div>
                <button class="inc-select-opt-btn" data-opt="${opt.option_id}" ${!opt.is_capability_available ? 'disabled' : ''} style="background: rgba(56, 189, 248, 0.2); border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                  Select Strategy
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderRecoveryTab() {
    if (!this.selectedIncident || !this.selectedIncident.recovery_plan) {
      return `
        <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 30px; text-align: center; color: #94a3b8;">
          No active recovery plan initiated for this incident yet. Select a strategy from Response Options to generate a phased recovery plan.
        </div>
      `;
    }
    const rec = this.selectedIncident.recovery_plan;

    return `
      <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; font-size: 17px; color: #f8fafc;">Phased Recovery Stepper (${rec.strategy.toUpperCase()})</h3>
          <span style="font-size: 12px; padding: 4px 8px; border-radius: 6px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-weight: 600;">
            Status: ${rec.status}
          </span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${(rec.steps || []).map((s, idx) => {
            const chk = rec.checkpoints.find((c) => c.step_id === s.step_id);
            const isPassed = chk && chk.is_passed;
            return `
              <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <div style="font-weight: 600; font-size: 14px; color: #f1f5f9;">Step ${idx + 1}: ${s.title}</div>
                  <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; ${isPassed ? 'background:rgba(34,197,94,0.2);color:#4ade80;' : 'background:rgba(245,158,11,0.2);color:#f59e0b;'}">
                    ${isPassed ? 'VERIFIED' : 'AWAITING VERIFICATION'}
                  </span>
                </div>
                ${chk ? `<div style="font-size: 12px; color: #94a3b8; margin-top: 6px;">Barrier Criteria: ${chk.verification_criteria}</div>` : ''}
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  _renderPostmortemTab() {
    if (!this.selectedIncident || !this.selectedIncident.postmortem) {
      return `
        <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 30px; text-align: center; color: #94a3b8;">
          Postmortem report is generated upon verified incident resolution.
        </div>
      `;
    }
    const pm = this.selectedIncident.postmortem;

    return `
      <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 24px;">
        <h3 style="margin: 0 0 12px 0; font-size: 18px; color: #f8fafc;">Blameless Post-Incident Review</h3>
        <div style="background: rgba(0,0,0,0.25); padding: 12px; border-radius: 8px; font-size: 13px; color: #cbd5e1; margin-bottom: 16px;">
          ${pm.summary}
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
          <div style="background: rgba(30, 41, 59, 0.5); padding: 12px; border-radius: 8px;">
            <div style="font-size: 13px; font-weight: 600; color: #4ade80; margin-bottom: 6px;">What Worked Well</div>
            <div style="font-size: 12px; color: #94a3b8;">${(pm.what_worked || []).map((w) => `• ${w}`).join('<br>')}</div>
          </div>
          <div style="background: rgba(30, 41, 59, 0.5); padding: 12px; border-radius: 8px;">
            <div style="font-size: 13px; font-weight: 600; color: #fb7185; margin-bottom: 6px;">What Failed / Caused Friction</div>
            <div style="font-size: 12px; color: #94a3b8;">${(pm.what_failed || []).map((f) => `• ${f}`).join('<br>') || 'None reported'}</div>
          </div>
        </div>

        <div>
          <div style="font-size: 13px; font-weight: 600; color: #e2e8f0; margin-bottom: 6px;">Proposed Strategic Planning Action Items</div>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${(pm.action_items || []).map((ai) => `
              <div style="background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px; font-size: 12px; display: flex; justify-content: space-between;">
                <span>${ai.title}</span>
                <span style="color: #38bdf8; font-weight: 600;">${ai.priority}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  _renderAuditTab() {
    return `
      <div style="background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px;">
        <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #f8fafc;">Tamper-Evident SHA-256 Audit Trail</h3>
        <div style="max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
          ${this.auditEvents.map((a) => `
            <div style="background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; padding: 10px; font-size: 12px;">
              <div style="display: flex; justify-content: space-between; color: #e2e8f0; font-weight: 600;">
                <span>[Seq #${a.sequence_number}] ${a.event_type} by ${a.actor}</span>
                <span style="color: #64748b; font-family: monospace;">${new Date(a.timestamp).toLocaleTimeString()}</span>
              </div>
              <div style="font-family: monospace; font-size: 10px; color: #38bdf8; margin-top: 4px;">
                Hash: ${a.entry_hash || a.hash || 'N/A'} (prev: ${(a.previous_hash || '').slice(0, 16)}...)
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderSeverityPill(severity) {
    const s = String(severity || 'MEDIUM').toUpperCase();
    const map = {
      CRITICAL: 'background: rgba(244, 63, 94, 0.2); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.4);',
      HIGH: 'background: rgba(249, 115, 22, 0.2); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.4);',
      MEDIUM: 'background: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.4);',
      LOW: 'background: rgba(34, 197, 94, 0.2); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.4);',
      INFO: 'background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4);',
    };
    const style = map[s] || map.MEDIUM;
    return `<span style="${style} padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: uppercase;">${s}</span>`;
  }

  _bindEvents(container) {
    container.querySelectorAll('.inc-tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        this.setTab(btn.getAttribute('data-tab'));
      });
    });

    container.querySelectorAll('.inc-card').forEach((card) => {
      card.addEventListener('click', () => {
        const id = card.getAttribute('data-id');
        const match = this.incidents.find((i) => i.incident_id === id);
        if (match) this.selectIncident(match);
      });
    });

    const refreshBtn = container.querySelector('#inc-refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }
  }

  renderLoading(isLoading) {
    // Optional helper
  }
}

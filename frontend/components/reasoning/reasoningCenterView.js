/**
 * ReasoningCenterView Component (Task 71)
 * Authoritative user interface for Kairo Autonomous Reasoning & Deliberation Engine.
 *
 * Implements:
 * - ACTIVE REASONING: current question, current phase, progress, and resource usage
 * - HYPOTHESES: candidate hypotheses, supporting/contradicting evidence, confidence, falsifiers
 * - EVIDENCE: empirical evidence items, source trust, reliability, relevance, and conflict alerts
 * - ASSUMPTIONS: tracked assumptions, status, dependent conclusions, and invalidation triggers
 * - ALTERNATIVES: comparative tradeoffs (risk, cost, reversibility, expected impact)
 * - CONCLUSION: synthesized conclusion, confidence, verification state, and uncertainty
 * - WHY? (Safe Explanation): concise rationale, counterarguments addressed, and assumptions made (STRICTLY NO PRIVATE CHAIN-OF-THOUGHT)
 */

import { reasoningApi } from '../../lib/api/endpoints.js';

export class ReasoningCenterView {
  constructor(options = {}) {
    this.container = options.container || null;
    this.activeTab = 'active';
    this.tenantId = options.tenantId || 'default';
    this.workspaceId = options.workspaceId || 'default';

    // State
    this.sessions = [];
    this.currentSession = null;
    this.health = null;
    this.explanation = null;
    this.quality = null;
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
      this.health = await reasoningApi.getHealth();
      this.sessions = await reasoningApi.listSessions(50, this.tenantId, this.workspaceId) || [];

      if (this.sessions.length > 0 && !this.currentSession) {
        await this.selectSession(this.sessions[0].reasoning_id);
      } else if (this.currentSession) {
        await this.selectSession(this.currentSession.reasoning_id);
      }
    } catch (err) {
      console.warn('ReasoningCenterView: Refresh encounter:', err);
      this.error = err.message || 'Failed to refresh reasoning data';
    } finally {
      this.loading = false;
    }
  }

  setTab(tabName) {
    this.activeTab = tabName;
    this.render();
  }

  async selectSession(reasoningId) {
    try {
      this.currentSession = await reasoningApi.getSession(reasoningId, this.tenantId);
      if (this.currentSession) {
        try {
          this.explanation = await reasoningApi.getExplanation(reasoningId, this.tenantId);
        } catch {
          this.explanation = this.currentSession.explanation || null;
        }
        try {
          this.quality = await reasoningApi.getQuality(reasoningId, this.tenantId);
        } catch {
          this.quality = null;
        }
      }
      this.render();
    } catch (err) {
      console.error('Failed to load reasoning session:', err);
      this.error = `Failed to load session ${reasoningId}`;
      this.render();
    }
  }

  async startReasoning(question, depth = 'STANDARD', riskLevel = 'MEDIUM') {
    if (!question || !question.trim()) return;
    this.loading = true;
    this.render();
    try {
      const newSession = await reasoningApi.start(
        {
          question: question.trim(),
          depth,
          risk_level: riskLevel,
        },
        this.tenantId,
        this.workspaceId
      );
      await this.refresh();
      if (newSession && newSession.reasoning_id) {
        await this.selectSession(newSession.reasoning_id);
      }
    } catch (err) {
      console.error('Start reasoning failed:', err);
      this.error = err.message || 'Failed to start deliberation';
      this.loading = false;
      this.render();
    }
  }

  async invalidateAssumption(assumptionId, reason) {
    if (!this.currentSession || !reason) return;
    try {
      await reasoningApi.invalidateAssumption(
        this.currentSession.reasoning_id,
        assumptionId,
        reason,
        this.tenantId
      );
      await this.selectSession(this.currentSession.reasoning_id);
    } catch (err) {
      console.error('Invalidate assumption failed:', err);
      alert(`Failed to invalidate assumption: ${err.message}`);
    }
  }

  async verifyConclusion() {
    if (!this.currentSession) return;
    try {
      await reasoningApi.verify(this.currentSession.reasoning_id, this.tenantId);
      await this.selectSession(this.currentSession.reasoning_id);
    } catch (err) {
      console.error('Verification failed:', err);
      alert(`Verification failed: ${err.message}`);
    }
  }

  render() {
    if (!this.container) return;

    const s = this.currentSession;
    const health = this.health || {};

    this.container.innerHTML = `
      <div class="reasoning-center-container" id="reasoning-center-view" style="display: flex; flex-direction: column; gap: 16px; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f1f5f9;">
        <!-- Header & Telemetry Bar -->
        <div style="display: flex; justify-content: space-between; align-items: center; background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
          <div>
            <h2 style="margin: 0 0 4px 0; font-size: 20px; color: #38bdf8; display: flex; align-items: center; gap: 8px;">
              <span>🧠</span> Kairo Autonomous Reasoning & Deliberation Engine
            </h2>
            <p style="margin: 0; font-size: 13px; color: #94a3b8;">
              Structured inquiry, competing hypotheses, falsification tests, and assumption-invalidation cascades. Zero private chain-of-thought exposure.
            </p>
          </div>
          <div style="display: flex; gap: 16px; font-size: 12px; background: #1e293b; padding: 8px 12px; border-radius: 6px;">
            <div>Completed: <strong style="color: #4ade80;">${health.completed_count || 0}</strong></div>
            <div>Active: <strong style="color: #38bdf8;">${health.active_reasoning_count || 0}</strong></div>
            <div>Contradictions: <strong style="color: #f87171;">${health.contradictions_detected || 0}</strong></div>
            <div>Avg Latency: <strong>${health.average_reasoning_latency_sec || 0}s</strong></div>
          </div>
        </div>

        <!-- Session Selector & New Query Bar -->
        <div style="display: flex; gap: 12px; align-items: center; background: #1e293b; padding: 12px 16px; border-radius: 8px;">
          <label style="font-size: 13px; color: #94a3b8;">Deliberation Session:</label>
          <select id="reasoning-session-select" style="background: #0f172a; color: #f8fafc; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; font-size: 13px; flex: 1;">
            ${
              this.sessions.length === 0
                ? '<option value="">No active sessions</option>'
                : this.sessions
                    .map(
                      (item) =>
                        `<option value="${item.reasoning_id}" ${s && s.reasoning_id === item.reasoning_id ? 'selected' : ''}>
                          [${item.depth}] ${item.question.slice(0, 70)}... (${item.current_state})
                        </option>`
                    )
                    .join('')
            }
          </select>

          <button id="btn-refresh-reasoning" style="background: #334155; color: #f8fafc; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 13px;">
            🔄 Refresh
          </button>
        </div>

        <!-- Initiate Deliberation Box -->
        <div style="background: #1e293b; padding: 12px 16px; border-radius: 8px; display: flex; gap: 8px;">
          <input type="text" id="reasoning-query-input" placeholder="Submit a complex question or objective for structured deliberation..." style="flex: 1; background: #0f172a; color: #fff; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; font-size: 13px;" />
          <select id="reasoning-depth-select" style="background: #0f172a; color: #fff; border: 1px solid #334155; padding: 6px 10px; border-radius: 6px; font-size: 12px;">
            <option value="STANDARD">STANDARD</option>
            <option value="QUICK">QUICK</option>
            <option value="DEEP">DEEP</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
          <button id="btn-start-reasoning" style="background: #0284c7; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600;">
            🚀 Deliberate
          </button>
        </div>

        <!-- Tabs Navigation -->
        <div style="display: flex; border-bottom: 1px solid #334155; gap: 8px;">
          ${this._renderTabBtn('active', 'Active Reasoning', '🎯')}
          ${this._renderTabBtn('hypotheses', `Hypotheses (${s ? s.hypotheses.length : 0})`, '🧪')}
          ${this._renderTabBtn('evidence', `Evidence (${s ? s.evidence.length : 0})`, '🔍')}
          ${this._renderTabBtn('assumptions', `Assumptions (${s ? s.assumptions.length : 0})`, '📌')}
          ${this._renderTabBtn('alternatives', `Alternatives (${s ? s.alternatives.length : 0})`, '⚖️')}
          ${this._renderTabBtn('conclusion', 'Conclusion', '🏁')}
          ${this._renderTabBtn('why', 'Why? (Safe Explanation)', '💡')}
        </div>

        <!-- Tab Body Content -->
        <div id="reasoning-tab-content" style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; min-height: 280px;">
          ${this._renderTabContent()}
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _renderTabBtn(key, label, icon) {
    const isActive = this.activeTab === key;
    return `
      <button class="reasoning-tab-btn" data-tab="${key}" style="
        padding: 8px 16px;
        background: ${isActive ? '#0f172a' : 'transparent'};
        color: ${isActive ? '#38bdf8' : '#94a3b8'};
        border: 1px solid ${isActive ? '#334155' : 'transparent'};
        border-bottom: ${isActive ? '2px solid #38bdf8' : 'none'};
        border-radius: 6px 6px 0 0;
        cursor: pointer;
        font-size: 13px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
      ">
        <span>${icon}</span> ${label}
      </button>
    `;
  }

  _renderTabContent() {
    const s = this.currentSession;
    if (!s) {
      return `<div style="color: #94a3b8; text-align: center; padding: 40px;">No deliberation session selected. Launch a query above to initiate reasoning.</div>`;
    }

    switch (this.activeTab) {
      case 'active':
        return this._renderActiveTab(s);
      case 'hypotheses':
        return this._renderHypothesesTab(s);
      case 'evidence':
        return this._renderEvidenceTab(s);
      case 'assumptions':
        return this._renderAssumptionsTab(s);
      case 'alternatives':
        return this._renderAlternativesTab(s);
      case 'conclusion':
        return this._renderConclusionTab(s);
      case 'why':
        return this._renderWhyTab(s);
      default:
        return `<div>Unknown view</div>`;
    }
  }

  _renderActiveTab(s) {
    const budget = s.budget || {};
    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 16px;">
          <div style="background: #1e293b; padding: 14px; border-radius: 6px;">
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px;">QUESTION / PROBLEM UNDER REASONING</div>
            <div style="font-size: 16px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">"${s.question}"</div>
            <div style="display: flex; gap: 12px; font-size: 12px;">
              <div>Phase: <strong style="color: #38bdf8;">${s.current_state}</strong></div>
              <div>Depth: <strong>${s.depth}</strong></div>
              <div>Confidence: <strong style="color: #4ade80;">${s.confidence}</strong></div>
              <div>Uncertainty: <strong>${s.uncertainty_state}</strong></div>
            </div>
          </div>

          <div style="background: #1e293b; padding: 14px; border-radius: 6px;">
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px;">RESOURCE & BOUND BUDGET</div>
            <div style="font-size: 12px; display: flex; flex-direction: column; gap: 4px; color: #cbd5e1;">
              <div>Max DAG Depth: <strong>${budget.max_depth || 3}</strong></div>
              <div>Max Subproblems: <strong>${budget.max_subproblems || 8}</strong></div>
              <div>Max Hypotheses: <strong>${budget.max_hypotheses || 6}</strong></div>
              <div>Tool Calls Used: <strong>${budget.tool_calls_used || 0} / ${budget.max_tool_calls || 4}</strong></div>
            </div>
          </div>
        </div>

        <!-- Decomposed Subproblems -->
        <div>
          <h4 style="margin: 0 0 8px 0; font-size: 14px; color: #e2e8f0;">Structured Subproblems (DAG Depth <= 3)</h4>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${
              s.subproblems.length === 0
                ? '<div style="color: #64748b; font-size: 13px;">No subproblems decomposed yet.</div>'
                : s.subproblems
                    .map(
                      (sp, idx) => `
                    <div style="background: #1e293b; padding: 10px 14px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid #38bdf8;">
                      <div>
                        <span style="font-size: 11px; color: #94a3b8; margin-right: 8px;">#${idx + 1} (Level ${sp.depth_level})</span>
                        <strong style="font-size: 13px; color: #f1f5f9;">${sp.question}</strong>
                      </div>
                      <span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #0f172a; color: #38bdf8;">${sp.status}</span>
                    </div>
                  `
                    )
                    .join('')
            }
          </div>
        </div>
      </div>
    `;
  }

  _renderHypothesesTab(s) {
    return `
      <div>
        <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #e2e8f0;">Competing Hypotheses & Popperian Falsifiers</h4>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          ${
            s.hypotheses.length === 0
              ? '<div style="color: #64748b; font-size: 13px;">No candidate hypotheses generated.</div>'
              : s.hypotheses
                  .map(
                    (h) => `
                  <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 14px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                      <span style="font-weight: 600; font-size: 14px; color: #f8fafc;">${h.description}</span>
                      <div style="display: flex; gap: 8px;">
                        <span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #0f172a; color: ${h.status === 'SUPPORTED' ? '#4ade80' : h.status === 'CONTRADICTED' || h.status === 'DISPROVEN' ? '#f87171' : '#fbbf24'};">${h.status}</span>
                        <span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #0f172a; color: #38bdf8;">Conf: ${h.confidence}</span>
                      </div>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">
                      Supporting Evidence: <strong>${h.supporting_evidence_ids.length}</strong> | Contradicting: <strong>${h.contradicting_evidence_ids.length}</strong>
                    </div>
                    <div style="background: #0f172a; padding: 8px 12px; border-radius: 4px; font-size: 12px; color: #cbd5e1;">
                      <span style="color: #f43f5e; font-weight: 600;">Refutation / Falsification Conditions:</span>
                      <ul style="margin: 4px 0 0 0; padding-left: 18px;">
                        ${
                          h.falsification_conditions.length === 0
                            ? '<li>No explicit empirical falsifiers attached.</li>'
                            : h.falsification_conditions.map((fc) => `<li>${fc}</li>`).join('')
                        }
                      </ul>
                    </div>
                  </div>
                `
                  )
                  .join('')
          }
        </div>
      </div>
    `;
  }

  _renderEvidenceTab(s) {
    return `
      <div>
        <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #e2e8f0;">Empirical Observations & Provenance</h4>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${
            s.evidence.length === 0
              ? '<div style="color: #64748b; font-size: 13px;">No evidence collected yet.</div>'
              : s.evidence
                  .map(
                    (e) => `
                  <div style="background: #1e293b; border: 1px solid ${e.is_conflict ? '#ef4444' : '#334155'}; border-radius: 6px; padding: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                      <span style="font-size: 11px; color: #38bdf8; font-weight: 600;">[${e.source_type.toUpperCase()}] Source: ${e.source_id} (Group: ${e.independence_group})</span>
                      <div style="display: flex; gap: 8px;">
                        <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #0f172a; color: #a5b4fc;">Trust: ${e.trust_level}</span>
                        <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #0f172a; color: #4ade80;">Reliability: ${(e.reliability * 100).toFixed(0)}%</span>
                        ${e.is_conflict ? '<span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #ef4444; color: #fff; font-weight: 600;">CONFLICT DETECTED</span>' : ''}
                      </div>
                    </div>
                    <div style="font-size: 13px; color: #f8fafc; font-family: monospace; background: #0f172a; padding: 8px; border-radius: 4px;">
                      ${e.content_summary}
                    </div>
                  </div>
                `
                  )
                  .join('')
          }
        </div>
      </div>
    `;
  }

  _renderAssumptionsTab(s) {
    return `
      <div>
        <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #e2e8f0;">Tracked Assumptions & Invalidation Cascades</h4>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${
            s.assumptions.length === 0
              ? '<div style="color: #64748b; font-size: 13px;">No explicit assumptions recorded.</div>'
              : s.assumptions
                  .map(
                    (a) => `
                  <div style="background: #1e293b; border: 1px solid ${a.status === 'INVALIDATED' ? '#ef4444' : '#334155'}; border-radius: 6px; padding: 12px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1; margin-right: 16px;">
                      <div style="font-size: 13px; font-weight: 600; color: #f8fafc; margin-bottom: 4px;">"${a.description}"</div>
                      <div style="font-size: 11px; color: #94a3b8;">
                        Status: <strong style="color: ${a.status === 'VALIDATED' ? '#4ade80' : a.status === 'INVALIDATED' ? '#ef4444' : '#fbbf24'};">${a.status}</strong> |
                        Dependent Conclusions: <strong>${a.dependent_conclusion_ids.length}</strong>
                        ${a.validation_source ? ` | Note: ${a.validation_source}` : ''}
                      </div>
                    </div>
                    ${
                      a.status !== 'INVALIDATED'
                        ? `<button class="btn-invalidate-asm" data-id="${a.assumption_id}" style="background: #ef4444; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; font-size: 11px; cursor: pointer; font-weight: 600;">
                            ⚡ Invalidate Assumption
                          </button>`
                        : '<span style="font-size: 11px; color: #ef4444; font-weight: 600;">INVALIDATED</span>'
                    }
                  </div>
                `
                  )
                  .join('')
          }
        </div>
      </div>
    `;
  }

  _renderAlternativesTab(s) {
    return `
      <div>
        <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #e2e8f0;">Comparative Tradeoff Alternatives</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;">
          ${
            s.alternatives.length === 0
              ? '<div style="color: #64748b; font-size: 13px;">No comparative alternatives generated.</div>'
              : s.alternatives
                  .map(
                    (alt) => `
                  <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                      <div style="font-size: 14px; font-weight: 600; color: #38bdf8; margin-bottom: 6px;">${alt.title}</div>
                      <p style="font-size: 12px; color: #cbd5e1; margin: 0 0 12px 0;">${alt.description}</p>
                    </div>
                    <div style="background: #0f172a; padding: 8px; border-radius: 4px; font-size: 11px; display: flex; flex-direction: column; gap: 4px;">
                      <div>Risk Score: <strong style="color: ${alt.risk_score > 0.5 ? '#f87171' : '#4ade80'};">${(alt.risk_score * 100).toFixed(0)}%</strong></div>
                      <div>Cost Score: <strong>${(alt.cost_score * 100).toFixed(0)}%</strong></div>
                      <div>Reversibility: <strong>${(alt.reversibility * 100).toFixed(0)}%</strong></div>
                      <div>Expected Impact: <strong style="color: #38bdf8;">${(alt.expected_impact * 100).toFixed(0)}%</strong></div>
                    </div>
                  </div>
                `
                  )
                  .join('')
          }
        </div>
      </div>
    `;
  }

  _renderConclusionTab(s) {
    const c = s.conclusions.length > 0 ? s.conclusions[0] : null;
    if (!c) {
      return `<div style="color: #94a3b8; text-align: center; padding: 30px;">No conclusion has been synthesized yet.</div>`;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px;">
          <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px;">SYNTHESIZED CONCLUSION</div>
          <div style="font-size: 16px; font-weight: 600; color: #f8fafc; margin-bottom: 12px;">"${c.summary}"</div>

          <div style="display: flex; gap: 16px; font-size: 12px; margin-bottom: 16px;">
            <div>Status: <strong style="color: #38bdf8;">${c.status}</strong></div>
            <div>Confidence: <strong style="color: #4ade80;">${c.confidence}</strong></div>
            <div>Uncertainty: <strong>${c.uncertainty_state}</strong></div>
            <div>Verified: <strong style="color: ${c.is_verified ? '#4ade80' : '#fbbf24'};">${c.is_verified ? 'YES (Task 42 Gate)' : 'NO / UNVERIFIED'}</strong></div>
          </div>

          ${
            !c.is_verified
              ? `<button id="btn-verify-conclusion" style="background: #10b981; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600;">
                  🛡️ Submit to Independent Verification (Task 42)
                </button>`
              : '<div style="color: #4ade80; font-size: 13px; font-weight: 600;">✅ Conclusion verified via Truth & Verification subsystem.</div>'
          }
        </div>
      </div>
    `;
  }

  _renderWhyTab(s) {
    const expl = this.explanation || s.explanation;
    if (!expl) {
      return `<div style="color: #94a3b8; text-align: center; padding: 30px;">No explanation generated yet.</div>`;
    }

    return `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="background: #1e293b; border-left: 4px solid #38bdf8; border-radius: 6px; padding: 14px;">
          <h4 style="margin: 0 0 8px 0; font-size: 15px; color: #f8fafc;">Why this conclusion?</h4>
          <p style="margin: 0 0 12px 0; font-size: 13px; color: #cbd5e1;">"${expl.conclusion_summary}"</p>

          <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px; font-weight: 600;">SUPPORTING EVIDENCE & RATIONALE:</div>
          <ul style="margin: 0 0 12px 0; padding-left: 20px; font-size: 12px; color: #e2e8f0;">
            ${
              expl.supporting_reasons.length === 0
                ? '<li>Deliberation supported by baseline observation heuristics.</li>'
                : expl.supporting_reasons.map((r) => `<li>${r}</li>`).join('')
            }
          </ul>

          <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px; font-weight: 600;">COUNTERARGUMENTS ADDRESSED:</div>
          <ul style="margin: 0 0 12px 0; padding-left: 20px; font-size: 12px; color: #e2e8f0;">
            ${
              expl.counterarguments_addressed.length === 0
                ? '<li>No conflicting counterarguments detected.</li>'
                : expl.counterarguments_addressed.map((c) => `<li>${c}</li>`).join('')
            }
          </ul>

          <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px; font-weight: 600;">ASSUMPTIONS MADE:</div>
          <ul style="margin: 0 0 12px 0; padding-left: 20px; font-size: 12px; color: #e2e8f0;">
            ${
              expl.assumptions_made.length === 0
                ? '<li>No secondary assumptions required.</li>'
                : expl.assumptions_made.map((a) => `<li>${a}</li>`).join('')
            }
          </ul>

          ${
            expl.remaining_uncertainty
              ? `<div style="background: #0f172a; padding: 8px 12px; border-radius: 4px; font-size: 12px; color: #fbbf24;">
                  ⚠️ <strong>Remaining Epistemic Uncertainty:</strong> ${expl.remaining_uncertainty}
                </div>`
              : ''
          }
        </div>

        <div style="font-size: 11px; color: #64748b; font-style: italic;">
          Security Policy: Private chain-of-thought is never persisted or rendered. Only structured, empirical claims are exposed.
        </div>
      </div>
    `;
  }

  _bindEvents() {
    // Tab switching
    this.container.querySelectorAll('.reasoning-tab-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    // Session selection
    const sel = this.container.querySelector('#reasoning-session-select');
    if (sel) {
      sel.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val) this.selectSession(val);
      });
    }

    // Refresh
    const btnRef = this.container.querySelector('#btn-refresh-reasoning');
    if (btnRef) {
      btnRef.addEventListener('click', () => this.refresh());
    }

    // Start reasoning
    const btnStart = this.container.querySelector('#btn-start-reasoning');
    if (btnStart) {
      btnStart.addEventListener('click', () => {
        const input = this.container.querySelector('#reasoning-query-input');
        const depthSel = this.container.querySelector('#reasoning-depth-select');
        if (input && input.value) {
          this.startReasoning(input.value, depthSel ? depthSel.value : 'STANDARD');
        }
      });
    }

    // Invalidate assumption buttons
    this.container.querySelectorAll('.btn-invalidate-asm').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const asmId = e.currentTarget.getAttribute('data-id');
        const reason = prompt('Specify the empirical reason or observation invalidating this assumption:');
        if (asmId && reason) {
          this.invalidateAssumption(asmId, reason);
        }
      });
    });

    // Verify conclusion button
    const btnVerify = this.container.querySelector('#btn-verify-conclusion');
    if (btnVerify) {
      btnVerify.addEventListener('click', () => this.verifyConclusion());
    }
  }
}

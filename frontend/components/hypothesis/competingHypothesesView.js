/**
 * Task 115: Competing Hypotheses & Autonomous Uncertainty Resolution Console
 * Section 55 & 56: Real-time side-by-side comparison, testable falsification,
 * discriminating observations, evidence independence, and cognitive bias safeguards.
 *
 * Hard Invariants:
 * - NO "WINNER", "BEST HYPOTHESIS", or arbitrary ranking.
 * - UNKNOWN / OTHER CAUSE is always displayed.
 * - Falsification conditions ("What would disprove this?") are first-class.
 */

import { hypothesesApi } from '../../lib/api/endpoints.js';

export class CompetingHypothesesView {
  constructor(containerId = 'main-content') {
    this.containerId = containerId;
    this.activeSetId = null;
    this.sets = [];
    this.currentSet = null;
    this.comparisonData = null;
    this.loading = false;
  }

  async render() {
    const container = document.getElementById(this.containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="hypotheses-container" style="padding: 24px; max-width: 1440px; margin: 0 auto; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; border-bottom: 1px solid #334155; padding-bottom: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <h1 style="font-size: 26px; font-weight: 700; color: #f8fafc; margin: 0;">Autonomous Hypothesis & Competing Explanations</h1>
              <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; border: 1px solid rgba(56, 189, 248, 0.3);">Task 115 Engine</span>
            </div>
            <p style="color: #94a3b8; font-size: 14px; margin: 6px 0 0 0;">
              Rigorous candidate explanation management with falsification conditions, evidence independence lineage, and cognitive bias protection.
            </p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="btn-new-incident" style="background: #2563eb; hover: #1d4ed8; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px;">
              + New Target Incident
            </button>
            <button id="btn-refresh-hyp" style="background: #334155; color: #cbd5e1; border: 1px solid #475569; padding: 8px 14px; border-radius: 6px; cursor: pointer;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Invariant Banner -->
        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #1e293b; border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 13px; color: #94a3b8; display: flex; gap: 24px; flex-wrap: wrap;">
          <span>⚖️ <strong>HYPOTHESIS ≠ BELIEF</strong></span>
          <span>🔍 <strong>CORRELATION ≠ CAUSATION</strong></span>
          <span>🛡️ <strong>AGENT CLAIM ≠ INDEPENDENT EVIDENCE</strong></span>
          <span>❓ <strong>UNKNOWN REMAINS FIRST-CLASS</strong></span>
          <span>🚫 <strong>NO ARBITRARY "WINNER" SELECTION</strong></span>
        </div>

        <!-- Main Body Grid -->
        <div style="display: grid; grid-template-columns: 320px 1fr; gap: 24px;">
          <!-- Sidebar: Sets List -->
          <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
            <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-top: 0; margin-bottom: 12px;">
              Target Incidents (${this.sets.length})
            </h3>
            <div id="hypothesis-sets-list" style="display: flex; flex-direction: column; gap: 8px; max-height: 650px; overflow-y: auto;">
              <div style="color: #64748b; font-size: 13px; padding: 8px;">Loading target incidents...</div>
            </div>
          </div>

          <!-- Content: Active Set View -->
          <div id="set-detail-content" style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; min-height: 600px;">
            <div style="color: #64748b; text-align: center; padding-top: 80px;">Select or create a target incident to inspect competing hypotheses.</div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
    await this.loadSets();
  }

  _bindEvents() {
    const btnNew = document.getElementById('btn-new-incident');
    if (btnNew) {
      btnNew.addEventListener('click', () => this.promptNewSet());
    }
    const btnRefresh = document.getElementById('btn-refresh-hyp');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => this.loadSets());
    }
  }

  async loadSets() {
    this.loading = true;
    try {
      this.sets = await hypothesesApi.listSets();
      this._renderSetsList();
      if (this.sets.length > 0 && !this.activeSetId) {
        this.selectSet(this.sets[0].set_id);
      } else if (this.activeSetId) {
        this.selectSet(this.activeSetId);
      }
    } catch (err) {
      console.error('Failed to load hypothesis sets:', err);
    } finally {
      this.loading = false;
    }
  }

  _renderSetsList() {
    const listEl = document.getElementById('hypothesis-sets-list');
    if (!listEl) return;

    if (this.sets.length === 0) {
      listEl.innerHTML = `<div style="color: #64748b; font-size: 13px; padding: 8px;">No target incidents. Click "+ New Target Incident" to start.</div>`;
      return;
    }

    listEl.innerHTML = this.sets.map(s => {
      const isSelected = s.set_id === this.activeSetId;
      const statusColor = s.is_resolved ? '#10b981' : '#f59e0b';
      const statusLabel = s.is_resolved ? 'RESOLVED' : 'UNRESOLVED';

      return `
        <div class="set-card" data-set-id="${s.set_id}" style="padding: 12px; background: ${isSelected ? 'rgba(56, 189, 248, 0.1)' : '#1e293b'}; border: 1px solid ${isSelected ? '#38bdf8' : '#334155'}; border-radius: 6px; cursor: pointer; transition: all 0.15s ease;">
          <div style="font-weight: 600; font-size: 14px; color: #f1f5f9; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${s.target_description || 'Unnamed Target'}
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #94a3b8;">
            <span>${(s.active_hypothesis_ids || []).length + 1} hypotheses</span>
            <span style="color: ${statusColor}; font-weight: 600;">${statusLabel}</span>
          </div>
        </div>
      `;
    }).join('');

    listEl.querySelectorAll('.set-card').forEach(card => {
      card.addEventListener('click', () => {
        const sid = card.getAttribute('data-set-id');
        this.selectSet(sid);
      });
    });
  }

  async selectSet(setId) {
    this.activeSetId = setId;
    this._renderSetsList();

    const detailEl = document.getElementById('set-detail-content');
    if (!detailEl) return;

    detailEl.innerHTML = `<div style="color: #94a3b8; text-align: center; padding: 40px;">Loading competing explanations matrix for ${setId}...</div>`;

    try {
      const [setData, compData] = await Promise.all([
        hypothesesApi.getSet(setId),
        hypothesesApi.compareSet(setId),
      ]);
      this.currentSet = setData;
      this.comparisonData = compData;
      this._renderSetDetail();
    } catch (err) {
      detailEl.innerHTML = `<div style="color: #ef4444; padding: 20px;">Failed to load set details: ${err.message}</div>`;
    }
  }

  _renderSetDetail() {
    const detailEl = document.getElementById('set-detail-content');
    if (!detailEl || !this.currentSet || !this.comparisonData) return;

    const s = this.currentSet;
    const m = this.comparisonData;

    detailEl.innerHTML = `
      <!-- Incident Target Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155;">
        <div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">Target Incident</span>
            <span style="background: ${s.is_resolved ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)'}; color: ${s.is_resolved ? '#34d399' : '#fbbf24'}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">
              ${s.resolution_summary || (s.is_resolved ? 'RESOLVED' : 'CAUSE_UNKNOWN')}
            </span>
          </div>
          <h2 style="font-size: 18px; font-weight: 700; color: #f8fafc; margin: 6px 0 4px 0;">${s.target_description}</h2>
          <div style="font-size: 12px; color: #94a3b8;">Set ID: <code>${s.set_id}</code> | Version: ${s.version}</div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button id="btn-attach-evidence" style="background: #10b981; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer;">
            + Attach Evidence
          </button>
          <button id="btn-add-hyp" style="background: #6366f1; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer;">
            + Propose Hypothesis
          </button>
        </div>
      </div>

      <!-- Information Gaps & Discriminators Banner -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
        <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 6px; padding: 12px;">
          <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
            🔭 Discriminating Observations (Task 114 VoI)
          </h4>
          ${(m.discriminators && m.discriminators.length > 0) ? `
            <div style="display: flex; flex-direction: column; gap: 6px; font-size: 12px;">
              ${m.discriminators.map(d => `
                <div style="background: #0f172a; padding: 8px; border-radius: 4px; border: 1px solid #1e293b;">
                  <strong style="color: #e2e8f0;">${d.target_metric_or_signal}</strong>
                  <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">VoI: <strong>${d.information_value}</strong> | Channel: ${d.observation_channel}</div>
                  <div style="color: #cbd5e1; font-size: 11px; margin-top: 2px;"><em>${d.rationale}</em></div>
                </div>
              `).join('')}
            </div>
          ` : `<div style="color: #64748b; font-size: 12px;">No divergent discriminators identified.</div>`}
        </div>

        <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 6px; padding: 12px;">
          <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #f59e0b; display: flex; align-items: center; gap: 6px;">
            ⚠️ Information Gaps & Uncertainty
          </h4>
          ${(m.information_gaps && m.information_gaps.length > 0) ? `
            <ul style="margin: 0; padding-left: 18px; font-size: 12px; color: #cbd5e1; display: flex; flex-direction: column; gap: 4px;">
              ${m.information_gaps.map(g => `<li>${g}</li>`).join('')}
            </ul>
          ` : `<div style="color: #64748b; font-size: 12px;">No open empirical information gaps recorded.</div>`}
        </div>
      </div>

      <!-- Section Title -->
      <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
        <h3 style="font-size: 15px; font-weight: 700; color: #f1f5f9; margin: 0;">
          Side-by-Side Competing Explanations Matrix (Section 56)
        </h3>
        <span style="font-size: 11px; color: #64748b;">Explicitly non-ranking; reflects multidimensional evidence</span>
      </div>

      <!-- Matrix Table -->
      <div style="overflow-x: auto; background: #0f172a; border: 1px solid #334155; border-radius: 8px; margin-bottom: 24px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
          <thead>
            <tr style="background: #1e293b; color: #94a3b8; border-bottom: 1px solid #334155;">
              <th style="padding: 10px 12px;">Hypothesis</th>
              <th style="padding: 10px 12px;">Status</th>
              <th style="padding: 10px 12px;">Mechanism</th>
              <th style="padding: 10px 12px;">Evidence (+ / -)</th>
              <th style="padding: 10px 12px;">Falsification Condition</th>
              <th style="padding: 10px 12px;">Predictions</th>
              <th style="padding: 10px 12px;">Uncertainty</th>
              <th style="padding: 10px 12px; text-align: center;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${m.matrix.map(row => {
              const isUnknown = row.is_unknown;
              const statusBadge = this._getStatusBadge(row.status);

              return `
                <tr style="border-bottom: 1px solid #1e293b; background: ${isUnknown ? 'rgba(100, 116, 139, 0.05)' : 'transparent'};">
                  <td style="padding: 12px; vertical-align: top; max-width: 240px;">
                    <div style="font-weight: 600; color: #f8fafc; margin-bottom: 4px;">
                      ${isUnknown ? '❓ [UNKNOWN] ' : ''}${row.statement}
                    </div>
                    <div style="font-size: 10px; color: #64748b;">ID: <code>${row.hypothesis_id}</code></div>
                    ${row.bias_guard_triggers && row.bias_guard_triggers.length > 0 ? `
                      <div style="margin-top: 6px; padding: 4px 6px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; font-size: 10px; color: #f87171;">
                        🛡️ ${row.bias_guard_triggers[0]}
                      </div>
                    ` : ''}
                  </td>
                  <td style="padding: 12px; vertical-align: top; white-space: nowrap;">
                    ${statusBadge}
                  </td>
                  <td style="padding: 12px; vertical-align: top; color: #cbd5e1; max-width: 200px;">
                    ${row.mechanism}
                  </td>
                  <td style="padding: 12px; vertical-align: top; white-space: nowrap;">
                    <span style="color: #34d399; font-weight: 600;">+${row.supporting_evidence_count}</span>
                    <span style="color: #64748b;"> / </span>
                    <span style="color: #f87171; font-weight: 600;">-${row.contradicting_evidence_count}</span>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">Str: ${row.evidence_strength}</div>
                  </td>
                  <td style="padding: 12px; vertical-align: top; color: #cbd5e1; max-width: 220px;">
                    ${(row.falsification_conditions && row.falsification_conditions.length > 0) ? `
                      <div style="color: #fb7185; font-size: 11px;">⚠️ ${row.falsification_conditions[0]}</div>
                    ` : '<span style="color: #64748b;">None defined</span>'}
                  </td>
                  <td style="padding: 12px; vertical-align: top; color: #cbd5e1; max-width: 160px;">
                    ${(row.predictions && row.predictions.length > 0) ? `
                      <div style="font-size: 11px;">🔮 ${row.predictions[0]}</div>
                    ` : '<span style="color: #64748b;">None</span>'}
                  </td>
                  <td style="padding: 12px; vertical-align: top; font-weight: 600; color: ${row.uncertainty > 0.5 ? '#f59e0b' : '#34d399'};">
                    ${row.uncertainty}
                  </td>
                  <td style="padding: 12px; vertical-align: top; text-align: center; white-space: nowrap;">
                    <button class="btn-verify-hyp" data-hid="${row.hypothesis_id}" style="background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; padding: 4px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; margin-bottom: 4px;">
                      Verify
                    </button>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;

    this._bindDetailActions();
  }

  _getStatusBadge(status) {
    const styles = {
      SUPPORTED: 'background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669;',
      STRONGLY_SUPPORTED: 'background: rgba(16, 185, 129, 0.35); color: #10b981; border: 1px solid #10b981; font-weight: 700;',
      CONTESTED: 'background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626;',
      WEAKENED: 'background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #d97706;',
      FALSIFIED: 'background: rgba(153, 27, 27, 0.4); color: #fca5a5; border: 1px solid #ef4444; font-weight: 700;',
      REJECTED: 'background: #334155; color: #94a3b8; border: 1px solid #475569;',
      VERIFIED: 'background: rgba(59, 130, 246, 0.3); color: #60a5fa; border: 1px solid #3b82f6; font-weight: 700;',
      UNDER_INVESTIGATION: 'background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #0284c7;',
      UNKNOWN: 'background: rgba(100, 116, 139, 0.2); color: #94a3b8; border: 1px solid #64748b;',
    };
    const style = styles[status] || 'background: #334155; color: #94a3b8; border: 1px solid #475569;';
    return `<span style="padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; ${style}">${status}</span>`;
  }

  _bindDetailActions() {
    const btnAttach = document.getElementById('btn-attach-evidence');
    if (btnAttach) {
      btnAttach.addEventListener('click', () => this.promptAttachEvidence());
    }

    const btnAddHyp = document.getElementById('btn-add-hyp');
    if (btnAddHyp) {
      btnAddHyp.addEventListener('click', () => this.promptAddHypothesis());
    }

    document.querySelectorAll('.btn-verify-hyp').forEach(btn => {
      btn.addEventListener('click', async () => {
        const hid = btn.getAttribute('data-hid');
        try {
          const res = await hypothesesApi.verify(hid);
          if (res.verified) {
            alert(`✅ Hypothesis Verified!\n${res.notes}`);
          } else {
            alert(`⚠️ Verification Invariants Blocked:\n• ${res.reasons_blocked.join('\n• ')}\n\n${res.advice}`);
          }
          await this.selectSet(this.activeSetId);
        } catch (e) {
          alert(`Verification Error: ${e.message}`);
        }
      });
    });
  }

  async promptNewSet() {
    const target = prompt('Enter target incident description:');
    if (!target) return;
    try {
      const hset = await hypothesesApi.createSet({ target_description: target });
      await this.loadSets();
      this.selectSet(hset.set_id);
    } catch (e) {
      alert(`Error creating hypothesis set: ${e.message}`);
    }
  }

  async promptAttachEvidence() {
    if (!this.activeSetId) return;
    const source = prompt('Evidence source (e.g., telemetry.cpu_monitor, network_probe, user_report):', 'telemetry.cpu_monitor');
    if (!source) return;
    const metric = prompt('Metric name in observation (e.g., cpu_memory_utilization, network_rtt_loss):', 'cpu_memory_utilization');
    if (!metric) return;
    const val = prompt('Observed metric value (e.g., 95.0 or 20.0):', '92.0');
    if (!val) return;

    try {
      await hypothesesApi.attachEvidence(this.activeSetId, {
        source,
        source_type: 'system',
        evidence_type: 'OBSERVATION',
        payload: { [metric]: parseFloat(val) },
      });
      alert('Evidence attached successfully and evaluated against competing hypotheses.');
      await this.selectSet(this.activeSetId);
    } catch (e) {
      alert(`Error attaching evidence: ${e.message}`);
    }
  }

  async promptAddHypothesis() {
    if (!this.activeSetId) return;
    const stmt = prompt('Hypothesis statement (candidate explanation):');
    if (!stmt) return;
    try {
      await hypothesesApi.createHypothesis({
        set_id: this.activeSetId,
        statement: stmt,
        provenance: 'USER_PROVIDED',
      });
      await this.selectSet(this.activeSetId);
    } catch (e) {
      alert(`Error adding hypothesis: ${e.message}`);
    }
  }
}

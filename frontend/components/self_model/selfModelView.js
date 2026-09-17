/**
 * Autonomous Self-Model, Capability Awareness & Internal State Intelligence View (Task 101)
 * Glassmorphic operational state intelligence dashboard answering Kairo's 15 canonical introspective questions.
 */

import { selfModelApi } from '../../lib/api/endpoints.js';

export class SelfModelView {
  constructor(containerId) {
    this.container = typeof document !== 'undefined' ? (typeof containerId === 'string' ? document.getElementById(containerId) : containerId) : null;
    this.activeTab = 'answers'; // answers, capabilities, limitations, uncertainties, deltas, grounding
    this.snapshot = null;
    this.answers = null;
    this.capabilities = {};
    this.limitations = [];
    this.uncertainties = [];
    this.deltas = [];
    this.groundingResult = null;
    this.isLoading = false;
    this.error = null;
    this.selectedCapability = null;
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
      const [snap, ans, lims, uncs, dts] = await Promise.all([
        selfModelApi.getSnapshot().catch(() => null),
        selfModelApi.getAnswers().catch(() => null),
        selfModelApi.getLimitations().catch(() => []),
        selfModelApi.getUncertainties().catch(() => []),
        selfModelApi.getDeltas().catch(() => []),
      ]);

      this.snapshot = snap;
      this.answers = ans;
      this.capabilities = snap ? (snap.capabilities || {}) : {};
      this.limitations = lims || [];
      this.uncertainties = uncs || [];
      this.deltas = dts || [];
    } catch (err) {
      console.error('Failed to load self-model data:', err);
      this.error = err.message || 'Failed to connect to Self-Model Service';
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async reconcile() {
    this.isLoading = true;
    try {
      const newSnap = await selfModelApi.reconcile();
      this.snapshot = newSnap;
      await this.loadData();
    } catch (err) {
      this.error = 'Reconciliation failed: ' + err.message;
      this.render();
    }
  }

  async verifyGrounding() {
    this.isLoading = true;
    try {
      this.groundingResult = await selfModelApi.verifyGrounding();
      this.activeTab = 'grounding';
    } catch (err) {
      this.error = 'Grounding verification failed: ' + err.message;
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
      <div class="self-model-loading" style="padding: 2.5rem; text-align: center; color: var(--text-muted, #94a3b8);">
        <div class="spinner" style="display: inline-block; width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.1); border-top-color: #38bdf8; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <p style="margin-top: 1rem; font-family: Inter, sans-serif;">Reconciling operational self-model telemetry...</p>
      </div>
    `;
  }

  render() {
    if (!this.container) return;

    if (this.isLoading && !this.snapshot) {
      this.renderSkeleton();
      return;
    }

    const snap = this.snapshot || {
      snapshot_id: 'pending',
      autonomy_mode: 'BOUNDED_AUTONOMY',
      emergency_stop_state: false,
      runtime_version: '0.2.0',
      resources: { saturation_pct: 0.0, degradation_tier: 'FULL_FIDELITY' },
    };

    const eStopActive = snap.emergency_stop_state;
    const readyCount = Object.values(this.capabilities).filter(c => c.readiness_state === 'READY').length;
    const degradedCount = Object.values(this.capabilities).filter(c => c.readiness_state === 'DEGRADED').length;
    const totalCount = Object.keys(this.capabilities).length;

    this.container.innerHTML = `
      <div class="self-model-view" style="display: flex; flex-direction: column; gap: 1.5rem; padding: 1.5rem; font-family: Inter, system-ui, sans-serif; color: #f8fafc;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 1.25rem;">
          <div>
            <h1 style="margin: 0; font-size: 1.5rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              Autonomous Self-Model & Capability Intelligence
            </h1>
            <p style="margin: 0.25rem 0 0; font-size: 0.875rem; color: #94a3b8;">
              Grounded, evidence-backed introspective state answering Kairo's operational readiness.
            </p>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button id="sm-audit-btn" style="background: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer;">
              Audit Grounding
            </button>
            <button id="sm-reconcile-btn" style="background: #2563eb; color: #ffffff; border: none; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer;">
              Reconcile State
            </button>
          </div>
        </div>

        ${this.error ? `
          <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #fca5a5; padding: 0.75rem 1rem; border-radius: 6px;">
            ${this.error}
          </div>
        ` : ''}

        <!-- Top Overview Metric Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Autonomy Mode</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: #38bdf8;">${snap.autonomy_mode}</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">Runtime v${snap.runtime_version}</div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Emergency Stop</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: ${eStopActive ? '#ef4444' : '#10b981'};">
              ${eStopActive ? 'ENGAGED (Fail-Closed)' : 'INACTIVE (Normal)'}
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">Kill-switch telemetry</div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Capabilities Ready</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: #10b981;">
              ${readyCount} / ${totalCount}
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">${degradedCount} degraded</div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Resource Saturation</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: #f59e0b;">
              ${Math.round((snap.resources?.saturation_pct || 0) * 100)}%
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">Tier: ${snap.resources?.degradation_tier || 'FULL_FIDELITY'}</div>
          </div>

          <div style="background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06); padding: 1rem; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Boundaries & Doubts</div>
            <div style="font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; color: #ec4899;">
              ${this.limitations.length} lims / ${this.uncertainties.length} uncs
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">Evidence-backed</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 0.5rem;">
          ${this.renderTabButton('answers', '15 Canonical Questions')}
          ${this.renderTabButton('capabilities', 'Capability Matrix')}
          ${this.renderTabButton('limitations', 'Self-Limitations')}
          ${this.renderTabButton('uncertainties', 'Epistemic Uncertainties')}
          ${this.renderTabButton('deltas', 'State Timeline / Diff')}
          ${this.renderTabButton('grounding', 'Grounding Audit')}
        </div>

        <!-- Main Tab Body -->
        <div class="sm-tab-content">
          ${this.renderTabContent()}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderTabButton(tabId, label) {
    const active = this.activeTab === tabId;
    return `
      <button class="sm-tab-btn" data-tab="${tabId}" style="background: ${active ? 'rgba(56, 189, 248, 0.15)' : 'transparent'}; color: ${active ? '#38bdf8' : '#94a3b8'}; border: 1px solid ${active ? 'rgba(56, 189, 248, 0.4)' : 'transparent'}; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; cursor: pointer;">
        ${label}
      </button>
    `;
  }

  renderTabContent() {
    switch (this.activeTab) {
      case 'answers':
        return this.renderAnswers();
      case 'capabilities':
        return this.renderCapabilities();
      case 'limitations':
        return this.renderLimitations();
      case 'uncertainties':
        return this.renderUncertainties();
      case 'deltas':
        return this.renderDeltas();
      case 'grounding':
        return this.renderGrounding();
      default:
        return `<p>Select a tab.</p>`;
    }
  }

  renderAnswers() {
    const a = this.answers || {};
    const questions = [
      { num: 1, title: 'What capabilities do I have?', val: (a.q1_capabilities || []).join(', ') || 'None registered' },
      { num: 2, title: 'Which versions are available?', val: JSON.stringify(a.q2_versions || {}, null, 2) },
      { num: 3, title: 'Which capabilities are actually ready?', val: (a.q3_ready_capabilities || []).join(', ') || 'None currently ready' },
      { num: 4, title: 'Which are degraded?', val: (a.q4_degraded_capabilities || []).join(', ') || 'None degraded' },
      { num: 5, title: 'Which are temporarily unavailable?', val: (a.q5_temporarily_unavailable || []).join(', ') || 'None unavailable' },
      { num: 6, title: 'What resources do I currently have?', val: `Saturation: ${Math.round((a.q6_current_resources?.saturation_pct || 0) * 100)}% | Tier: ${a.q6_current_resources?.degradation_tier || 'NORMAL'}` },
      { num: 7, title: 'What tools can I use?', val: `${(a.q7_usable_tools || []).length} registered usable tools` },
      { num: 8, title: 'What access is currently authorized?', val: (a.q8_authorized_access || []).join('; ') || 'Restricted' },
      { num: 9, title: 'Which actions require approval?', val: (a.q9_actions_requiring_approval || []).join(', ') || 'None' },
      { num: 10, title: 'Which dependencies are failing?', val: (a.q10_failing_dependencies || []).join(', ') || 'All dependencies healthy' },
      { num: 11, title: 'Which capabilities have recently failed?', val: (a.q11_recently_failed_capabilities || []).join(', ') || 'None recently failed' },
      { num: 12, title: 'How reliable is each capability?', val: JSON.stringify(a.q12_capability_reliability || {}, null, 2) },
      { num: 13, title: 'What has changed since the last check?', val: `${(a.q13_changes_since_last_check || []).length} state transition events recorded` },
      { num: 14, title: 'What do I know about my own limitations?', val: `${(a.q14_limitations || []).length} active empirical limitations` },
      { num: 15, title: 'What am I uncertain about?', val: `${(a.q15_uncertainties || []).length} epistemic uncertainties requiring revalidation` },
    ];

    return `
      <div style="display: flex; flex-direction: column; gap: 0.75rem;">
        ${questions.map(q => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 0.875rem 1.25rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">Q${q.num}</span>
              <strong style="color: #f1f5f9; font-size: 0.9375rem;">${q.title}</strong>
            </div>
            <pre style="margin: 0.5rem 0 0 1.75rem; color: #cbd5e1; font-size: 0.8125rem; white-space: pre-wrap; word-break: break-all; font-family: monospace;">${q.val}</pre>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderCapabilities() {
    const caps = Object.values(this.capabilities);
    if (!caps.length) return `<p style="color: #94a3b8;">No capabilities loaded.</p>`;

    return `
      <div style="overflow-x: auto; background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem; text-align: left;">
          <thead>
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); background: rgba(30, 41, 59, 0.5); color: #94a3b8;">
              <th style="padding: 0.75rem 1rem;">Capability</th>
              <th style="padding: 0.75rem 1rem;">Version</th>
              <th style="padding: 0.75rem 1rem;">Lifecycle</th>
              <th style="padding: 0.75rem 1rem;">Readiness</th>
              <th style="padding: 0.75rem 1rem;">Health</th>
              <th style="padding: 0.75rem 1rem;">Reliability</th>
              <th style="padding: 0.75rem 1rem;">Failures</th>
              <th style="padding: 0.75rem 1rem;">Evidence</th>
            </tr>
          </thead>
          <tbody>
            ${caps.map(c => {
              const rColor = c.readiness_state === 'READY' ? '#10b981' : (c.readiness_state === 'DEGRADED' ? '#f59e0b' : '#ef4444');
              return `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                  <td style="padding: 0.75rem 1rem; font-weight: 600; color: #f8fafc;">${c.name || c.capability_id}</td>
                  <td style="padding: 0.75rem 1rem; color: #94a3b8;">v${c.version}</td>
                  <td style="padding: 0.75rem 1rem; color: #cbd5e1;">${c.lifecycle_state}</td>
                  <td style="padding: 0.75rem 1rem;">
                    <span style="background: ${rColor}22; color: ${rColor}; border: 1px solid ${rColor}55; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">
                      ${c.readiness_state}
                    </span>
                  </td>
                  <td style="padding: 0.75rem 1rem; color: #cbd5e1;">${c.health_state}</td>
                  <td style="padding: 0.75rem 1rem; color: #cbd5e1;">${Math.round(c.reliability_score * 100)}%</td>
                  <td style="padding: 0.75rem 1rem; color: ${c.consecutive_failures > 0 ? '#ef4444' : '#94a3b8'};">${c.consecutive_failures}</td>
                  <td style="padding: 0.75rem 1rem; color: #94a3b8; font-size: 0.75rem;">${(c.evidence || []).join('; ')}</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  renderLimitations() {
    if (!this.limitations.length) {
      return `<p style="color: #10b981;">No active operational limitations detected.</p>`;
    }
    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
        ${this.limitations.map(l => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 8px; padding: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 0.75rem; background: rgba(245, 158, 11, 0.15); color: #f59e0b; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700;">
                ${l.subject}
              </span>
              <span style="font-size: 0.75rem; color: #64748b;">${l.is_hard_limit ? 'HARD BOUNDARY' : 'ADAPTIVE'}</span>
            </div>
            <div style="margin-top: 0.5rem; font-weight: 600; color: #f8fafc;">${l.description}</div>
            <div style="margin-top: 0.25rem; font-size: 0.8125rem; color: #94a3b8;"><strong>Reason:</strong> ${l.reason}</div>
            <div style="margin-top: 0.25rem; font-size: 0.75rem; color: #64748b;"><strong>Evidence:</strong> ${l.evidence}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderUncertainties() {
    if (!this.uncertainties.length) {
      return `<p style="color: #10b981;">No active epistemic uncertainties.</p>`;
    }
    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
        ${this.uncertainties.map(u => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(236, 72, 153, 0.2); border-radius: 8px; padding: 1rem;">
            <span style="font-size: 0.75rem; background: rgba(236, 72, 153, 0.15); color: #ec4899; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700;">
              ${u.subject}
            </span>
            <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #f8fafc;">${u.reason}</div>
            <div style="margin-top: 0.25rem; font-size: 0.75rem; color: #94a3b8;"><strong>Evidence:</strong> ${u.evidence}</div>
            <div style="margin-top: 0.25rem; font-size: 0.75rem; color: #38bdf8;"><strong>Policy:</strong> ${u.revalidation_policy}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderDeltas() {
    if (!this.deltas.length) {
      return `<p style="color: #94a3b8;">No state changes recorded between snapshots.</p>`;
    }
    return `
      <div style="display: flex; flex-direction: column; gap: 0.75rem;">
        ${this.deltas.map(d => `
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 1rem;">
            <div style="font-size: 0.75rem; color: #94a3b8;">Target Snapshot: ${d.target_snapshot_id} (Base: ${d.base_snapshot_id})</div>
            <div style="margin-top: 0.5rem;">
              ${(d.changes || []).map(ch => `
                <div style="margin-top: 0.25rem; font-size: 0.8125rem;">
                  <strong style="color: #38bdf8;">[${ch.change_type}]</strong> ${ch.target_id}: 
                  <span style="color: #ef4444;">${ch.old_state}</span> → <span style="color: #10b981;">${ch.new_state}</span>
                  <div style="color: #64748b; font-size: 0.75rem; margin-left: 1rem;">${ch.reason}</div>
                </div>
              `).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderGrounding() {
    const res = this.groundingResult;
    if (!res) {
      return `
        <div style="text-align: center; padding: 2rem; color: #94a3b8;">
          <p>Click "Audit Grounding" to execute empirical invariant verification.</p>
        </div>
      `;
    }
    const isGrounded = res.is_grounded;
    return `
      <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid ${isGrounded ? '#10b981' : '#ef4444'}; border-radius: 8px; padding: 1.5rem;">
        <h3 style="margin-top: 0; color: ${isGrounded ? '#10b981' : '#ef4444'};">
          ${isGrounded ? 'GROUNDED: 100% Empirical Alignment' : 'GROUNDING BREACH DETECTED'}
        </h3>
        <p style="color: #cbd5e1; font-size: 0.875rem;">
          Total claims audited: <strong>${res.total_claims}</strong> | Verified claims: <strong>${res.verified_claims}</strong>
        </p>
        ${res.violations && res.violations.length ? `
          <div style="margin-top: 1rem; color: #ef4444; font-size: 0.875rem;">
            <strong>Violations:</strong>
            <ul>
              ${res.violations.map(v => `<li>${v}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `;
  }

  bindEvents() {
    const rBtn = this.container.querySelector('#sm-reconcile-btn');
    if (rBtn) rBtn.onclick = () => this.reconcile();

    const aBtn = this.container.querySelector('#sm-audit-btn');
    if (aBtn) aBtn.onclick = () => this.verifyGrounding();

    const tabs = this.container.querySelectorAll('.sm-tab-btn');
    tabs.forEach(t => {
      t.onclick = () => this.setTab(t.getAttribute('data-tab'));
    });
  }
}

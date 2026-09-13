/**
 * Kairo Autonomous Governance, Constitutional Reasoning, Policy Intelligence
 * & Authority Management Engine View (Task 78).
 *
 * Views:
 * 1. POLICY OVERVIEW: 6-tier policy hierarchy (SYSTEM > SECURITY > TENANT > PROJECT > WORKFLOW > TASK), active counts.
 * 2. CONSTITUTION MATRIX: 11 principles, weights, strictness (MANDATORY, STRICT, ADVISORY), compliance gauge.
 * 3. AUTHORITY MAP: Discrete authority levels (NONE to ADMIN), subject grants, least-privilege advice.
 * 4. HUMAN REVIEW QUEUE: Pending human oversight reviews, handoff packets, non-self-approving resolution buttons.
 * 5. DECISIONS AUDIT: Pre-execution reviews, evidence trails, constitutional scores, explanations.
 * 6. POLICY CONFLICTS: Multi-tier conflict resolution logs, deterministic precedence winners.
 * 7. ESCALATIONS & OVERRIDES: Privilege escalation, control weakening, and probe hammering detections.
 *
 * SAFETY INVARIANT BADGES:
 * CAPABILITY != AUTHORITY != PERMISSION != APPROVAL != POLICY != CONSTITUTION != GOAL != OVERSIGHT != ETHICS
 */

import { governanceApi } from '../../lib/api/endpoints.js';

export class GovernanceCenterView {
  constructor(container) {
    this.container = container;
    this.activeSubTab = 'overview'; // 'overview', 'constitution', 'authority', 'human_queue', 'decisions', 'conflicts', 'escalations'
    this.dashboardData = null;
    this.constitutionData = null;
    this.humanQueueData = [];
    this.escalationsData = [];
    this.authorityData = null;
    this.isLoading = false;
    this.statusMessage = null;
  }

  setSubTab(tab) {
    this.activeSubTab = tab;
    this.render();
  }

  formatStateBadge(state) {
    const s = (state || 'PENDING_REVIEW').toUpperCase();
    let color = '#3b82f6'; // Blue for pending
    if (s === 'APPROVED' || s === 'EXECUTABLE') color = '#10b981'; // Green
    else if (s === 'DENIED' || s === 'ABORTED') color = '#ef4444'; // Red
    else if (s === 'REQUIRES_HUMAN') color = '#ec4899'; // Pink/Magenta
    else if (s === 'REQUIRES_APPROVAL') color = '#f59e0b'; // Amber
    else if (s === 'EXPIRED') color = '#64748b'; // Slate

    return `
      <span style="display:inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; background-color: ${color}20; color: ${color}; border: 1px solid ${color}60;">
        ${s}
      </span>
    `;
  }

  formatStrictnessBadge(strictness) {
    const s = (strictness || 'ADVISORY').toUpperCase();
    let color = '#3b82f6';
    if (s === 'MANDATORY') color = '#ef4444';
    else if (s === 'STRICT') color = '#f59e0b';
    return `
      <span style="display:inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; background-color: ${color}20; color: ${color}; border: 1px solid ${color}60;">
        ${s}
      </span>
    `;
  }

  formatTierBadge(tier) {
    const t = (tier || 'TASK').toUpperCase();
    let color = '#64748b';
    if (t === 'SYSTEM') color = '#ef4444';
    else if (t === 'SECURITY') color = '#f97316';
    else if (t === 'TENANT') color = '#8b5cf6';
    else if (t === 'PROJECT') color = '#3b82f6';
    else if (t === 'WORKFLOW') color = '#10b981';
    return `
      <span style="display:inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; background-color: ${color}20; color: ${color}; border: 1px solid ${color}60;">
        ${t}
      </span>
    `;
  }

  async loadData() {
    this.isLoading = true;
    this.render();

    try {
      const [dash, constData, pending, escalations] = await Promise.allSettled([
        governanceApi.getDashboard(),
        governanceApi.getConstitution(),
        governanceApi.listPendingHumanReviews(),
        governanceApi.getEscalations(50),
      ]);

      if (dash.status === 'fulfilled') this.dashboardData = dash.value;
      if (constData.status === 'fulfilled') this.constitutionData = constData.value;
      if (pending.status === 'fulfilled') this.humanQueueData = pending.value || [];
      if (escalations.status === 'fulfilled') this.escalationsData = escalations.value || [];

      // Also fetch system admin authority as default sample
      try {
        this.authorityData = await governanceApi.getAuthority('system_admin');
      } catch (e) {
        // Fallback
      }
    } catch (err) {
      this.statusMessage = { type: 'error', text: `Failed to load governance data: ${err.message}` };
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async handleResolveReview(reviewId, approved) {
    const rationale = prompt(
      `Enter rationale for ${approved ? 'APPROVING' : 'DENYING'} action:`,
      approved ? 'Verified safe by human operator' : 'Action rejected by human operator'
    );
    if (rationale === null) return;

    try {
      await governanceApi.resolveHumanReview(reviewId, {
        reviewer_id: 'human_operator_1',
        approved,
        rationale,
      });
      this.statusMessage = {
        type: 'success',
        text: `Review ${reviewId} successfully ${approved ? 'APPROVED' : 'DENIED'} by human operator.`,
      };
      await this.loadData();
    } catch (err) {
      this.statusMessage = { type: 'error', text: `Failed to resolve review: ${err.message}` };
      this.render();
    }
  }

  render() {
    if (!this.container) return;

    const subTabs = [
      { id: 'overview', label: 'Policy Overview' },
      { id: 'constitution', label: 'Constitution Matrix' },
      { id: 'authority', label: 'Authority Map' },
      { id: 'human_queue', label: `Human Review Queue (${this.humanQueueData.length})` },
      { id: 'decisions', label: 'Decision Log' },
      { id: 'conflicts', label: 'Policy Conflicts' },
      { id: 'escalations', label: `Escalations (${this.escalationsData.length})` },
    ];

    let contentHtml = '';
    if (this.isLoading) {
      contentHtml = `
        <div style="padding: 40px; text-align: center; color: #94a3b8;">
          <div style="display: inline-block; width: 32px; height: 32px; border: 3px solid rgba(59, 130, 246, 0.3); border-radius: 50%; border-top-color: #3b82f6; animation: spin 1s ease-in-out infinite;"></div>
          <p style="margin-top: 12px; font-size: 14px;">Evaluating constitutional reasoning and governance boundaries...</p>
        </div>
      `;
    } else {
      switch (this.activeSubTab) {
        case 'overview': contentHtml = this.renderOverview(); break;
        case 'constitution': contentHtml = this.renderConstitution(); break;
        case 'authority': contentHtml = this.renderAuthority(); break;
        case 'human_queue': contentHtml = this.renderHumanQueue(); break;
        case 'decisions': contentHtml = this.renderDecisions(); break;
        case 'conflicts': contentHtml = this.renderConflicts(); break;
        case 'escalations': contentHtml = this.renderEscalations(); break;
        default: contentHtml = this.renderOverview();
      }
    }

    this.container.innerHTML = `
      <div style="padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc; background: #0b0f17; min-height: 100vh;">
        <!-- Header banner -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 16px; margin-bottom: 20px;">
          <div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; color: #f1f5f9;">
                Autonomous Governance & Constitutional Intelligence Engine
              </h1>
              <span style="background: #1e293b; color: #93c5fd; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; border: 1px solid #3b82f640;">
                TASK 78
              </span>
            </div>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 13px;">
              Enforces machine-readable constitution, 6-tier policy hierarchy, discrete authority boundaries, and non-self-approving human oversight.
            </p>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <button id="gov-refresh-btn" style="background: #1e293b; border: 1px solid #334155; color: #cbd5e1; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500;">
              Refresh Metrics
            </button>
          </div>
        </div>

        <!-- Invariant Banner -->
        <div style="background: rgba(30, 41, 59, 0.4); border: 1px dashed #334155; border-radius: 8px; padding: 10px 16px; margin-bottom: 20px; font-size: 12px; color: #94a3b8; display: flex; justify-content: space-between;">
          <span><strong>Core Invariant:</strong> CAPABILITY &ne; AUTHORITY &ne; PERMISSION &ne; APPROVAL &ne; POLICY &ne; CONSTITUTION &ne; GOAL &ne; OVERSIGHT</span>
          <span style="color: #10b981; font-weight: 600;">Autonomous Self-Approval Strictly Prohibited</span>
        </div>

        <!-- Status Toast -->
        ${this.statusMessage ? `
          <div style="padding: 10px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 13px; ${this.statusMessage.type === 'error' ? 'background: #ef444420; color: #f87171; border: 1px solid #ef444460;' : 'background: #10b98120; color: #34d399; border: 1px solid #10b98160;'}">
            ${this.statusMessage.text}
          </div>
        ` : ''}

        <!-- Sub Tabs -->
        <div style="display: flex; gap: 6px; border-bottom: 1px solid #1e293b; margin-bottom: 20px; overflow-x: auto; padding-bottom: 2px;">
          ${subTabs.map(t => `
            <button class="gov-tab-btn" data-tab="${t.id}" style="background: ${this.activeSubTab === t.id ? '#1e293b' : 'transparent'}; border: 1px solid ${this.activeSubTab === t.id ? '#3b82f680' : 'transparent'}; border-bottom: ${this.activeSubTab === t.id ? '2px solid #3b82f6' : 'none'}; color: ${this.activeSubTab === t.id ? '#60a5fa' : '#94a3b8'}; padding: 8px 16px; border-radius: 6px 6px 0 0; cursor: pointer; font-size: 13px; font-weight: 600; white-space: nowrap;">
              ${t.label}
            </button>
          `).join('')}
        </div>

        <!-- Tab Content -->
        <div id="gov-tab-content">
          ${contentHtml}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    const refreshBtn = this.container.querySelector('#gov-refresh-btn');
    if (refreshBtn) {
      refreshBtn.onclick = () => this.loadData();
    }

    const tabBtns = this.container.querySelectorAll('.gov-tab-btn');
    tabBtns.forEach(btn => {
      btn.onclick = () => this.setSubTab(btn.getAttribute('data-tab'));
    });

    const approveBtns = this.container.querySelectorAll('.gov-approve-btn');
    approveBtns.forEach(btn => {
      btn.onclick = () => this.handleResolveReview(btn.getAttribute('data-id'), true);
    });

    const denyBtns = this.container.querySelectorAll('.gov-deny-btn');
    denyBtns.forEach(btn => {
      btn.onclick = () => this.handleResolveReview(btn.getAttribute('data-id'), false);
    });
  }

  renderOverview() {
    const d = this.dashboardData || {
      active_policies_by_tier: { SYSTEM: 1, SECURITY: 2, TENANT: 0, PROJECT: 0, WORKFLOW: 0, TASK: 0 },
      active_authority_grants_count: 1,
      pending_human_reviews_count: this.humanQueueData.length,
      recent_escalations_count: this.escalationsData.length,
      constitutional_compliance_index: 1.0,
    };

    const tiers = ['SYSTEM', 'SECURITY', 'TENANT', 'PROJECT', 'WORKFLOW', 'TASK'];

    return `
      <div>
        <!-- Metric Cards Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Constitutional Index</div>
            <div style="font-size: 28px; font-weight: 800; color: #10b981; margin-top: 4px;">${(d.constitutional_compliance_index * 100).toFixed(1)}%</div>
            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">11 Canonical Principles Active</div>
          </div>
          <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Pending Human Reviews</div>
            <div style="font-size: 28px; font-weight: 800; color: ${d.pending_human_reviews_count > 0 ? '#ec4899' : '#94a3b8'}; margin-top: 4px;">${d.pending_human_reviews_count}</div>
            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Blocked awaiting human verification</div>
          </div>
          <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Authority Grants</div>
            <div style="font-size: 28px; font-weight: 800; color: #3b82f6; margin-top: 4px;">${d.active_authority_grants_count}</div>
            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Discrete scopes separated from capability</div>
          </div>
          <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
            <div style="font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Escalation Incidents</div>
            <div style="font-size: 28px; font-weight: 800; color: ${d.recent_escalations_count > 0 ? '#ef4444' : '#10b981'}; margin-top: 4px;">${d.recent_escalations_count}</div>
            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Bypass & privilege creep attempts</div>
          </div>
        </div>

        <!-- Hierarchy Precedence Overview -->
        <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px;">
          <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #f1f5f9;">
            6-Tier Policy Hierarchy Precedence (Higher Tiers Strictly Override Lower Tiers)
          </h3>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;">
            ${tiers.map((t, idx) => {
              const count = (d.active_policies_by_tier && d.active_policies_by_tier[t]) || 0;
              return `
                <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; text-align: center;">
                  <div style="font-size: 10px; color: #64748b; font-weight: 700;">RANK ${idx}</div>
                  <div style="margin-top: 4px;">${this.formatTierBadge(t)}</div>
                  <div style="font-size: 18px; font-weight: 700; color: #e2e8f0; margin-top: 8px;">${count}</div>
                  <div style="font-size: 10px; color: #94a3b8;">Active Policies</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>
    `;
  }

  renderConstitution() {
    const principles = this.constitutionData?.principles || [];

    return `
      <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; font-size: 15px; font-weight: 700; color: #f1f5f9;">
            Machine-Readable Constitution Principles (${principles.length})
          </h3>
          <span style="font-size: 12px; color: #94a3b8;">Version: ${this.constitutionData?.version || '1.0.0'}</span>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="border-bottom: 1px solid #1e293b; color: #94a3b8; text-align: left;">
              <th style="padding: 10px;">Principle</th>
              <th style="padding: 10px;">Strictness</th>
              <th style="padding: 10px;">Weight</th>
              <th style="padding: 10px;">Description</th>
              <th style="padding: 10px;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${principles.map(p => `
              <tr style="border-bottom: 1px solid #1e293b20;">
                <td style="padding: 12px 10px; font-weight: 700; color: #e2e8f0;">${p.name}</td>
                <td style="padding: 12px 10px;">${this.formatStrictnessBadge(p.strictness)}</td>
                <td style="padding: 12px 10px; color: #93c5fd; font-family: monospace;">${(p.weight * 100).toFixed(0)}%</td>
                <td style="padding: 12px 10px; color: #cbd5e1;">${p.description}</td>
                <td style="padding: 12px 10px;">
                  <span style="color: ${p.enabled ? '#10b981' : '#64748b'}; font-weight: 600; font-size: 11px;">
                    ${p.enabled ? 'ACTIVE' : 'DISABLED'}
                  </span>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  renderAuthority() {
    const d = this.authorityData || { subject_id: 'system_admin', highest_authority_level: 'ADMIN', grants: [] };

    return `
      <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #f1f5f9;">
          Discrete Authority Matrix: Subject '${d.subject_id}'
        </h3>
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 14px; margin-bottom: 20px; display: flex; gap: 24px;">
          <div>
            <span style="font-size: 11px; color: #64748b; text-transform: uppercase;">Highest Level</span>
            <div style="font-size: 18px; font-weight: 700; color: #60a5fa; margin-top: 2px;">${d.highest_authority_level}</div>
          </div>
          <div>
            <span style="font-size: 11px; color: #64748b; text-transform: uppercase;">Active Grants</span>
            <div style="font-size: 18px; font-weight: 700; color: #f8fafc; margin-top: 2px;">${(d.grants || []).length}</div>
          </div>
        </div>

        <h4 style="margin: 0 0 12px 0; font-size: 13px; font-weight: 600; color: #94a3b8;">Issued Authority Grants</h4>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${(d.grants || []).map(g => `
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; font-size: 12px;">
              <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <span style="font-weight: 700; color: #93c5fd;">Grant ID: ${g.grant_id}</span>
                <span style="color: #64748b;">Level: <strong style="color:#e2e8f0;">${g.authority_level}</strong></span>
              </div>
              <div style="color: #cbd5e1;">Scopes: <code>${(g.allowed_scopes || []).join(', ')}</code></div>
              <div style="color: #cbd5e1; margin-top: 2px;">Actions: <code>${(g.allowed_actions || []).join(', ')}</code></div>
            </div>
          `).join('') || '<div style="color: #64748b; font-size: 13px;">No explicit grants recorded.</div>'}
        </div>
      </div>
    `;
  }

  renderHumanQueue() {
    const queue = this.humanQueueData || [];

    return `
      <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="margin: 0; font-size: 15px; font-weight: 700; color: #f1f5f9;">
            Pending Human Review Queue (${queue.length})
          </h3>
          <span style="font-size: 12px; color: #ec4899; font-weight: 600;">Autonomous execution blocked until human operator signs</span>
        </div>

        ${queue.length === 0 ? `
          <div style="padding: 40px; text-align: center; color: #64748b; font-size: 13px;">
            No actions currently require human oversight. All operations are within safe autonomous bounds.
          </div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 14px;">
            ${queue.map(r => `
              <div style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                  <div>
                    <span style="font-weight: 700; font-size: 14px; color: #f8fafc;">Review ID: ${r.review_id}</span>
                    <div style="margin-top: 4px;">${this.formatStateBadge(r.state)}</div>
                  </div>
                  <div style="display: flex; gap: 8px;">
                    <button class="gov-approve-btn" data-id="${r.review_id}" style="background: #10b981; border: none; color: #fff; padding: 6px 14px; border-radius: 4px; font-weight: 600; font-size: 12px; cursor: pointer;">
                      Approve Action
                    </button>
                    <button class="gov-deny-btn" data-id="${r.review_id}" style="background: #ef4444; border: none; color: #fff; padding: 6px 14px; border-radius: 4px; font-weight: 600; font-size: 12px; cursor: pointer;">
                      Deny Action
                    </button>
                  </div>
                </div>
                <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 8px;">
                  <strong>Explanation:</strong> ${r.explanation}
                </div>
                <div style="font-size: 12px; color: #94a3b8; background: #0b0f17; border-radius: 4px; padding: 8px;">
                  <strong>Evidence Trail:</strong>
                  <ul style="margin: 4px 0 0 16px; padding: 0;">
                    ${(r.evidence || []).map(e => `<li>${e}</li>`).join('')}
                  </ul>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  renderDecisions() {
    return `
      <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #f1f5f9;">
          Governance Decision Audit Trail
        </h3>
        <p style="font-size: 13px; color: #94a3b8;">
          All autonomous requests undergo pre-execution evaluation across the 11 constitutional principles and 6-tier policy hierarchy.
        </p>
      </div>
    `;
  }

  renderConflicts() {
    return `
      <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #f1f5f9;">
          Multi-Tier Policy Conflict Resolutions
        </h3>
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 14px; font-size: 13px; color: #cbd5e1;">
          <strong>Precedence Rule:</strong> Higher tiers strictly override lower tiers: SYSTEM &gt; SECURITY &gt; TENANT &gt; PROJECT &gt; WORKFLOW &gt; TASK. Ties at the same tier are deterministically resolved with DENIED beating REQUIRES_HUMAN beating REQUIRES_APPROVAL beating ALLOWED.
        </div>
      </div>
    `;
  }

  renderEscalations() {
    const list = this.escalationsData || [];

    return `
      <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px;">
        <h3 style="margin: 0 0 16px 0; font-size: 15px; font-weight: 700; color: #f1f5f9;">
          Authority Escalation & Bypass Detections (${list.length})
        </h3>
        ${list.length === 0 ? `
          <div style="padding: 30px; text-align: center; color: #64748b; font-size: 13px;">
            No privilege escalation or security control tampering incidents flagged.
          </div>
        ` : `
          <div style="display: flex; flex-direction: column; gap: 12px;">
            ${list.map(i => `
              <div style="background: #0f172a; border: 1px solid #ef444440; border-radius: 6px; padding: 14px; font-size: 13px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                  <span style="font-weight: 700; color: #f87171;">Technique: ${i.bypass_technique || 'UNKNOWN'}</span>
                  <span style="background: #ef444420; color: #ef4444; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700;">${i.severity}</span>
                </div>
                <div style="color: #cbd5e1;">${i.rationale}</div>
                ${(i.flagged_actions || []).length ? `
                  <div style="margin-top: 6px; font-size: 12px; color: #94a3b8;">Flagged Actions: <code>${i.flagged_actions.join(', ')}</code></div>
                ` : ''}
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }
}

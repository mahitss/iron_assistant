/**
 * Task 116: Autonomous Claim Verification, Source Integrity & Evidence Provenance Center
 * Section 40: Comprehensive Verification Center covering:
 * 1. Verification Inbox
 * 2. Verification Detail
 * 3. Claim Breakdown
 * 4. Evidence Explorer
 * 5. Provenance Graph
 * 6. Source History
 * 7. Corroboration View
 * 8. Contradiction View
 * 9. Verification Timeline
 * 10. Verification Gaps
 * 11. Revalidation Panel
 *
 * Hard Invariants:
 * - SOURCE != DOCUMENT != OBSERVATION != EXTRACTED EVIDENCE != CLAIM != INTERPRETATION != INFERENCE != VERIFICATION != BELIEF != TRUTH != AUTHORIZATION.
 * - Never fabricate certainty.
 */

import { verificationsApi } from '../../lib/api/endpoints.js';

export class VerificationCenterView {
  constructor(containerOrOptions = 'main-content') {
    if (typeof containerOrOptions === 'string') {
      this.containerId = containerOrOptions;
      this.container = null;
    } else if (containerOrOptions && containerOrOptions.container) {
      this.container = containerOrOptions.container;
      this.containerId = this.container.id || 'main-content-viewport';
    } else {
      this.containerId = 'main-content-viewport';
      this.container = null;
    }

    this.activeTab = 'inbox'; // inbox, detail, claims, evidence, provenance, corroboration, contradictions, gaps, timeline
    this.cases = [];
    this.selectedCaseId = null;
    this.selectedCase = null;
    this.selectedResult = null;
    this.explanation = null;
    this.loading = false;
  }

  async init() {
    await this.render();
    await this.loadCases();
  }

  async render() {
    const container = this.container || document.getElementById(this.containerId) || document.getElementById('main-content-viewport');
    if (!container) return;

    container.innerHTML = `
      <div class="verification-center" style="padding: 24px; max-width: 1500px; margin: 0 auto; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <h1 style="font-size: 26px; font-weight: 700; color: #f8fafc; margin: 0;">Claim Verification & Provenance Center</h1>
              <span style="background: rgba(168, 85, 247, 0.15); color: #c084fc; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; border: 1px solid rgba(168, 85, 247, 0.3);">Task 116 Engine</span>
            </div>
            <p style="color: #94a3b8; font-size: 14px; margin: 6px 0 0 0;">
              Production-grade claim decomposition, source integrity verification, cryptographic content hashing, copy detection, and provenance lineage audit.
            </p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="btn-new-verification" style="background: #7c3aed; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px;">
              + Verify New Claim
            </button>
            <button id="btn-refresh-verifications" style="background: #1e293b; color: #cbd5e1; border: 1px solid #475569; padding: 8px 14px; border-radius: 6px; cursor: pointer;">
              ↻ Refresh
            </button>
          </div>
        </div>

        <!-- Invariant Guarantee Banner -->
        <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid #1e293b; border-left: 4px solid #a855f7; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 12px; color: #94a3b8; display: flex; gap: 20px; flex-wrap: wrap;">
          <span>⚖️ <strong>VERIFICATION ≠ ABSOLUTE TRUTH</strong></span>
          <span>🔗 <strong>SOURCE ≠ DOCUMENT ≠ CLAIM</strong></span>
          <span>📋 <strong>COPIED SOURCES ≠ INDEPENDENT SUPPORT</strong></span>
          <span>⚡ <strong>EMERGENCY STOP IS ABSOLUTE</strong></span>
          <span>🛡️ <strong>EXTERNAL CONTENT UNTRUSTED</strong></span>
        </div>

        <!-- Navigation Tabs -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid #334155; margin-bottom: 20px; overflow-x: auto; padding-bottom: 4px;">
          ${this._renderTabBtn('inbox', '📥 Inbox / Cases')}
          ${this._renderTabBtn('detail', '🔍 Case Detail')}
          ${this._renderTabBtn('claims', '🧩 Claim Breakdown')}
          ${this._renderTabBtn('evidence', '📑 Evidence Explorer')}
          ${this._renderTabBtn('provenance', '🕸️ Provenance Graph')}
          ${this._renderTabBtn('corroboration', '🤝 Corroboration & Independence')}
          ${this._renderTabBtn('contradictions', '⚡ Contradictions')}
          ${this._renderTabBtn('gaps', '❓ Verification Gaps')}
          ${this._renderTabBtn('timeline', '⏱️ Timeline & Audit')}
        </div>

        <!-- Dynamic Content Body -->
        <div id="vc-body-container" style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; min-height: 480px;">
          <div style="display: flex; justify-content: center; align-items: center; height: 300px; color: #64748b;">
            Loading Verification Center data...
          </div>
        </div>
      </div>
    `;

    this._bindEvents();
  }

  _renderTabBtn(tabId, label) {
    const isActive = this.activeTab === tabId;
    return `
      <button class="vc-tab-btn" data-tab="${tabId}" style="background: ${isActive ? '#7c3aed' : 'transparent'}; color: ${isActive ? '#ffffff' : '#94a3b8'}; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.15s ease;">
        ${label}
      </button>
    `;
  }

  _bindEvents() {
    const container = this.container || document.getElementById(this.containerId) || document.getElementById('main-content-viewport');
    if (!container) return;

    container.querySelectorAll('.vc-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.dataset.tab;
        this.activeTab = tab;
        this.render();
        this._renderCurrentTab();
      });
    });

    const refreshBtn = container.querySelector('#btn-refresh-verifications');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadCases());
    }

    const newBtn = container.querySelector('#btn-new-verification');
    if (newBtn) {
      newBtn.addEventListener('click', () => this._showNewVerificationModal());
    }
  }

  async loadCases() {
    try {
      this.loading = true;
      const res = await verificationsApi.list();
      this.cases = Array.isArray(res) ? res : [];
      if (this.cases.length > 0 && !this.selectedCaseId) {
        this.selectedCaseId = this.cases[0].case_id;
      }
      if (this.selectedCaseId) {
        await this.loadCaseDetails(this.selectedCaseId);
      }
      this._renderCurrentTab();
    } catch (err) {
      console.error('Failed to load verification cases:', err);
    } finally {
      this.loading = false;
    }
  }

  async loadCaseDetails(caseId) {
    try {
      this.selectedCaseId = caseId;
      const data = await verificationsApi.get(caseId);
      this.selectedCase = data.case;
      this.selectedResult = data.result;
      try {
        this.explanation = await verificationsApi.getExplanation(caseId);
      } catch {
        this.explanation = null;
      }
    } catch (err) {
      console.error(`Failed to load case ${caseId}:`, err);
    }
  }

  _renderCurrentTab() {
    const body = document.getElementById('vc-body-container');
    if (!body) return;

    switch (this.activeTab) {
      case 'inbox':
        this._renderInbox(body);
        break;
      case 'detail':
        this._renderDetail(body);
        break;
      case 'claims':
        this._renderClaims(body);
        break;
      case 'evidence':
        this._renderEvidence(body);
        break;
      case 'provenance':
        this._renderProvenance(body);
        break;
      case 'corroboration':
        this._renderCorroboration(body);
        break;
      case 'contradictions':
        this._renderContradictions(body);
        break;
      case 'gaps':
        this._renderGaps(body);
        break;
      case 'timeline':
        this._renderTimeline(body);
        break;
      default:
        this._renderInbox(body);
    }
  }

  _renderInbox(container) {
    if (!this.cases.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 60px 20px;">
          <div style="font-size: 40px; margin-bottom: 12px;">📥</div>
          <h3 style="color: #f8fafc; font-size: 18px; margin: 0 0 8px 0;">No Verification Cases Yet</h3>
          <p style="color: #64748b; font-size: 14px; max-width: 480px; margin: 0 auto 20px auto;">
            Initiate a structured verification case to analyze claim breakdown, source integrity, copy detection, and provenance lineage.
          </p>
          <button id="btn-inbox-new" style="background: #7c3aed; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; cursor: pointer;">
            + Verify First Claim
          </button>
        </div>
      `;
      const btn = container.querySelector('#btn-inbox-new');
      if (btn) btn.addEventListener('click', () => this._showNewVerificationModal());
      return;
    }

    const rows = this.cases.map(c => {
      const isSelected = c.case_id === this.selectedCaseId;
      const statusColor = this._getStatusColor(c.status);
      const createdStr = new Date(c.created_at).toLocaleString();

      return `
        <tr class="vc-row" data-id="${c.case_id}" style="cursor: pointer; background: ${isSelected ? 'rgba(124, 58, 237, 0.12)' : 'transparent'}; border-bottom: 1px solid #1e293b; transition: background 0.15s ease;">
          <td style="padding: 12px 16px; font-family: monospace; color: #a855f7; font-size: 13px;">${c.case_id}</td>
          <td style="padding: 12px 16px; color: #f8fafc; font-weight: 500;">${c.title}</td>
          <td style="padding: 12px 16px;">
            <span style="background: ${statusColor.bg}; color: ${statusColor.text}; border: 1px solid ${statusColor.border}; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">
              ${c.status}
            </span>
          </td>
          <td style="padding: 12px 16px; color: #94a3b8; font-size: 13px;">${createdStr}</td>
          <td style="padding: 12px 16px; text-align: right;">
            <button class="btn-select-case" data-id="${c.case_id}" style="background: #334155; color: #cbd5e1; border: none; padding: 5px 12px; border-radius: 4px; font-size: 12px; cursor: pointer;">
              Inspect →
            </button>
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0;">Active Verification Cases (${this.cases.length})</h2>
          <span style="font-size: 12px; color: #64748b;">Click a case to inspect full evidence lineage</span>
        </div>
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <thead>
            <tr style="border-bottom: 1px solid #334155; color: #94a3b8; font-size: 12px; text-transform: uppercase;">
              <th style="padding: 10px 16px;">Case ID</th>
              <th style="padding: 10px 16px;">Title / Claim</th>
              <th style="padding: 10px 16px;">Status</th>
              <th style="padding: 10px 16px;">Created At</th>
              <th style="padding: 10px 16px; text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;

    container.querySelectorAll('.vc-row, .btn-select-case').forEach(el => {
      el.addEventListener('click', async (e) => {
        const cid = el.dataset.id;
        await this.loadCaseDetails(cid);
        this.activeTab = 'detail';
        this.render();
        this._renderCurrentTab();
      });
    });
  }

  _renderDetail(container) {
    if (!this.selectedCase) {
      container.innerHTML = `<div style="color: #64748b; padding: 20px;">No case selected. Please select a case from the Inbox.</div>`;
      return;
    }

    const c = this.selectedCase;
    const r = this.selectedResult;
    const sc = this._getStatusColor(c.status);

    container.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
          <div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <h2 style="font-size: 20px; font-weight: 600; color: #f8fafc; margin: 0;">${c.title}</h2>
              <span style="background: ${sc.bg}; color: ${sc.text}; border: 1px solid ${sc.border}; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 700;">
                ${c.status}
              </span>
            </div>
            <p style="color: #94a3b8; font-size: 13px; margin: 6px 0 0 0; font-family: monospace;">Case ID: ${c.case_id} | Claim ID: ${c.claim_id}</p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="btn-revalidate-case" style="background: #2563eb; color: white; border: none; padding: 6px 14px; border-radius: 4px; font-size: 12px; cursor: pointer;">
              🔄 Revalidate Case
            </button>
            <button id="btn-cancel-case" style="background: #dc2626; color: white; border: none; padding: 6px 14px; border-radius: 4px; font-size: 12px; cursor: pointer;">
              🛑 Cancel Case
            </button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
          <!-- Left Column: Primary Justification and Lineage Summary -->
          <div style="background: #1e293b; padding: 18px; border-radius: 6px; border: 1px solid #334155;">
            <h3 style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 0.5px;">Authoritative Justification</h3>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">
              ${r ? r.justification : (c.resolution_summary || 'Verification in progress...')}
            </p>

            <h3 style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 16px 0 10px 0; text-transform: uppercase; letter-spacing: 0.5px;">Scope Constraints</h3>
            <pre style="background: #0f172a; padding: 12px; border-radius: 4px; font-size: 12px; color: #94a3b8; margin: 0; overflow-x: auto;">${JSON.stringify(c.scope, null, 2)}</pre>
          </div>

          <!-- Right Column: Verification Metadata & Freshness -->
          <div style="background: #1e293b; padding: 18px; border-radius: 6px; border: 1px solid #334155;">
            <h3 style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0 0 14px 0; text-transform: uppercase; letter-spacing: 0.5px;">Audit Metadata</h3>
            
            <div style="margin-bottom: 10px;">
              <span style="color: #94a3b8; font-size: 12px; display: block;">Reproducibility:</span>
              <strong style="color: #38bdf8; font-size: 13px;">${r ? r.reproducibility_status : 'PENDING'}</strong>
            </div>

            <div style="margin-bottom: 10px;">
              <span style="color: #94a3b8; font-size: 12px; display: block;">Evidence Items:</span>
              <strong style="color: #f8fafc; font-size: 13px;">${r ? r.evidence_ids.length : 0} artifacts attached</strong>
            </div>

            <div style="margin-bottom: 10px;">
              <span style="color: #94a3b8; font-size: 12px; display: block;">Contradictions:</span>
              <strong style="color: ${r && r.contradiction_ids.length > 0 ? '#ef4444' : '#22c55e'}; font-size: 13px;">
                ${r ? r.contradiction_ids.length : 0} detected
              </strong>
            </div>

            <div style="margin-bottom: 10px;">
              <span style="color: #94a3b8; font-size: 12px; display: block;">Verified At:</span>
              <span style="color: #cbd5e1; font-size: 12px;">${r ? new Date(r.verified_at).toLocaleString() : 'N/A'}</span>
            </div>

            <div>
              <span style="color: #94a3b8; font-size: 12px; display: block;">Expires At:</span>
              <span style="color: #cbd5e1; font-size: 12px;">${r && r.expires_at ? new Date(r.expires_at).toLocaleString() : 'Never / Scope-bounded'}</span>
            </div>
          </div>
        </div>
      </div>
    `;

    const revalBtn = container.querySelector('#btn-revalidate-case');
    if (revalBtn) {
      revalBtn.addEventListener('click', async () => {
        await verificationsApi.revalidate(c.case_id);
        await this.loadCaseDetails(c.case_id);
        this._renderCurrentTab();
      });
    }

    const cancelBtn = container.querySelector('#btn-cancel-case');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', async () => {
        await verificationsApi.cancel(c.case_id);
        await this.loadCaseDetails(c.case_id);
        this._renderCurrentTab();
      });
    }
  }

  _renderClaims(container) {
    if (!this.explanation || !this.explanation.claim) {
      container.innerHTML = `<div style="color: #64748b; padding: 20px;">No decomposed claim breakdown available for this case.</div>`;
      return;
    }

    const cl = this.explanation.claim;
    const frags = cl.fragments || [];

    const fragCards = frags.map((f, i) => `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 14px; margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-size: 12px; font-weight: 700; color: #a855f7; font-family: monospace;">FRAGMENT #${i + 1} (${f.fragment_type})</span>
          <span style="font-size: 11px; color: #64748b; font-family: monospace;">${f.fragment_id}</span>
        </div>
        <div style="font-size: 14px; color: #f8fafc; margin-bottom: 8px; font-weight: 500;">
          "${f.statement}"
        </div>
        <div style="display: flex; gap: 16px; font-size: 12px; color: #94a3b8;">
          <span>Subject: <strong style="color: #cbd5e1;">${f.subject || 'N/A'}</strong></span>
          <span>Predicate: <strong style="color: #cbd5e1;">${f.predicate || 'N/A'}</strong></span>
          <span>Object: <strong style="color: #cbd5e1;">${f.object_val || 'N/A'}</strong></span>
        </div>
      </div>
    `).join('');

    container.innerHTML = `
      <div>
        <div style="margin-bottom: 16px;">
          <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0 0 6px 0;">Canonical Claim Decomposition</h2>
          <p style="color: #94a3b8; font-size: 14px; margin: 0;">
            Original Statement: <em style="color: #e2e8f0;">"${cl.text}"</em>
          </p>
        </div>
        <div style="margin-top: 16px;">
          <h3 style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0 0 12px 0;">Decomposed Claim Fragments (${frags.length})</h3>
          ${fragCards || '<div style="color: #64748b;">No sub-fragments generated.</div>'}
        </div>
      </div>
    `;
  }

  _renderEvidence(container) {
    if (!this.explanation || !this.explanation.supporting_evidence) {
      container.innerHTML = `<div style="color: #64748b; padding: 20px;">No evidence artifacts attached to this case.</div>`;
      return;
    }

    const arts = this.explanation.supporting_evidence;
    const cards = arts.map((a, i) => `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 16px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 13px; font-weight: 700; color: #38bdf8;">Artifact #${i + 1}</span>
            <span style="font-size: 11px; background: rgba(56, 189, 248, 0.1); color: #38bdf8; padding: 2px 6px; border-radius: 4px;">${a.direct_status ? 'DIRECT' : 'INDIRECT'}</span>
          </div>
          <span style="font-family: monospace; font-size: 11px; color: #94a3b8;">${a.evidence_id}</span>
        </div>
        <div style="background: #0f172a; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #cbd5e1; margin-bottom: 10px; border-left: 3px solid #38bdf8;">
          ${a.content_text}
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; font-family: monospace;">
          <span>Source: ${a.source_id}</span>
          <span>SHA-256: ${a.content_hash.slice(0, 16)}...</span>
        </div>
      </div>
    `).join('');

    container.innerHTML = `
      <div>
        <div style="margin-bottom: 16px;">
          <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0;">Extracted Evidence Artifacts (${arts.length})</h2>
          <span style="color: #94a3b8; font-size: 13px;">Exact content hashes and lineage tracking</span>
        </div>
        ${cards || '<div style="color: #64748b;">No evidence artifacts found.</div>'}
      </div>
    `;
  }

  _renderProvenance(container) {
    if (!this.explanation || !this.explanation.provenance_links) {
      container.innerHTML = `<div style="color: #64748b; padding: 20px;">No provenance DAG data available.</div>`;
      return;
    }

    const links = this.explanation.provenance_links;
    const rows = links.map(l => `
      <tr style="border-bottom: 1px solid #1e293b;">
        <td style="padding: 10px 14px; font-family: monospace; color: #a855f7; font-size: 12px;">${l.from_type}:${l.from_entity_id}</td>
        <td style="padding: 10px 14px; font-weight: 600; color: #38bdf8; font-size: 12px;">--[ ${l.predicate} ]--></td>
        <td style="padding: 10px 14px; font-family: monospace; color: #f8fafc; font-size: 12px;">${l.to_type}:${l.to_entity_id}</td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div>
        <div style="margin-bottom: 16px;">
          <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0;">W3C-PROV Directed Provenance Links (${links.length})</h2>
          <span style="color: #94a3b8; font-size: 13px;">Full transformation and derivation lineage graph</span>
        </div>
        <table style="width: 100%; border-collapse: collapse; text-align: left; background: #1e293b; border-radius: 6px; overflow: hidden;">
          <thead>
            <tr style="border-bottom: 1px solid #334155; color: #94a3b8; font-size: 11px; text-transform: uppercase;">
              <th style="padding: 8px 14px;">Origin / From</th>
              <th style="padding: 8px 14px;">Predicate</th>
              <th style="padding: 8px 14px;">Destination / To</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  _renderCorroboration(container) {
    if (!this.explanation) {
      container.innerHTML = `<div style="color: #64748b; padding: 20px;">No corroboration data available.</div>`;
      return;
    }

    const cor = this.explanation.corroboration || {};
    const ind = this.explanation.independence || {};

    container.innerHTML = `
      <div>
        <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0 0 16px 0;">Corroboration & True Source Independence</h2>
        
        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 18px; margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
            <span style="font-size: 14px; font-weight: 600; color: #e2e8f0;">Corroboration Classification</span>
            <strong style="color: #a855f7;">${cor.corroboration_type || 'UNKNOWN'}</strong>
          </div>
          <p style="color: #cbd5e1; font-size: 13px; line-height: 1.5; margin: 0 0 12px 0;">
            ${cor.summary || 'No corroboration summary.'}
          </p>
          <div style="display: flex; gap: 20px; font-size: 12px; color: #94a3b8;">
            <span>Semantic Alignment: <strong style="color: #38bdf8;">${(cor.semantic_alignment || 0).toFixed(2)}</strong></span>
            <span>Temporal Alignment: <strong style="color: #38bdf8;">${(cor.temporal_alignment || 0).toFixed(2)}</strong></span>
            <span>Independence Score: <strong style="color: #38bdf8;">${(ind.independence_score || 0).toFixed(2)}</strong></span>
          </div>
        </div>

        <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 18px;">
          <h3 style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0 0 10px 0;">Independence Assessment Details</h3>
          <p style="color: #94a3b8; font-size: 13px; margin: 0 0 10px 0;">
            ${ind.justification || 'No explicit dependency or citation cycle detected.'}
          </p>
          <div style="font-size: 12px; color: #64748b;">
            Cycles Detected: ${ind.cycles && ind.cycles.length > 0 ? `<span style="color: #ef4444; font-weight: 700;">YES (${ind.cycles.length})</span>` : '<span style="color: #22c55e;">NONE</span>'}
          </div>
        </div>
      </div>
    `;
  }

  _renderContradictions(container) {
    if (!this.explanation || !this.explanation.contradictions) {
      container.innerHTML = `<div style="color: #64748b; padding: 20px;">No contradictions data available.</div>`;
      return;
    }

    const contras = this.explanation.contradictions;
    if (!contras.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: #22c55e;">
          <div style="font-size: 32px; margin-bottom: 8px;">✓</div>
          <h3 style="margin: 0 0 4px 0; font-size: 16px; color: #f8fafc;">Zero Contradictions Detected</h3>
          <p style="color: #64748b; font-size: 13px; margin: 0;">Supporting evidence items are internally consistent across state and numeric dimensions.</p>
        </div>
      `;
      return;
    }

    const cards = contras.map(c => `
      <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 16px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="color: #ef4444; font-size: 14px;">${c.contradiction_type}</strong>
          <span style="font-size: 11px; background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 2px 6px; border-radius: 4px;">Severity: ${c.severity}</span>
        </div>
        <p style="color: #f8fafc; font-size: 13px; margin: 0 0 8px 0;">${c.description}</p>
        <div style="font-family: monospace; font-size: 11px; color: #94a3b8;">
          Conflicting Evidence: ${c.evidence_a_id} vs ${c.evidence_b_id}
        </div>
      </div>
    `).join('');

    container.innerHTML = `
      <div>
        <div style="margin-bottom: 16px;">
          <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0;">Detected Contradictions (${contras.length})</h2>
          <span style="color: #ef4444; font-size: 13px;">Contradictions are first-class conflicts routed to Belief/Hypothesis arbitration</span>
        </div>
        ${cards}
      </div>
    `;
  }

  _renderGaps(container) {
    if (!this.explanation || !this.explanation.unresolved_gaps) {
      container.innerHTML = `<div style="color: #64748b; padding: 20px;">No verification gaps registered.</div>`;
      return;
    }

    const gaps = this.explanation.unresolved_gaps;
    if (!gaps.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: #22c55e;">
          <div style="font-size: 32px; margin-bottom: 8px;">✓</div>
          <h3 style="margin: 0 0 4px 0; font-size: 16px; color: #f8fafc;">No Information Gaps</h3>
          <p style="color: #64748b; font-size: 13px; margin: 0;">All expected evidence types and claim fragments have supporting observations.</p>
        </div>
      `;
      return;
    }

    const cards = gaps.map(g => `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 16px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="color: #f59e0b; font-size: 14px;">Missing Evidence: ${g.missing_evidence_desc}</strong>
          <span style="font-size: 11px; color: #94a3b8;">Urgency: ${(g.urgency * 100).toFixed(0)}%</span>
        </div>
        <p style="color: #cbd5e1; font-size: 13px; margin: 0 0 8px 0;">${g.impact_reason}</p>
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748b;">
          <span>Recommended Acquisition: <strong>${(g.possible_methods || []).join(', ')}</strong></span>
          <span>Info Gain: <strong>${(g.expected_info_gain * 100).toFixed(0)}%</strong></span>
        </div>
      </div>
    `).join('');

    container.innerHTML = `
      <div>
        <div style="margin-bottom: 16px;">
          <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0;">Unresolved Information Gaps (${gaps.length})</h2>
          <span style="color: #94a3b8; font-size: 13px;">Bridges to Task 114 Active Observation for targeted uncertainty reduction</span>
        </div>
        ${cards}
      </div>
    `;
  }

  _renderTimeline(container) {
    if (!this.selectedCaseId) {
      container.innerHTML = `<div style="color: #64748b; padding: 20px;">No case selected.</div>`;
      return;
    }

    container.innerHTML = `<div style="color: #94a3b8; padding: 20px;">Loading timeline events...</div>`;
    verificationsApi.getTimeline(this.selectedCaseId).then(events => {
      if (!events || !events.length) {
        container.innerHTML = `<div style="color: #64748b; padding: 20px;">No timeline events recorded yet.</div>`;
        return;
      }

      const rows = events.map(e => `
        <div style="display: flex; gap: 14px; padding: 10px 0; border-bottom: 1px solid #1e293b;">
          <div style="color: #a855f7; font-family: monospace; font-size: 12px; width: 160px;">${new Date(e.timestamp).toLocaleTimeString()}</div>
          <div style="flex: 1;">
            <strong style="color: #f8fafc; font-size: 13px;">${e.event_type}</strong>
            <span style="color: #64748b; font-size: 11px; margin-left: 8px;">by ${e.actor}</span>
            <pre style="background: #0f172a; padding: 6px 10px; border-radius: 4px; font-size: 11px; color: #94a3b8; margin: 6px 0 0 0;">${JSON.stringify(e.payload)}</pre>
          </div>
        </div>
      `).join('');

      container.innerHTML = `
        <div>
          <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0 0 16px 0;">Append-Only Lifecycle Timeline (${events.length})</h2>
          <div>${rows}</div>
        </div>
      `;
    });
  }

  _showNewVerificationModal() {
    const modalId = 'vc-modal-new-verification';
    let existing = document.getElementById(modalId);
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = modalId;
    modal.style.cssText = `
      position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 1000;
      display: flex; justify-content: center; align-items: center; padding: 20px;
    `;

    modal.innerHTML = `
      <div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; max-width: 600px; width: 100%; padding: 24px; color: #e2e8f0;">
        <h2 style="font-size: 18px; font-weight: 600; color: #f8fafc; margin: 0 0 14px 0;">Initiate Autonomous Claim Verification</h2>
        
        <div style="margin-bottom: 14px;">
          <label style="display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px;">Claim Assertion Text *</label>
          <textarea id="inp-claim-text" rows="3" style="width: 100%; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 8px 12px; border-radius: 4px; font-size: 13px;" placeholder="e.g. The database latency increased after deployment leading to timeout errors."></textarea>
        </div>

        <div style="margin-bottom: 14px;">
          <label style="display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px;">Case Title (Optional)</label>
          <input id="inp-case-title" type="text" style="width: 100%; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 8px 12px; border-radius: 4px; font-size: 13px;" placeholder="e.g. Incident 402 Latency Verification" />
        </div>

        <div style="margin-bottom: 14px;">
          <label style="display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px;">Supporting Evidence (Optional text snippet)</label>
          <textarea id="inp-evidence-text" rows="2" style="width: 100%; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 8px 12px; border-radius: 4px; font-size: 13px;" placeholder="Telemetry shows database p99 latency reached 850ms at 14:02 UTC."></textarea>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
          <button id="btn-modal-cancel" style="background: #334155; color: #cbd5e1; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Cancel</button>
          <button id="btn-modal-submit" style="background: #7c3aed; color: white; border: none; padding: 8px 18px; border-radius: 4px; font-weight: 600; cursor: pointer;">Start Verification</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('#btn-modal-cancel').addEventListener('click', () => modal.remove());
    modal.querySelector('#btn-modal-submit').addEventListener('click', async () => {
      const claimText = modal.querySelector('#inp-claim-text').value.trim();
      const title = modal.querySelector('#inp-case-title').value.trim();
      const evidenceText = modal.querySelector('#inp-evidence-text').value.trim();

      if (!claimText) {
        alert('Please enter a claim assertion to verify.');
        return;
      }

      const sources = [{ uri: 'ui://console/manual_input', publisher: 'operator' }];
      const evidence = evidenceText ? [{ content_text: evidenceText }] : [];

      try {
        const res = await verificationsApi.create({
          claim_text: claimText,
          title: title || undefined,
          sources: sources,
          evidence: evidence,
        });
        modal.remove();
        await this.loadCases();
        if (res && res.case) {
          await this.loadCaseDetails(res.case.case_id);
          this.activeTab = 'detail';
          this.render();
          this._renderCurrentTab();
        }
      } catch (err) {
        alert(`Failed to start verification: ${err.message}`);
      }
    });
  }

  _getStatusColor(status) {
    switch (status) {
      case 'VERIFIED_UNDER_SCOPE':
      case 'SUPPORTED':
        return { bg: 'rgba(34, 197, 94, 0.15)', text: '#4ade80', border: 'rgba(34, 197, 94, 0.3)' };
      case 'PARTIALLY_VERIFIED':
      case 'INCONCLUSIVE':
        return { bg: 'rgba(234, 179, 8, 0.15)', text: '#facc15', border: 'rgba(234, 179, 8, 0.3)' };
      case 'CONTRADICTED':
      case 'FAILED':
        return { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.3)' };
      case 'STALE':
      case 'EXPIRED':
      case 'REVALIDATION_REQUIRED':
        return { bg: 'rgba(249, 115, 22, 0.15)', text: '#fb923c', border: 'rgba(249, 115, 22, 0.3)' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.15)', text: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)' };
    }
  }
}

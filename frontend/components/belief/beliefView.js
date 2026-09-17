/**
 * Belief & World-Model Revision Console View (Task 107)
 * Comprehensive UI for Autonomous Belief Maintenance, Evidence Arbitration,
 * Conflict Resolution, Temporal Freshness, and Decision-Time Epistemic Snapshots.
 */

import { beliefApi } from '../../lib/api/endpoints.js';

export class BeliefView {
  constructor(options = {}) {
    this.container = options.container || (typeof document !== 'undefined' ? document.getElementById('main-content-viewport') : null);
    this.activeTab = 'dashboard';
    this.dashboardData = null;
    this.beliefs = [];
    this.selectedBeliefId = null;
    this.selectedBelief = null;
    this.explanation = null;
    this.evidenceList = [];
    this.conflicts = [];
    this.snapshots = [];
    this.dependencies = [];
    this.loading = false;
    this.error = null;
    this.filterScope = 'ALL';
    this.filterStatus = 'ALL';
  }

  async init() {
    this.renderContainer();
    await this.loadData();
  }

  renderContainer() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="belief-console" id="belief-console-root">
        <!-- Header -->
        <header class="console-header">
          <div class="header-left">
            <div class="header-badge">TASK 107</div>
            <h1 class="console-title">Autonomous Belief & World-Model Revision</h1>
            <p class="console-sub">Versioned, provenance-backed representation of empirical evidence, competing claims, and contextual truth.</p>
          </div>
          <div class="header-right">
            <div id="estop-indicator" class="estop-pill safe">
              <span class="pulse-dot"></span>
              <span id="estop-text">EmergencyStop Disengaged</span>
            </div>
            <button id="btn-refresh-belief" class="btn btn-secondary btn-sm">
              <span class="icon">↻</span> Refresh
            </button>
            <button id="btn-snap-belief" class="btn btn-secondary btn-sm">
              <span class="icon">📷</span> Capture Snapshot
            </button>
            <button id="btn-new-belief" class="btn btn-primary btn-sm">
              <span class="icon">+</span> New Belief
            </button>
          </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="console-tabs" role="tablist">
          <button class="tab-btn active" data-tab="dashboard">Dashboard</button>
          <button class="tab-btn" data-tab="beliefs">Current Beliefs</button>
          <button class="tab-btn" data-tab="detail">Belief Detail & Explanation</button>
          <button class="tab-btn" data-tab="evidence">Evidence Timeline</button>
          <button class="tab-btn" data-tab="conflicts">Conflict Matrix</button>
          <button class="tab-btn" data-tab="dependencies">Dependency Graph</button>
          <button class="tab-btn" data-tab="snapshots">Epistemic Snapshots</button>
        </nav>

        <!-- Main Viewport -->
        <main class="console-body" id="belief-tab-content">
          <div class="loading-spinner">Loading Belief Manifold...</div>
        </main>
      </div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    if (!this.container) return;

    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.target.dataset.tab;
        this.switchTab(tab);
      });
    });

    const refreshBtn = this.container.querySelector('#btn-refresh-belief');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    const snapBtn = this.container.querySelector('#btn-snap-belief');
    if (snapBtn) {
      snapBtn.addEventListener('click', () => this.promptSnapshot());
    }

    const newBtn = this.container.querySelector('#btn-new-belief');
    if (newBtn) {
      newBtn.addEventListener('click', () => this.promptNewBelief());
    }
  }

  switchTab(tabName) {
    this.activeTab = tabName;
    if (!this.container) return;

    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      if (btn.dataset.tab === tabName) btn.classList.add('active');
      else btn.classList.remove('active');
    });

    this.renderActiveTab();
  }

  async loadData() {
    this.loading = true;
    try {
      const [dash, beliefs, evidence, conflicts] = await Promise.all([
        beliefApi.getDashboard().catch(() => null),
        beliefApi.listBeliefs(null, null, null, 100).catch(() => []),
        beliefApi.listEvidence(100).catch(() => []),
        beliefApi.listConflicts().catch(() => []),
      ]);

      this.dashboardData = dash || {
        total_beliefs: beliefs.length,
        confident_beliefs: beliefs.filter(b => b.status === 'CONFIDENT').length,
        contested_beliefs: beliefs.filter(b => b.status === 'CONTESTED').length,
        stale_beliefs: beliefs.filter(b => b.is_stale).length,
        unknown_beliefs: beliefs.filter(b => b.status === 'UNKNOWN').length,
        total_evidence_items: evidence.length,
        active_conflicts: conflicts.length,
        total_revisions: 0,
        total_snapshots: 0,
      };

      this.beliefs = beliefs || [];
      this.evidenceList = evidence || [];
      this.conflicts = conflicts || [];

      if (!this.selectedBeliefId && this.beliefs.length > 0) {
        this.selectedBeliefId = this.beliefs[0].belief_id;
        this.selectedBelief = this.beliefs[0];
      }

      this.renderActiveTab();
    } catch (err) {
      this.error = err.message || 'Failed to load belief data';
      this.renderError();
    } finally {
      this.loading = false;
    }
  }

  renderActiveTab() {
    const viewport = this.container ? this.container.querySelector('#belief-tab-content') : null;
    if (!viewport) return;

    switch (this.activeTab) {
      case 'dashboard':
        viewport.innerHTML = this.renderDashboardHtml();
        break;
      case 'beliefs':
        viewport.innerHTML = this.renderBeliefsHtml();
        this.bindBeliefsEvents();
        break;
      case 'detail':
        viewport.innerHTML = this.renderDetailHtml();
        this.bindDetailEvents();
        break;
      case 'evidence':
        viewport.innerHTML = this.renderEvidenceHtml();
        break;
      case 'conflicts':
        viewport.innerHTML = this.renderConflictsHtml();
        break;
      case 'dependencies':
        viewport.innerHTML = this.renderDependenciesHtml();
        break;
      case 'snapshots':
        viewport.innerHTML = this.renderSnapshotsHtml();
        break;
      default:
        viewport.innerHTML = `<div class="empty-state">Tab '${this.activeTab}' not found.</div>`;
    }
  }

  renderDashboardHtml() {
    const d = this.dashboardData || {};
    return `
      <div class="dashboard-grid">
        <!-- Telemetry Cards -->
        <div class="kpi-card">
          <div class="kpi-label">Active Beliefs</div>
          <div class="kpi-value text-primary">${d.total_beliefs || 0}</div>
          <div class="kpi-sub">Total Proposition Manifold</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Confident State</div>
          <div class="kpi-value text-success">${d.confident_beliefs || 0}</div>
          <div class="kpi-sub">Verified & Uncontested</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Contested Beliefs</div>
          <div class="kpi-value text-warning">${d.contested_beliefs || 0}</div>
          <div class="kpi-sub">Competing Evidence</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Stale Beliefs</div>
          <div class="kpi-value text-danger">${d.stale_beliefs || 0}</div>
          <div class="kpi-sub">Aged past domain TTL</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Unknown / Insufficient</div>
          <div class="kpi-value text-muted">${d.unknown_beliefs || 0}</div>
          <div class="kpi-sub">Absence of Observations</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Ingested Evidence</div>
          <div class="kpi-value text-primary">${d.total_evidence_items || 0}</div>
          <div class="kpi-sub">Telemetry & Outcomes</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Active Conflicts</div>
          <div class="kpi-value text-warning">${d.active_conflicts || 0}</div>
          <div class="kpi-sub">Direct, Scope & Version</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Versioned Revisions</div>
          <div class="kpi-value text-accent">${d.total_revisions || 0}</div>
          <div class="kpi-sub">Immutable History Preserved</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Decision Snapshots</div>
          <div class="kpi-value text-success">${d.total_snapshots || 0}</div>
          <div class="kpi-sub">Auditable Epistemic Replay</div>
        </div>
      </div>

      <!-- Invariants Card -->
      <div class="card mt-4">
        <div class="card-header">
          <h3 class="card-title">Epistemic Architectural Invariants</h3>
          <span class="badge badge-success">ACTIVE & ENFORCED</span>
        </div>
        <div class="card-body">
          <div class="invariant-pill-grid">
            <span class="inv-pill">BELIEF != TRUTH</span>
            <span class="inv-pill">BELIEF != AUTHORIZATION</span>
            <span class="inv-pill">BELIEF != POLICY</span>
            <span class="inv-pill">BELIEF != GOAL</span>
            <span class="inv-pill">BELIEF != DECISION</span>
            <span class="inv-pill">BELIEF != MEMORY</span>
            <span class="inv-pill">FORECAST != OBSERVATION</span>
            <span class="inv-pill">SIMULATION != REALITY</span>
            <span class="inv-pill">AGENT REPORT != INDEPENDENT TRUTH</span>
            <span class="inv-pill">UNKNOWN != FALSE</span>
            <span class="inv-pill">EMERGENCY_STOP ABSOLUTE PRIMACY</span>
          </div>
        </div>
      </div>
    `;
  }

  renderBeliefsHtml() {
    const list = this.beliefs || [];
    const rows = list.map(b => {
      const badgeClass = b.status === 'CONFIDENT' ? 'badge-success' :
                         b.status === 'CONTESTED' ? 'badge-warning' :
                         b.status === 'CONTRADICTED' ? 'badge-danger' :
                         b.status === 'STALE' ? 'badge-danger' : 'badge-primary';
      const staleTag = b.is_stale ? '<span class="tag-stale">STALE</span>' : '';
      return `
        <tr class="belief-row ${b.belief_id === this.selectedBeliefId ? 'selected' : ''}" data-id="${b.belief_id}">
          <td class="font-mono">${b.belief_id}</td>
          <td><strong>${b.subject}</strong></td>
          <td>${b.predicate}</td>
          <td><span class="badge ${badgeClass}">${b.status}</span> ${staleTag}</td>
          <td>
            <div class="confidence-bar-bg">
              <div class="confidence-bar-fill" style="width: ${Math.round(b.confidence * 100)}%;"></div>
            </div>
            <span class="conf-text">${Math.round(b.confidence * 100)}%</span>
          </td>
          <td>${b.scope}</td>
          <td>v${b.current_version}</td>
          <td>
            <button class="btn btn-xs btn-secondary btn-select-belief" data-id="${b.belief_id}">Inspect</button>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="beliefs-container">
        <div class="table-actions">
          <input type="text" id="belief-search-input" class="input input-sm" placeholder="Filter by subject or predicate...">
          <button class="btn btn-sm btn-secondary" id="btn-filter-stale">Toggle Stale</button>
        </div>
        <div class="table-responsive">
          <table class="kairo-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Subject</th>
                <th>Predicate</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Scope</th>
                <th>Version</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${rows.length > 0 ? rows : '<tr><td colspan="8" class="text-center py-4 text-muted">No beliefs registered in this view.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  bindBeliefsEvents() {
    if (!this.container) return;
    this.container.querySelectorAll('.btn-select-belief').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.target.dataset.id;
        this.selectedBeliefId = id;
        this.selectedBelief = this.beliefs.find(b => b.belief_id === id) || null;
        try {
          this.explanation = await beliefApi.explainBelief(id);
        } catch (_) {
          this.explanation = null;
        }
        this.switchTab('detail');
      });
    });
  }

  renderDetailHtml() {
    const b = this.selectedBelief;
    if (!b) {
      return `<div class="empty-state">No belief selected. Choose one from the Current Beliefs tab.</div>`;
    }

    const exp = this.explanation;
    return `
      <div class="belief-detail-grid">
        <div class="card detail-main-card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${b.subject} <span class="text-muted">::</span> ${b.predicate}</h2>
              <p class="font-mono text-xs text-muted">ID: ${b.belief_id} | Scope: ${b.scope} | Version: v${b.current_version}</p>
            </div>
            <div class="detail-actions">
              <button class="btn btn-sm btn-secondary" id="btn-trigger-correction">User Correction</button>
            </div>
          </div>
          <div class="card-body">
            <div class="explanation-box">
              <h4 class="box-title">Epistemic State</h4>
              <p class="exp-what">${exp ? exp.what : `Belief status is ${b.status} with ${(b.confidence * 100).toFixed(1)}% confidence.`}</p>
              <p class="exp-when text-muted text-sm">${exp ? exp.when : `Validity interval: ${b.valid_from}`}</p>
            </div>

            <div class="detail-sections mt-4">
              <div class="section-block">
                <h5>Supporting Evidence (${b.evidence_ids.length})</h5>
                <ul class="evidence-pill-list">
                  ${exp && exp.why_evidence.length > 0
                    ? exp.why_evidence.map(e => `<li class="ev-item-pill support">${e}</li>`).join('')
                    : '<li>No direct supporting evidence recorded.</li>'}
                </ul>
              </div>

              <div class="section-block mt-3">
                <h5>Active Contradictions (${b.contradiction_evidence_ids.length})</h5>
                <ul class="evidence-pill-list">
                  ${exp && exp.when_not_contradictions.length > 0
                    ? exp.when_not_contradictions.map(c => `<li class="ev-item-pill contradict">${c}</li>`).join('')
                    : '<li class="text-muted">Zero active contradictions observed.</li>'}
                </ul>
              </div>

              <div class="section-block mt-3">
                <h5>Known Limitations</h5>
                <ul class="text-sm text-muted">
                  ${exp && exp.limitations.length > 0
                    ? exp.limitations.map(l => `<li>• ${l}</li>`).join('')
                    : '<li>• Standard bounded empirical confidence.</li>'}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  bindDetailEvents() {
    if (!this.container) return;
    const corrBtn = this.container.querySelector('#btn-trigger-correction');
    if (corrBtn) {
      corrBtn.addEventListener('click', async () => {
        const stmt = prompt(`Enter user correction for '${this.selectedBelief.subject}.${this.selectedBelief.predicate}':`);
        if (!stmt) return;
        try {
          await beliefApi.recordCorrection(this.selectedBeliefId, stmt);
          alert('User correction recorded as USER_ASSERTION evidence. Manifold re-arbitrated.');
          await this.loadData();
        } catch (e) {
          alert('Failed to record correction: ' + e.message);
        }
      });
    }
  }

  renderEvidenceHtml() {
    const evList = this.evidenceList || [];
    const items = evList.map(e => `
      <div class="timeline-item">
        <div class="timeline-badge">${e.source_type}</div>
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="font-mono text-xs">${e.evidence_id}</span>
            <span class="text-xs text-muted">${e.timestamp}</span>
          </div>
          <div class="timeline-body">${e.summary || JSON.stringify(e.content)}</div>
          <div class="timeline-footer">
            <span>Weight: ${e.reliability_weight}</span> | <span>Hash: ${e.content_hash.slice(0, 10)}...</span>
          </div>
        </div>
      </div>
    `).join('');

    return `
      <div class="evidence-timeline">
        <h3>Ingested Evidence Chronology</h3>
        <div class="timeline-container">
          ${items.length > 0 ? items : '<div class="empty-state">No evidence items recorded yet.</div>'}
        </div>
      </div>
    `;
  }

  renderConflictsHtml() {
    const cList = this.conflicts || [];
    const items = cList.map(c => `
      <div class="conflict-card ${c.resolution === 'CONTESTED' ? 'active-conflict' : 'resolved-conflict'}">
        <div class="conflict-header">
          <span class="badge ${c.resolution === 'CONTESTED' ? 'badge-warning' : 'badge-success'}">${c.conflict_type}</span>
          <span class="font-mono text-xs">${c.conflict_id}</span>
        </div>
        <div class="conflict-body">
          <p><strong>Rationale:</strong> ${c.rationale}</p>
          <p class="text-sm"><strong>Resolution:</strong> ${c.resolution}</p>
        </div>
      </div>
    `).join('');

    return `
      <div class="conflicts-container">
        <h3>Epistemic Conflict Matrix</h3>
        <div class="conflict-grid">
          ${items.length > 0 ? items : '<div class="empty-state">Zero unresolved conflicts detected.</div>'}
        </div>
      </div>
    `;
  }

  renderDependenciesHtml() {
    return `
      <div class="dependencies-container">
        <h3>Epistemic Dependency DAG</h3>
        <p class="text-sm text-muted">Bounded downstream uncertainty propagation (max depth: 4).</p>
        <div class="card mt-3">
          <div class="card-body font-mono text-sm">
            ${this.beliefs.map(b => `
              <div class="dep-row">
                <span class="text-primary">${b.subject}.${b.predicate}</span>
                <span class="text-muted">-> status: ${b.status}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  renderSnapshotsHtml() {
    return `
      <div class="snapshots-container">
        <h3>Decision & Mission Epistemic Snapshots</h3>
        <p class="text-sm text-muted">Immutable manifests of beliefs and evidence captured at decision time for complete auditability.</p>
        <div class="empty-state mt-4">Snapshots are captured automatically by Task 94 Decision Deliberation and Task 100 Mission Checkpoints.</div>
      </div>
    `;
  }

  async promptSnapshot() {
    const ref = prompt('Enter Decision ID or Mission ID reference (optional):');
    try {
      const snap = await beliefApi.captureSnapshot({ trigger_type: 'MANUAL', reference_id: ref || null });
      alert(`Snapshot captured: ${snap.snapshot_id}\nIntegrity Hash: ${snap.integrity_hash}`);
      await this.loadData();
    } catch (e) {
      alert('Failed to capture snapshot: ' + e.message);
    }
  }

  async promptNewBelief() {
    const subject = prompt('Enter subject (e.g. "api.stripe.com"):');
    if (!subject) return;
    const predicate = prompt('Enter predicate (e.g. "is_available"):');
    if (!predicate) return;
    const val = prompt('Enter claimed value (e.g. "true"):');
    try {
      await beliefApi.createBelief({
        subject,
        predicate,
        object_value: val,
        scope: 'SYSTEM',
        initial_confidence: 0.6,
      });
      alert('Belief created as CANDIDATE. Ingest evidence to increase confidence.');
      await this.loadData();
    } catch (e) {
      alert('Failed to create belief: ' + e.message);
    }
  }

  renderError() {
    if (!this.container) return;
    const viewport = this.container.querySelector('#belief-tab-content');
    if (viewport) {
      viewport.innerHTML = `<div class="error-banner">Error: ${this.error}</div>`;
    }
  }
}

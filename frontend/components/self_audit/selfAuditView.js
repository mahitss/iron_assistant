/**
 * Metacognitive Control & Autonomous Self-Audit Engine View (Task 67)
 * Glassmorphic Self-Audit & Metacognitive Control Center dashboard.
 */

import { selfAuditApi } from '../../lib/api/endpoints.js';

export class SelfAuditView {
  constructor(containerId) {
    this.container = typeof document !== 'undefined' ? (typeof containerId === 'string' ? document.getElementById(containerId) : containerId) : null;
    this.activeTab = 'active_audits'; // active_audits, reasoning_claims, calibration_accuracy, behavior_drift, error_clusters, beliefs_revisions, findings_recommendations
    this.audits = [];
    this.selectedAudit = null;
    this.overview = null;
    this.beliefs = [];
    this.calibrationData = null;
    this.driftData = [];
    this.errorData = null;
    this.isLoading = false;
    this.error = null;
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
      this.overview = await selfAuditApi.getOverview();
      this.audits = await selfAuditApi.listAudits();
      this.beliefs = await selfAuditApi.listBeliefs();
      this.driftData = await selfAuditApi.getDrift();
      this.calibrationData = await selfAuditApi.getCalibration();
      this.errorData = await selfAuditApi.getErrors();

      if (this.audits && this.audits.length > 0 && !this.selectedAudit) {
        await this.selectAudit(this.audits[0].audit_id);
      }
    } catch (err) {
      console.error('Failed to load self-audit data:', err);
      this.error = err.message || 'Failed to connect to Self-Audit Engine';
    } finally {
      this.isLoading = false;
      if (this.container) this.render();
    }
  }

  async selectAudit(auditOrId) {
    if (typeof auditOrId === 'object' && auditOrId !== null) {
      this.selectedAudit = auditOrId;
      if (this.container) this.render();
      return;
    }
    const auditId = auditOrId;
    this.isLoading = true;
    try {
      this.selectedAudit = await selfAuditApi.getAudit(auditId);
    } catch (err) {
      console.error(`Failed to select audit ${auditId}:`, err);
      this.error = err.message || `Failed to fetch audit ${auditId}`;
    } finally {
      this.isLoading = false;
      if (this.container) this.render();
    }
  }

  setTab(tabName) {
    this.activeTab = tabName;
    if (this.container) {
      this.render();
    }
  }

  async triggerAuditCycle(isAdversarial = false) {
    if (!this.container) return;
    const subjectInput = this.container.querySelector('#audit-cycle-subject');
    const subject = subjectInput ? subjectInput.value.trim() : 'Operational telemetry audit';
    if (!subject) return;

    this.isLoading = true;
    try {
      const record = await selfAuditApi.runCycle({
        subject,
        observed_actions: [
          `Evaluated live execution flow for ${subject}`,
          'Checked reasoning consistency against empirical evidence citations',
          'Audited confidence calibration against verified outcomes',
        ],
        reported_confidence: 0.85,
        depth: 'STANDARD',
        is_adversarial: isAdversarial,
      });
      await this.loadData();
      if (record && record.audit_id) {
        await this.selectAudit(record.audit_id);
      }
    } catch (err) {
      alert(`Audit failed: ${err.message}`);
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  async resolveFinding(findingId) {
    const evidence = prompt('Enter empirical evidence verifying that this finding is resolved:');
    if (!evidence) return;

    try {
      await selfAuditApi.resolveFinding(findingId, evidence);
      await this.loadData();
    } catch (err) {
      alert(`Resolution failed: ${err.message}`);
    }
  }

  renderSkeleton() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="self-audit-container glassmorphic loading-skeleton">
        <div class="skeleton-header"></div>
        <div class="skeleton-grid"></div>
      </div>
    `;
  }

  render() {
    if (!this.container) return;

    const ov = this.overview || {
      metacognitive_state: 'CONFIDENT',
      calibration_state: 'WELL_CALIBRATED',
      total_audits: 0,
      open_findings_count: 0,
      critical_findings_count: 0,
      active_beliefs_count: 0,
      active_drifts_count: 0,
      recurring_error_clusters: 0,
      average_brier_score: 0.0,
    };

    const stateColor = ov.metacognitive_state === 'CONFIDENT' ? '#10b981' : (ov.metacognitive_state === 'UNCERTAIN' ? '#f59e0b' : '#ef4444');
    const calibColor = ov.calibration_state === 'WELL_CALIBRATED' ? '#10b981' : '#f59e0b';

    this.container.innerHTML = `
      <div class="self-audit-view glass-panel">
        <!-- Header & Invariants Banner -->
        <div class="view-header">
          <div>
            <div class="subsystem-pill">TASK 67</div>
            <h2>Metacognitive Control & Autonomous Self-Audit Engine</h2>
            <p class="subtitle">Continuous self-reflection, belief revision, reasoning quality auditing, and confidence calibration.</p>
          </div>
          <div class="invariant-banner">
            <span class="invariant-tag">SELF-REFLECTION &ne; REALITY</span>
            <span class="invariant-tag">SELF-AUDIT &ne; TRUTH</span>
            <span class="invariant-tag">CONFIDENCE &ne; CERTAINTY</span>
            <span class="invariant-tag">IMMUTABLE GOVERNANCE</span>
          </div>
        </div>

        ${this.error ? `<div class="error-banner"><strong>Error:</strong> ${this.error}</div>` : ''}

        <!-- Top Telemetry KPIs -->
        <div class="kpi-grid">
          <div class="kpi-card glassmorphic">
            <span class="kpi-label">Metacognitive State</span>
            <span class="kpi-value" style="color: ${stateColor};">${ov.metacognitive_state}</span>
            <span class="kpi-meta">Self-awareness posture</span>
          </div>
          <div class="kpi-card glassmorphic">
            <span class="kpi-label">Confidence Calibration</span>
            <span class="kpi-value" style="color: ${calibColor};">${ov.calibration_state}</span>
            <span class="kpi-meta">Avg Brier: ${ov.average_brier_score.toFixed(4)}</span>
          </div>
          <div class="kpi-card glassmorphic">
            <span class="kpi-label">Active Drift Alerts</span>
            <span class="kpi-value ${ov.active_drifts_count > 0 ? 'text-warning' : 'text-success'}">${ov.active_drifts_count}</span>
            <span class="kpi-meta">Operational deviations</span>
          </div>
          <div class="kpi-card glassmorphic">
            <span class="kpi-label">Error Clusters</span>
            <span class="kpi-value text-accent">${ov.recurring_error_clusters}</span>
            <span class="kpi-meta">Recurring failure patterns</span>
          </div>
          <div class="kpi-card glassmorphic">
            <span class="kpi-label">Open Findings</span>
            <span class="kpi-value ${ov.critical_findings_count > 0 ? 'text-danger' : 'text-info'}">${ov.open_findings_count}</span>
            <span class="kpi-meta">${ov.critical_findings_count} critical severity</span>
          </div>
          <div class="kpi-card glassmorphic">
            <span class="kpi-label">Active Beliefs</span>
            <span class="kpi-value text-primary">${ov.active_beliefs_count}</span>
            <span class="kpi-meta">Internal epistemic claims</span>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-navigation">
          <button class="tab-btn ${this.activeTab === 'active_audits' ? 'active' : ''}" data-tab="active_audits">
            Self-Audits (${this.audits.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'reasoning_claims' ? 'active' : ''}" data-tab="reasoning_claims">
            Reasoning & Claims
          </button>
          <button class="tab-btn ${this.activeTab === 'calibration_accuracy' ? 'active' : ''}" data-tab="calibration_accuracy">
            Confidence Calibration
          </button>
          <button class="tab-btn ${this.activeTab === 'behavior_drift' ? 'active' : ''}" data-tab="behavior_drift">
            Behavior Drift (${this.driftData.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'error_clusters' ? 'active' : ''}" data-tab="error_clusters">
            Error Clusters & Heatmap
          </button>
          <button class="tab-btn ${this.activeTab === 'beliefs_revisions' ? 'active' : ''}" data-tab="beliefs_revisions">
            Beliefs & Revisions (${this.beliefs.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'findings_recommendations' ? 'active' : ''}" data-tab="findings_recommendations">
            Findings & Fixes
          </button>
        </div>

        <!-- Tab Content Body -->
        <div class="tab-content-area">
          ${this.renderActiveTabContent()}
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  renderActiveTabContent() {
    switch (this.activeTab) {
      case 'active_audits':
        return this.renderAuditsTab();
      case 'reasoning_claims':
        return this.renderReasoningTab();
      case 'calibration_accuracy':
        return this.renderCalibrationTab();
      case 'behavior_drift':
        return this.renderDriftTab();
      case 'error_clusters':
        return this.renderErrorsTab();
      case 'beliefs_revisions':
        return this.renderBeliefsTab();
      case 'findings_recommendations':
        return this.renderFindingsTab();
      default:
        return `<div class="p-4">Unknown tab: ${this.activeTab}</div>`;
    }
  }

  renderAuditsTab() {
    return `
      <div class="split-view">
        <div class="left-panel glassmorphic">
          <div class="panel-action-bar">
            <h4>Executed Self-Audits</h4>
            <div class="input-group">
              <input type="text" id="audit-cycle-subject" placeholder="Subject to audit..." value="Production reasoning and execution telemetry" class="form-input" />
              <button id="btn-run-standard" class="btn btn-primary">Run Audit</button>
              <button id="btn-run-adversarial" class="btn btn-warning">Adversarial</button>
            </div>
          </div>
          <div class="audit-list">
            ${this.audits.length === 0 ? '<div class="empty-notice">No self-audits recorded yet. Run an audit cycle above.</div>' : ''}
            ${this.audits.map(a => `
              <div class="audit-card ${this.selectedAudit && this.selectedAudit.audit_id === a.audit_id ? 'selected' : ''}" data-id="${a.audit_id}">
                <div class="card-header-row">
                  <span class="audit-subject">${this.escapeHtml(a.subject)}</span>
                  <span class="badge badge-${a.severity.toLowerCase()}">${a.severity}</span>
                </div>
                <div class="card-meta-row">
                  <span>${a.depth} &bull; ${a.audit_type}</span>
                  <span>${new Date(a.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="card-findings-count">${a.findings ? a.findings.length : 0} findings recorded</div>
              </div>
            `).join('')}
          </div>
        </div>

        <div class="right-panel glassmorphic">
          ${this.selectedAudit ? this.renderAuditDetail(this.selectedAudit) : '<div class="empty-state">Select an audit run on the left to inspect detailed checks and findings.</div>'}
        </div>
      </div>
    `;
  }

  renderAuditDetail(audit) {
    return `
      <div class="audit-detail">
        <div class="detail-header">
          <div>
            <h3>${this.escapeHtml(audit.subject)}</h3>
            <span class="detail-id">${audit.audit_id} &bull; Version ${audit.version} &bull; Scope: ${audit.scope}</span>
          </div>
          <span class="badge badge-${audit.severity.toLowerCase()} large">${audit.severity}</span>
        </div>

        <div class="detail-section">
          <h5>Checks Performed (${audit.checks_performed ? audit.checks_performed.length : 0})</h5>
          <div class="tag-cloud">
            ${(audit.checks_performed || []).map(c => `<span class="check-tag">&check; ${this.escapeHtml(c)}</span>`).join('')}
          </div>
        </div>

        <div class="detail-section">
          <h5>Evidence Collected (${audit.evidence ? audit.evidence.length : 0})</h5>
          <ul class="evidence-list">
            ${(audit.evidence || []).map(e => `<li>${this.escapeHtml(e)}</li>`).join('')}
          </ul>
        </div>

        <div class="detail-section">
          <h5>Recommendations</h5>
          <ul class="recommendation-list">
            ${(audit.recommendations || []).map(r => `<li><strong>Recommendation:</strong> ${this.escapeHtml(r)}</li>`).join('')}
          </ul>
        </div>
      </div>
    `;
  }

  renderReasoningTab() {
    return `
      <div class="tab-panel glassmorphic">
        <h4>Reasoning Trace & Claim Quality Audit (Spec 10, 11, 12)</h4>
        <p class="text-muted">Structured epistemic evaluation without exposing raw model chains-of-thought to untrusted contexts.</p>
        <div class="checks-grid">
          <div class="check-item-card">
            <h6>False Certainty Defense</h6>
            <p>Flags claims with reported confidence &ge; 0.99 lacking at least 3 independent corroborating evidence citations.</p>
          </div>
          <div class="check-item-card">
            <h6>Unsupported Assumptions</h6>
            <p>Audits critical decision premises against external ground truth citations to ensure assertions are grounded.</p>
          </div>
          <div class="check-item-card">
            <h6>Confirmation Bias Guard</h6>
            <p>Detects when reasoning selectively cites supportive data while ignoring contradictory empirical observations.</p>
          </div>
          <div class="check-item-card">
            <h6>Causal Overreach Check</h6>
            <p>Identifies logical leaps confusing correlation with deterministic causation.</p>
          </div>
        </div>
      </div>
    `;
  }

  renderCalibrationTab() {
    const cal = this.calibrationData || { mean_brier_score: 0.0, calibration_state: 'UNKNOWN', buckets: {}, alerts: [] };
    return `
      <div class="tab-panel glassmorphic">
        <h4>Confidence Calibration & Brier Scoring (Spec 24, 25, 26)</h4>
        <div class="brier-metric-box">
          <div class="brier-score">${cal.mean_brier_score.toFixed(4)}</div>
          <div class="brier-label">Mean Brier Score (Lower is better, 0.0 = perfect calibration)</div>
        </div>

        ${cal.alerts && cal.alerts.length > 0 ? `
          <div class="alert-box-warning">
            ${cal.alerts.map(a => `<div class="alert-item">&excl; ${this.escapeHtml(a)}</div>`).join('')}
          </div>
        ` : ''}

        <h5>Confidence Distribution Buckets</h5>
        <div class="buckets-grid">
          <div class="bucket-card">
            <h6>Low Confidence (0.0 - 0.33)</h6>
            <div>Predictions: ${cal.buckets.low_confidence ? cal.buckets.low_confidence.count : 0}</div>
            <div>Avg Brier: ${cal.buckets.low_confidence ? cal.buckets.low_confidence.avg_brier : 0}</div>
          </div>
          <div class="bucket-card">
            <h6>Medium Confidence (0.34 - 0.66)</h6>
            <div>Predictions: ${cal.buckets.medium_confidence ? cal.buckets.medium_confidence.count : 0}</div>
            <div>Avg Brier: ${cal.buckets.medium_confidence ? cal.buckets.medium_confidence.avg_brier : 0}</div>
          </div>
          <div class="bucket-card">
            <h6>High Confidence (0.67 - 1.0)</h6>
            <div>Predictions: ${cal.buckets.high_confidence ? cal.buckets.high_confidence.count : 0}</div>
            <div>Avg Brier: ${cal.buckets.high_confidence ? cal.buckets.high_confidence.avg_brier : 0}</div>
          </div>
        </div>
      </div>
    `;
  }

  renderDriftTab() {
    return `
      <div class="tab-panel glassmorphic">
        <h4>Behavioral Baseline & Drift Tracking (Spec 32, 33, 34)</h4>
        <p class="text-muted">Monitors deviations in operational parameters against empirical running baselines.</p>
        <div class="drift-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Baseline Mean</th>
                <th>Current Value</th>
                <th>Status</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              ${this.driftData.length === 0 ? '<tr><td colspan="5" class="text-center text-muted">All operational parameters currently within normal baseline thresholds.</td></tr>' : ''}
              ${this.driftData.map(d => `
                <tr class="drift-row-warning">
                  <td><strong>${this.escapeHtml(d.metric_name)}</strong></td>
                  <td>${d.baseline_mean.toFixed(2)}</td>
                  <td>${d.current_value.toFixed(2)}</td>
                  <td><span class="badge badge-warning">DRIFTING</span></td>
                  <td>${this.escapeHtml(d.drift_reason)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  renderErrorsTab() {
    const errs = this.errorData || { error_clusters: [], error_heatmap: {} };
    return `
      <div class="tab-panel glassmorphic">
        <h4>12-Category Error Taxonomy & Recurring Failure Clusters (Spec 27, 29, 31)</h4>
        <h5>Category Heatmap Distribution</h5>
        <div class="heatmap-grid">
          ${Object.entries(errs.error_heatmap || {}).map(([cat, count]) => `
            <div class="heatmap-cell ${count > 0 ? 'active' : ''}">
              <span class="heatmap-cat">${cat.replace('_ERROR', '')}</span>
              <span class="heatmap-count">${count}</span>
            </div>
          `).join('')}
        </div>

        <h5 class="mt-4">Identified Failure Clusters</h5>
        <div class="clusters-list">
          ${errs.error_clusters.length === 0 ? '<div class="empty-notice">No systematic failure clusters identified.</div>' : ''}
          ${errs.error_clusters.map(c => `
            <div class="cluster-card glassmorphic">
              <div class="cluster-title-row">
                <h6>${this.escapeHtml(c.pattern_name)}</h6>
                <span class="badge badge-danger">Repeated ${c.recurring_count}x</span>
              </div>
              <p class="text-muted">${this.escapeHtml(c.root_cause_hypothesis)}</p>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderBeliefsTab() {
    return `
      <div class="tab-panel glassmorphic">
        <div class="panel-action-bar">
          <h4>Internal Epistemic Beliefs & Lineage (Spec 7, 8)</h4>
        </div>
        <div class="beliefs-grid">
          ${this.beliefs.length === 0 ? '<div class="empty-notice">No beliefs recorded yet.</div>' : ''}
          ${this.beliefs.map(b => `
            <div class="belief-card glassmorphic">
              <div class="belief-header-row">
                <span class="belief-subject">${this.escapeHtml(b.subject)}</span>
                <span class="badge badge-${b.status.toLowerCase()}">${b.status}</span>
              </div>
              <p class="belief-claim">&ldquo;${this.escapeHtml(b.claim)}&rdquo;</p>
              <div class="belief-meta">
                <span>Confidence: ${(b.confidence * 100).toFixed(0)}%</span>
                <span>Basis: ${this.escapeHtml(b.basis)}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderFindingsTab() {
    const allFindings = (this.audits || []).flatMap(a => a.findings || []);
    return `
      <div class="tab-panel glassmorphic">
        <h4>Self-Audit Findings & Verified Remediations (Spec 50, 81, 82)</h4>
        <div class="findings-list">
          ${allFindings.length === 0 ? '<div class="empty-notice">No active findings. All self-audit checks passing cleanly.</div>' : ''}
          ${allFindings.map(f => `
            <div class="finding-card glassmorphic">
              <div class="finding-header-row">
                <div>
                  <span class="badge badge-${f.severity.toLowerCase()}">${f.severity}</span>
                  <span class="finding-category">${f.category}</span>
                </div>
                <span class="finding-status badge badge-${f.status.toLowerCase()}">${f.status}</span>
              </div>
              <div class="finding-desc">${this.escapeHtml(f.description)}</div>
              ${f.recommendation ? `<div class="finding-rec"><strong>Recommendation:</strong> ${this.escapeHtml(f.recommendation)}</div>` : ''}
              ${f.status !== 'RESOLVED' ? `
                <button class="btn btn-sm btn-outline-success mt-2 btn-resolve-finding" data-id="${f.finding_id}">
                  Verify & Resolve
                </button>
              ` : '<span class="text-success small">&check; Verified resolved</span>'}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  attachEventListeners() {
    if (!this.container) return;

    // Tab buttons
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        if (tab) this.setTab(tab);
      });
    });

    // Audit cards selection
    this.container.querySelectorAll('.audit-card').forEach(card => {
      card.addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        if (id) await this.selectAudit(id);
      });
    });

    // Run audit buttons
    const runStd = this.container.querySelector('#btn-run-standard');
    if (runStd) {
      runStd.addEventListener('click', () => this.triggerAuditCycle(false));
    }
    const runAdv = this.container.querySelector('#btn-run-adversarial');
    if (runAdv) {
      runAdv.addEventListener('click', () => this.triggerAuditCycle(true));
    }

    // Resolve finding buttons
    this.container.querySelectorAll('.btn-resolve-finding').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const fId = e.currentTarget.getAttribute('data-id');
        if (fId) await this.resolveFinding(fId);
      });
    });
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

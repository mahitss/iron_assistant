/**
 * Kairo Truth, Verification & Self-Correction Engine View (Task 42)
 * Renders Claims, Evidence Triangulation, Contradictions, Invariants,
 * Calibrated Confidence, and Self-Correction Records.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class VerificationView {
  constructor(container) {
    this.container = container;
    this.stats = null;
    this.claims = [];
    this.corrections = [];
    this.activeTab = 'claims';
    this.isLoading = false;
  }

  async render() {
    this.container.innerHTML = `
      <div class="verification-view">
        <header class="section-header">
          <div>
            <h1 class="page-title">Truth, Verification & Self-Correction Engine</h1>
            <p class="page-subtitle">Multi-source triangulation, anti-self-attestation, invariant validation, and transparent error correction</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-secondary" id="refresh-verification-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              Refresh
            </button>
            <button class="btn btn-primary" id="new-claim-btn">
              + Register Claim
            </button>
          </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <div class="metrics-grid" id="verification-kpis">
          <div class="metric-card">
            <span class="metric-label">Verified Claims</span>
            <span class="metric-value text-success" id="kpi-verified-claims">0</span>
            <span class="metric-trend">Independently Proven</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Contradictions Detected</span>
            <span class="metric-value text-danger" id="kpi-contradictions">0</span>
            <span class="metric-trend">Conflicts Caught</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Self-Corrections</span>
            <span class="metric-value text-warning" id="kpi-self-corrections">0</span>
            <span class="metric-trend">Loop & Oscillation Guarded</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Calibration Accuracy</span>
            <span class="metric-value text-info" id="kpi-calibration-acc">100%</span>
            <span class="metric-trend">Brier Calibrated</span>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-nav">
          <button class="tab-btn active" data-tab="claims">Claims & Evidence</button>
          <button class="tab-btn" data-tab="contradictions">Contradictions & Invariants</button>
          <button class="tab-btn" data-tab="corrections">Self-Correction Admissions</button>
          <button class="tab-btn" data-tab="triangulation">Triangulation & Citations</button>
        </div>

        <!-- Tab Content Panes -->
        <div class="tab-content" style="margin-top: 16px;">
          <!-- Claims Pane -->
          <div class="tab-pane active" id="verification-tab-claims">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Active Claims & Truth Status</h3>
                <span class="badge badge-info" id="claims-count-badge">0 claims</span>
              </div>
              <div class="table-responsive" style="padding: 12px;">
                <table class="data-table" id="claims-table" style="width: 100%;">
                  <thead>
                    <tr>
                      <th>Claim ID</th>
                      <th>Statement</th>
                      <th>Type</th>
                      <th>Truth Status</th>
                      <th>Confidence</th>
                      <th>Evidence Count</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody id="claims-table-body">
                    <tr><td colspan="7" class="text-center text-muted">No claims registered yet.</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Contradictions Pane -->
          <div class="tab-pane" id="verification-tab-contradictions" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Contradiction Engine & Invariants</h3>
              </div>
              <div id="contradictions-container" style="padding: 16px;">
                <p class="text-muted">No unresolved contradictions detected across active claims.</p>
              </div>
            </div>
          </div>

          <!-- Corrections Pane -->
          <div class="tab-pane" id="verification-tab-corrections" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Transparent Self-Corrections & User Admissions</h3>
              </div>
              <div id="corrections-container" style="padding: 16px;">
                <p class="text-muted">No self-corrections required. System state matches verified observations.</p>
              </div>
            </div>
          </div>

          <!-- Triangulation Pane -->
          <div class="tab-pane" id="verification-tab-triangulation" style="display: none;">
            <div class="panel-card">
              <div class="panel-header">
                <h3 class="panel-title">Multi-Source Triangulation & Citation Integrity</h3>
              </div>
              <div id="triangulation-container" style="padding: 16px;">
                <p class="text-muted">Select a claim to view source agreement ratios, independent corroborations, and citation checks.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  }

  bindEvents() {
    const refreshBtn = this.container.querySelector('#refresh-verification-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadData());
    }

    const tabs = this.container.querySelectorAll('.tab-btn');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        const tabName = tab.getAttribute('data-tab');
        this.activeTab = tabName;

        const panes = this.container.querySelectorAll('.tab-pane');
        panes.forEach((p) => (p.style.display = 'none'));
        const activePane = this.container.querySelector(`#verification-tab-${tabName}`);
        if (activePane) activePane.style.display = 'block';
      });
    });
  }

  async loadData() {
    try {
      this.isLoading = true;
      const [stats, claims] = await Promise.all([
        Endpoints.getVerificationStats().catch(() => null),
        Endpoints.listVerificationClaims().catch(() => []),
      ]);

      if (stats) {
        this.stats = stats;
        this.updateKpis(stats);
      }
      if (Array.isArray(claims)) {
        this.claims = claims;
        this.renderClaimsTable(claims);
      }
    } catch (err) {
      console.warn('Could not load verification engine data:', err);
    } finally {
      this.isLoading = false;
    }
  }

  updateKpis(stats) {
    const metrics = stats.metrics || {};
    const verifiedEl = this.container.querySelector('#kpi-verified-claims');
    const contraEl = this.container.querySelector('#kpi-contradictions');
    const corrEl = this.container.querySelector('#kpi-self-corrections');

    if (verifiedEl) verifiedEl.textContent = metrics.claims_verified || 0;
    if (contraEl) contraEl.textContent = metrics.claims_contradicted || 0;
    if (corrEl) corrEl.textContent = metrics.corrections_applied || 0;
  }

  renderClaimsTable(claims) {
    const tbody = this.container.querySelector('#claims-table-body');
    const badge = this.container.querySelector('#claims-count-badge');
    if (badge) badge.textContent = `${claims.length} claims`;

    if (!tbody) return;
    if (claims.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No claims registered yet.</td></tr>';
      return;
    }

    tbody.innerHTML = claims.map((c) => {
      const statusBadge = this.getStatusBadge(c.truth_status);
      const confBadge = c.confidence === 'HIGH' ? 'badge-success' : (c.confidence === 'MEDIUM' ? 'badge-warning' : 'badge-secondary');
      return `
        <tr>
          <td><code>${escapeHtml(c.claim_id)}</code></td>
          <td><strong>${escapeHtml(c.statement)}</strong></td>
          <td><span class="badge badge-outline">${escapeHtml(c.claim_type)}</span></td>
          <td>${statusBadge}</td>
          <td><span class="badge ${confBadge}">${escapeHtml(c.confidence)}</span></td>
          <td>${(c.evidence_refs || []).length} refs</td>
          <td>
            <button class="btn btn-sm btn-outline" data-action="triangulate" data-id="${escapeHtml(c.claim_id)}">Triangulate</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  getStatusBadge(truthStatus) {
    switch (truthStatus) {
      case 'VERIFIED':
        return '<span class="badge badge-success">VERIFIED</span>';
      case 'SUPPORTED':
        return '<span class="badge badge-info">SUPPORTED</span>';
      case 'CONTRADICTED':
        return '<span class="badge badge-danger">CONTRADICTED</span>';
      case 'STALE':
        return '<span class="badge badge-warning">STALE</span>';
      case 'INVALID':
      case 'REJECTED':
        return '<span class="badge badge-danger">' + escapeHtml(truthStatus) + '</span>';
      default:
        return '<span class="badge badge-secondary">' + escapeHtml(truthStatus || 'UNVERIFIED') + '</span>';
    }
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

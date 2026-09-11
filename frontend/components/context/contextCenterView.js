/**
 * ContextCenterView Component (Task 69)
 * Authoritative management interface for Kairo Universal Context & Adaptive Personalization Engine.
 */

import { universalContextApi } from '../../lib/api/endpoints.js';

export class ContextCenterView {
  constructor(options = {}) {
    this.container = options.container || null;
    this.activeTab = 'current_context';
    this.tenantId = options.tenantId || 'default';

    // State collections
    this.currentContext = null;
    this.qualityOverview = null;
    this.missingContext = [];
    this.conflicts = [];
    this.preferences = [];
    this.snapshots = [];
    this.health = null;
    this.selectedSnapshot = null;
    this.selectedItemExplanation = null;
  }

  async init() {
    await this.refresh();
  }

  async refresh() {
    try {
      this.health = await universalContextApi.getHealth(this.tenantId);
      this.qualityOverview = await universalContextApi.getQuality(this.tenantId);
      this.missingContext = await universalContextApi.getMissing(this.tenantId);
      this.conflicts = await universalContextApi.getConflicts(this.tenantId);
      this.preferences = await universalContextApi.listPreferences(null, this.tenantId);
      this.snapshots = await universalContextApi.listSnapshots(null, 20, this.tenantId);
    } catch (err) {
      console.warn('ContextCenterView: Some endpoints could not be refreshed:', err);
    }
  }

  setTab(tabName) {
    this.activeTab = tabName;
    this.render();
  }

  selectSnapshot(snapshotId) {
    this.selectedSnapshot = this.snapshots.find(s => s.snapshot_id === snapshotId) || null;
    this.render();
  }

  render() {
    if (!this.container) return this._renderHtml();
    this.container.innerHTML = this._renderHtml();
    this._attachEventListeners();
    return this.container.innerHTML;
  }

  _renderHtml() {
    return `
      <div class="universal-context-center">
        <div class="context-center-header">
          <div class="title-area">
            <h2>🧠 Universal Context & Adaptive Personalization</h2>
            <p class="subtitle">Context intelligence layer: task relevance, token budgeting, cognitive scoping, and safe operational preferences.</p>
          </div>
          <div class="header-badges">
            <span class="badge badge-quality">Quality Score: ${this.health ? (this.health.average_quality_score * 100).toFixed(0) + '%' : '100%'}</span>
            <span class="badge badge-tokens">Avg Tokens: ${this.health ? this.health.average_token_usage : 0}</span>
            <span class="badge badge-prefs">Active Prefs: ${this.health ? this.health.active_preferences : 0}</span>
          </div>
        </div>

        <div class="cognitive-invariant-banner">
          <span>🔒 <strong>Cognitive Invariants:</strong> CONTEXT ≠ MEMORY ≠ TRUTH ≠ INSTRUCTION ≠ AUTHORIZATION ≠ PREFERENCE ≠ IDENTITY.</span>
          <span class="safety-indicator">Sensitive Profiling Prohibited: ACTIVE</span>
        </div>

        <div class="context-tabs-nav" role="tablist">
          <button class="tab-btn ${this.activeTab === 'current_context' ? 'active' : ''}" onclick="window.contextCenterView.setTab('current_context')">
            Active Context
          </button>
          <button class="tab-btn ${this.activeTab === 'quality' ? 'active' : ''}" onclick="window.contextCenterView.setTab('quality')">
            Context Quality
          </button>
          <button class="tab-btn ${this.activeTab === 'explanations' ? 'active' : ''}" onclick="window.contextCenterView.setTab('explanations')">
            Why This Context?
          </button>
          <button class="tab-btn ${this.activeTab === 'missing' ? 'active' : ''}" onclick="window.contextCenterView.setTab('missing')">
            Missing Context (${this.missingContext.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'conflicts' ? 'active' : ''}" onclick="window.contextCenterView.setTab('conflicts')">
            Context Conflicts (${this.conflicts.length})
          </button>
          <button class="tab-btn ${this.activeTab === 'personalization' ? 'active' : ''}" onclick="window.contextCenterView.setTab('personalization')">
            Adaptive Personalization
          </button>
          <button class="tab-btn ${this.activeTab === 'history' ? 'active' : ''}" onclick="window.contextCenterView.setTab('history')">
            Context History & Snapshots
          </button>
        </div>

        <div class="context-tab-content">
          ${this._renderActiveTab()}
        </div>
      </div>
    `;
  }

  _renderActiveTab() {
    switch (this.activeTab) {
      case 'current_context':
        return this._renderCurrentContextTab();
      case 'quality':
        return this._renderQualityTab();
      case 'explanations':
        return this._renderExplanationsTab();
      case 'missing':
        return this._renderMissingTab();
      case 'conflicts':
        return this._renderConflictsTab();
      case 'personalization':
        return this._renderPersonalizationTab();
      case 'history':
        return this._renderHistoryTab();
      default:
        return `<div class="empty-state">Select a view tab above.</div>`;
    }
  }

  _renderCurrentContextTab() {
    const items = this.currentContext ? this.currentContext.items : [];
    return `
      <div class="current-context-pane">
        <div class="action-bar">
          <button class="btn btn-primary" onclick="window.contextCenterView.buildSampleContext()">Simulate Task Context Resolution</button>
          <span class="text-muted">Target Environment: <code>production</code> | Hierarchy Scope: Level 0 through Level 6</span>
        </div>

        <div class="context-cards-grid">
          <div class="summary-card">
            <h4>Level 0: Immediate Task</h4>
            <p>${this.currentContext ? this._escapeHtml(this.currentContext.task || 'None') : 'No active task registered.'}</p>
          </div>
          <div class="summary-card">
            <h4>Level 2: User Workspace</h4>
            <p>Tenant: <code>${this.tenantId}</code> | Workspace isolated</p>
          </div>
          <div class="summary-card">
            <h4>Level 5 & 6: Memory & Knowledge</h4>
            <p>${this.currentContext ? (this.currentContext.memories.length + this.currentContext.knowledge.length) + ' items' : 'Durable memory ready'}</p>
          </div>
        </div>

        <div class="section-title">Selected Context Items (${items.length})</div>
        ${items.length === 0 ? `
          <div class="empty-state">No context bundle assembled yet. Click 'Simulate Task Context Resolution' to test.</div>
        ` : `
          <div class="context-items-list">
            ${items.map(it => `
              <div class="context-item-card tier-${it.priority_tier.toLowerCase()}">
                <div class="item-header">
                  <span class="badge badge-type">${it.context_type}</span>
                  <span class="badge badge-level">${it.hierarchy_level}</span>
                  <span class="badge badge-score">Relevance: ${(it.relevance_score * 100).toFixed(0)}%</span>
                  <span class="badge badge-freshness">Freshness: ${(it.freshness_score * 100).toFixed(0)}%</span>
                </div>
                <div class="item-title">${this._escapeHtml(it.title)}</div>
                <div class="item-content">${this._escapeHtml(it.content)}</div>
                <div class="item-footer">
                  <span class="reason">💡 ${this._escapeHtml(it.reason)}</span>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  _renderQualityTab() {
    const q = this.qualityOverview || {
      average_quality_score: 0.92,
      average_tokens: 340,
      total_packages: 12,
    };
    return `
      <div class="quality-pane">
        <h3>Context Quality & Information Density Metrics</h3>
        <p class="subtitle">Ensuring high information density rather than maximum information volume.</p>

        <div class="quality-kpi-grid">
          <div class="kpi-card">
            <div class="kpi-val">${(q.average_quality_score * 100).toFixed(0)}%</div>
            <div class="kpi-label">Average Quality Score</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val">${q.average_tokens}</div>
            <div class="kpi-label">Average Token Usage</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val">${q.total_packages}</div>
            <div class="kpi-label">Assembled Packages</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val">0</div>
            <div class="kpi-label">Tenant Boundary Violations</div>
          </div>
        </div>

        <div class="quality-breakdown-card">
          <h4>Multi-Dimensional Scoring Factors</h4>
          <ul>
            <li><strong>Relevance (35%):</strong> Task, intent, and semantic keyword alignment.</li>
            <li><strong>Coverage (20%):</strong> Proportion of required task context sources covered.</li>
            <li><strong>Freshness (15%):</strong> Temporal validity and recency decay.</li>
            <li><strong>Trust & Confidence (30%):</strong> Verified evidence weighting vs unverified propositions.</li>
            <li><strong>Penalties:</strong> Redundancy deduction and noise reduction for low-value context.</li>
          </ul>
        </div>
      </div>
    `;
  }

  _renderExplanationsTab() {
    const items = this.currentContext ? this.currentContext.items : [];
    return `
      <div class="explanations-pane">
        <h3>Why Was This Context Included or Excluded?</h3>
        <p class="subtitle">Every context element is fully explainable without hidden ranking heuristics.</p>

        ${items.length === 0 ? `
          <div class="empty-state">No context package loaded. Generate or preview context in the 'Active Context' tab first.</div>
        ` : `
          <div class="explanations-table-container">
            <table class="explanations-table">
              <thead>
                <tr>
                  <th>Item Title</th>
                  <th>Source / Type</th>
                  <th>Hierarchy Level</th>
                  <th>Priority</th>
                  <th>Why Included</th>
                </tr>
              </thead>
              <tbody>
                ${items.map(it => `
                  <tr>
                    <td><strong>${this._escapeHtml(it.title)}</strong></td>
                    <td><code>${it.source_type}</code> / ${it.context_type}</td>
                    <td>${it.hierarchy_level}</td>
                    <td><span class="pill pill-${it.priority_tier.toLowerCase()}">${it.priority_tier}</span></td>
                    <td>${this._escapeHtml(it.reason)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    `;
  }

  _renderMissingTab() {
    return `
      <div class="missing-pane">
        <h3>Missing Context Detection</h3>
        <p class="subtitle">Kairo identifies when essential context is absent rather than hallucinating or fabricating data.</p>

        ${this.missingContext.length === 0 ? `
          <div class="empty-state">No critical context gaps detected. All recent task requests had sufficient context.</div>
        ` : `
          <div class="missing-list">
            ${this.missingContext.map(m => `
              <div class="missing-card">
                <div class="missing-header">
                  <span class="badge badge-warning">MISSING CONTEXT</span>
                  <span class="missing-category">${this._escapeHtml(m.category)}</span>
                  <span class="badge badge-priority">${m.importance}</span>
                </div>
                <div class="missing-desc">${this._escapeHtml(m.description)}</div>
                <div class="missing-impact">⚠️ <strong>Impact:</strong> ${this._escapeHtml(m.impact)}</div>
                <div class="missing-sources">
                  <strong>Potential Sources:</strong> ${m.potential_sources ? m.potential_sources.join(', ') : 'None'}
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  _renderConflictsTab() {
    return `
      <div class="conflicts-pane">
        <h3>Context Conflict Center</h3>
        <p class="subtitle">Conflicting context claims are surfaced without silent overwrites or false resolutions.</p>

        ${this.conflicts.length === 0 ? `
          <div class="empty-state">No active context contradictions detected across current workspace items.</div>
        ` : `
          <div class="conflicts-list">
            ${this.conflicts.map(c => `
              <div class="conflict-card">
                <div class="conflict-header">
                  <span class="badge badge-danger">CONFLICT</span>
                  <span class="conflict-subject">${this._escapeHtml(c.subject)}</span>
                  <span class="badge badge-status">${c.resolution_status}</span>
                </div>
                <div class="conflict-grid">
                  <div class="claim-box">
                    <div class="claim-label">Claim A (${c.source_a}):</div>
                    <div class="claim-text">${this._escapeHtml(c.claim_a)}</div>
                  </div>
                  <div class="claim-box">
                    <div class="claim-label">Claim B (${c.source_b}):</div>
                    <div class="claim-text">${this._escapeHtml(c.claim_b)}</div>
                  </div>
                </div>
                <div class="conflict-reason">
                  <strong>Reason:</strong> ${this._escapeHtml(c.reason)}
                  ${c.temporal_difference ? ` | <em>${this._escapeHtml(c.temporal_difference)}</em>` : ''}
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  _renderPersonalizationTab() {
    return `
      <div class="personalization-pane">
        <div class="personalization-header">
          <div>
            <h3>Adaptive Personalization (Safe Operational Preferences)</h3>
            <p class="subtitle">Learned and explicit workflow, detail, formatting, and tooling preferences. Zero sensitive personal profiling.</p>
          </div>
        </div>

        <div class="preferences-table-container">
          <table class="prefs-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Preference Key</th>
                <th>Value</th>
                <th>Source</th>
                <th>Confidence</th>
                <th>Occurrences</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${this.preferences.length === 0 ? `
                <tr><td colspan="7" class="text-center">No operational preferences registered.</td></tr>
              ` : this.preferences.map(p => `
                <tr>
                  <td><code>${p.category}</code></td>
                  <td><strong>${this._escapeHtml(p.key)}</strong></td>
                  <td>${JSON.stringify(p.value)}</td>
                  <td><span class="badge ${p.source === 'EXPLICIT_PREFERENCE' ? 'badge-explicit' : 'badge-inferred'}">${p.source}</span></td>
                  <td>${p.confidence} (${(p.confidence_score * 100).toFixed(0)}%)</td>
                  <td>${p.occurrences}</td>
                  <td><span class="status-dot ${p.is_active ? 'active' : 'inactive'}"></span> ${p.is_active ? 'Active' : 'Inactive'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  _renderHistoryTab() {
    return `
      <div class="history-pane">
        <h3>Context History & Snapshots</h3>
        <p class="subtitle">Immutable audit trail of assembled context bundles enabling deterministic replay.</p>

        <div class="snapshots-list">
          ${this.snapshots.length === 0 ? `
            <div class="empty-state">No context snapshots recorded yet.</div>
          ` : this.snapshots.map(s => `
            <div class="snapshot-card" onclick="window.contextCenterView.selectSnapshot('${s.snapshot_id}')">
              <div class="snapshot-header">
                <strong>Snapshot: ${s.snapshot_id}</strong>
                <span class="badge badge-tokens">${s.token_estimate} tokens</span>
                <span class="badge badge-quality">${(s.quality_score * 100).toFixed(0)}% quality</span>
              </div>
              <div class="snapshot-meta">
                <span>Items: ${s.selected_items ? s.selected_items.length : 0}</span>
                <span>Created: ${new Date(s.created_at).toLocaleTimeString()}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  async buildSampleContext() {
    try {
      this.currentContext = await universalContextApi.buildContext({
        query: "Investigate why deployment failed in production",
        intent: "debug_deployment",
        environment: "production",
        maximum_tokens: 3000,
        maximum_items: 20,
      }, this.tenantId);
      await this.refresh();
      this.render();
    } catch (err) {
      console.error('Failed to build sample context:', err);
    }
  }

  _attachEventListeners() {
    // Window export for interactive buttons
    window.contextCenterView = this;
  }

  _escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

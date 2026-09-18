/**
 * CognitiveWorkingSetView Component (Task 110)
 * Control Center interface for Cognitive Working Sets, Context Assembly, Relevance Packing,
 * Freshness, Provenance Lineage, and Context Lifecycle.
 */

import { workingSetApi } from '../../lib/api/endpoints.js';

export class CognitiveWorkingSetView {
  constructor(options = {}) {
    this.container = options.container || null;
    this.activeTab = 'items'; // items, sections, conflicts_gaps, quality, snapshot
    this.selectedSection = 'ALL';
    this.workingSets = [];
    this.activeWorkingSet = null;
    this.qualityAssessment = null;
    this.snapshot = null;
    this.selectedItem = null;
    this.loading = false;
    this.error = null;
  }

  async init() {
    await this.refresh();
  }

  async refresh() {
    this.loading = true;
    this.error = null;
    try {
      this.workingSets = await workingSetApi.listWorkingSets();
      if (this.workingSets.length > 0 && !this.activeWorkingSet) {
        await this.selectWorkingSet(this.workingSets[0].working_set_id);
      } else if (this.activeWorkingSet) {
        await this.selectWorkingSet(this.activeWorkingSet.working_set_id);
      }
    } catch (err) {
      console.warn('CognitiveWorkingSetView: Refresh error:', err);
      this.error = err.message || 'Failed to load working sets';
    } finally {
      this.loading = false;
      this.render();
    }
  }

  async selectWorkingSet(workingSetId) {
    try {
      this.activeWorkingSet = await workingSetApi.getWorkingSet(workingSetId);
      try {
        this.qualityAssessment = await workingSetApi.getQuality(workingSetId);
      } catch (qErr) {
        this.qualityAssessment = null;
      }
      try {
        this.snapshot = await workingSetApi.getWorkingSetSnapshot(workingSetId);
      } catch (sErr) {
        this.snapshot = null;
      }
      this.selectedItem = null;
    } catch (err) {
      this.error = `Could not load working set: ${err.message}`;
    }
    this.render();
  }

  setTab(tabName) {
    this.activeTab = tabName;
    this.render();
  }

  setSectionFilter(section) {
    this.selectedSection = section;
    this.render();
  }

  selectItem(itemId) {
    if (!this.activeWorkingSet) return;
    for (const sec of Object.values(this.activeWorkingSet.sections)) {
      const found = sec.items.find(i => i.item_id === itemId);
      if (found) {
        this.selectedItem = found;
        break;
      }
    }
    this.render();
  }

  async handlePin(itemId) {
    if (!this.activeWorkingSet) return;
    try {
      await workingSetApi.pinItem(this.activeWorkingSet.working_set_id, itemId);
      await this.selectWorkingSet(this.activeWorkingSet.working_set_id);
    } catch (err) {
      alert(`Pin failed: ${err.message}`);
    }
  }

  async handleUnpin(itemId) {
    if (!this.activeWorkingSet) return;
    try {
      await workingSetApi.unpinItem(this.activeWorkingSet.working_set_id, itemId);
      await this.selectWorkingSet(this.activeWorkingSet.working_set_id);
    } catch (err) {
      alert(`Unpin failed: ${err.message}`);
    }
  }

  async handleRefresh() {
    if (!this.activeWorkingSet) return;
    try {
      await workingSetApi.refreshWorkingSet(this.activeWorkingSet.working_set_id);
      await this.refresh();
    } catch (err) {
      alert(`Refresh failed: ${err.message}`);
    }
  }

  async handleInvalidate() {
    if (!this.activeWorkingSet) return;
    if (!confirm('Are you sure you want to invalidate this working set? Downstream cognition will fail-closed until revalidated.')) return;
    try {
      await workingSetApi.invalidateWorkingSet(this.activeWorkingSet.working_set_id, 'User manually invalidated');
      await this.selectWorkingSet(this.activeWorkingSet.working_set_id);
    } catch (err) {
      alert(`Invalidation failed: ${err.message}`);
    }
  }

  render() {
    if (!this.container) return this._renderHtml();
    this.container.innerHTML = this._renderHtml();
    this._attachEventListeners();
    return this.container.innerHTML;
  }

  _renderHtml() {
    const ws = this.activeWorkingSet;

    return `
      <div class="cognitive-working-set-view">
        <!-- Header -->
        <div class="cws-header">
          <div class="cws-title-area">
            <h2>🧠 Cognitive Working Set & Context Assembly</h2>
            <p class="subtitle">Task 110: Bounded working sets, relevance packing, provenance lineage, freshness decay, and context lifecycle.</p>
          </div>
          <div class="cws-header-actions">
            ${ws ? `
              <button class="btn btn-secondary btn-refresh" id="cws-btn-refresh">🔄 Refresh & Revalidate</button>
              <button class="btn btn-danger btn-invalidate" id="cws-btn-invalidate">⛔ Invalidate Fail-Closed</button>
            ` : ''}
          </div>
        </div>

        ${this.error ? `<div class="alert alert-danger">${this.error}</div>` : ''}

        <!-- Working Set Selector & Metric Ribbon -->
        <div class="cws-control-ribbon">
          <div class="ws-picker">
            <label for="cws-select-ws"><strong>Active Working Set:</strong></label>
            <select id="cws-select-ws" class="form-select">
              ${this.workingSets.map(w => `
                <option value="${w.working_set_id}" ${ws && ws.working_set_id === w.working_set_id ? 'selected' : ''}>
                  ${w.working_set_id} (v${w.version}) - ${w.operation_type} - ${w.lifecycle}
                </option>
              `).join('')}
              ${this.workingSets.length === 0 ? '<option value="">No working sets found</option>' : ''}
            </select>
          </div>

          ${ws ? `
            <div class="ws-badges">
              <span class="badge badge-${this._getLifecycleBadgeClass(ws.lifecycle)}">State: ${ws.lifecycle}</span>
              <span class="badge badge-${ws.lease_state === 'VALID' ? 'success' : 'warning'}">Lease: ${ws.lease_state}</span>
              <span class="badge badge-tokens">Tokens: ${ws.total_tokens}</span>
              <span class="badge badge-items">Items: ${ws.item_count}</span>
              <span class="badge badge-quality">Quality: ${(ws.quality_score * 100).toFixed(0)}%</span>
              ${ws.has_untrusted_content ? '<span class="badge badge-danger">⚠️ Untrusted Ingested</span>' : ''}
            </div>
          ` : ''}
        </div>

        ${ws ? `
          <!-- Active Task Context Banner -->
          <div class="cws-objective-card">
            <h4>🎯 Operation Objective: <span class="badge badge-info">${ws.operation_type}</span></h4>
            <p class="objective-text">${this._escapeHtml(ws.objective)}</p>
            <div class="meta-row">
              <small>Request ID: <code>${ws.request_id}</code> | Trace ID: <code>${ws.trace_id}</code> | Created: ${new Date(ws.created_at).toLocaleTimeString()}</small>
            </div>
          </div>

          <!-- Navigation Tabs -->
          <div class="cws-tabs">
            <button class="tab-btn ${this.activeTab === 'items' ? 'active' : ''}" data-tab="items">Working Set Items (${ws.item_count})</button>
            <button class="tab-btn ${this.activeTab === 'sections' ? 'active' : ''}" data-tab="sections">Sections (${Object.keys(ws.sections).length})</button>
            <button class="tab-btn ${this.activeTab === 'conflicts_gaps' ? 'active' : ''}" data-tab="conflicts_gaps">Conflicts & Gaps (${ws.conflicts_count + ws.gaps_count})</button>
            <button class="tab-btn ${this.activeTab === 'quality' ? 'active' : ''}" data-tab="quality">Quality Scorecard</button>
            <button class="tab-btn ${this.activeTab === 'snapshot' ? 'active' : ''}" data-tab="snapshot">Audit Snapshot</button>
          </div>

          <!-- Tab Contents -->
          <div class="cws-tab-content">
            ${this.activeTab === 'items' ? this._renderItemsTab(ws) : ''}
            ${this.activeTab === 'sections' ? this._renderSectionsTab(ws) : ''}
            ${this.activeTab === 'conflicts_gaps' ? this._renderConflictsGapsTab(ws) : ''}
            ${this.activeTab === 'quality' ? this._renderQualityTab() : ''}
            ${this.activeTab === 'snapshot' ? this._renderSnapshotTab() : ''}
          </div>
        ` : `
          <div class="empty-state">
            <p>No cognitive working sets currently loaded. Use the CLI or trigger an autonomous operation to assemble one.</p>
          </div>
        `}

        <!-- Item Detail Drawer / Modal -->
        ${this.selectedItem ? this._renderItemDetailDrawer(this.selectedItem) : ''}
      </div>
    `;
  }

  _renderItemsTab(ws) {
    // Gather all items across sections
    let allItems = [];
    for (const sec of Object.values(ws.sections)) {
      allItems = allItems.concat(sec.items);
    }

    const filteredItems = this.selectedSection === 'ALL'
      ? allItems
      : allItems.filter(i => i.section === this.selectedSection);

    return `
      <div class="items-view-container">
        <div class="filter-bar">
          <label>Filter by Section:</label>
          <select id="cws-filter-section" class="form-select form-select-sm">
            <option value="ALL" ${this.selectedSection === 'ALL' ? 'selected' : ''}>All Sections (${allItems.length})</option>
            ${Object.entries(ws.sections).map(([k, s]) => `
              <option value="${k}" ${this.selectedSection === k ? 'selected' : ''}>${s.title} (${s.item_count})</option>
            `).join('')}
          </select>
        </div>

        <table class="table cws-items-table">
          <thead>
            <tr>
              <th>Title & Section</th>
              <th>Inclusion</th>
              <th>Relevance</th>
              <th>Freshness</th>
              <th>Provenance / Trust</th>
              <th>Compression</th>
              <th>Tokens</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${filteredItems.map(item => `
              <tr class="${item.is_untrusted ? 'row-untrusted' : ''} ${item.is_pinned ? 'row-pinned' : ''}">
                <td>
                  <strong>${this._escapeHtml(item.title)}</strong>
                  <br/><small class="text-muted">${item.section} [v${item.version}]</small>
                </td>
                <td>
                  <span class="badge badge-${this._getInclusionBadgeClass(item.inclusion)}">${item.inclusion}</span>
                  ${item.is_pinned ? '<span class="badge badge-pinned">📌 PINNED</span>' : ''}
                </td>
                <td>
                  <div class="progress-bar-container">
                    <div class="progress-fill" style="width: ${(item.relevance_score * 100).toFixed(0)}%"></div>
                  </div>
                  <small>${item.relevance_score.toFixed(2)}</small>
                </td>
                <td>
                  <span class="badge badge-${this._getFreshnessBadgeClass(item.freshness_classification)}">
                    ${item.freshness_classification}
                  </span>
                </td>
                <td>
                  <span class="badge badge-source">${item.provenance_source}</span>
                  <br/><small class="trust-${item.trust_label.toLowerCase()}">${item.trust_label}</small>
                </td>
                <td>
                  <span class="badge badge-compression">${item.compression_level}</span>
                </td>
                <td>${item.token_estimate}</td>
                <td>
                  <button class="btn btn-xs btn-outline btn-inspect-item" data-id="${item.item_id}">Inspect</button>
                  ${item.is_pinned ? `
                    <button class="btn btn-xs btn-outline-warning btn-unpin-item" data-id="${item.item_id}">Unpin</button>
                  ` : `
                    <button class="btn btn-xs btn-outline-primary btn-pin-item" data-id="${item.item_id}">Pin</button>
                  `}
                </td>
              </tr>
            `).join('')}
            ${filteredItems.length === 0 ? '<tr><td colspan="8" class="text-center">No items match section filter</td></tr>' : ''}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderSectionsTab(ws) {
    return `
      <div class="sections-grid">
        ${Object.entries(ws.sections).map(([secType, sec]) => `
          <div class="section-card ${sec.is_empty ? 'section-empty' : ''}">
            <div class="section-card-header">
              <h5>${sec.title}</h5>
              <span class="badge badge-info">${sec.item_count} items | ${sec.total_tokens} tokens</span>
            </div>
            <div class="section-card-body">
              ${sec.items.slice(0, 3).map(i => `
                <div class="section-mini-item">
                  <strong>${this._escapeHtml(i.title)}</strong>
                  <span class="text-muted">(${i.token_estimate} tokens)</span>
                </div>
              `).join('')}
              ${sec.item_count > 3 ? `<small class="text-muted">+ ${sec.item_count - 3} more items...</small>` : ''}
              ${sec.is_empty ? '<p class="text-muted">Section empty in this working set.</p>' : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  _renderConflictsGapsTab(ws) {
    return `
      <div class="conflicts-gaps-container">
        <!-- Conflicts Panel -->
        <div class="panel-conflicts">
          <h4>⚖️ Preserved Epistemic Conflicts (${ws.conflicts_count})</h4>
          <p class="subtitle">Conflicts are surfaced explicitly without hallucinating false consensus.</p>
          ${ws.conflicts_count === 0 ? '<p class="text-muted">No unresolved conflicts active in this working set.</p>' : ''}
        </div>

        <!-- Gaps Panel -->
        <div class="panel-gaps">
          <h4>🧩 Identified Context Gaps (${ws.gaps_count})</h4>
          <p class="subtitle">Explicit missing information required for high-confidence reasoning.</p>
          ${ws.gaps_count === 0 ? '<p class="text-muted">No context gaps identified.</p>' : ''}
        </div>
      </div>
    `;
  }

  _renderQualityTab() {
    const q = this.qualityAssessment;
    if (!q) return '<p class="text-muted">Quality scorecard not yet computed.</p>';

    const dimensions = [
      { name: 'Relevance Score', val: q.relevance_score },
      { name: 'Freshness Score', val: q.freshness_score },
      { name: 'Completeness Score', val: q.completeness_score },
      { name: 'Provenance Coverage', val: q.provenance_coverage_score },
      { name: 'Contradiction Visibility', val: q.contradiction_visibility_score },
      { name: 'Compression Quality', val: q.compression_quality_score },
      { name: 'Budget Efficiency', val: q.budget_efficiency_score },
      { name: 'Source Diversity', val: q.source_diversity_score },
      { name: 'Task Alignment', val: q.task_alignment_score },
      { name: 'Safety Coverage', val: q.safety_coverage_score },
    ];

    return `
      <div class="quality-dashboard">
        <div class="composite-score-badge">
          <h3>Overall Quality: ${(q.composite_quality * 100).toFixed(1)}%</h3>
          <small>Evaluated across 13 objective dimensions</small>
        </div>

        <div class="dimension-grid">
          ${dimensions.map(d => `
            <div class="dim-card">
              <div class="dim-header">
                <span>${d.name}</span>
                <strong>${(d.val * 100).toFixed(0)}%</strong>
              </div>
              <div class="progress-bar-container">
                <div class="progress-fill" style="width: ${(d.val * 100).toFixed(0)}%"></div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _renderSnapshotTab() {
    const snap = this.snapshot;
    if (!snap) return '<p class="text-muted">No audit snapshot found for this working set.</p>';

    return `
      <div class="snapshot-card">
        <h4>🔒 Immutable Audit Context Snapshot</h4>
        <p class="subtitle">Cryptographic fingerprint proving exact context available at decision time.</p>
        <table class="table">
          <tr><th>Snapshot ID:</th><td><code>${snap.snapshot_id}</code></td></tr>
          <tr><th>Fingerprint (SHA-256):</th><td><code>${snap.snapshot_hash}</code></td></tr>
          <tr><th>Working Set Version:</th><td>v${snap.working_set_version}</td></tr>
          <tr><th>Item Count:</th><td>${snap.item_ids.length} items</td></tr>
          <tr><th>Total Tokens:</th><td>${snap.total_tokens}</td></tr>
          <tr><th>Created At:</th><td>${new Date(snap.created_at).toLocaleString()}</td></tr>
        </table>
      </div>
    `;
  }

  _renderItemDetailDrawer(item) {
    return `
      <div class="item-detail-drawer">
        <div class="drawer-header">
          <h4>Item Detail: ${this._escapeHtml(item.title)}</h4>
          <button class="btn btn-close" id="cws-close-drawer">✕</button>
        </div>
        <div class="drawer-body">
          <div class="meta-block">
            <span class="badge badge-source">${item.provenance_source}</span>
            <span class="badge badge-trust">${item.trust_label}</span>
            <span class="badge badge-${this._getFreshnessBadgeClass(item.freshness_classification)}">${item.freshness_classification}</span>
            <span class="badge badge-tokens">${item.token_estimate} tokens</span>
          </div>
          <h5>Content Payload:</h5>
          <pre class="content-preview">${this._escapeHtml(item.content)}</pre>
          <h5>Relevance Component Breakdown:</h5>
          <pre class="json-preview">${JSON.stringify(item.relevance_components, null, 2)}</pre>
        </div>
      </div>
    `;
  }

  _attachEventListeners() {
    if (!this.container) return;

    // Working set dropdown
    const selectWs = this.container.querySelector('#cws-select-ws');
    if (selectWs) {
      selectWs.addEventListener('change', (e) => {
        if (e.target.value) this.selectWorkingSet(e.target.value);
      });
    }

    // Tab buttons
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => this.setTab(btn.dataset.tab));
    });

    // Section filter
    const filterSec = this.container.querySelector('#cws-filter-section');
    if (filterSec) {
      filterSec.addEventListener('change', (e) => this.setSectionFilter(e.target.value));
    }

    // Refresh button
    const btnRefresh = this.container.querySelector('#cws-btn-refresh');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => this.handleRefresh());
    }

    // Invalidate button
    const btnInvalidate = this.container.querySelector('#cws-btn-invalidate');
    if (btnInvalidate) {
      btnInvalidate.addEventListener('click', () => this.handleInvalidate());
    }

    // Inspect buttons
    this.container.querySelectorAll('.btn-inspect-item').forEach(btn => {
      btn.addEventListener('click', () => this.selectItem(btn.dataset.id));
    });

    // Pin buttons
    this.container.querySelectorAll('.btn-pin-item').forEach(btn => {
      btn.addEventListener('click', () => this.handlePin(btn.dataset.id));
    });

    // Unpin buttons
    this.container.querySelectorAll('.btn-unpin-item').forEach(btn => {
      btn.addEventListener('click', () => this.handleUnpin(btn.dataset.id));
    });

    // Close drawer
    const btnCloseDrawer = this.container.querySelector('#cws-close-drawer');
    if (btnCloseDrawer) {
      btnCloseDrawer.addEventListener('click', () => {
        this.selectedItem = null;
        this.render();
      });
    }
  }

  _getLifecycleBadgeClass(lifecycle) {
    const map = {
      'READY': 'success',
      'IN_USE': 'primary',
      'VALIDATING': 'info',
      'ASSEMBLING': 'info',
      'DRAFT': 'secondary',
      'REFRESHING': 'warning',
      'EXPIRED': 'warning',
      'INVALIDATED': 'danger',
      'FAILED': 'danger',
    };
    return map[lifecycle] || 'secondary';
  }

  _getInclusionBadgeClass(inclusion) {
    const map = {
      'REQUIRED': 'danger',
      'IMPORTANT': 'warning',
      'OPTIONAL': 'secondary',
      'REFERENCE_ONLY': 'info',
      'EXCLUDED': 'dark',
    };
    return map[inclusion] || 'secondary';
  }

  _getFreshnessBadgeClass(freshness) {
    const map = {
      'FRESH': 'success',
      'RECENT': 'info',
      'AGING': 'warning',
      'STALE': 'danger',
      'EXPIRED': 'dark',
    };
    return map[freshness] || 'secondary';
  }

  _escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

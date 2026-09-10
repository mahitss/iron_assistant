/**
 * Kairo Self-Modeling, Metacognition & Self-Correction Engine View (Task 51)
 * Visualizes operational capabilities, limitations, uncertainty, introspection console,
 * reflections, and resource awareness.
 * Strictly enforces that SelfModel is operational system metadata and NOT consciousness.
 */

import { Endpoints } from '../../lib/api/endpoints.js';

export class MetacognitionView {
  constructor(container) {
    this.container = container;
    this.selfModel = null;
    this.capabilities = [];
    this.limitations = [];
    this.reflections = [];
    this.metrics = null;
    this.activeTab = 'capabilities';
    this.isLoading = false;
    this.introspectionResult = null;
  }

  formatDate(isoStr) {
    if (!isoStr) return 'N/A';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  getCapabilityBadgeClass(state) {
    switch (state) {
      case 'AVAILABLE':
        return 'badge-success';
      case 'RESTRICTED':
      case 'REQUIRES_APPROVAL':
      case 'REQUIRES_AUTHORIZATION':
        return 'badge-warning';
      case 'DEGRADED':
      case 'TEMPORARILY_DISABLED':
        return 'badge-danger';
      case 'UNAVAILABLE':
      default:
        return 'badge-neutral';
    }
  }

  getLimitationSeverityClass(severity) {
    switch (severity) {
      case 'BLOCKING':
        return 'badge-danger';
      case 'HIGH':
        return 'badge-warning';
      case 'MEDIUM':
        return 'badge-info';
      case 'LOW':
      default:
        return 'badge-neutral';
    }
  }

  async loadData() {
    this.isLoading = true;
    try {
      const [modelRes, capsRes, limitsRes, metricsRes] = await Promise.all([
        Endpoints.getSelfModel(),
        Endpoints.listCapabilities(),
        Endpoints.listLimitations(),
        Endpoints.getMetacognitiveMetrics(),
      ]);
      this.selfModel = modelRes;
      this.capabilities = capsRes || [];
      this.limitations = limitsRes || [];
      this.metrics = metricsRes;
    } catch (err) {
      console.error('Failed to load metacognition telemetry:', err);
    } finally {
      this.isLoading = false;
    }
  }

  async handleIntrospect(questionType, subject = null) {
    try {
      this.introspectionResult = await Endpoints.introspect(questionType, subject);
      this.render();
    } catch (err) {
      alert(`Introspection failed: ${err.message}`);
    }
  }

  render() {
    if (!this.container) return;

    const availableCount = this.capabilities.filter(c => c.state === 'AVAILABLE').length;
    const degradedCount = this.capabilities.filter(c => c.state === 'DEGRADED').length;
    const activeLimitsCount = this.limitations.filter(l => l.status === 'ACTIVE').length;

    this.container.innerHTML = `
      <div class="metacognition-view-container">
        <!-- Header -->
        <header class="metacognition-header">
          <div class="header-left">
            <h2>Metacognition & Operational Self-Model</h2>
            <span class="badge badge-neutral system-model-badge">OPERATIONAL METADATA ONLY (NOT SENTIENT)</span>
          </div>
          <div class="header-actions">
            <button id="btn-refresh-metacog" class="btn btn-secondary">Refresh Telemetry</button>
          </div>
        </header>

        <!-- KPI Summary Cards -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <span class="kpi-label">Available Capabilities</span>
            <span class="kpi-value text-success">${availableCount}</span>
            <span class="kpi-subtext">${this.capabilities.length} total registered</span>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">Degraded Capabilities</span>
            <span class="kpi-value text-danger">${degradedCount}</span>
            <span class="kpi-subtext">Requires attention</span>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">Active Limitations</span>
            <span class="kpi-value text-warning">${activeLimitsCount}</span>
            <span class="kpi-subtext">Actionable boundaries</span>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">Confidence Calibration</span>
            <span class="kpi-value text-info">${this.metrics?.confidence_calibration ?? '1.0'}</span>
            <span class="kpi-subtext">Empirical accuracy factor</span>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-bar">
          <button class="tab-btn ${this.activeTab === 'capabilities' ? 'active' : ''}" data-tab="capabilities">
            Capabilities Matrix
          </button>
          <button class="tab-btn ${this.activeTab === 'limitations' ? 'active' : ''}" data-tab="limitations">
            System Limitations (${activeLimitsCount})
          </button>
          <button class="tab-btn ${this.activeTab === 'introspection' ? 'active' : ''}" data-tab="introspection">
            Introspection Console
          </button>
          <button class="tab-btn ${this.activeTab === 'resources' ? 'active' : ''}" data-tab="resources">
            Resource Awareness
          </button>
        </div>

        <!-- Tab Content -->
        <div class="tab-content">
          ${this.renderActiveTabContent()}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  renderActiveTabContent() {
    if (this.activeTab === 'capabilities') {
      return this.renderCapabilitiesTab();
    } else if (this.activeTab === 'limitations') {
      return this.renderLimitationsTab();
    } else if (this.activeTab === 'introspection') {
      return this.renderIntrospectionTab();
    } else if (this.activeTab === 'resources') {
      return this.renderResourcesTab();
    }
    return '';
  }

  renderCapabilitiesTab() {
    if (this.capabilities.length === 0) {
      return '<div class="empty-state">No registered capabilities.</div>';
    }

    return `
      <div class="capabilities-grid">
        ${this.capabilities.map(c => `
          <div class="capability-card ${c.state === 'DEGRADED' ? 'card-degraded' : ''}">
            <div class="card-header">
              <span class="cap-name">${c.name}</span>
              <span class="badge ${this.getCapabilityBadgeClass(c.state)}">${c.state}</span>
            </div>
            <p class="cap-desc">${c.description}</p>
            <div class="cap-details">
              <div><strong>Tools:</strong> ${c.tools?.length ? c.tools.join(', ') : 'None (service-native)'}</div>
              <div><strong>Services:</strong> ${c.services?.join(', ') || 'N/A'}</div>
              <div><strong>Dependencies:</strong> ${c.dependencies?.join(', ') || 'N/A'}</div>
              ${c.degradation_reason ? `<div class="text-danger mt-1"><strong>Issue:</strong> ${c.degradation_reason}</div>` : ''}
              ${c.alternatives?.length ? `<div class="text-info mt-1"><strong>Alternatives:</strong> ${c.alternatives.join(', ')}</div>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderLimitationsTab() {
    if (this.limitations.length === 0) {
      return '<div class="empty-state">No active operational limitations detected.</div>';
    }

    return `
      <div class="limitations-list">
        ${this.limitations.map(l => `
          <div class="limitation-item">
            <div class="lim-header">
              <span class="badge badge-neutral">${l.category}</span>
              <span class="badge ${this.getLimitationSeverityClass(l.severity)}">${l.severity}</span>
              <span class="lim-date">${this.formatDate(l.detected_at)}</span>
            </div>
            <p class="lim-desc">${l.description}</p>
            ${l.mitigation_suggestion ? `<div class="lim-suggestion"><strong>Actionable Mitigation:</strong> ${l.mitigation_suggestion}</div>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  }

  renderIntrospectionTab() {
    return `
      <div class="introspection-container">
        <div class="introspection-controls">
          <p class="section-lead">Ask Kairo verifiable operational metacognitive questions:</p>
          <div class="btn-group">
            <button class="btn btn-secondary btn-introspect" data-q="WHAT_CAN_YOU_DO">What can you do?</button>
            <button class="btn btn-secondary btn-introspect" data-q="WHY_CANT_YOU" data-subj="code_execution">Why can't you do this?</button>
            <button class="btn btn-secondary btn-introspect" data-q="HOW_SURE" data-subj="auth_system">How sure are you?</button>
            <button class="btn btn-secondary btn-introspect" data-q="DID_YOU_DO_IT" data-subj="deploy_production">Did you actually do it?</button>
            <button class="btn btn-secondary btn-introspect" data-q="WHAT_WENT_WRONG">What went wrong?</button>
          </div>
        </div>

        ${this.introspectionResult ? `
          <div class="introspection-result-card mt-3">
            <div class="result-header">
              <span class="badge badge-info">${this.introspectionResult.question_type}</span>
              <span class="result-confidence">Confidence: ${(this.introspectionResult.confidence * 100).toFixed(0)}%</span>
            </div>
            <div class="result-body">
              <pre>${this.introspectionResult.grounded_answer}</pre>
            </div>
          </div>
        ` : '<div class="hint-box mt-3">Select an introspection question above to inspect verified system state.</div>'}
      </div>
    `;
  }

  renderResourcesTab() {
    const res = this.selfModel?.resource_state || {};
    return `
      <div class="resources-grid">
        <div class="resource-card">
          <h4>Compute & Latency</h4>
          <p><strong>Compute Pressure:</strong> ${res.compute_pressure || 'NORMAL'}</p>
          <p><strong>Memory Pressure:</strong> ${res.memory_pressure || 'NORMAL'}</p>
          <p><strong>Average Latency:</strong> ${res.latency_ms || 45} ms</p>
        </div>
        <div class="resource-card">
          <h4>API Budget & Cost</h4>
          <p><strong>Remaining Budget:</strong> ${res.api_budget_remaining_percent || 100}%</p>
          <p><strong>Estimated Session Cost:</strong> $${(res.cost_usd || 0.0).toFixed(4)} USD</p>
          <p><strong>Active Tokens:</strong> ${res.active_tokens || 0}</p>
        </div>
        <div class="resource-card">
          <h4>Rate Limits</h4>
          <p><strong>Rate Limited Tools:</strong> ${res.rate_limited_tools?.length ? res.rate_limited_tools.join(', ') : 'None'}</p>
        </div>
      </div>
    `;
  }

  bindEvents() {
    const refreshBtn = this.container.querySelector('#btn-refresh-metacog');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        await this.loadData();
        this.render();
      });
    }

    const tabBtns = this.container.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.activeTab = e.currentTarget.getAttribute('data-tab');
        this.render();
      });
    });

    const introBtns = this.container.querySelectorAll('.btn-introspect');
    introBtns.forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const qType = e.currentTarget.getAttribute('data-q');
        const subj = e.currentTarget.getAttribute('data-subj');
        await this.handleIntrospect(qType, subj);
      });
    });
  }
}

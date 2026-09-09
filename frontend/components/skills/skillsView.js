/**
 * SkillsView Component — Kairo Skills & Capability Catalog
 * Interactive catalog dashboard allowing inspection, filtering, and enable/disable toggling of Kairo skills.
 */

import { Endpoints } from '../../lib/api/endpoints.js';
import { store } from '../../state/store.js';

export class SkillsView {
  constructor(container, options = {}) {
    this.container = container;
    this.store = options.store || store;
    this.skills = [];
    this.selectedCategory = 'all';
    this.searchQuery = '';
    this.selectedSkill = null;
    this.isLoading = false;
  }

  async init() {
    await this.loadSkills();
    this.render();
  }

  async loadSkills() {
    this.isLoading = true;
    try {
      this.skills = await Endpoints.listSkills();
    } catch (err) {
      console.error('Failed to fetch skills catalog:', err);
      this.skills = [];
    } finally {
      this.isLoading = false;
    }
  }

  _getFilteredSkills() {
    return this.skills.filter(s => {
      const cat = (s.category || '').toLowerCase();
      const selected = (this.selectedCategory || 'all').toLowerCase();
      const matchCat = selected === 'all' || cat === selected;
      const q = (this.searchQuery || '').toLowerCase();
      const matchQuery = !q ||
        (s.name && s.name.toLowerCase().includes(q)) ||
        (s.id && s.id.toLowerCase().includes(q)) ||
        (s.description && s.description.toLowerCase().includes(q));
      return matchCat && matchQuery;
    });
  }

  _renderLayout() {
    const categories = [
      { id: 'ALL', label: 'All Categories' },
      { id: 'RESEARCH', label: 'Research' },
      { id: 'KNOWLEDGE', label: 'Knowledge' },
      { id: 'DEVELOPER', label: 'Developer & Git' },
      { id: 'AUTOMATION', label: 'Automation' },
      { id: 'BROWSER', label: 'Browser' },
      { id: 'VOICE', label: 'Voice' },
      { id: 'VISION', label: 'Vision' },
      { id: 'COMPUTER', label: 'Computer Control' },
    ];

    const filteredSkills = this._getFilteredSkills();

    return `
      <div class="skills-view-container" role="region" aria-label="Skills & Capabilities Catalog">
        <div class="view-header">
          <div class="header-titles">
            <h1 class="view-title">KAIRO SKILLS &amp; CAPABILITIES</h1>
            <p class="view-subtitle">High-level reusable capabilities orchestrating tools under authoritative SecurityCenter bounds.</p>
          </div>
        </div>

        <!-- Controls Bar -->
        <div class="skills-controls-bar">
          <div class="skills-search-wrapper">
            <input
              type="text"
              class="form-input skills-search-input"
              id="skills-search-input"
              placeholder="Search skills by name, ID, or description (Ctrl+K)..."
              value="${this._escapeHtml(this.searchQuery)}"
              aria-label="Search skills"
            />
          </div>

          <div class="category-pills-scroll skills-category-filters" role="tablist" aria-label="Filter by skill category">
            ${categories.map(cat => `
              <button
                class="category-pill filter-btn ${this.selectedCategory.toLowerCase() === cat.id.toLowerCase() ? 'active' : ''}"
                data-category="${cat.id}"
                role="tab"
                aria-selected="${this.selectedCategory.toLowerCase() === cat.id.toLowerCase()}"
              >${cat.label}</button>
            `).join('')}
          </div>
        </div>

        <!-- Skills Grid -->
        <div class="skills-grid" id="skills-grid">
          ${this.isLoading ? `
            <div class="skills-loading-state">Loading skills catalog...</div>
          ` : filteredSkills.length === 0 ? `
            <div class="skills-empty-state">
              <span class="empty-icon">🧩</span>
              <p>No skills found matching your filters.</p>
            </div>
          ` : filteredSkills.map(skill => this._renderSkillCard(skill)).join('')}
        </div>

        <!-- Detail Modal Container -->
        <div id="skill-detail-modal-root"></div>
      </div>
    `;
  }

  render() {
    this.container.innerHTML = this._renderLayout();
    this._bindEvents();
  }

  _renderSkillCard(skill) {
    const riskLevel = skill.risk_level || 'READ_ONLY';
    const riskBadgeClass = `badge-risk-${riskLevel.toLowerCase().replace(/_/g, '-')}`;
    const healthStatus = skill.health || skill.health_status || 'HEALTHY';
    const healthBadgeClass = `badge-health-${healthStatus.toLowerCase()}`;
    const toolCount = (skill.required_tools?.length || 0) + (skill.optional_tools?.length || 0);

    return `
      <div class="skill-card ${skill.enabled ? 'enabled' : 'disabled'}" data-skill-id="${skill.id}">
        <div class="skill-card-header">
          <div class="skill-ident">
            <div class="skill-title-row">
              <h3 class="skill-name">${this._escapeHtml(skill.name)}</h3>
              <span class="skill-version">v${this._escapeHtml(skill.version)}</span>
            </div>
            <span class="skill-id-code">${this._escapeHtml(skill.id)}</span>
          </div>

          <div class="skill-toggle-wrapper">
            <label class="switch" title="Toggle skill availability">
              <input
                type="checkbox"
                class="skill-toggle-input"
                data-skill-id="${skill.id}"
                ${skill.enabled ? 'checked' : ''}
              />
              <span class="slider"></span>
            </label>
          </div>
        </div>

        <p class="skill-desc">${this._escapeHtml(skill.description)}</p>

        <div class="skill-meta-tags">
          <span class="badge ${riskBadgeClass}">${riskLevel.replace(/_/g, ' ')}</span>
          <span class="badge ${healthBadgeClass}">${healthStatus}</span>
          <span class="badge badge-category">${skill.category}</span>
          ${skill.requires_approval ? '<span class="badge badge-warning">Requires Approval</span>' : ''}
          ${skill.project_scoped ? '<span class="badge badge-scoped">Project Scoped</span>' : ''}
          ${skill.device_scoped ? '<span class="badge badge-scoped">Device Scoped</span>' : ''}
        </div>

        <div class="skill-card-footer">
          <span class="skill-tools-count">${toolCount} tools</span>
          <button class="btn-sm btn-outline inspect-skill-btn" data-skill-id="${skill.id}">
            Inspect Capabilities & Tools
          </button>
        </div>
      </div>
    `;
  }

  _bindEvents() {
    // Search input
    const searchInput = this.container.querySelector('#skills-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value;
        this.render();
      });
    }

    // Category pills
    const pills = this.container.querySelectorAll('.category-pill');
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        this.selectedCategory = pill.dataset.category;
        this.render();
      });
    });

    // Toggle switches
    const toggles = this.container.querySelectorAll('.skill-toggle-input');
    toggles.forEach(toggle => {
      toggle.addEventListener('change', async (e) => {
        const skillId = toggle.dataset.skillId;
        const enabled = toggle.checked;
        try {
          await Endpoints.toggleSkill(skillId, enabled);
          const s = this.skills.find(x => x.id === skillId);
          if (s) s.enabled = enabled;
          this.render();
        } catch (err) {
          console.error('Failed to toggle skill:', err);
          toggle.checked = !enabled; // Revert on failure
        }
      });
    });

    // Inspect buttons
    const inspectBtns = this.container.querySelectorAll('.inspect-skill-btn');
    inspectBtns.forEach(btn => {
      btn.addEventListener('click', async () => {
        const skillId = btn.dataset.skillId;
        await this._openDetailModal(skillId);
      });
    });
  }

  async _openDetailModal(skillId) {
    const root = this.container.querySelector('#skill-detail-modal-root');
    if (!root) return;

    try {
      const detail = await Endpoints.getSkillDetail(skillId);
      const manifest = detail.manifest;

      root.innerHTML = `
        <div class="modal-backdrop" id="skill-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-skill-title">
          <div class="modal-card skill-detail-modal">
            <div class="modal-header">
              <div>
                <h2 class="modal-title" id="modal-skill-title">${this._escapeHtml(manifest.name)}</h2>
                <span class="skill-id-code">${this._escapeHtml(manifest.id)} &bull; v${this._escapeHtml(manifest.version)}</span>
              </div>
              <button class="modal-close-btn" id="close-modal-btn" aria-label="Close modal">&times;</button>
            </div>

            <div class="modal-body">
              <p class="skill-modal-desc">${this._escapeHtml(manifest.description)}</p>

              <div class="modal-section">
                <h4 class="modal-section-title">Security & Risk Classification</h4>
                <div class="meta-row">
                  <span class="badge badge-risk-${manifest.risk_level.toLowerCase()}">Risk: ${manifest.risk_level}</span>
                  <span class="badge badge-health-${detail.health.toLowerCase()}">Health: ${detail.health}</span>
                  <span class="badge badge-category">Category: ${manifest.category}</span>
                </div>
                ${detail.health_reason ? `<p class="health-diagnostic-text">Status note: ${this._escapeHtml(detail.health_reason)}</p>` : ''}
              </div>

              <div class="modal-section">
                <h4 class="modal-section-title">Required Capabilities & Permissions</h4>
                <div class="tags-list">
                  ${manifest.capabilities.length ? manifest.capabilities.map(c => `<span class="tag-item">Gate: ${c}</span>`).join('') : '<span class="text-muted">No external capability gates required.</span>'}
                  ${manifest.permissions.length ? manifest.permissions.map(p => `<span class="tag-item">Perm: ${p}</span>`).join('') : ''}
                </div>
              </div>

              <div class="modal-section">
                <h4 class="modal-section-title">Orchestrated Tools</h4>
                <div class="tools-breakdown">
                  <div><strong>Required:</strong> ${manifest.required_tools.length ? manifest.required_tools.map(t => `<code class="tool-code">${t}</code>`).join(' ') : 'None'}</div>
                  <div style="margin-top: 6px;"><strong>Optional:</strong> ${manifest.optional_tools.length ? manifest.optional_tools.map(t => `<code class="tool-code">${t}</code>`).join(' ') : 'None'}</div>
                </div>
              </div>

              <div class="modal-section">
                <h4 class="modal-section-title">Execution Bounds</h4>
                <ul class="limits-list">
                  <li>Max Steps: <strong>${manifest.execution_limits.max_steps}</strong></li>
                  <li>Execution Timeout: <strong>${manifest.execution_limits.timeout_seconds}s</strong></li>
                  <li>Max Tool Calls: <strong>${manifest.execution_limits.max_tool_calls}</strong></li>
                </ul>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn btn-outline" id="modal-dismiss-btn">Close</button>
            </div>
          </div>
        </div>
      `;

      const closeModal = () => { root.innerHTML = ''; };
      root.querySelector('#close-modal-btn')?.addEventListener('click', closeModal);
      root.querySelector('#modal-dismiss-btn')?.addEventListener('click', closeModal);
      root.querySelector('#skill-modal-backdrop')?.addEventListener('click', (e) => {
        if (e.target.id === 'skill-modal-backdrop') closeModal();
      });

      const keyHandler = (e) => {
        if (e.key === 'Escape') {
          closeModal();
          document.removeEventListener('keydown', keyHandler);
        }
      };
      document.addEventListener('keydown', keyHandler);

    } catch (err) {
      console.error('Failed to load skill details:', err);
    }
  }

  _escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

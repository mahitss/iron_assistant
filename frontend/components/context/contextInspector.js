/**
 * ContextInspector Component
 * Explains "Why Kairo used this context" with human-readable provenance explanations without raw mathematical formulas.
 */

import { store } from '../../state/store.js';

export class ContextInspector {
  constructor(options = {}) {
    this.store = options.store || store;
  }

  render() {
    const state = this.store.getState();
    const isOpen = state.contextInspectorOpen;
    if (!isOpen) return '';

    const packet = state.contextPacket;
    const activeProject = state.activeProject;
    const items = packet && packet.items ? packet.items : [];

    return `
      <div class="modal-overlay" onclick="window.kairoApp.closeContextInspector()" role="presentation">
        <div class="context-inspector-drawer" onclick="event.stopPropagation()" role="dialog" aria-modal="true" aria-label="Context Inspector">
          <div class="drawer-header">
            <div class="drawer-title-group">
              <span class="drawer-icon">🧠</span>
              <h3 class="drawer-title">WHY KAIRO USED THIS CONTEXT</h3>
            </div>
            <button class="drawer-close-btn" onclick="window.kairoApp.closeContextInspector()" aria-label="Close drawer">&times;</button>
          </div>

          <div class="drawer-body">
            <!-- Active Project Association -->
            <div class="context-section">
              <div class="context-section-label">ANCHOR WORKSPACE</div>
              ${activeProject ? `
                <div class="context-card active-project-card">
                  <div class="card-main-title">Project: ${this._escapeHtml(activeProject.name)}</div>
                  <div class="card-meta">Status: <span class="status-pill status-${activeProject.status.toLowerCase()}">${activeProject.status}</span></div>
                  ${activeProject.repositories && activeProject.repositories.length > 0 ? `
                    <div class="card-repo">Linked Repository: <code>${this._escapeHtml(activeProject.repositories[0])}</code></div>
                  ` : ''}
                  <div class="provenance-note">Selected because this project is currently pinned as your active workspace.</div>
                </div>
              ` : `
                <div class="context-card empty">
                  <div>No specific project workspace pinned. Running in general session mode.</div>
                </div>
              `}
            </div>

            <!-- Aggregated Context Items with Provenance -->
            <div class="context-section">
              <div class="context-section-label">RETRIEVED CONTEXT ELEMENTS (${items.length})</div>
              ${items.length === 0 ? `
                <div class="context-card empty">
                  <div>No external context required for this turn. Kairo used direct conversational session memory.</div>
                </div>
              ` : items.map(item => `
                <div class="context-card item-card">
                  <div class="context-card-top">
                    <span class="context-source-badge ${this._badgeClass(item.source_type)}">${item.source_type}</span>
                    <span class="context-timestamp">${this._formatTime(item.timestamp)}</span>
                  </div>
                  <div class="context-item-title">${this._escapeHtml(item.title)}</div>
                  <div class="context-item-content">${this._escapeHtml(item.content)}</div>
                  <div class="context-item-reason">
                    <span class="reason-icon">💡</span>
                    <span>Reason: ${this._escapeHtml(item.reason || 'Relevant to active task')}</span>
                  </div>
                </div>
              `).join('')}
            </div>

            <!-- Bounded Guarantees Box -->
            <div class="privacy-guarantee-box">
              <div class="guarantee-title">🔒 Privacy & Bounding Guarantees</div>
              <div class="guarantee-text">
                Kairo's Context Engine provides task-relevant context; it does not create unrestricted user profiles.
                Context items are bounded (max 30 total), sanitized against secrets and prompt injections, and strictly isolated to your user account.
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _badgeClass(sourceType) {
    if (!sourceType) return '';
    const s = sourceType.toLowerCase();
    if (s.includes('project')) return 'badge-project';
    if (s.includes('memory')) return 'badge-memory';
    if (s.includes('workflow')) return 'badge-workflow';
    if (s.includes('developer')) return 'badge-developer';
    if (s.includes('session')) return 'badge-session';
    return 'badge-default';
  }

  _formatTime(ts) {
    if (!ts) return '';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

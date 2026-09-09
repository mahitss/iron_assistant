/**
 * Command Palette Component (Ctrl+K / Cmd+K)
 * Fast, accessible modal for jumping between views and executing actions.
 */

import { store } from '../../state/store.js';

export class CommandPalette {
  constructor(options = {}) {
    this.store = options.store || store;
    this.commands = [
      { id: 'nav-home', label: 'Go to Home Dashboard', category: 'Navigation', icon: '📊', action: () => window.kairoApp.navigateTo('home') },
      { id: 'nav-chat', label: 'Go to Chat', category: 'Navigation', icon: '💬', action: () => window.kairoApp.navigateTo('chat') },
      { id: 'nav-projects', label: 'Open Projects Workspace', category: 'Navigation', icon: '📁', action: () => window.kairoApp.navigateTo('projects') },
      { id: 'nav-automations', label: 'View Automations & Workflows', category: 'Navigation', icon: '⚡', action: () => window.kairoApp.navigateTo('automations') },
      { id: 'nav-activity', label: 'View Activity Timeline', category: 'Navigation', icon: '⏱️', action: () => window.kairoApp.navigateTo('activity') },
      { id: 'nav-security', label: 'Open Security Center', category: 'Navigation', icon: '🛡️', action: () => window.kairoApp.navigateTo('security') },
      { id: 'nav-knowledge', label: 'Explore Knowledge Fabric', category: 'Navigation', icon: '🌐', action: () => window.kairoApp.navigateTo('knowledge') },
      { id: 'nav-memory', label: 'Inspect Memory Center', category: 'Navigation', icon: '🧠', action: () => window.kairoApp.navigateTo('memory') },
      { id: 'nav-notifications', label: 'Open Notifications', category: 'Navigation', icon: '🔔', action: () => window.kairoApp.navigateTo('notifications') },
      { id: 'nav-status', label: 'Check System Status', category: 'Navigation', icon: '📈', action: () => window.kairoApp.navigateTo('status') },
      { id: 'nav-settings', label: 'Open Settings', category: 'Navigation', icon: '⚙️', action: () => window.kairoApp.navigateTo('settings') },
      { id: 'act-new-chat', label: 'New Conversation', category: 'Action', icon: '✨', action: () => { window.kairoApp.newChat(); window.kairoApp.navigateTo('chat'); } },
      { id: 'act-context', label: 'Inspect Current Context', category: 'Action', icon: '🔍', action: () => window.kairoApp.openContextInspector() },
      { id: 'act-emergency', label: 'EMERGENCY STOP (Halt All Actions)', category: 'Security', icon: '🛑', action: () => window.kairoApp.confirmEmergencyStop() },
    ];
    this.query = '';
    this.selectedIndex = 0;
  }

  render() {
    const isOpen = this.store.getState().commandPaletteOpen;
    if (!isOpen) return '';

    const filtered = this.getFilteredCommands();

    return `
      <div class="modal-overlay" onclick="window.kairoApp.closeCommandPalette()" role="presentation">
        <div class="command-palette-modal" onclick="event.stopPropagation()" role="dialog" aria-modal="true" aria-label="Command Palette">
          <div class="palette-search-bar">
            <span class="palette-search-icon">🔍</span>
            <input
              type="text"
              id="paletteInput"
              class="palette-input"
              placeholder="Type a command or jump to view..."
              value="${this._escapeHtml(this.query)}"
              oninput="window.kairoApp.onPaletteSearch(this.value)"
              onkeydown="window.kairoApp.onPaletteKeyDown(event)"
              autocomplete="off"
              autofocus
            />
            <kbd class="palette-esc-kbd" onclick="window.kairoApp.closeCommandPalette()">Esc</kbd>
          </div>

          <div class="palette-results" id="paletteResults" role="listbox">
            ${filtered.length === 0 ? `
              <div class="palette-empty">No matching commands found</div>
            ` : filtered.map((cmd, idx) => `
              <div
                class="palette-item ${idx === this.selectedIndex ? 'selected' : ''}"
                onclick="window.kairoApp.executePaletteCommand('${cmd.id}')"
                role="option"
                aria-selected="${idx === this.selectedIndex}"
                data-index="${idx}"
              >
                <span class="cmd-icon">${cmd.icon}</span>
                <span class="cmd-label">${this._escapeHtml(cmd.label)}</span>
                <span class="cmd-category">${cmd.category}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  getFilteredCommands() {
    if (!this.query.trim()) return this.commands;
    const q = this.query.toLowerCase();
    return this.commands.filter(c => c.label.toLowerCase().includes(q) || c.category.toLowerCase().includes(q));
  }

  setQuery(q) {
    this.query = q;
    this.selectedIndex = 0;
  }

  moveSelection(delta) {
    const total = this.getFilteredCommands().length;
    if (total === 0) return;
    this.selectedIndex = (this.selectedIndex + delta + total) % total;
  }

  getSelectedCommand() {
    const filtered = this.getFilteredCommands();
    return filtered[this.selectedIndex] || null;
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

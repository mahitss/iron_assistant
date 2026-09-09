/**
 * Composer Component — Chat Message Input & Action Bar (Task 30)
 * Unified Multimodal Composer supporting:
 * [＋] [Image] [File] [Voice] and visibly separated [Share Screen].
 * Pre-send media preview with remove and replace controls (Specs 81-84).
 */

import { store } from '../../state/store.js';

export class Composer {
  constructor(options = {}) {
    this.store = options.store || store;
    this.attachment = null;
    this.screenContextActive = false;
    this.activeDeviceId = 'companion-desktop-primary';
  }

  render() {
    const state = this.store.getState();
    const isStreaming = state.isStreaming;

    return `
      <div class="composer-box">
        <!-- Pre-Send Media Preview Bar (Spec 83) -->
        ${(this.attachment || this.screenContextActive) ? `
          <div class="attachment-preview-bar" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.75rem; background: rgba(255, 255, 255, 0.04); border-bottom: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.8rem;">
            ${this.attachment ? `
              <div class="attachment-chip" style="display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 0.2rem 0.5rem;">
                <span class="attachment-icon">${this._getModalityIcon(this.attachment.type)}</span>
                <span class="attachment-name" style="font-weight: 500; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  ${this._escapeHtml(this.attachment.name)}
                </span>
                <span style="font-size: 0.7rem; color: var(--text-muted);">${this._formatSize(this.attachment.size)}</span>
                <button type="button" class="btn-replace" onclick="window.kairoApp?.replaceComposerAttachment?.()" style="background: none; border: none; cursor: pointer; color: #38bdf8; font-size: 0.75rem; padding: 0 0.2rem;" title="Replace attachment">🔄</button>
                <button type="button" class="attachment-remove-btn" onclick="window.kairoApp?.removeComposerAttachment?.()" style="background: none; border: none; cursor: pointer; color: #f87171; font-size: 1rem; line-height: 1; padding: 0 0.2rem;" aria-label="Remove attachment">&times;</button>
              </div>
            ` : ''}

            ${this.screenContextActive ? `
              <div class="screen-context-badge" style="display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 6px; padding: 0.2rem 0.5rem; color: #f59e0b;">
                <span>🖥️</span>
                <span>Screen Sharing Active</span>
                <span style="font-size: 0.7rem; opacity: 0.8;">(${this._escapeHtml(this.activeDeviceId)})</span>
                <button type="button" onclick="window.kairoApp?.toggleScreenShare?.(false)" style="background: none; border: none; cursor: pointer; color: #f87171; font-size: 1rem; line-height: 1; padding: 0 0.2rem;" aria-label="Stop screen sharing">&times;</button>
              </div>
            ` : ''}
          </div>
        ` : ''}

        <form class="composer-form" id="chatComposerForm" onsubmit="window.kairoApp?.handleComposerSubmit?.(event)">
          <!-- Unified Multimodal Action Bar (Spec 81) -->
          <div class="composer-action-group" style="display: inline-flex; align-items: center; gap: 0.25rem;">
            <!-- [＋] Add / Options button -->
            <button
              type="button"
              class="composer-btn"
              id="multimodalMenuBtn"
              title="Add media or document"
              onclick="window.kairoApp?.toggleAttachmentMenu?.()"
              aria-label="Add Media"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            </button>

            <!-- [Image] Attachment Trigger -->
            <label class="composer-btn attachment-btn" title="Attach Image" aria-label="Attach Image">
              <input type="file" id="imageAttachmentInput" accept="image/*" style="display: none;" onchange="window.kairoApp?.handleImageAttach?.(event)" />
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
            </label>

            <!-- [File] Document Trigger -->
            <label class="composer-btn file-btn" title="Attach Document (PDF, DOCX, TXT, JSON)" aria-label="Attach Document">
              <input type="file" id="docAttachmentInput" accept=".pdf,.docx,.txt,.md,.json,.csv" style="display: none;" onchange="window.kairoApp?.handleDocumentAttach?.(event)" />
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            </label>

            <!-- [Voice] Trigger -->
            <button
              type="button"
              class="composer-btn voice-btn"
              id="voiceBtn"
              onclick="window.kairoApp?.openVoiceModal?.()"
              title="Voice input (Push to talk)"
              aria-label="Start Voice Interaction"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
            </button>

            <!-- [Share Screen] Visibly Separate Button (Spec 82) -->
            <button
              type="button"
              class="composer-btn screen-btn ${this.screenContextActive ? 'active' : ''}"
              id="screenShareBtn"
              onclick="window.kairoApp?.toggleScreenShare?.()"
              title="${this.screenContextActive ? 'Screen capture active - Click to stop' : 'Share Screen with Kairo'}"
              style="${this.screenContextActive ? 'color: #f59e0b; background: rgba(245, 158, 11, 0.2);' : ''}"
              aria-label="Share Desktop Screen"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
            </button>
          </div>

          <!-- Main Input Field -->
          <textarea
            id="chatComposerTextarea"
            class="composer-textarea"
            placeholder="Ask Kairo, paste images, or query documents... (Shift+Enter for newline)"
            rows="1"
            onkeydown="window.kairoApp?.handleComposerKeyDown?.(event)"
            ${isStreaming ? 'disabled' : ''}
            autocomplete="off"
          ></textarea>

          <!-- Submit Button -->
          <button
            type="submit"
            class="composer-send-btn ${isStreaming ? 'disabled' : ''}"
            id="composerSendBtn"
            aria-label="Send message"
            ${isStreaming ? 'disabled' : ''}
          >
            ${isStreaming ? `
              <span class="btn-spinner"></span>
            ` : `
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            `}
          </button>
        </form>
      </div>
    `;
  }

  setAttachment(file, type = 'image') {
    this.attachment = {
      name: file.name || 'file',
      size: file.size || 0,
      type: type,
      rawFile: file,
    };
  }

  clearAttachment() {
    this.attachment = null;
  }

  setScreenContext(active = true, deviceId = 'companion-desktop-primary') {
    this.screenContextActive = active;
    this.activeDeviceId = deviceId;
  }

  _getModalityIcon(type) {
    if (type === 'document') return '📄';
    if (type === 'audio') return '🎙️';
    if (type === 'video') return '🎬';
    return '🖼️';
  }

  _formatSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

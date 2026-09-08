/**
 * Composer Component — Chat Message Input & Action Bar
 * Supports text messaging, streaming status, explicit push-to-talk voice toggle, and image attachment preview.
 */

import { store } from '../../state/store.js';

export class Composer {
  constructor(options = {}) {
    this.store = options.store || store;
    this.attachment = null;
  }

  render() {
    const isStreaming = this.store.getState().isStreaming;

    return `
      <div class="composer-box">
        <!-- Optional Image Attachment Preview -->
        ${this.attachment ? `
          <div class="attachment-preview-bar">
            <div class="attachment-chip">
              <span class="attachment-icon">🖼️</span>
              <span class="attachment-name">${this._escapeHtml(this.attachment.name)}</span>
              <button class="attachment-remove-btn" onclick="window.kairoApp.removeComposerAttachment()" aria-label="Remove attachment">&times;</button>
            </div>
          </div>
        ` : ''}

        <form class="composer-form" id="chatComposerForm" onsubmit="window.kairoApp.handleComposerSubmit(event)">
          <!-- Attachment Trigger (Vision) -->
          <label class="composer-btn attachment-btn" title="Attach image for visual inspection" aria-label="Attach Image">
            <input type="file" id="imageAttachmentInput" accept="image/*" style="display: none;" onchange="window.kairoApp.handleImageAttach(event)" />
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
          </label>

          <!-- Main Input Field -->
          <textarea
            id="chatComposerTextarea"
            class="composer-textarea"
            placeholder="Ask Kairo anything or give an instruction... (Shift+Enter for newline)"
            rows="1"
            onkeydown="window.kairoApp.handleComposerKeyDown(event)"
            ${isStreaming ? 'disabled' : ''}
            autocomplete="off"
          ></textarea>

          <!-- Voice Input Trigger (Explicit Activation) -->
          <button
            type="button"
            class="composer-btn voice-btn"
            onclick="window.kairoApp.openVoiceModal()"
            title="Voice input (Click to talk)"
            aria-label="Start Voice Interaction"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
          </button>

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

  setAttachment(file) {
    this.attachment = file;
  }

  clearAttachment() {
    this.attachment = null;
  }

  _escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
